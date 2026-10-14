"""Transform: προσθέτει σε κάθε καθαρή γραμμή του GL έτοιμες «ετικέτες» για τους κανόνες.

Ποια ημερομηνία κοιτάμε:
- entry_datetime = ΠΟΤΕ πληκτρολογήθηκε η εγγραφή  -> ώρα, Σαββατοκύριακο, αργία
- posting_date   = σε ποια ΛΟΓΙΣΤΙΚΗ μέρα ανήκει    -> απόσταση από το κλείσιμο
"""
import pandas as pd

from audit_ai import config as cfg


def add_features(gl):
    """Επιστρέφει ΑΝΤΙΓΡΑΦΟ του GL με νέες στήλες. Το αρχικό δεν αλλάζει ποτέ."""
    df = gl.copy()
    entry, posting = df["entry_datetime"], df["posting_date"]

    # Κάθε γραμμή έχει ή χρέωση ή πίστωση, άρα |Χ − Π| = το ποσό της γραμμής
    df["amount"] = (df["debit"] - df["credit"]).abs().round(2)

    # Οι χρήστες συστήματος τρέχουν νύχτα και ΣΚ από σχεδιασμό: δεν είναι red flag
    is_human = ~df["created_by"].isin(list(cfg.SYSTEM_USERS))

    holidays = pd.to_datetime(list(cfg.GREEK_HOLIDAYS_2025))
    start_hour, end_hour = cfg.WORK_HOURS
    df["is_weekend"] = (entry.dt.dayofweek >= 5) & is_human               # 5 = Σάββατο, 6 = Κυριακή
    df["is_holiday"] = entry.dt.normalize().isin(holidays) & is_human
    df["is_after_hours"] = ~entry.dt.hour.between(start_hour, end_hour - 1) & is_human

    # Μέρες ως το τέλος του μήνα και ως το τέλος της χρήσης (31/12 -> 0 και στα δύο)
    df["days_to_period_end"] = (posting + pd.offsets.MonthEnd(0) - posting).dt.days
    df["days_to_year_end"] = (pd.Timestamp(cfg.FISCAL_YEAR_END) - posting).dt.days

    df["is_round_amount"] = (df["amount"] >= cfg.ROUND_AMOUNT_MIN) & (df["amount"] % cfg.ROUND_AMOUNT_MODULO == 0)
    df["is_manual"] = df["source"].eq("Manual")
    return df
