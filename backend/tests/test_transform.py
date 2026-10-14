"""Tests για το transform: μικρές χειροποίητες γραμμές, ώστε να φαίνεται καθαρά τι περιμένουμε."""
import pandas as pd

from audit_ai import transform


def make_line(entry, debit=100.0, credit=0.0, user="ACC_01", source="Automatic"):
    """Μία γραμμή GL με λογικές προεπιλογές. Σε κάθε test αλλάζουμε μόνο ό,τι μας ενδιαφέρει."""
    entry = pd.Timestamp(entry)
    return {"journal_id": "JE-T", "line_id": 1, "account": "64.00",
            "entry_datetime": entry, "posting_date": entry.normalize(),
            "debit": debit, "credit": credit, "created_by": user, "approved_by": None,
            "source": source, "description": "test", "vendor_id": None}


def features(**kwargs):
    return transform.add_features(pd.DataFrame([make_line(**kwargs)])).iloc[0]


def test_saturday_is_weekend():
    assert features(entry="2025-03-08 10:00")["is_weekend"]                 # Σάββατο


def test_greek_holiday_is_detected():
    row = features(entry="2025-03-25 10:00")                                # 25η Μαρτίου, Τρίτη
    assert row["is_holiday"] and not row["is_weekend"]


def test_working_hours_boundaries():
    assert not features(entry="2025-03-04 08:00")["is_after_hours"]         # αρχή ωραρίου
    assert not features(entry="2025-03-04 17:59")["is_after_hours"]
    assert features(entry="2025-03-04 18:00")["is_after_hours"]             # 18:00 = ήδη εκτός
    assert features(entry="2025-03-04 02:45")["is_after_hours"]


def test_system_users_are_never_flagged():
    row = features(entry="2025-03-08 23:30", user="SYS_BATCH")              # Σάββατο βράδυ
    assert not row["is_weekend"] and not row["is_after_hours"]


def test_days_to_period_and_year_end():
    assert features(entry="2025-03-25 10:00")["days_to_period_end"] == 6    # ως τις 31/3
    assert features(entry="2025-12-31 10:00")["days_to_year_end"] == 0


def test_round_amount_needs_size_and_zeros():
    assert features(entry="2025-03-04 10:00", debit=25_000.0)["is_round_amount"]
    assert not features(entry="2025-03-04 10:00", debit=5_000.0)["is_round_amount"]     # μικρό
    assert not features(entry="2025-03-04 10:00", debit=25_300.0)["is_round_amount"]    # όχι χιλιάδες


def test_amount_for_credit_lines_and_manual_flag():
    row = features(entry="2025-03-04 10:00", debit=0.0, credit=1_234.5, source="Manual")
    assert row["amount"] == 1_234.5 and row["is_manual"]


def test_input_is_not_modified():
    gl = pd.DataFrame([make_line(entry="2025-03-04 10:00")])
    transform.add_features(gl)
    assert "amount" not in gl.columns
