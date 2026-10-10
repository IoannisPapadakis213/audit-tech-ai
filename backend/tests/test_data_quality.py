import pandas as pd
import pytest

from audit_ai import data_quality


def make_gl(**overrides):
    """Μια μικρή, καθαρή εγγραφή. Με overrides "χαλάμε" ό,τι θέλουμε να ελέγξουμε."""
    row = {
        "transaction_id": "TRX-1",
        "posting_datetime": pd.Timestamp("2023-05-10 10:00"),
        "account": "Travel",
        "amount": 120.5,
        "user_id": "User_01",
        "description": "Standard entry",
    }
    row.update(overrides)
    return pd.DataFrame([row])


def test_clean_row_passes_all_checks():
    clean, quarantine, results = data_quality.run_checks(make_gl())
    assert len(clean) == 1
    assert quarantine.empty
    assert all(r.passed for r in results)


@pytest.mark.parametrize("overrides, expected_check", [
    ({"amount": None}, "null_critical_fields"),
    ({"amount": -50.0}, "non_positive_amount"),
    ({"account": "Misc"}, "unknown_account"),
    ({"posting_datetime": pd.Timestamp("2024-01-03")}, "outside_fiscal_year"),
])
def test_bad_row_goes_to_quarantine(overrides, expected_check):
    clean, quarantine, _ = data_quality.run_checks(make_gl(**overrides))
    assert clean.empty
    assert quarantine.iloc[0]["dq_reasons"] == expected_check


def test_duplicate_ids_are_both_quarantined():
    df = pd.concat([make_gl(), make_gl()], ignore_index=True)
    clean, quarantine, _ = data_quality.run_checks(df)
    assert clean.empty
    assert len(quarantine) == 2


def test_missing_column_raises():
    with pytest.raises(data_quality.SchemaError):
        data_quality.run_checks(make_gl().drop(columns=["amount"]))
