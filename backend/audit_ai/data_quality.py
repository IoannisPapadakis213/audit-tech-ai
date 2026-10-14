"""Data Quality: πρώτα αποδεικνύουμε ότι το GL είναι ΠΛΗΡΕΣ, μετά απομονώνουμε τα κακά δεδομένα."""
import pandas as pd

from audit_ai import config as cfg


class SchemaError(Exception):
    """Το αρχείο του πελάτη δεν έχει τις στήλες που περιμένουμε."""


class ReconciliationError(Exception):
    """Το GL δεν συμφωνεί με το Ισοζύγιο: το extract δεν είναι πλήρες. STOP."""

    def __init__(self, message, reconciliation):
        super().__init__(message)
        self.reconciliation = reconciliation


def read_raw(gl_path=cfg.GL_CSV, tb_path=cfg.TB_CSV):
    """Διαβάζει τα CSV του πελάτη με σωστούς τύπους. Ό,τι δεν διαβάζεται γίνεται κενό (NaN/NaT)."""
    gl = pd.read_csv(gl_path, dtype={"account": str, "journal_id": str})
    gl["posting_date"] = pd.to_datetime(gl["posting_date"], errors="coerce")
    gl["entry_datetime"] = pd.to_datetime(gl["entry_datetime"], errors="coerce")
    for col in ("debit", "credit"):
        gl[col] = pd.to_numeric(gl[col], errors="coerce")
    tb = pd.read_csv(tb_path, dtype={"account": str})
    return gl, tb


def check_schema(gl):
    missing = set(cfg.GL_COLUMNS) - set(gl.columns)
    if missing:
        raise SchemaError(f"Λείπουν στήλες: {sorted(missing)}")


def reconcile(gl, tb):
    """Συμφωνία GL ↔ Ισοζύγιο ανά λογαριασμό. Αν δεν συμφωνεί -> ReconciliationError.

    Τρέχει στο ΠΛΗΡΕΣ GL (πριν την καραντίνα): ελέγχει αν πήραμε ΟΛΕΣ τις εγγραφές.
    """
    in_year = gl[gl["posting_date"].between(cfg.FISCAL_YEAR_START, cfg.FISCAL_YEAR_END)]
    gl_moves = in_year.groupby("account")[["debit", "credit"]].sum()
    gl_moves.columns = ["gl_debit", "gl_credit"]

    rec = tb.set_index("account").join(gl_moves, how="outer").fillna(0.0)
    rec["diff_debit"] = (rec["gl_debit"] - rec["period_debit"]).round(2)
    rec["diff_credit"] = (rec["gl_credit"] - rec["period_credit"]).round(2)
    rec["diff_rollforward"] = (
        rec["opening_balance"] + rec["period_debit"] - rec["period_credit"] - rec["closing_balance"]
    ).round(2)
    diffs = rec[["diff_debit", "diff_credit", "diff_rollforward"]].abs()
    rec["status"] = (diffs.max(axis=1) <= cfg.BALANCE_TOLERANCE).map({True: "OK", False: "ΔΙΑΦΟΡΑ"})
    rec = rec.reset_index()

    failed = rec[rec["status"] != "OK"]
    if not failed.empty:
        raise ReconciliationError(
            f"Το GL δεν συμφωνεί με το Ισοζύγιο σε {len(failed)} λογαριασμούς: "
            f"{failed['account'].tolist()}. STOP: ζήτα νέο extract από τον πελάτη.",
            rec,
        )
    return rec


# ======================= Μέρος Β: έλεγχοι και καραντίνα =======================

def line_checks(gl):
    """Οι 5 έλεγχοι ποιότητας. Ο καθένας: (όνομα, περιγραφή, Series True/False ανά γραμμή, True = πρόβλημα)."""
    start, end = pd.Timestamp(cfg.FISCAL_YEAR_START), pd.Timestamp(cfg.FISCAL_YEAR_END)
    sums = gl.groupby("journal_id")[["debit", "credit"]].transform("sum")
    return [
        ("missing_field", "Κενό υποχρεωτικό πεδίο",
         gl[list(cfg.GL_REQUIRED_FIELDS)].isna().any(axis=1)),
        ("duplicate_id", "Ίδιο journal_id + line_id πάνω από μία φορά",
         gl.duplicated(["journal_id", "line_id"], keep=False)),
        ("out_of_period", "Ημερομηνία εκτός χρήσης ή καταχώρηση μετά το POST_CLOSE_END",
         ~gl["posting_date"].between(start, end) | (gl["entry_datetime"] > pd.Timestamp(cfg.POST_CLOSE_END))),
        ("unknown_account", "Λογαριασμός που δεν υπάρχει στο λογιστικό σχέδιο",
         ~gl["account"].isin(list(cfg.CHART_OF_ACCOUNTS))),
        ("unbalanced", "Το journal δεν ισοσκελίζει (Σ χρεώσεων ≠ Σ πιστώσεων)",
         (sums["debit"] - sums["credit"]).abs() > cfg.BALANCE_TOLERANCE),
    ]


def quarantine(gl):
    """Χωρίζει το GL σε (clean, quarantine, summary). Ποτέ δεν σβήνει και ποτέ δεν διορθώνει.

    Αν έστω μία γραμμή ενός journal έχει πρόβλημα, ΟΛΟ το journal πάει σε καραντίνα:
    ένα μισό journal δεν ισοσκελίζει και δεν έχει λογιστικό νόημα.
    """
    reasons = pd.Series("", index=gl.index)
    summary = []
    for name, description, failed in line_checks(gl):
        reasons[failed] += name + "; "
        summary.append({"check": name, "description": description,
                        "failed_lines": int(failed.sum()),
                        "failed_journals": int(gl.loc[failed, "journal_id"].nunique())})

    bad_journals = gl.loc[reasons != "", "journal_id"].unique()
    in_quarantine = gl["journal_id"].isin(bad_journals)

    q = gl[in_quarantine].copy()
    q["dq_reason"] = reasons[in_quarantine].str.rstrip("; ").replace("", "same_journal")
    clean = gl[~in_quarantine].copy()
    return clean, q, pd.DataFrame(summary)
