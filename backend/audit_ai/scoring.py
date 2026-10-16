"""Risk score και λίστα ελεγκτή: όλα τα ευρήματα γίνονται ΜΙΑ ιεραρχημένη λίστα.

risk_score = άθροισμα βαρών των ΔΙΑΦΟΡΕΤΙΚΩΝ κανόνων που χτύπησαν το journal.
Όσα έχουν risk_score >= RISK_SCORE_THRESHOLD μπαίνουν στη λίστα του ελεγκτή.
"""
import pandas as pd

from audit_ai import config as cfg
from audit_ai import database as db

SCORES_SQL = """
    WITH journals AS (
        SELECT journal_id,
               MIN(posting_date)    AS posting_date,
               MIN(entry_datetime)  AS entry_datetime,
               MIN(created_by)      AS created_by,
               MIN(description)     AS description,
               ROUND(SUM(debit), 2) AS amount
        FROM silver_gl
        GROUP BY journal_id
    ),
    scores AS (
        SELECT journal_id,
               SUM(weight)                              AS risk_score,
               COUNT(*)                                 AS n_rules,
               GROUP_CONCAT(rule || ' (' || weight || ')', ', ') AS reasons
        FROM rule_hits
        GROUP BY journal_id
    )
    SELECT s.journal_id, s.risk_score, s.n_rules, s.reasons,
           j.created_by, j.posting_date, j.entry_datetime, j.amount, j.description
    FROM scores AS s JOIN journals AS j ON j.journal_id = s.journal_id
    ORDER BY s.risk_score DESC, j.amount DESC
"""


def run_scoring(conn):
    """Γράφει risk_scores (όλα τα journals με τουλάχιστον ένα εύρημα) και high_risk_journals (η λίστα)."""
    scores = db.query(conn, SCORES_SQL)
    scores.insert(0, "rank", range(1, len(scores) + 1))
    db.save_table(conn, "risk_scores", scores)

    high_risk = scores[scores["risk_score"] >= cfg.RISK_SCORE_THRESHOLD].copy()
    db.save_table(conn, "high_risk_journals", high_risk)
    return high_risk


def evaluate(high_risk, truth, total_journals):
    """Πόσο καλή είναι η λίστα; Σύγκριση με το ground truth.

    Μετράμε μόνο ανωμαλίες ΣΕ ΕΠΙΠΕΔΟ ΕΓΓΡΑΦΗΣ. Εξαιρούνται:
      - dq_*: έχουν ήδη πάει στην καραντίνα, δεν φτάνουν ποτέ εδώ
      - benford_fabricated: τις πιάνει ο Benford σε επίπεδο ΧΡΗΣΤΗ, όχι εγγραφής
    """
    planted = truth[~truth["anomaly_type"].str.startswith("dq_") & (truth["anomaly_type"] != "benford_fabricated")]
    listed = set(high_risk["journal_id"])
    relevant = set(planted["journal_id"])
    hits = listed & relevant

    by_type = (planted.assign(found=planted["journal_id"].isin(listed))
               .groupby("anomaly_type")["found"].agg(["sum", "count"])
               .rename(columns={"sum": "στη_λίστα", "count": "φυτεμένα"}))
    summary = {
        "journals_εξετάστηκαν": total_journals,
        "μέγεθος_λίστας": len(listed),
        "precision": round(len(hits) / len(listed), 3) if listed else 0.0,
        "recall": round(len(hits) / len(relevant), 3) if relevant else 0.0,
    }
    return summary, by_type


def threshold_table(scores, truth, total_journals, thresholds=range(1, 9)):
    """Τι θα γινόταν με άλλο όριο; Για κάθε όριο: μέγεθος λίστας, precision, recall."""
    rows = []
    for t in thresholds:
        summary, _ = evaluate(scores[scores["risk_score"] >= t], truth, total_journals)
        rows.append({"όριο": t, "μέγεθος_λίστας": summary["μέγεθος_λίστας"],
                     "precision": summary["precision"], "recall": summary["recall"]})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    with db.connect() as conn:
        high_risk = run_scoring(conn)
        total = db.query(conn, "SELECT COUNT(DISTINCT journal_id) AS n FROM silver_gl")["n"].iloc[0]
        all_scores = db.query(conn, "SELECT * FROM risk_scores")
    truth = pd.read_csv(cfg.GROUND_TRUTH_CSV)
    summary, by_type = evaluate(high_risk, truth, total)
    for key, value in summary.items():
        print(f"{key:22s} {value}")
    print()
    print(by_type.to_string())
    print()
    print(threshold_table(all_scores, truth, total).to_string(index=False))
    print()
    print(high_risk[["rank", "journal_id", "risk_score", "created_by", "amount", "reasons"]].head(10).to_string(index=False))
