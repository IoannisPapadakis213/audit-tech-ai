# Audit Tech AI: Προδιαγραφές και αρχιτεκτονική

## 1. Στόχος

Εφαρμογή **Journal Entry Testing (ISA 240)** για τη θέση Data Analyst – Assurance στην Deloitte.

Η εφαρμογή:
1. Παίρνει το **Γενικό Καθολικό (GL)** του πελάτη.
2. Αποδεικνύει πρώτα ότι είναι **πλήρες** (συμφωνία με το Ισοζύγιο).
3. **Απομονώνει** τα κακά δεδομένα.
4. Εφαρμόζει **κανόνες ISA 240, στατιστική και ML**.
5. Δίνει στον ελεγκτή μια **μικρή, ιεραρχημένη λίστα** εγγραφών υψηλού κινδύνου, με **πλήρη αναπαραγωγιμότητα**.

---

## 2. Αρχιτεκτονική (ροή)

```
ERP πελάτη (SoftOne / SAP / Entersoft: GL + Ισοζύγιο)
 │
 ├─ 1. Ingestion     Azure Data Factory ή Fabric pipeline, mapping στηλών σε κοινό σχήμα
 ├─ 2. Data Quality  καραντίνα με λόγο, ισοσκελισμός, συμφωνία GL ↔ Ισοζύγιο (αν αποτύχει → STOP)
 ├─ 3. Transform     is_weekend, is_holiday, is_after_hours, days_to_period_end,
 │                   is_round_amount, is_manual
 ├─ 4. Αποθήκευση    SQLite (τοπικά) → Azure SQL → Databricks / Fabric Lakehouse
 │                   (medallion bronze / silver / gold)
 ├─ 5. Ανίχνευση     κανόνες SQL + Benford + robust z-score + Isolation Forest
 ├─ 6. Risk Score    βάρος ανά κανόνα, score ≥ 6 → λίστα ελεγκτή
 │
 └─ Έξοδοι (ίδια βάση, single source of truth)
     ├─ 7. Power BI report (κύρια αναφορά ελεγκτή)
     ├─ 8. FastAPI → React dashboard + AI chatbot
     └─ 9. Export σε Excel για working papers

Όλα μέσα σε Azure: Entra ID, Key Vault, App Service, logs, περιοχή ΕΕ (GDPR)
```

---

## 3. Κοινό σχήμα GL (στόχος)

| Στήλη | Περιγραφή |
|---|---|
| `journal_id` | Αναγνωριστικό άρθρου (journal) |
| `line_id` | Αριθμός γραμμής μέσα στο άρθρο |
| `posting_date` | Λογιστική ημερομηνία |
| `entry_datetime` | Πότε καταχωρήθηκε πραγματικά στο σύστημα |
| `account` | Λογαριασμός |
| `debit` | Χρέωση |
| `credit` | Πίστωση |
| `created_by` | Χρήστης που καταχώρησε |
| `approved_by` | Χρήστης που ενέκρινε |
| `source` | `Manual` / `Automatic` |
| `description` | Αιτιολογία |
| `vendor_id` | Προμηθευτής |

- Κάθε journal έχει **πολλές γραμμές** και πρέπει **Χρεώσεις = Πιστώσεις**.
- Ο generator φτιάχνει και **`trial_balance`**: υπόλοιπο αρχής, κινήσεις, υπόλοιπο τέλους ανά λογαριασμό.

---

## 4. Config (`config.py`)

```python
CLIENT_NAME = "Aigaio Emporio SA"
FISCAL_YEAR_START = "2025-01-01"
FISCAL_YEAR_END = "2025-12-31"
POST_CLOSE_END = "2026-02-28"

OVERALL_MATERIALITY = 500_000
PERFORMANCE_MATERIALITY = 375_000
CLEARLY_TRIVIAL = 25_000

WORK_HOURS = (8, 18)
GREEK_HOLIDAYS_2025 = [
    "2025-01-01", "2025-01-06", "2025-03-03", "2025-03-25",
    "2025-04-18", "2025-04-21", "2025-05-01", "2025-06-09",
    "2025-08-15", "2025-10-28", "2025-12-25", "2025-12-26",
]

SYSTEM_USERS = ["SYS_BATCH", "SYS_PAYROLL"]          # εξαιρούνται από weekend / after-hours
AUTHORIZED_POSTERS = ["ACC_01", "ACC_02", "ACC_03", "ACC_04", "FIN_MGR"]
SENIOR_MANAGEMENT = ["CFO", "CEO"]

PERIOD_END_WINDOW_DAYS = 10
ROUND_AMOUNT_MIN = 10_000
ROUND_AMOUNT_MODULO = 1_000
DUPLICATE_WINDOW_DAYS = 7
RARE_ACCOUNT_MAX_USES = 5

ROBUST_Z_THRESHOLD = 3.5                               # διάμεσος + MAD
BENFORD_MIN_AMOUNT = 10
BENFORD_MAD_LIMITS = {"close": 0.006, "acceptable": 0.012, "marginal": 0.015}

ISOLATION_FOREST = {"n_estimators": 200, "contamination": 0.01, "random_state": 42}

RULE_WEIGHTS = {
    "post_close": 5,
    "senior_mgmt_user": 5,
    "unauthorized_user": 4,
    "period_end_manual": 3,
    "duplicate": 3,
    "round_amount": 2,
    "weekend_holiday": 2,
    "rare_account": 2,
    "robust_z_outlier": 2,
    "isolation_forest": 2,
    "after_hours": 1,
    "no_description": 1,
}
RISK_SCORE_THRESHOLD = 6
```

