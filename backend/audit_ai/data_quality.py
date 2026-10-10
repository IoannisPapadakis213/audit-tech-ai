"""Data Quality Controls: τι ελέγχουμε ΠΡΙΝ εμπιστευτούμε τα δεδομένα για audit.

Κάθε έλεγχος επιστρέφει μια μάσκα (True = η γραμμή αποτυγχάνει). Οι γραμμές που
αποτυγχάνουν δεν σβήνονται: πάνε σε "καραντίνα" με τον λόγο, για να τις δει ο ελεγκτής.
"""
from dataclasses import dataclass

import pandas as pd

from audit_ai import config


class SchemaError(Exception):
    """Λείπουν βασικές στήλες: δεν έχει νόημα να συνεχίσει το pipeline."""


@dataclass
class CheckResult:
    name: str
    description: str
    failed_rows: int

    @property
    def passed(self):
        return self.failed_rows == 0


def check_schema(df):
    missing = set(config.REQUIRED_COLUMNS) - set(df.columns)
    if missing:
        raise SchemaError(f"Λείπουν στήλες: {sorted(missing)}")


# (όνομα, περιγραφή, συνάρτηση df -> μάσκα αποτυχίας)
CHECKS = [
    (
        "null_critical_fields",
        "Κενές τιμές σε transaction_id, ημερομηνία, λογαριασμό ή ποσό",
        lambda df: df[["transaction_id", "posting_datetime", "account", "amount"]].isna().any(axis=1),
    ),
    (
        "non_positive_amount",
        "Ποσό μηδενικό ή αρνητικό",
        lambda df: df["amount"].notna() & (df["amount"] <= 0),
    ),
    (
        "duplicate_transaction_id",
        "Το ίδιο transaction_id εμφανίζεται πάνω από μία φορά",
        lambda df: df["transaction_id"].duplicated(keep=False),
    ),
    (
        "outside_fiscal_year",
        f"Ημερομηνία εκτός χρήσης {config.FISCAL_YEAR}",
        lambda df: df["posting_datetime"].notna() & (df["posting_datetime"].dt.year != config.FISCAL_YEAR),
    ),
    (
        "unknown_account",
        "Λογαριασμός εκτός λογιστικού σχεδίου",
        lambda df: df["account"].notna() & ~df["account"].isin(config.CHART_OF_ACCOUNTS),
    ),
]


def run_checks(df):
    """Επιστρέφει (clean, quarantine, results)."""
    check_schema(df)

    results = []
    reasons = pd.Series("", index=df.index)
    for name, description, rule in CHECKS:
        failed = rule(df)
        results.append(CheckResult(name, description, int(failed.sum())))
        reasons[failed] += name + ";"

    bad = reasons != ""
    clean = df[~bad].copy()
    quarantine = df[bad].assign(dq_reasons=reasons[bad].str.rstrip(";"))
    return clean, quarantine, results


def results_to_frame(results):
    return pd.DataFrame(
        [{"check": r.name, "description": r.description, "failed_rows": r.failed_rows, "passed": r.passed}
         for r in results]
    )
