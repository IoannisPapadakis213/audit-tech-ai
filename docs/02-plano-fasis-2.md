# Πλάνο Φάσης 2 (προς έγκριση)

> Σχήμα με debit/credit + Ισοζύγιο, Benford, robust z-score, Isolation Forest, Risk Score, run log.
> Βάση: `docs/01-arxitektoniki.md`.

---

## 1. Η βασική απόφαση: πώς μένουν πράσινα τα 13 tests

Το νέο σχήμα (journals με χρεώσεις/πιστώσεις, χρήση 2025) είναι **ασύμβατο** με της Φάσης 1
(μία γραμμή = ένα ποσό, χρήση 2023). Αν άλλαζα τα υπάρχοντα modules, τα 13 tests θα έσπαγαν.

**Πρόταση:** χτίζουμε τη Φάση 2 ως **νέο sub-package `audit_ai/jet/`**, δίπλα στον υπάρχοντα κώδικα.

```
backend/audit_ai/
├── config.py            ← προσθέτουμε νέα ενότητα "Φάση 2", ΔΕΝ αλλάζουμε τα υπάρχοντα
├── data_generator.py    ┐
├── data_quality.py      │  Φάση 1: μένουν ως έχουν (και τα 13 tests τους)
├── etl.py               │
├── audit_queries.py     ┘
└── jet/                 ← ΝΕΟ: Φάση 2
    ├── generator.py     journals + trial balance + ground truth
    ├── data_quality.py  6 έλεγχοι, STOP, dq_report.xlsx
    ├── transform.py     παράγωγες στήλες
    ├── rules.py         12 κανόνες → rule_hits
    ├── benford.py       πρώτο ψηφίο, MAD Nigrini, συνολικά και ανά χρήστη
    ├── ml.py            robust z-score + Isolation Forest
    ├── scoring.py       risk score + λίστα ελεγκτή
    ├── run_log.py       run_id, git_commit, config_hash, input_file_hash, random_state
    └── pipeline.py      python -m audit_ai.jet
```

**Γιατί:** μηδέν διαγραφές, και η Φάση 1 μένει ως «v1» στο ιστορικό. Μόλις η v2 καλύψει τα πάντα,
αποφασίζεις εσύ αν η v1 θα μείνει ή θα αποσυρθεί.

---

## 2. Generator (`jet/generator.py`)

**Λογιστικό σχέδιο** (~15 λογαριασμοί σε στυλ ΕΓΛΣ, με τύπο για το Ισοζύγιο):
Ταμείο/Τράπεζες (38), Πελάτες (30), Αποθέματα (20), Πάγια (14), Προμηθευτές (50),
ΦΠΑ (54), Υποχρεώσεις μισθοδοσίας (53), Κεφάλαιο (40), Πωλήσεις (70), Αγορές (60–64),
Μισθοδοσία (60), Αποσβέσεις (66), Αμοιβές τρίτων (61) κ.λπ.

**Τύποι journals** (όλα ισοσκελισμένα: Χ = Π):

| Τύπος | Παράδειγμα γραμμών | Χρήστης | Source |
|---|---|---|---|
| Τιμολόγιο πώλησης | Χ Πελάτες / Π Πωλήσεις / Π ΦΠΑ | ACC_xx | Automatic |
| Τιμολόγιο αγοράς | Χ Αγορές / Χ ΦΠΑ / Π Προμηθευτές | ACC_xx | Automatic |
| Πληρωμή / είσπραξη | Χ Προμηθευτές / Π Τράπεζα | ACC_xx | Manual |
| Μισθοδοσία (μηνιαία) | Χ Μισθοδοσία / Π Υποχρ. / Π Τράπεζα | SYS_PAYROLL | Automatic |
| Αποσβέσεις (μηνιαίες) | Χ Αποσβέσεις / Π Πάγια | SYS_BATCH | Automatic |
| Χειροκίνητη εγγραφή | Προβλέψεις, διορθώσεις | ACC_xx / FIN_MGR | Manual |

- **Μέγεθος:** περίπου 3.000 journals, δηλαδή περίπου 9.000 γραμμές.
- **Ποσά:** lognormal, ώστε να ισχύει ο Benford.
- **Ισοζύγιο:** υπόλοιπο αρχής + κινήσεις GL = υπόλοιπο τέλους, ανά λογαριασμό.

**Φυτεμένες ανωμαλίες** (ground truth σε επίπεδο journal), μία ομάδα για κάθε κανόνα:
- post-close καταχώρηση (entry Ιαν–Φεβ 2026, posting Δεκ 2025)
- χρήστης CFO/CEO
- μη εξουσιοδοτημένος χρήστης
- χειροκίνητη εγγραφή κοντά στο κλείσιμο
- διπλή πληρωμή
- στρογγυλό ποσό
- Σαββατοκύριακο / αργία
- σπάνιος λογαριασμός
- ακραίο ποσό
- εκτός ωραρίου
- κενή αιτιολογία

