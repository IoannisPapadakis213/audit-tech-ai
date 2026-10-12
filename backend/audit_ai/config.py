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