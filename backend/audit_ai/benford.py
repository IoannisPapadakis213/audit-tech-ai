"""Νόμος του Benford: ανάλυση πρώτου ψηφίου σε όλο το GL και ανά χρήστη.

Στα πραγματικά οικονομικά δεδομένα, το πρώτο ψηφίο ΔΕΝ είναι ισοπίθανο:
το 1 εμφανίζεται ~30% των φορών, το 9 μόνο ~4,6%. Όταν κάποιος «επινοεί» ποσά,
συνήθως χαλάει αυτή την κατανομή. Μέτρο απόκλισης: MAD (Nigrini).
"""
import numpy as np
import pandas as pd

from audit_ai import config as cfg
from audit_ai import database as db

DIGITS = np.arange(1, 10)
EXPECTED = np.log10(1 + 1 / DIGITS)                 # 30,1% 17,6% 12,5% ... 4,6%


def first_digit(amounts):
    """Πρώτο σημαντικό ψηφίο: 4.850,20 -> 4, 0,73 -> 7."""
    a = np.abs(np.asarray(amounts, dtype=float))
    a = a[a > 0]
    return (a / 10 ** np.floor(np.log10(a))).astype(int)


def conformity(mad):
    """Κατάταξη κατά Nigrini: πόσο «μοιάζει» με Benford."""
    limits = cfg.BENFORD_MAD_LIMITS
    if mad <= limits["close"]:
        return "close"
    if mad <= limits["acceptable"]:
        return "acceptable"
    if mad <= limits["marginal"]:
        return "marginal"
    return "nonconformity"


def analyze(amounts):
    """Επιστρέφει (πίνακας ανά ψηφίο, MAD, κατάταξη, πλήθος)."""
    digits = first_digit(amounts)
    n = len(digits)
    actual = np.bincount(digits, minlength=10)[1:] / n if n else np.zeros(9)
    table = pd.DataFrame({"digit": DIGITS, "expected": EXPECTED.round(4),
                          "actual": actual.round(4), "count": (actual * n).round().astype(int)})
    mad = float(np.mean(np.abs(actual - EXPECTED)))
    return table, round(mad, 4), conformity(mad), n


def benford_lines(conn):
    """Μία γραμμή ανά ποσό: μόνο χρεώσεις (αλλιώς κάθε ποσό μετράει διπλά) και ≥ BENFORD_MIN_AMOUNT."""
    return db.query(conn, "SELECT created_by, debit AS amount FROM silver_gl WHERE debit >= ?",
                    (cfg.BENFORD_MIN_AMOUNT,))


def run_benford(conn):
    """Benford σε όλο το GL και ανά χρήστη. Γράφει benford_overall και benford_by_user."""
    lines = benford_lines(conn)

    overall, mad, verdict, n = analyze(lines["amount"])
    overall["mad"], overall["conformity"], overall["n"] = mad, verdict, n
    db.save_table(conn, "benford_overall", overall)

    rows = []
    for user, group in lines.groupby("created_by"):
        _, mad, verdict, n = analyze(group["amount"])
        if n < cfg.BENFORD_MIN_SAMPLE:
            verdict = "insufficient_sample"            # λίγα ποσά: το συμπέρασμα δεν είναι αξιόπιστο
        rows.append({"created_by": user, "n": n, "mad": mad, "conformity": verdict})
    by_user = pd.DataFrame(rows)
    by_user["reliable"] = by_user["conformity"] != "insufficient_sample"
    by_user = by_user.sort_values(["reliable", "mad"], ascending=[False, False]).drop(columns="reliable")
    db.save_table(conn, "benford_by_user", by_user)
    return overall, by_user


if __name__ == "__main__":
    with db.connect() as conn:
        overall, by_user = run_benford(conn)
    print(f"Όλο το GL: MAD = {overall['mad'].iloc[0]} -> {overall['conformity'].iloc[0]} (n = {overall['n'].iloc[0]})")
    print(overall[["digit", "expected", "actual"]].to_string(index=False))
    print("\nΑνά χρήστη:")
    print(by_user.to_string(index=False))
