"""Tests για το risk score και τη λίστα του ελεγκτή."""
import pytest

from audit_ai import config as cfg
from audit_ai import database as db
from audit_ai import generator, pipeline, scoring


@pytest.fixture(scope="module")
def env(tmp_path_factory):
    folder = tmp_path_factory.mktemp("audit")
    gl, tb, truth = generator.generate()
    paths = generator.save(gl, tb, truth, raw_dir=folder)
    conn = db.connect(pipeline.run(paths["gl"], paths["tb"], folder / "audit.db"))
    high_risk = db.query(conn, "SELECT * FROM high_risk_journals")
    total = db.query(conn, "SELECT COUNT(DISTINCT journal_id) AS n FROM silver_gl")["n"].iloc[0]
    return conn, truth, high_risk, total


def test_score_is_sum_of_rule_weights(env):
    conn, *_ = env
    check = db.query(conn, """
        SELECT s.journal_id, s.risk_score, SUM(h.weight) AS expected
        FROM risk_scores AS s JOIN rule_hits AS h ON h.journal_id = s.journal_id
        GROUP BY s.journal_id
    """)
    assert (check["risk_score"] == check["expected"]).all()


def test_list_respects_threshold_and_is_sorted(env):
    _, _, high_risk, _ = env
    assert (high_risk["risk_score"] >= cfg.RISK_SCORE_THRESHOLD).all()
    assert high_risk["risk_score"].is_monotonic_decreasing


def test_needles_are_at_the_top(env):
    _, truth, high_risk, _ = env
    needles = set(truth.loc[truth["anomaly_type"] == "multi_flag", "journal_id"])
    assert set(high_risk.head(5)["journal_id"]) == needles


def test_list_is_small_and_precise(env):
    _, truth, high_risk, total = env
    summary, _ = scoring.evaluate(high_risk, truth, total)
    assert summary["μέγεθος_λίστας"] < total * 0.02          # λιγότερο από 2% των journals
    assert summary["precision"] >= 0.9


def test_lower_threshold_means_more_recall(env):
    conn, truth, _, total = env
    table = scoring.threshold_table(db.query(conn, "SELECT * FROM risk_scores"), truth, total)
    assert table["recall"].is_monotonic_decreasing
    assert table["μέγεθος_λίστας"].is_monotonic_decreasing
