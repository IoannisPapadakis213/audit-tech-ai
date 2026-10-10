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
