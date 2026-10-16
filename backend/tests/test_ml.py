"""Tests για το Isolation Forest: αναπαραγωγιμότητα και ποιότητα ευρημάτων."""
import pytest

from audit_ai import config as cfg
from audit_ai import database as db
from audit_ai import generator, ml, pipeline


@pytest.fixture(scope="module")
def env(tmp_path_factory):
    folder = tmp_path_factory.mktemp("audit")
    gl, tb, truth = generator.generate()
    paths = generator.save(gl, tb, truth, raw_dir=folder)
    conn = db.connect(pipeline.run(paths["gl"], paths["tb"], folder / "audit.db"))
    return conn, truth


def flagged(conn):
    return set(db.query(conn, "SELECT journal_id FROM rule_hits WHERE rule = 'isolation_forest'")["journal_id"])


def test_same_seed_same_result(env):
    conn, _ = env
    first = flagged(conn)
    ml.run_isolation_forest(conn)
    assert flagged(conn) == first


def test_flags_about_one_percent(env):
    conn, _ = env
    total = db.query(conn, "SELECT COUNT(*) AS n FROM ml_scores")["n"].iloc[0]
    assert len(flagged(conn)) == pytest.approx(total * cfg.ISOLATION_FOREST["contamination"], abs=2)


def test_system_jobs_are_not_in_the_model(env):
    conn, _ = env
    users = set(db.query(conn, "SELECT DISTINCT created_by FROM ml_scores")["created_by"])
    assert not users & set(cfg.SYSTEM_USERS)


def test_needles_are_the_most_unusual(env):
    conn, truth = env
    top5 = set(db.query(conn, "SELECT journal_id FROM ml_scores ORDER BY anomaly_score DESC LIMIT 5")["journal_id"])
    assert top5 == set(truth.loc[truth["anomaly_type"] == "multi_flag", "journal_id"])


def test_most_flags_are_real_anomalies(env):
    conn, truth = env
    found = flagged(conn)
    precision = len(found & set(truth["journal_id"])) / len(found)
    assert precision >= 0.8
