"""Το τελικό working paper: ένα Excel με ό,τι χρειάζεται ο ελεγκτής για τον φάκελο ελέγχου."""
import pandas as pd

from audit_ai import config as cfg
from audit_ai import database as db


def write_audit_report(conn, run, path=cfg.AUDIT_REPORT_XLSX):
    """Γράφει το audit_report.xlsx. Το «run» είναι η γραμμή του run log αυτής της εκτέλεσης."""
    high_risk = db.query(conn, "SELECT * FROM high_risk_journals")
    lines = db.query(conn, """
        SELECT g.journal_id, g.line_id, g.posting_date, g.entry_datetime, g.account,
               g.debit, g.credit, g.created_by, g.approved_by, g.source, g.description, g.vendor_id
        FROM silver_gl AS g JOIN high_risk_journals AS h ON h.journal_id = g.journal_id
        ORDER BY h.rank, g.line_id
    """)
    rule_summary = db.query(conn, """
        SELECT rule AS κανόνας, MAX(weight) AS βάρος, COUNT(*) AS journals
        FROM rule_hits GROUP BY rule ORDER BY βάρος DESC, journals DESC
    """)
    summary = pd.DataFrame({
        "Στοιχείο": ["Πελάτης", "Χρήση", "Run ID", "Ημερομηνία εκτέλεσης", "Git commit",
                     "Hash ρυθμίσεων", "Hash αρχείου GL", "Hash αρχείου Ισοζυγίου",
                     "Γραμμές που παραλήφθηκαν", "Γραμμές σε καραντίνα", "Journals που αναλύθηκαν",
                     "Όριο risk score", "Journals υψηλού κινδύνου"],
        "Τιμή": [run["client"], f"{cfg.FISCAL_YEAR_START} έως {cfg.FISCAL_YEAR_END}", run["run_id"],
                 run["finished_at"], run["git_commit"], run["config_hash"], run["gl_file_hash"],
                 run["tb_file_hash"], run["lines_received"], run["lines_quarantined"],
                 run["journals_analyzed"], run["risk_threshold"], run["high_risk_journals"]],
    })

    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path) as xl:
        summary.to_excel(xl, sheet_name="Σύνοψη", index=False)
        high_risk.to_excel(xl, sheet_name="Λίστα υψηλού κινδύνου", index=False)
        lines.to_excel(xl, sheet_name="Γραμμές λίστας", index=False)
        rule_summary.to_excel(xl, sheet_name="Κανόνες", index=False)
        db.query(conn, "SELECT * FROM benford_by_user").to_excel(xl, sheet_name="Benford ανά χρήστη", index=False)
        db.query(conn, "SELECT * FROM dq_summary").to_excel(xl, sheet_name="Ποιότητα δεδομένων", index=False)
        db.query(conn, "SELECT * FROM dq_reconciliation").to_excel(xl, sheet_name="Συμφωνία GL-TB", index=False)
    return path
