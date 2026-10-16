"""Tests για το run log και το τελικό Excel."""
import pandas as pd
import pytest

from audit_ai import database as db
from audit_ai import generator, pipeline, run_log


@pytest.fixture(scope="module")
def env(tmp_path_factory):
    folder = tmp_path_factory.mktemp("audit")
    gl, tb, truth = generator.generate()
    paths = generator.save(gl, tb, truth, raw_dir=folder)
    report = folder / "audit_report.xlsx"
    conn = db.connect(pipeline.run(paths["gl"], paths["tb"], folder / "audit.db", report))
    return conn, paths, report


def test_same_file_same_hash(env):
    _, paths, _ = env
    assert run_log.file_hash(paths["gl"]) == run_log.file_hash(paths["gl"])


def test_changed_file_changes_hash(tmp_path):
    a, b = tmp_path / "a.csv", tmp_path / "b.csv"
    a.write_text("1000.00")
    b.write_text("1000.01")                       # ένα λεπτό διαφορά
    assert run_log.file_hash(a) != run_log.file_hash(b)


def test_run_log_records_the_run(env):
    conn, paths, _ = env
    last = db.query(conn, "SELECT * FROM run_log").iloc[-1]
    assert last["gl_file_hash"] == run_log.file_hash(paths["gl"])[:16]
    assert last["lines_received"] == last["lines_quarantined"] + db.query(conn, "SELECT COUNT(*) AS n FROM silver_gl")["n"].iloc[0]
    assert last["high_risk_journals"] > 0


def test_two_runs_same_inputs_same_results(env):
    conn, paths, report = env
    pipeline.run(paths["gl"], paths["tb"], paths["gl"].parent / "audit.db", report)
    runs = db.query(conn, "SELECT * FROM run_log")
    assert len(runs) >= 2
    a, b = runs.iloc[-2], runs.iloc[-1]
    assert a["run_id"] != b["run_id"]
    for col in ("gl_file_hash", "config_hash", "high_risk_journals", "journals_analyzed"):
        assert a[col] == b[col]


def test_excel_report_has_all_sheets(env):
    _, _, report = env
    sheets = pd.read_excel(report, sheet_name=None)
    assert list(sheets) == ["Σύνοψη", "Λίστα υψηλού κινδύνου", "Γραμμές λίστας", "Κανόνες",
                            "Benford ανά χρήστη", "Ποιότητα δεδομένων", "Συμφωνία GL-TB"]
    assert len(sheets["Λίστα υψηλού κινδύνου"]) == 19
