"""Tests για την πλήρη πύλη ποιότητας και την αναφορά Excel."""
import pandas as pd
import pytest

from audit_ai import data_quality as dq
from audit_ai import generator


def test_run_returns_everything():
    gl, tb, _ = generator.generate()
    result = dq.run(gl, tb)
    assert set(result) == {"clean", "quarantine", "summary", "reconciliation"}


def test_run_stops_before_quarantine_on_incomplete_extract():
    gl, tb, _ = generator.generate(break_tb=True)
    with pytest.raises(dq.ReconciliationError):
        dq.run(gl, tb)


def test_excel_report_has_three_sheets(tmp_path):
    gl, tb, _ = generator.generate()
    path = dq.write_report(dq.run(gl, tb), tmp_path / "dq.xlsx")
    sheets = pd.read_excel(path, sheet_name=None)
    assert list(sheets) == ["Σύνοψη", "Καραντίνα", "Συμφωνία GL-TB"]
    assert len(sheets["Καραντίνα"]) == 16
