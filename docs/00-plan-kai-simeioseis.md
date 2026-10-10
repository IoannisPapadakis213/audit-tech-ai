# Audit Tech AI: Πλάνο, σημειώσεις και οδηγίες

> Σύνοψη όλων όσων είπαμε στο terminal μέχρι τώρα.
> Το αναλυτικό μάθημα της Φάσης 1 είναι στο `docs/lessons/01-etl-data-quality.md`.

---

## 1. Η θέση εργασίας

**Data Analyst – Data & Analytics – Assurance**, Deloitte, Αθήνα (Associate, πλήρης απασχόληση)

### Αρμοδιότητες
- Εξαγωγή, μετασχηματισμός, επικύρωση και ανάλυση μεγάλου όγκου οικονομικών και λειτουργικών δεδομένων για Audit & Assurance.
- Κατασκευή ροών μετασχηματισμού δεδομένων (data transformation workflows) και ελέγχων ποιότητας, ώστε να προκύπτουν datasets έτοιμα για έλεγχο (audit-ready).
- Αυτοματοποιημένα analytics, dashboards και αναφορές BI για τους ελεγκτές.
- Χρήση analytics, αυτοματοποίησης και AI για πιο αποτελεσματικό έλεγχο.
- Συνεργασία με τις ομάδες ελέγχου: μετατροπή των αναγκών τους σε αναλυτικές λύσεις.
- Παρουσίαση ευρημάτων σε ομάδες και ενδιαφερόμενους.

### Απαιτούμενα
- 1–3 χρόνια εμπειρία σε data analytics, audit analytics, assurance ή risk.
- Πτυχίο σε θετική/τεχνική κατεύθυνση (πληροφορική, στατιστική, μηχανική).
- **Δυνατή Python** για επεξεργασία δεδομένων, αυτοματοποίηση και reporting.
- Εντοπισμός ανωμαλιών, τάσεων και κινδύνων σε μεγάλα datasets.
- Scripts, data pipelines, αυτοματοποιημένοι έλεγχοι.
- **Git, testing, documentation.**
- Γνώσεις audit, financial reporting, εσωτερικών ελέγχων (πλεονέκτημα).

### Επιθυμητά (nice-to-have)
- **Databricks**
- **Azure** (Data Factory, Azure SQL, App Services, Fabric, Azure Databricks)
- **AI / ML / Generative AI**
- **Power BI** ή άλλα εργαλεία οπτικοποίησης
- Data engineering, ETL/ELT, σύγχρονες αρχιτεκτονικές δεδομένων

---

## 2. Πώς το project καλύπτει την αγγελία

| Απαίτηση της αγγελίας | Πού τη δείχνουμε στο project |
|---|---|
| Python για επεξεργασία και αυτοματοποίηση | Όλο το backend (pandas, package `audit_ai`) |
| Data quality controls, audit-ready datasets | `data_quality.py`: έλεγχοι, καραντίνα, αναφορά |
| Εντοπισμός ανωμαλιών και κινδύνων | SQL κανόνες, και στη Φάση 2 Benford, z-score, Isolation Forest |
| Pipelines, αυτοματοποιημένοι έλεγχοι | `etl.py`: Extract → Validate → Transform → Load |
| Git, testing, documentation | GitHub, `pytest`, README, μαθήματα στο `docs/` |
| Dashboards και BI | React frontend με γραφήματα |
| AI / GenAI | Chatbot με Gemini που απαντά σε ερωτήσεις για το ledger |
| Azure | Deploy σε Azure App Service, ίσως Azure SQL |
| Databricks | Το ίδιο pipeline σε PySpark |

---

## 3. Αρχιτεκτονική (ο τελικός στόχος)

```
data_generator ─► ETL + Data Quality ─► Database (SQLite → Azure SQL)
                                            │
                                   FastAPI backend (Python)
                                 ┌──────────┼──────────────┐
                           /anomalies    /stats      /chat (Gemini)
                                            │
                              React frontend (dashboard + chatbot)
                                            │
                                     Azure App Service
```

