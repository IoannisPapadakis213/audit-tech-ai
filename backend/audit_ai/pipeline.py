"""Το pipeline από άκρη σε άκρη: αρχεία πελάτη -> ποιότητα -> transform -> βάση -> κανόνες."""
from audit_ai import config as cfg
from audit_ai import data_quality as dq
from audit_ai import database as db
from audit_ai import rules, transform


def run(gl_path=cfg.GL_CSV, tb_path=cfg.TB_CSV, db_path=cfg.DB_PATH):
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
    return db_path


if __name__ == "__main__":
    path = run()
    with db.connect(path) as conn:
        print(db.query(conn, """
            SELECT name AS πίνακας
            FROM sqlite_master WHERE type = 'table' ORDER BY name
        """).to_string(index=False))
    print(f"\nΒάση -> {path}")
