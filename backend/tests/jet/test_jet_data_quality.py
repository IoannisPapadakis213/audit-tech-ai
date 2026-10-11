import pandas as pd
import pytest

from audit_ai.data_quality import SchemaError
from audit_ai.jet import data_quality as dq
from audit_ai.jet import generator


@pytest.fixture(scope="module")
def raw():
    gl, tb, _ = generator.generate(seed=42)
    return gl, tb


@pytest.fixture(scope="module")
def result(raw):
    return dq.run_checks(*raw)


def test_every_planted_dq_problem_is_quarantined(result):
    # 7 χαλασμένα journals: 2 κενά πεδία, διπλό line, μετά το post-close,
    # άγνωστος λογαριασμός, μη ισοσκελισμένο, εκτός χρήσης
    assert result.quarantine["journal_id"].nunique() == 7
    failed = {c.name for c in result.checks if not c.passed}
    assert failed == {
        "missing_required_field", "duplicate_line_id", "outside_fiscal_year",
        "entered_after_post_close", "unknown_account", "unbalanced_journal",
    }


def test_nothing_is_lost(raw, result):
    gl, _ = raw
    assert len(result.clean) + len(result.quarantine) == len(gl)


def test_quarantine_takes_whole_journal(result):
    assert not set(result.clean["journal_id"]) & set(result.quarantine["journal_id"])
    assert "same_journal" in set(result.quarantine["dq_reasons"])


def test_clean_journals_are_balanced(result):
    net = result.clean.groupby("journal_id")[["debit", "credit"]].sum().eval("debit - credit")
    assert net.abs().max() < 0.01


def test_reconciliation_passes_on_complete_extract(result):
    assert result.reconciliation["reconciled"].all()


def test_incomplete_extract_stops_the_pipeline():
    gl, tb, _ = generator.generate(seed=42, break_tb=True)
    with pytest.raises(dq.ReconciliationError) as err:
        dq.run_checks(gl, tb)
    assert not err.value.reconciliation["reconciled"].all()


def test_missing_column_raises(raw):
    gl, tb = raw
    with pytest.raises(SchemaError):
        dq.run_checks(gl.drop(columns="vendor_id"), tb)


def test_excel_report_has_three_sheets(result, tmp_path):
    path = dq.write_dq_report(tmp_path / "dq.xlsx", result.checks, result.quarantine, result.reconciliation)
    assert set(pd.ExcelFile(path).sheet_names) == {"Σύνοψη", "Καραντίνα", "Συμφωνία GL-TB"}


def test_read_raw_roundtrip(tmp_path):
    gl, tb, truth = generator.generate(seed=1)
    paths = generator.save(gl, tb, truth, tmp_path)
    gl2, tb2 = dq.read_raw(paths["gl"], paths["tb"])
    assert len(gl2) == len(gl)
    assert dq.reconcile(gl2, tb2)["reconciled"].all()
