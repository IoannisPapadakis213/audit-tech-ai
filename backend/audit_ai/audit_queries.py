"""Journal Entry Testing σε SQL. Κάθε σενάριο = ένας κανόνας κινδύνου που θα έτρεχε ένας ελεγκτής."""
import sqlite3

import pandas as pd

from audit_ai import config

# Κάθε query επιστρέφει τις ύποπτες εγγραφές. Τα ονόματα γίνονται αργότερα API endpoints.
QUERIES = {
    # Στρογγυλά μεγάλα ποσά: οι πραγματικές συναλλαγές σπάνια είναι "τέλειες" χιλιάδες.
    "round_amounts": """
        SELECT transaction_id, posting_datetime, account, amount, user_id, description
        FROM general_ledger
        WHERE is_round_amount = 1
        ORDER BY amount DESC
    """,

    # Εγγραφές Σαββατοκύριακου. Το strftime('%w') δίνει 0=Κυριακή ... 6=Σάββατο.
    # (Έχουμε και την έτοιμη στήλη is_weekend, εδώ δείχνουμε και την καθαρή SQL εκδοχή.)
    "weekend_entries": """
        SELECT transaction_id, posting_datetime, weekday, account, amount, user_id, description
        FROM general_ledger
        WHERE strftime('%w', posting_datetime) IN ('0', '6')
        ORDER BY posting_datetime
    """,

    "after_hours_entries": """
        SELECT transaction_id, posting_datetime, posting_hour, account, amount, user_id
        FROM general_ledger
        WHERE is_after_hours = 1
        ORDER BY posting_hour
    """,

    # Window function: μετράμε πόσες εγγραφές έχουν ίδιο λογαριασμό/ποσό/ημέρα/χρήστη
    # χωρίς να "μαζέψουμε" τις γραμμές όπως θα έκανε το GROUP BY.
    "duplicate_payments": """
        SELECT *
        FROM (
            SELECT transaction_id, posting_datetime, account, amount, user_id,
                   COUNT(*) OVER (PARTITION BY account, amount, posting_date, user_id) AS times_seen
            FROM general_ledger
        )
        WHERE times_seen > 1
        ORDER BY amount DESC, posting_datetime
    """,

    # Outlier ανά λογαριασμό με window AVG(): κάθε γραμμή βλέπει τον μέσο όρο του λογαριασμού της.
    "account_outliers": f"""
        SELECT *
        FROM (
            SELECT transaction_id, account, amount, user_id,
                   ROUND(AVG(amount) OVER (PARTITION BY account), 2) AS account_avg
            FROM general_ledger
        )
        WHERE amount > account_avg * {config.OUTLIER_MULTIPLIER}
        ORDER BY amount / account_avg DESC
    """,

    # Προφίλ χρηστών: συγκέντρωση κινδύνου (ποιος χειρίζεται τι, πόσο συχνά εκτός ωραρίου).
    "user_activity": """
        SELECT user_id,
               COUNT(*)                              AS total_entries,
               ROUND(SUM(amount), 2)                 AS total_value,
               SUM(is_weekend)                       AS weekend_entries,
               SUM(is_after_hours)                   AS after_hours_entries,
               SUM(is_round_amount)                  AS round_amount_entries
        FROM general_ledger
        GROUP BY user_id
        ORDER BY total_value DESC
    """,
}


def run_query(name, db_path=config.DB_PATH):
    with sqlite3.connect(db_path) as conn:
        return pd.read_sql_query(QUERIES[name], conn)


if __name__ == "__main__":
    pd.set_option("display.width", 140)
    for name in QUERIES:
        result = run_query(name)
        print(f"\n🚨 {name}: {len(result)} γραμμές")
        print(result.head(5).to_string(index=False))
