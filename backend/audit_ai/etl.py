"""ETL pipeline: Extract (CSV) -> Transform (παράγωγες στήλες) -> Validate (DQ) -> Load (SQLite)."""
import sqlite3
from pathlib import Path

import pandas as pd

from audit_ai import config, data_quality


def extract(csv_path=config.RAW_CSV):
    df = pd.read_csv(csv_path)
    # errors="coerce": μια χαλασμένη ημερομηνία γίνεται NaT αντί να σκάσει όλο το load,
    # και μετά την πιάνει ο έλεγχος null_critical_fields.
    df["posting_datetime"] = pd.to_datetime(df["posting_datetime"], errors="coerce")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    return df


def transform(df):
    """Προσθέτει τα χαρακτηριστικά που χρειάζονται οι audit κανόνες."""
    start, end = config.BUSINESS_HOURS
    dt = df["posting_datetime"]
    return df.assign(
        posting_date=dt.dt.strftime("%Y-%m-%d"),
        posting_hour=dt.dt.hour,
        weekday=dt.dt.day_name(),
        is_weekend=dt.dt.weekday >= 5,
        is_after_hours=(dt.dt.hour < start) | (dt.dt.hour >= end),
        is_round_amount=(df["amount"] >= config.ROUND_AMOUNT_THRESHOLD) & (df["amount"] % 1000 == 0),
    )


def load(clean, quarantine, dq_results, db_path=config.DB_PATH):
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        clean.to_sql("general_ledger", conn, if_exists="replace", index=False)
        quarantine.to_sql("dq_quarantine", conn, if_exists="replace", index=False)
        data_quality.results_to_frame(dq_results).to_sql("dq_report", conn, if_exists="replace", index=False)
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_gl_trx ON general_ledger(transaction_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS ix_gl_account ON general_ledger(account)")


def run(csv_path=config.RAW_CSV, db_path=config.DB_PATH):
    raw = extract(csv_path)
    clean, quarantine, results = data_quality.run_checks(raw)
    clean = transform(clean)
    load(clean, quarantine, results, db_path)
    return clean, quarantine, results


if __name__ == "__main__":
    clean, quarantine, results = run()
    print("🔍 Data Quality Report")
    for r in results:
        print(f"  {'✅' if r.passed else '⚠️ '} {r.name:<26} αποτυχίες: {r.failed_rows}")
    print(f"\n💾 {len(clean)} καθαρές εγγραφές -> general_ledger")
    print(f"🚧 {len(quarantine)} εγγραφές σε καραντίνα -> dq_quarantine")
