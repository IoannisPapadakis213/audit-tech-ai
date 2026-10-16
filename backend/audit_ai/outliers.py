"""Robust z-score: ποσά παράλογα μεγάλα (ή μικρά) για τον λογαριασμό τους.

Απλό z-score = (x − μέσος) / τυπική απόκλιση. Πρόβλημα: τα ίδια τα ακραία ποσά
«τραβάνε» τον μέσο και την απόκλιση, και κρύβονται. Το robust z-score χρησιμοποιεί
διάμεσο και MAD, που δεν επηρεάζονται από λίγες ακραίες τιμές (Iglewicz & Hoaglin):

    z = 0,6745 · (x − διάμεσος) / MAD,  ακραίο αν |z| > 3,5

Το υπολογίζουμε στο log10(ποσού): τα ποσά είναι lognormal, και στην απλή κλίμακα
όλη η φυσιολογική «ουρά» των μεγάλων ποσών θα έβγαινε ακραία.
"""
import numpy as np
import pandas as pd

from audit_ai import config as cfg
from audit_ai import database as db


def robust_z(values):
    """Robust z-score για μια σειρά αριθμών. Αν MAD = 0 (όλα ίδια), επιστρέφει 0."""
    values = np.asarray(values, dtype=float)
    median = np.median(values)
    mad = np.median(np.abs(values - median))
    if mad == 0:
        return np.zeros_like(values)
    return 0.6745 * (values - median) / mad


def run_robust_z(conn):
    """Υπολογίζει z ανά λογαριασμό, γράφει τα ακραία στον πίνακα robust_z_outliers
    και προσθέτει τον κανόνα robust_z_outlier στο rule_hits."""
    lines = db.query(conn, "SELECT journal_id, account, debit AS amount FROM silver_gl WHERE debit > 0")

    parts = []
    for account, group in lines.groupby("account"):
        if len(group) < cfg.ROBUST_Z_MIN_LINES:          # λίγες γραμμές: το MAD δεν είναι αξιόπιστο
            continue
        group = group.copy()
        group["z"] = robust_z(np.log10(group["amount"])).round(2)
        parts.append(group)
    scored = pd.concat(parts, ignore_index=True)

    outliers = scored[scored["z"].abs() > cfg.ROBUST_Z_THRESHOLD].sort_values("z", ascending=False)
    db.save_table(conn, "robust_z_outliers", outliers)

    hits = outliers[["journal_id"]].drop_duplicates()
    hits["rule"] = "robust_z_outlier"
    hits["weight"] = cfg.RULE_WEIGHTS["robust_z_outlier"]
    conn.execute("DELETE FROM rule_hits WHERE rule = 'robust_z_outlier'")
    hits.to_sql("rule_hits", conn, if_exists="append", index=False)
    return outliers


if __name__ == "__main__":
    with db.connect() as conn:
        out = run_robust_z(conn)
    print(f"Ακραία ποσά: {len(out)}")
    print(out.to_string(index=False))