Σε μερικά journals φυτεύουμε **πολλές σημαίες μαζί** (π.χ. CFO + Κυριακή + στρογγυλό + post-close),
ώστε να ξεπερνούν το score 6. Αυτά είναι η «βελόνα στα άχυρα» που πρέπει να βρει ο ελεγκτής.

**Benford σενάριο:** ο χρήστης `ACC_04` καταχωρεί επινοημένα ποσά λίγο κάτω από το όριο έγκρισης
(π.χ. 4.8xx–4.9xx €). Ο Benford ανά χρήστη πρέπει να τον εντοπίσει, ενώ ο συνολικός Benford μένει «close».

**Βρώμικα δεδομένα** για το DQ: κενά πεδία, διπλό line ID, ημερομηνία εκτός χρήσης, άγνωστος λογαριασμός,
ένα **μη ισοσκελισμένο** journal.

Με παράμετρο `break_tb=True` το Ισοζύγιο δεν συμφωνεί (για το test του STOP).

---

## 3. Data Quality (`jet/data_quality.py`)

| # | Έλεγχος | Αποτέλεσμα αν αποτύχει |
|---|---|---|
| 1 | Πληρότητα πεδίων | Καραντίνα |
| 2 | Διπλά IDs (`journal_id` + `line_id`) | Καραντίνα |
| 3 | `posting_date` εκτός χρήσης / `entry_datetime` μετά το POST_CLOSE_END | Καραντίνα |
| 4 | Άγνωστος λογαριασμός | Καραντίνα |
| 5 | Ισοσκελισμός ανά journal (Σ Χ = Σ Π) | Καραντίνα **ολόκληρου** του journal |
| 6 | Συμφωνία GL ↔ Ισοζύγιο (rollforward) | **STOP** (`ReconciliationError`) |

- **Απόφαση προς έγκριση:** ο έλεγχος 6 τρέχει στο **πλήρες** GL, πριν την καραντίνα. Ελέγχει αν
  το extract είναι **πλήρες** (completeness), όχι αν είναι καθαρό. Αν τον τρέχαμε μετά την καραντίνα,
  δεν θα συμφωνούσε ποτέ.
- **Ανοχή:** διαφορά ≤ 0,01 € ανά λογαριασμό (στρογγυλοποιήσεις).
- **Έξοδος:** `dq_report.xlsx` με φύλλα «Σύνοψη», «Καραντίνα», «Συμφωνία GL-TB». Και οι ίδιοι πίνακες στη βάση.
- Ποτέ σβήσιμο ή αυτόματη διόρθωση.

---

## 4. Transform (`jet/transform.py`)

`is_weekend`, `is_holiday`, `is_after_hours` (με βάση το `entry_datetime`, εξαιρούνται οι SYSTEM_USERS),
`days_to_period_end`, `is_round_amount`, `is_manual`, `amount = |debit − credit|`.

---

## 5. Κανόνες (`jet/rules.py`)

Οι 12 κανόνες ελέγχουν γραμμές και ανεβαίνουν σε επίπεδο **journal**. Στον πίνακα `rule_hits`
γράφεται μία γραμμή ανά (journal, κανόνα), ώστε ένας κανόνας να μετράει **μία φορά** ανά journal.

| Κανόνας | Ορισμός |
|---|---|
| `post_close` | `entry_datetime` > FISCAL_YEAR_END και `posting_date` ≤ FISCAL_YEAR_END |
| `senior_mgmt_user` | `created_by` ∈ SENIOR_MANAGEMENT |
| `unauthorized_user` | `created_by` ∉ AUTHORIZED_POSTERS ∪ SYSTEM_USERS ∪ SENIOR_MANAGEMENT |
| `period_end_manual` | Manual και `days_to_period_end` ≤ 10 (τέλος μήνα) |
| `duplicate` | Ίδιος λογαριασμός + ποσό + vendor, άλλο journal, μέσα σε 7 ημέρες |
| `round_amount` | Ποσό ≥ 10.000 και πολλαπλάσιο του 1.000 |
| `weekend_holiday` | ΣΚ ή αργία (όχι SYSTEM_USERS) |
| `rare_account` | Λογαριασμός με ≤ 5 χρήσεις στη χρήση |
| `robust_z_outlier` | Βλ. §7 |
| `isolation_forest` | Βλ. §7 |
| `after_hours` | Εκτός 08:00–18:00 (όχι SYSTEM_USERS) |
| `no_description` | Κενή αιτιολογία |

- Οι κανόνες γράφονται σε **SQL** (με window functions όπου ταιριάζει), ώστε να μεταφέρονται αυτούσιοι σε Azure SQL / Databricks SQL.
- Τα ML κομμάτια γράφονται σε Python.
- **Ερώτηση:** το `period_end_manual` το ορίζω ως **τέλος μήνα**. Αν το θέλεις μόνο για το **τέλος χρήσης** (Δεκέμβριος), πες μου.

---

## 6. Benford (`jet/benford.py`)

