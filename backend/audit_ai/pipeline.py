"""Το pipeline από άκρη σε άκρη: αρχεία πελάτη -> ποιότητα -> transform -> βάση -> κανόνες ->
ακραία ποσά -> ML -> risk score -> Benford -> run log -> Excel."""
from datetime import datetime

from audit_ai import config as cfg
from audit_ai import data_quality as dq
from audit_ai import database as db
from audit_ai import benford, ml, outliers, report, rules, run_log, scoring, transform


def run(gl_path=cfg.GL_CSV, tb_path=cfg.TB_CSV, db_path=cfg.DB_PATH, report_path=cfg.AUDIT_REPORT_XLSX):
    started_at = datetime.now()
    gl, tb = dq.read_raw(gl_path, tb_path)
    result = dq.run(gl, tb)                       # STOP εδώ αν το GL δεν είναι πλήρες
    silver = transform.add_features(result["clean"])

    with db.connect(db_path) as conn:
        db.save_table(conn, "bronze_gl", gl)
        db.save_table(conn, "bronze_tb", tb)
        db.save_table(conn, "dq_quarantine", result["quarantine"])
        db.save_table(conn, "dq_summary", result["summary"])
        db.save_table(conn, "dq_reconciliation", result["reconciliation"])
        db.save_table(conn, "silver_gl", silver)
        rules.run_rules(conn)                     # gold: rule_hits
        outliers.run_robust_z(conn)               # gold: robust_z_outliers + rule_hits
        ml.run_isolation_forest(conn)             # gold: ml_scores + rule_hits
        scoring.run_scoring(conn)                 # gold: risk_scores, high_risk_journals
        benford.run_benford(conn)                 # gold: benford_overall, benford_by_user
        run = run_log.write_run_log(conn, gl_path, tb_path, started_at)
        report.write_audit_report(conn, run, report_path)
    return db_path


if __name__ == "__main__":
    path = run()
    with db.connect(path) as conn:
        last = db.query(conn, "SELECT * FROM run_log ORDER BY started_at DESC LIMIT 1").iloc[0]
    print("Τελευταία εκτέλεση:")
    print(last.to_string())
    print(f"\nΒάση   -> {path}")
    print(f"Excel  -> {cfg.AUDIT_REPORT_XLSX}")