### Φάσεις (roadmap)

- [x] **Φάση 1:** Θεμέλια, ETL, Data Quality, SQL κανόνες, tests
- [ ] **Φάση 2:** Στατιστική ανίχνευση: νόμος του Benford, z-score, Isolation Forest
- [ ] **Φάση 3:** Backend API με FastAPI
- [ ] **Φάση 4:** Frontend σε React (Vite) με εντυπωσιακό dashboard, που τραβάει και δεδομένα από εξωτερικό API (π.χ. ισοτιμίες της ΕΚΤ)
- [ ] **Φάση 5:** AI chatbot με Gemini
- [ ] **Φάση 6:** Deploy σε Azure
- [ ] **Φάση 7:** Databricks / PySpark

---

## 4. Τι είχες φτιάξει στην αρχή (ο παλιός κώδικας)

- **`data_generator.py`:** έφτιαχνε ένα General Ledger (GL), δηλαδή όλες τις λογιστικές εγγραφές της χρήσης, με φυτεμένες ανωμαλίες. Σε πραγματικό audit ο ελεγκτής εξετάζει τις εγγραφές του GL (*journal entry testing*).
- **`db_setup.py`:** φόρτωνε το CSV σε SQLite και έκανε 2 ελέγχους ποιότητας (κενά και αρνητικά ποσά).
- **`audit_sql_queries.py`:** 3 σενάρια σε SQL: εγγραφές Σαββατοκύριακου, προφίλ χρηστών, outliers με subquery και JOIN.

**Για τη συνέντευξη:** «Γιατί οι εγγραφές Σαββατοκύριακου είναι red flag;»
→ Το **ISA 240** (πρότυπο ελέγχου για την απάτη) ζητά από τον ελεγκτή να εξετάζει εγγραφές με ασυνήθιστα χαρακτηριστικά: σε ασυνήθιστες ώρες, από ασυνήθιστους χρήστες, με στρογγυλά ποσά.

### Τι ήθελε διόρθωση και γιατί
1. Στο `.gitignore`, το `*db` έπιανε κάθε αρχείο που τελειώνει σε «db». Το σωστό είναι `*.db`.
2. Οι έλεγχοι ποιότητας έκαναν μόνο `print`. Ένα σωστό pipeline πρέπει να **απομονώνει** τα κακά δεδομένα ή να **σταματά**. Χρειάζονταν και περισσότεροι έλεγχοι (διπλά IDs, ημερομηνίες εκτός χρήσης, άγνωστοι λογαριασμοί).
3. Τα ποσά ήταν ομοιόμορφα (`uniform`), κάτι μη ρεαλιστικό που χαλάει τον νόμο του Benford. Τα αλλάξαμε σε `lognormal`.
4. Δεν υπήρχαν GitHub remote και tests.

---

## 5. Τι φτιάξαμε στη Φάση 1

```
audit-tech-ai/
├── backend/
│   ├── audit_ai/
│   │   ├── config.py           ← ρυθμίσεις (paths, λογαριασμοί, κατώφλια)
│   │   ├── data_generator.py   ← συνθετικό GL + ground truth
│   │   ├── data_quality.py     ← 5 έλεγχοι, καραντίνα
│   │   ├── etl.py              ← Extract → Validate → Transform → Load
│   │   ├── audit_queries.py    ← 6 SQL κανόνες (window functions)
│   │   └── __main__.py         ← τρέχει όλο το pipeline
│   ├── tests/                  ← 13 tests
│   ├── requirements.txt
│   └── pyproject.toml
├── docs/
│   ├── 00-plan-kai-simeioseis.md   ← αυτό το αρχείο
│   └── lessons/01-etl-data-quality.md
└── README.md
```