- Πρώτο ψηφίο, για ποσά ≥ BENFORD_MIN_AMOUNT.
- **MAD Nigrini** σε σύγκριση με τα BENFORD_MAD_LIMITS → close / acceptable / marginal / nonconformity.
- **Συνολικά** και **ανά χρήστη**. Για χρήστες με < 300 γραμμές το αποτέλεσμα σημειώνεται «ανεπαρκές δείγμα» (ο Nigrini προτείνει ≥ 1.000).
- Ο Benford είναι **ανάλυση πληθυσμού**, όχι κανόνας ανά εγγραφή, γι' αυτό δεν έχει βάρος.
  Αποθηκεύεται στους πίνακες `benford_overall` και `benford_by_user`, και αργότερα γίνεται `dim_digit` στο Power BI.

---

## 7. Στατιστική και ML (`jet/ml.py`)

**Robust z-score** ανά λογαριασμό: `z = 0,6745 · (x − διάμεσος) / MAD`, με κατώφλι |z| > 3,5 (Iglewicz & Hoaglin).
- **Απόφαση προς έγκριση:** το υπολογίζω στο **log10(ποσού)**. Τα ποσά είναι lognormal, άρα σε απλή κλίμακα
  ο κανόνας θα σημάδευε όλη την «ουρά» (το πρόβλημα με τα 557 της Φάσης 1). Στο log, το «ακραίο» σημαίνει πραγματικά ακραίο.
- Λογαριασμοί με λιγότερες από 30 γραμμές εξαιρούνται (το MAD δεν είναι αξιόπιστο).

**Isolation Forest** σε επίπεδο **journal**, με τις παραμέτρους του config.
Features: log συνολικού ποσού, αριθμός γραμμών, ώρα, ημέρα εβδομάδας, `days_to_period_end`, `is_manual`,
συχνότητα χρήστη, συχνότητα λογαριασμού.
Με contamination 0,01 σημαδεύει περίπου το 1% των journals.

---

## 8. Risk Score και λίστα ελεγκτή (`jet/scoring.py`)

- `risk_score` = Σ βαρών των **διαφορετικών** κανόνων που χτύπησαν το journal.
- `risk_score ≥ 6` → πίνακας `high_risk_journals`, ταξινομημένος κατά score και ποσό.
- **Μέτρηση** με το ground truth: precision, recall και μέγεθος λίστας. Στόχος είναι μια λίστα **δεκάδων**, όχι εκατοντάδων εγγραφών.

---

## 9. Run log (`jet/run_log.py`)

Πίνακας `run_log`: `run_id` (uuid), `started_at`, `git_commit`, `config_hash` (sha256 των ρυθμίσεων),
`input_file_hash` (sha256 του GL και του TB), `random_state`, πλήθος γραμμών, καραντίνα, high-risk.

---

## 10. Νέες βιβλιοθήκες

`scikit-learn` (Isolation Forest) και `openpyxl` (Excel), με ακριβείς εκδόσεις στο `requirements.txt`.

---

## 11. Commits (ένα ανά βήμα, και σε κάθε ένα τρέχουν ΟΛΑ τα tests)

| # | Commit | Νέα tests (ενδεικτικά) |
|---|---|---|
| 1 | `docs: phase 2 plan` (αυτό το αρχείο) | – |
| 2 | `feat(config): phase 2 settings` + requirements | – |
| 3 | `feat(jet): journal generator with trial balance` | ισοσκελισμός, rollforward, ground truth |
| 4 | `feat(jet): data quality with GL-TB reconciliation` | καραντίνα, STOP, Excel |
| 5 | `feat(jet): transform features` | αργίες, εξαίρεση system users |
| 6 | `feat(jet): ISA 240 rule engine` | κάθε κανόνας βρίσκει τα φυτεμένα του |
| 7 | `feat(jet): Benford analysis` | ACC_04 βγαίνει nonconformity |
| 8 | `feat(jet): robust z-score and Isolation Forest` | αναπαραγωγιμότητα με seed |
| 9 | `feat(jet): risk scoring, run log, pipeline` | end-to-end, recall στα multi-flag journals |
| 10 | `docs: lesson 02 + README roadmap` | – |

Τα 13 tests της Φάσης 1 **δεν αγγίζονται**.

---

## 12. Χρειάζομαι την έγκρισή σου για

1. Τη χωριστή δομή `audit_ai/jet/` (v2 δίπλα στη v1).
2. Τη συμφωνία GL ↔ TB **πριν** την καραντίνα.
3. Το robust z-score σε **log** κλίμακα.
4. Το `period_end_manual` = τέλος **μήνα** (ή μόνο τέλος χρήσης;).

### Εκκρεμότητες που χρειάζονται εσένα
- **Παλιά αρχεία:** δεν τα σβήνω (όπως ζήτησες). Όποτε θέλεις, τρέξε:
  `! rm db_setup.py audit_sql_queries.py audit_data.db && git rm -q data_generator.py && git commit -qm "chore: remove old scripts"`
- **GitHub:** στείλε μου το link ενός άδειου repo `audit-tech-ai` ή τρέξε `! brew install gh && gh auth login`.
