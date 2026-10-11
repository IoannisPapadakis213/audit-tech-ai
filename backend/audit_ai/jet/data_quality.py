"""Data Quality της Φάσης 2: πρώτα πληρότητα (GL ↔ Ισοζύγιο), μετά καραντίνα.

Σειρά:
1. Σχήμα: λείπουν στήλες -> SchemaError.
2. Συμφωνία GL ↔ Ισοζύγιο στο ΠΛΗΡΕΣ extract -> αν δεν συμφωνεί, ReconciliationError (STOP).
3. Έλεγχοι γραμμής/journal -> καραντίνα ολόκληρου του journal, με λόγο. Ποτέ σβήσιμο ή διόρθωση.
"""
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from audit_ai import config as cfg
from audit_ai.data_quality import CheckResult, SchemaError, results_to_frame


class ReconciliationError(Exception):
    """Το GL δεν συμφωνεί με το Ισοζύγιο: το extract δεν είναι πλήρες."""

    def __init__(self, message, reconciliation):
        super().__init__(message)
        self.reconciliation = reconciliation


@dataclass
class DQResult:
    clean: pd.DataFrame
    quarantine: pd.DataFrame
    checks: list
    reconciliation: pd.DataFrame = field(default_factory=pd.DataFrame)


def read_raw(gl_path=cfg.JET_GL_CSV, tb_path=cfg.JET_TB_CSV):
    """Διαβάζει τα αρχεία του πελάτη με σωστούς τύπους. Ό,τι δεν διαβάζεται γίνεται NaN/NaT."""
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
    """Rollforward ανά λογαριασμό: κινήσεις GL της χρήσης έναντι κινήσεων Ισοζυγίου."""
    start, end = pd.Timestamp(cfg.FISCAL_YEAR_START), pd.Timestamp(cfg.FISCAL_YEAR_END)
    in_year = gl[gl["posting_date"].between(start, end)]
    gl_moves = in_year.groupby("account")[["debit", "credit"]].sum().add_prefix("gl_")

    rec = tb.set_index("account").join(gl_moves, how="outer").fillna(0.0)
    rec["diff_debit"] = (rec["gl_debit"] - rec["period_debit"]).round(2)
    rec["diff_credit"] = (rec["gl_credit"] - rec["period_credit"]).round(2)
    # Εσωτερική συνέπεια του Ισοζυγίου: αρχή + κινήσεις = τέλος
    rec["diff_rollforward"] = (
        rec["opening_balance"] + rec["period_debit"] - rec["period_credit"] - rec["closing_balance"]
    ).round(2)
    diffs = rec[["diff_debit", "diff_credit", "diff_rollforward"]].abs()
    rec["reconciled"] = (diffs <= cfg.BALANCE_TOLERANCE).all(axis=1)
    return rec.reset_index()


def _line_checks(gl):
    """(όνομα, περιγραφή, μάσκα αποτυχίας) για κάθε έλεγχο."""
    start, end = pd.Timestamp(cfg.FISCAL_YEAR_START), pd.Timestamp(cfg.FISCAL_YEAR_END)
    post_close_end = pd.Timestamp(cfg.POST_CLOSE_END) + pd.Timedelta(days=1)
    net = (gl["debit"].fillna(0) - gl["credit"].fillna(0)).groupby(gl["journal_id"]).transform("sum")
    return [
        ("missing_required_field", "Κενό υποχρεωτικό πεδίο",
         gl[list(cfg.GL_REQUIRED_FIELDS)].isna().any(axis=1)),
        ("duplicate_line_id", "Ίδιο journal_id + line_id πάνω από μία φορά",
         gl.duplicated(["journal_id", "line_id"], keep=False)),
        ("outside_fiscal_year", f"posting_date εκτός χρήσης {cfg.FISCAL_YEAR_START} – {cfg.FISCAL_YEAR_END}",
         gl["posting_date"].notna() & ~gl["posting_date"].between(start, end)),
        ("entered_after_post_close", f"Καταχώρηση μετά το {cfg.POST_CLOSE_END}",
         gl["entry_datetime"] >= post_close_end),
        ("unknown_account", "Λογαριασμός εκτός λογιστικού σχεδίου",
         gl["account"].notna() & ~gl["account"].isin(cfg.JET_CHART_OF_ACCOUNTS)),
        ("unbalanced_journal", "Σ Χρεώσεων ≠ Σ Πιστώσεων στο journal",
         net.abs() > cfg.BALANCE_TOLERANCE),
    ]


def run_checks(gl, tb):
    """Επιστρέφει DQResult. Σηκώνει ReconciliationError αν το GL δεν συμφωνεί με το Ισοζύγιο."""
    check_schema(gl)

    rec = reconcile(gl, tb)  # στο ΠΛΗΡΕΣ extract, πριν την καραντίνα
    if not rec["reconciled"].all():
        bad = rec.loc[~rec["reconciled"], "account"].tolist()
        raise ReconciliationError(f"Το GL δεν συμφωνεί με το Ισοζύγιο στους λογαριασμούς {bad}", rec)

    reasons = pd.Series("", index=gl.index)
    checks = []
    for name, description, failed in _line_checks(gl):
        checks.append(CheckResult(name, description, int(failed.sum())))
        reasons[failed] += name + ";"

    # Το journal είναι η μονάδα ελέγχου: μία κακή γραμμή -> ολόκληρο το journal σε καραντίνα
    bad_journals = gl.loc[reasons != "", "journal_id"].unique()
    in_quarantine = gl["journal_id"].isin(bad_journals)
    reasons = reasons.str.rstrip(";").where(reasons != "", "same_journal")

    clean = gl[~in_quarantine].copy()
    quarantine = gl[in_quarantine].assign(dq_reasons=reasons[in_quarantine])
    return DQResult(clean, quarantine, checks, rec)


def write_dq_report(path=cfg.JET_DQ_REPORT_XLSX, checks=(), quarantine=None, reconciliation=None):
    """dq_report.xlsx για τα working papers. Δέχεται και μερικά αποτελέσματα (π.χ. μετά από STOP)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as xls:
        results_to_frame(list(checks)).to_excel(xls, sheet_name="Σύνοψη", index=False)
        (quarantine if quarantine is not None else pd.DataFrame()).to_excel(
            xls, sheet_name="Καραντίνα", index=False)
        (reconciliation if reconciliation is not None else pd.DataFrame()).to_excel(
            xls, sheet_name="Συμφωνία GL-TB", index=False)
    return path