### Σε απλά λόγια
- **`data_generator.py`:** φτιάχνει τις εγγραφές με ρεαλιστικά ποσά. Φυτεύει 4 τύπους ανωμαλιών (στρογγυλά ποσά, Σαββατοκύριακο, εκτός ωραρίου, διπλές πληρωμές) και 10 εγγραφές με λάθη. Κρατάει και αρχείο με το ποιες είναι οι ύποπτες (ground truth), ώστε να ελέγχουμε αν τις βρίσκουμε.
- **`data_quality.py`:** οι προβληματικές εγγραφές δεν σβήνονται. Μπαίνουν σε **καραντίνα** μαζί με τον λόγο.
- **`etl.py`:** διαβάζει, ελέγχει, προσθέτει βοηθητικές στήλες (π.χ. `is_weekend`) και αποθηκεύει στη βάση.
- **`audit_queries.py`:** οι κανόνες ανίχνευσης σε SQL.

### Αποτελέσματα
| Κανόνας | Εγγραφές που βρέθηκαν |
|---|---|
| Στρογγυλά ποσά | 50 (όσα φυτέψαμε) |
| Σαββατοκύριακο | 30 (όσα φυτέψαμε) |
| Εκτός ωραρίου | 20 (όσα φυτέψαμε) |
| Διπλές πληρωμές | 30 (15 ζεύγη) |
| Outliers ανά λογαριασμό | **557: πάρα πολλά** |

- Και οι 10 εγγραφές με λάθη πήγαν στην καραντίνα.
- Πέρασαν και τα 13 tests.

**Το πρόβλημα με τα 557:** ο μέσος όρος επηρεάζεται από τις ίδιες τις ακραίες τιμές. Ένας ελεγκτής δεν μπορεί να εξετάσει 557 εγγραφές (πρόβλημα **false positives**). Θα το λύσουμε στη Φάση 2.

### Πώς το τρέχεις
```bash
source venv/bin/activate
cd backend
python -m audit_ai      # όλο το pipeline
python -m pytest        # tests
```

---

## 6. Τι εκκρεμεί

1. **Σβήσιμο των παλιών αρχείων** (`data_generator.py`, `db_setup.py` και `audit_sql_queries.py` στη ρίζα, και το `audit_data.db`). Οι νέες εκδόσεις τους είναι στο `backend/`. Γράψε στο Claude Code:
   ```
   ! rm db_setup.py audit_sql_queries.py audit_data.db && git rm -q data_generator.py && git commit -qm "chore: remove old scripts"
   ```
2. **GitHub:** φτιάξε άδειο repo `audit-tech-ai` στο github.com/IoannisPapadakis213 (χωρίς README) και δώσε το link στο Claude Code. Εναλλακτικά, τρέξε `! brew install gh && gh auth login`.
3. **Φάση 2:** Benford, z-score, Isolation Forest.

---

## 7. Prompt για το Claude (claude.ai)

Ανέβασε αυτό το αρχείο και το `docs/lessons/01-etl-data-quality.md` (και τα `.py` αν θέλεις) και γράψε:

```
Είμαι υποψήφιος για τη θέση Data Analyst – Data & Analytics (Assurance) στην Deloitte Αθήνας.
Σου επισυνάπτω το πλάνο του project μου και το μάθημα της Φάσης 1.

Θέλω να γίνεις ο δάσκαλός μου, στα ελληνικά:
1. Φτιάξε ένα δομημένο μάθημα σε ενότητες, με απλά παραδείγματα και αναλογίες.
2. Μετά από κάθε ενότητα κάνε μου 2-3 ερωτήσεις και περίμενε την απάντησή μου πριν συνεχίσεις.
3. Διόρθωσέ με σαν να ήσουν interviewer της Deloitte: τι θα έλεγε ένας καλός υποψήφιος.
4. Στο τέλος δώσε μου ένα cheat sheet μιας σελίδας και 10 πιθανές ερωτήσεις συνέντευξης με
   πρότυπες απαντήσεις που βασίζονται στο δικό μου project.

Ξεκίνα από την Ενότητα 1: τι είναι το Journal Entry Testing και γιατί το απαιτεί το ISA 240.
```
