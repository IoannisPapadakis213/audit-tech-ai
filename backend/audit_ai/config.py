"""Κεντρικές ρυθμίσεις του ελέγχου. Ό,τι αλλάζει από πελάτη σε πελάτη ζει ΜΟΝΟ εδώ."""
from pathlib import Path

# ---------- Φάκελοι ----------
# Το αρχείο είναι στο backend/audit_ai/config.py.
# parents[0] = audit_ai, parents[1] = backend, parents[2] = ρίζα του repo
REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"

# ---------- Πελάτης και χρήση ----------
CLIENT_NAME = "Aigaio Emporio SA"
FISCAL_YEAR_START = "2025-01-01"
FISCAL_YEAR_END = "2025-12-31"
POST_CLOSE_END = "2026-02-28"   # ως πότε γίνονται εγγραφές κλεισίματος για τη χρήση

# ---------- Σημαντικότητα (ISA 320), σε € ----------
OVERALL_MATERIALITY = 500_000
PERFORMANCE_MATERIALITY = 375_000
CLEARLY_TRIVIAL = 25_000
# ---------- Ωράριο και αργίες ----------
WORK_HOURS = (8, 18)   # εργάσιμες ώρες: από 08:00 έως 17:59
GREEK_HOLIDAYS_2025 = (
    "2025-01-01", "2025-01-06", "2025-03-03", "2025-03-25",
    "2025-04-18", "2025-04-21", "2025-05-01", "2025-06-09",
    "2025-08-15", "2025-10-28", "2025-12-25", "2025-12-26",
)

# ---------- Χρήστες του ERP ----------
SYSTEM_USERS = ("SYS_BATCH", "SYS_PAYROLL")      # αυτόματες διαδικασίες
AUTHORIZED_POSTERS = ("ACC_01", "ACC_02", "ACC_03", "ACC_04", "FIN_MGR")
SENIOR_MANAGEMENT = ("CFO", "CEO")

# ---------- Λογιστικό σχέδιο (στυλ ΕΓΛΣ) ----------
# κωδικός -> (περιγραφή, φύση υπολοίπου: D = χρεωστικό, C = πιστωτικό)
CHART_OF_ACCOUNTS = {
    "14.00": ("Πάγια", "D"),
    "20.00": ("Εμπορεύματα", "D"),
    "30.00": ("Πελάτες", "D"),
    "38.03": ("Καταθέσεις όψεως", "D"),
    "40.00": ("Μετοχικό κεφάλαιο", "C"),
    "50.00": ("Προμηθευτές", "C"),
    "53.00": ("Πιστωτές διάφοροι", "C"),
    "54.00": ("ΦΠΑ", "C"),
    "55.00": ("Ασφαλιστικοί οργανισμοί", "C"),
    "60.00": ("Αμοιβές προσωπικού", "D"),
    "61.00": ("Αμοιβές τρίτων", "D"),
    "62.00": ("Παροχές τρίτων", "D"),
    "64.00": ("Διάφορα έξοδα", "D"),
    "66.00": ("Αποσβέσεις", "D"),
    "70.00": ("Πωλήσεις εμπορευμάτων", "C"),
    "71.00": ("Πωλήσεις υπηρεσιών", "C"),
    "81.00": ("Έκτακτα αποτελέσματα", "D"),
}

# ---------- Κοινό σχήμα του GL ----------
# Όποιο ERP κι αν έχει ο πελάτης (SoftOne, SAP, Entersoft), το φέρνουμε σε αυτές τις στήλες.
GL_COLUMNS = (
    "journal_id", "line_id", "posting_date", "entry_datetime", "account",
    "debit", "credit", "created_by", "approved_by", "source", "description", "vendor_id",
)
# Αυτές δεν επιτρέπεται να είναι κενές (approved_by, description, vendor_id μπορεί να λείπουν)
GL_REQUIRED_FIELDS = (
    "journal_id", "line_id", "posting_date", "entry_datetime", "account",
    "debit", "credit", "created_by", "source",
)

# ---------- Κατώφλια κανόνων ----------
PERIOD_END_WINDOW_DAYS = 10     # "κοντά στο κλείσιμο" = τελευταίες 10 μέρες
ROUND_AMOUNT_MIN = 10_000       # στρογγυλό ποσό: τουλάχιστον 10.000 €...
ROUND_AMOUNT_MODULO = 1_000     # ...και ακέραιες χιλιάδες (π.χ. 25.000)
DUPLICATE_WINDOW_DAYS = 7       # ίδια πληρωμή δύο φορές μέσα σε 7 μέρες
RARE_ACCOUNT_MAX_USES = 5       # λογαριασμός που χρησιμοποιήθηκε ≤ 5 φορές τον χρόνο
BALANCE_TOLERANCE = 0.01        # ανοχή στρογγυλοποίησης: 1 λεπτό

# ---------- Στατιστική και ML ----------
ROBUST_Z_THRESHOLD = 3.5
ROBUST_Z_MIN_LINES = 30
BENFORD_MIN_AMOUNT = 10
BENFORD_MIN_SAMPLE = 300
BENFORD_MAD_LIMITS = {"close": 0.006, "acceptable": 0.012, "marginal": 0.015}
ISOLATION_FOREST = {"n_estimators": 200, "contamination": 0.01, "random_state": 42}

# ---------- Βάρη κινδύνου (πόντοι ανά κανόνα) ----------
RULE_WEIGHTS = {
    "post_close": 5,          # εγγραφή μετά το κλείσιμο
    "senior_mgmt_user": 5,    # την έκανε ο CFO / CEO
    "unauthorized_user": 4,   # χρήστης εκτός λίστας
    "period_end_manual": 3,   # χειροκίνητη, κοντά στο κλείσιμο
    "duplicate": 3,           # πιθανή διπλή πληρωμή
    "round_amount": 2,
    "weekend_holiday": 2,
    "rare_account": 2,
    "robust_z_outlier": 2,    # ακραίο ποσό για τον λογαριασμό
    "isolation_forest": 2,    # "περίεργη" κατά το ML
    "after_hours": 1,
    "no_description": 1,      # κενή αιτιολογία
}
RISK_SCORE_THRESHOLD = 6      # από 6 πόντους και πάνω -> λίστα ελεγκτή
