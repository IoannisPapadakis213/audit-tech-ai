"""Παράγει ένα συνθετικό General Ledger με γνωστές ("φυτεμένες") ανωμαλίες.

Επειδή ξέρουμε ακριβώς ποιες εγγραφές είναι ύποπτες (ground truth), μπορούμε
αργότερα να μετρήσουμε αν οι κανόνες και τα μοντέλα μας τις βρίσκουν.
"""
from pathlib import Path

import numpy as np
import pandas as pd

from audit_ai import config


def _random_business_datetimes(rng, n, hours=config.BUSINESS_HOURS):
    """Τυχαίες εργάσιμες μέρες (Δευ-Παρ) της χρήσης, σε ώρες γραφείου."""
    year = config.FISCAL_YEAR
    business_days = pd.bdate_range(f"{year}-01-01", f"{year}-12-31")
    days = pd.DatetimeIndex(rng.choice(business_days, n))
    hour = rng.integers(hours[0], hours[1], n)
    minute = rng.integers(0, 60, n)
    return days + pd.to_timedelta(hour, unit="h") + pd.to_timedelta(minute, unit="min")


def generate_gl(num_records=10_000, seed=42):
    """Επιστρέφει (gl, ground_truth): το ledger και ποιες εγγραφές φυτέψαμε ως ανωμαλίες."""
    rng = np.random.default_rng(seed)

    # Τα πραγματικά οικονομικά ποσά ακολουθούν περίπου log-normal κατανομή:
    # πολλά μικρά, λίγα μεγάλα. Έτσι ισχύει και ο νόμος του Benford.
    amounts = np.round(rng.lognormal(mean=6.5, sigma=1.1, size=num_records), 2)

    gl = pd.DataFrame({
        "transaction_id": [f"TRX-{100000 + i}" for i in range(num_records)],
        "posting_datetime": _random_business_datetimes(rng, num_records),
        "account": rng.choice(config.CHART_OF_ACCOUNTS, num_records),
        "amount": amounts,
        "user_id": rng.choice(config.USERS, num_records),
        "description": "Standard entry",
    })

    injected = []  # (transaction_id, anomaly_type)
    used = set()

    def pick(k):
        """Διαλέγει k γραμμές που δεν έχουν ήδη χρησιμοποιηθεί για άλλη ανωμαλία."""
        available = gl.index.difference(list(used))
        idx = rng.choice(available, k, replace=False)
        used.update(idx)
        return idx

    # Α. Μεγάλα στρογγυλά ποσά (ISA 240: ασυνήθιστα / στρογγυλά ποσά)
    idx = pick(50)
    gl.loc[idx, "amount"] = rng.choice([10_000.0, 25_000.0, 50_000.0], len(idx))
    gl.loc[idx, "description"] = "Consulting advance payment"
    injected += [(t, "round_amount") for t in gl.loc[idx, "transaction_id"]]

    # Β. Εγγραφές Σαββατοκύριακου από τον "ύποπτο" User_04
    idx = pick(30)
    saturday_or_sunday = rng.integers(5, 7, len(idx))
    current = gl.loc[idx, "posting_datetime"].dt.weekday.to_numpy()
    gl.loc[idx, "posting_datetime"] += pd.to_timedelta(saturday_or_sunday - current, unit="D")
    gl.loc[idx, "user_id"] = "User_04"
    gl.loc[idx, "description"] = "Urgent weekend adjustment"
    injected += [(t, "weekend_entry") for t in gl.loc[idx, "transaction_id"]]

    # Γ. Εγγραφές εκτός ωραρίου (22:00 - 04:59)
    idx = pick(20)
    late_hour = rng.choice([22, 23, 0, 1, 2, 3, 4], len(idx))
    gl.loc[idx, "posting_datetime"] = (
        gl.loc[idx, "posting_datetime"].dt.normalize()
        + pd.to_timedelta(late_hour, unit="h")
        + pd.to_timedelta(rng.integers(0, 60, len(idx)), unit="min")
    )
    injected += [(t, "after_hours") for t in gl.loc[idx, "transaction_id"]]

    # Δ. Διπλές πληρωμές: ίδιος λογαριασμός, ποσό, ημέρα, χρήστης, νέο transaction_id
    idx = pick(15)
    duplicates = gl.loc[idx].copy()
    duplicates["transaction_id"] = [f"TRX-{900000 + i}" for i in range(len(duplicates))]
    gl = pd.concat([gl, duplicates], ignore_index=True)
    injected += [(t, "duplicate_payment") for t in duplicates["transaction_id"]]

    # Ε. "Βρώμικα" δεδομένα: αυτά πρέπει να τα πιάσει το Data Quality, όχι ο έλεγχος απάτης
    dirty = rng.choice(gl.index.difference(list(used)), 10, replace=False)
    gl.loc[dirty[:4], "amount"] = np.nan                                   # κενό ποσό
    gl.loc[dirty[4:6], "account"] = "Misc"                                 # εκτός λογιστικού σχεδίου
    gl.loc[dirty[6:8], "posting_datetime"] += pd.DateOffset(years=1)       # εκτός χρήσης
    gl.loc[dirty[8:10], "transaction_id"] = gl.loc[dirty[0], "transaction_id"]  # διπλό ID

    gl = gl.sample(frac=1, random_state=seed).reset_index(drop=True)  # ανακάτεμα
    ground_truth = pd.DataFrame(injected, columns=["transaction_id", "anomaly_type"])
    return gl, ground_truth


def save(gl, ground_truth, csv_path=config.RAW_CSV, truth_path=config.GROUND_TRUTH_CSV):
    Path(csv_path).parent.mkdir(parents=True, exist_ok=True)
    gl.to_csv(csv_path, index=False)
    ground_truth.to_csv(truth_path, index=False)


if __name__ == "__main__":
    gl, truth = generate_gl()
    save(gl, truth)
    print(f"✅ {len(gl)} εγγραφές -> {config.RAW_CSV}")
    print(f"✅ {len(truth)} φυτεμένες ανωμαλίες -> {config.GROUND_TRUTH_CSV}")