---

## 5. Έλεγχοι Data Quality

1. Πληρότητα πεδίων
2. Διπλά IDs
3. Ημερομηνίες εκτός χρήσης / post-close
4. Άγνωστοι λογαριασμοί
5. Ισοσκελισμός ανά journal
6. Συμφωνία GL ↔ Ισοζύγιο (rollforward)

- Καραντίνα → `dq_report.xlsx`.
- **Ποτέ σβήσιμο ή αυτόματη διόρθωση.**

---

## 6. Κανόνες ανίχνευσης

| Κανόνας | Βάρος |
|---|---|
| `post_close` | 5 |
| `senior_mgmt_user` | 5 |
| `unauthorized_user` | 4 |
| `period_end_manual` | 3 |
| `duplicate` | 3 |
| `round_amount` | 2 |
| `weekend_holiday` | 2 |
| `rare_account` | 2 |
| `robust_z_outlier` (ανά λογαριασμό) | 2 |
| `isolation_forest` | 2 |
| `after_hours` | 1 |
| `no_description` | 1 |
| **Benford** (σε όλο το GL και ανά χρήστη, MAD Nigrini) | ανάλυση πληθυσμού |

Κάθε hit γράφεται στον πίνακα **`rule_hits`** (`journal_id`, `rule`, `weight`).

---

## 7. Power BI

- **Star schema:** `fact_journal_lines`, `fact_rule_hits`, `dim_date`, `dim_user`, `dim_account`, `dim_digit`, `trial_balance`.
- **DAX measures:** High Risk Entries, % Manual Entries, Benford Expected %, Benford MAD, GL vs TB Difference.
- **Σελίδες:**
  1. Σύνοψη + χωνί
  2. Ποιότητα δεδομένων
  3. Χάρτης θερμότητας ημέρα × ώρα
  4. Χρήστες
  5. Benford
  6. Λίστα υψηλού κινδύνου με drill-through + export
- **RLS** ανά πελάτη.
- **Στο repo:** `.pbix` (μόνο συνθετικά δεδομένα), screenshots στο README, αρχείο με τα DAX.
- **Περιβάλλον:** Mac, άρα Power BI Desktop μέσω Windows VM ή Power BI Service / Fabric στον browser.

---

## 8. API / Frontend / AI

- **FastAPI:** `/anomalies`, `/stats`, `/dq-report`, `/chat`.
- **React (Vite):** dashboard + chatbot με Gemini.
- **Ιδιωτικότητα:** το chatbot στέλνει στο LLM **μόνο την ερώτηση και συγκεντρωτικά αποτελέσματα**, όχι όλο το GL.
- **Σε παραγωγή:** Azure OpenAI μέσα στο tenant.

---

## 9. Azure / Databricks / Fabric

| Υπηρεσία | Ρόλος |
|---|---|
| Data Factory | Λήψη δεδομένων |
| Blob Storage | Αρχικά αρχεία |
| Azure SQL | Αποτελέσματα |
| App Service | API + React |
| Key Vault | Μυστικά |
| Entra ID | Ταυτοποίηση |
| Power BI Service | Αναφορές |

- **Databricks:** το ίδιο pipeline σε PySpark, medallion bronze / silver / gold.
- **Fabric:** notebook → Lakehouse → Power BI με Direct Lake.

---

## 10. Αναπαραγωγιμότητα

Κάθε run γράφει **run log**: `run_id`, `git_commit`, `config_hash`, `input_file_hash`, `random_state`.

---

## 11. Roadmap

- [x] **Φάση 1:** ETL, Data Quality, SQL κανόνες, 13 tests
- [ ] **Φάση 2:** σχήμα με debit/credit + trial balance, Benford, robust z-score, Isolation Forest, Risk Score, run log
- [ ] **Φάση 3:** Power BI report
- [ ] **Φάση 4:** FastAPI
- [ ] **Φάση 5:** React + AI chatbot
- [ ] **Φάση 6:** Azure
- [ ] **Φάση 7:** Databricks / Fabric

### Εκκρεμότητες
- Σβήσιμο των παλιών αρχείων στη ρίζα (`db_setup.py`, `audit_sql_queries.py`, `audit_data.db`, `data_generator.py`).
- Ανέβασμα στο GitHub ως `audit-tech-ai`.
