"""Machine learning: Isolation Forest σε επίπεδο journal.

Ιδέα: φτιάχνουμε πολλά τυχαία «δέντρα» που χωρίζουν τα journals με τυχαίες ερωτήσεις
(π.χ. «ώρα < 14;», «ποσό > 3.000;»). Ένα ΣΥΝΗΘΙΣΜΕΝΟ journal μοιάζει με πολλά άλλα και
χρειάζεται πολλές ερωτήσεις για να απομονωθεί. Ένα ΑΣΥΝΗΘΙΣΤΟ απομονώνεται γρήγορα.
Λίγες ερωτήσεις = ύποπτο. Δεν χρειάζεται κανέναν κανόνα και καμία «σωστή απάντηση».
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from audit_ai import config as cfg
from audit_ai import database as db

FEATURES = [
    "log_amount",         # πόσο μεγάλο είναι το journal
    "n_lines",            # πόσες γραμμές έχει
    "hour",               # τι ώρα πληκτρολογήθηκε
    "day_of_week",        # τι μέρα (0 = Δευτέρα ... 6 = Κυριακή)
    "days_to_year_end",   # πόσο κοντά στο κλείσιμο
    "is_manual",          # χειροκίνητο ή αυτόματο
    "user_share",         # πόσο συχνός είναι ο χρήστης (σπάνιος χρήστης = ασυνήθιστο)
    "account_rarity",     # πόσο σπάνιος είναι ο πιο σπάνιος λογαριασμός του
]


def journal_features(conn):
    """Μία γραμμή ανά journal, με αριθμητικά χαρακτηριστικά που «καταλαβαίνει» ο αλγόριθμος."""
    # Οι αυτόματες εργασίες του συστήματος (μισθοδοσία, αποσβέσεις) τρέχουν νύχτα από σχεδιασμό.
    # Αν μπουν στο μοντέλο, «κλέβουν» τις θέσεις των ασυνήθιστων: τις εξαιρούμε, όπως και στο transform.
    lines = db.query(conn, f"SELECT * FROM silver_gl WHERE created_by NOT IN ({', '.join(repr(u) for u in cfg.SYSTEM_USERS)})")
    lines["entry_datetime"] = pd.to_datetime(lines["entry_datetime"])

    account_uses = lines.groupby("account")["journal_id"].nunique()
    lines["account_uses"] = lines["account"].map(account_uses)

    j = lines.groupby("journal_id").agg(
        amount=("debit", "sum"),
        n_lines=("line_id", "count"),
        entry=("entry_datetime", "first"),
        days_to_year_end=("days_to_year_end", "first"),
        is_manual=("is_manual", "max"),
        created_by=("created_by", "first"),
        min_account_uses=("account_uses", "min"),
    )
    j["log_amount"] = np.log10(j["amount"].clip(lower=1))
    j["hour"] = j["entry"].dt.hour
    j["day_of_week"] = j["entry"].dt.dayofweek
    j["user_share"] = j["created_by"].map(j["created_by"].value_counts(normalize=True))
    j["account_rarity"] = 1 / j["min_account_uses"]
    return j.reset_index()


def run_isolation_forest(conn):
    """Εκπαιδεύει το Isolation Forest, γράφει τα σκορ στον πίνακα ml_scores
    και προσθέτει τον κανόνα isolation_forest στο rule_hits."""
    j = journal_features(conn)
    model = IsolationForest(**cfg.ISOLATION_FOREST)
    model.fit(j[FEATURES])

    j["anomaly_score"] = (-model.score_samples(j[FEATURES])).round(4)   # μεγαλύτερο = πιο ασυνήθιστο
    j["is_anomaly"] = model.predict(j[FEATURES]) == -1
    scores = j[["journal_id", "created_by", "amount"] + FEATURES + ["anomaly_score", "is_anomaly"]]
    scores = scores.sort_values("anomaly_score", ascending=False)
    db.save_table(conn, "ml_scores", scores)

    hits = scores.loc[scores["is_anomaly"], ["journal_id"]].copy()
    hits["rule"] = "isolation_forest"
    hits["weight"] = cfg.RULE_WEIGHTS["isolation_forest"]
    conn.execute("DELETE FROM rule_hits WHERE rule = 'isolation_forest'")
    hits.to_sql("rule_hits", conn, if_exists="append", index=False)
    return scores


if __name__ == "__main__":
    with db.connect() as conn:
        scores = run_isolation_forest(conn)
    flagged = scores[scores["is_anomaly"]]
    print(f"Journals: {len(scores)} | Ασυνήθιστα κατά το Isolation Forest: {len(flagged)}")
    print(flagged[["journal_id", "created_by", "amount", "hour", "day_of_week", "anomaly_score"]].head(12).to_string(index=False))
