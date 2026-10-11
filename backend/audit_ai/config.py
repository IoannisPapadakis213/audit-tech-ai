"""Κεντρικές ρυθμίσεις. Ό,τι αλλάζει από engagement σε engagement ζει εδώ, όχι σκόρπιο στον κώδικα."""
from pathlib import Path

# backend/audit_ai/config.py -> parents[2] = ρίζα του repo
REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
RAW_CSV = DATA_DIR / "raw" / "general_ledger_2023.csv"
GROUND_TRUTH_CSV = DATA_DIR / "raw" / "injected_anomalies.csv"
DB_PATH = DATA_DIR / "audit_data.db"

FISCAL_YEAR = 2023

# Λογιστικό σχέδιο (chart of accounts): οι μόνοι έγκυροι λογαριασμοί
CHART_OF_ACCOUNTS = (
    "Revenue",
    "Payroll",
    "Office Supplies",
    "Marketing",
    "Consulting Fees",
    "Travel",
)

USERS = ("User_01", "User_02", "User_03", "User_04", "System_Auto")

REQUIRED_COLUMNS = (
    "transaction_id",
    "posting_datetime",
    "account",
    "amount",
    "user_id",
    "description",
)

# Κανόνες κινδύνου
ROUND_AMOUNT_THRESHOLD = 10_000   # στρογγυλά ποσά από εδώ και πάνω = red flag
BUSINESS_HOURS = (8, 19)          # [08:00, 19:00) θεωρούνται εργάσιμες ώρες
OUTLIER_MULTIPLIER = 3            # ποσό > 3x μέσου όρου λογαριασμού = outlier


# =====================================================================
# Φάση 2: Journal Entry Testing (ISA 240) με debit/credit και Ισοζύγιο.
# Οι ρυθμίσεις της Φάσης 1 παραπάνω μένουν ως έχουν (τις χρησιμοποιούν τα tests της).
# =====================================================================

JET_RAW_DIR = DATA_DIR / "jet" / "raw"
JET_GL_CSV = JET_RAW_DIR / "general_ledger_2025.csv"
JET_TB_CSV = JET_RAW_DIR / "trial_balance_2025.csv"
JET_GROUND_TRUTH_CSV = JET_RAW_DIR / "injected_anomalies.csv"
JET_DB_PATH = DATA_DIR / "jet" / "jet_audit.db"
JET_DQ_REPORT_XLSX = DATA_DIR / "jet" / "dq_report.xlsx"

CLIENT_NAME = "Aigaio Emporio SA"
FISCAL_YEAR_START = "2025-01-01"
FISCAL_YEAR_END = "2025-12-31"
POST_CLOSE_END = "2026-02-28"       # μέχρι πότε δεχόμαστε καταχωρήσεις για τη χρήση

# Σημαντικότητα (materiality, ISA 320)
OVERALL_MATERIALITY = 500_000
PERFORMANCE_MATERIALITY = 375_000
CLEARLY_TRIVIAL = 25_000

WORK_HOURS = (8, 18)                # [08:00, 18:00)
GREEK_HOLIDAYS_2025 = (
    "2025-01-01", "2025-01-06", "2025-03-03", "2025-03-25",
    "2025-04-18", "2025-04-21", "2025-05-01", "2025-06-09",
    "2025-08-15", "2025-10-28", "2025-12-25", "2025-12-26",
)

SYSTEM_USERS = ("SYS_BATCH", "SYS_PAYROLL")     # εξαιρούνται από weekend / after-hours
AUTHORIZED_POSTERS = ("ACC_01", "ACC_02", "ACC_03", "ACC_04", "FIN_MGR")
SENIOR_MANAGEMENT = ("CFO", "CEO")

# Λογιστικό σχέδιο σε στυλ ΕΓΛΣ: κωδικός -> (περιγραφή, φύση υπολοίπου)
# Η "φύση" λέει αν ο λογαριασμός κανονικά έχει χρεωστικό (D) ή πιστωτικό (C) υπόλοιπο.
JET_CHART_OF_ACCOUNTS = {
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

GL_COLUMNS = (
    "journal_id", "line_id", "posting_date", "entry_datetime", "account",
    "debit", "credit", "created_by", "approved_by", "source", "description", "vendor_id",
)
GL_REQUIRED_FIELDS = (
    "journal_id", "line_id", "posting_date", "entry_datetime", "account",
    "debit", "credit", "created_by", "source",
)

# Κανόνες ανίχνευσης
PERIOD_END_WINDOW_DAYS = 10         # τελευταίες 10 μέρες κάθε μήνα
ROUND_AMOUNT_MIN = 10_000
ROUND_AMOUNT_MODULO = 1_000
DUPLICATE_WINDOW_DAYS = 7
RARE_ACCOUNT_MAX_USES = 5
BALANCE_TOLERANCE = 0.01            # ανοχή στρογγυλοποίησης σε €

# Στατιστική και ML
ROBUST_Z_THRESHOLD = 3.5            # Iglewicz & Hoaglin, πάνω σε log10(ποσού)
ROBUST_Z_MIN_LINES = 30             # λιγότερες γραμμές -> το MAD δεν είναι αξιόπιστο
BENFORD_MIN_AMOUNT = 10
BENFORD_MIN_SAMPLE = 300            # κάτω από αυτό: "ανεπαρκές δείγμα"
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
