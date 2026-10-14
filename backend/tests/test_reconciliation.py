"""Tests για τη συμφωνία GL ↔ Ισοζύγιο: η πρώτη πύλη του pipeline."""
import pytest

from audit_ai import data_quality as dq
from audit_ai import generator


@pytest.fixture(scope="module")
def data():
    gl, tb, _ = generator.generate()
    return gl, tb


def test_complete_extract_reconciles(data):
    gl, tb = data
    rec = dq.reconcile(gl, tb)
    assert (rec["status"] == "OK").all()


def test_incomplete_extract_stops_the_pipeline():
    gl, tb, _ = generator.generate(break_tb=True)
    with pytest.raises(dq.ReconciliationError) as err:
        dq.reconcile(gl, tb)
    assert (err.value.reconciliation["status"] == "ΔΙΑΦΟΡΑ").any()


def test_missing_column_raises(data):
    gl, _ = data
    with pytest.raises(dq.SchemaError):
        dq.check_schema(gl.drop(columns=["account"]))


def test_csv_roundtrip_still_reconciles(data, tmp_path):
    gl, tb = data
    paths = generator.save(gl, tb, gl.head(0), raw_dir=tmp_path)
    gl2, tb2 = dq.read_raw(paths["gl"], paths["tb"])
    assert (dq.reconcile(gl2, tb2)["status"] == "OK").all()
