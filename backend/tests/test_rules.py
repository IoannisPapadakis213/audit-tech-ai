"""Tests για τους κανόνες: κάθε κανόνας πρέπει να βρίσκει ΟΛΕΣ τις ανωμαλίες που φυτέψαμε γι' αυτόν."""
import pytest

from audit_ai import config as cfg
from audit_ai import database as db
from audit_ai import generator, pipeline, rules


@pytest.fixture(scope="module")
def env(tmp_path_factory):
    folder = tmp_path_factory.mktemp("audit")
    gl, tb, truth = generator.generate()
    paths = generator.save(gl, tb, truth, raw_dir=folder)
    conn = db.connect(pipeline.run(paths["gl"], paths["tb"], folder / "audit.db"))
    return conn, truth


@pytest.mark.parametrize("rule", list(rules.RULES))
def test_rule_finds_every_planted_anomaly(env, rule):
    conn, truth = env
    found = set(db.query(conn, "SELECT journal_id FROM rule_hits WHERE rule = ?", (rule,))["journal_id"])
    planted = set(truth.loc[truth["anomaly_type"] == rule, "journal_id"])
    assert planted <= found, f"{rule}: έλειψαν {sorted(planted - found)}"


def test_one_hit_per_journal_and_rule(env):
    conn, _ = env
    dupes = db.query(conn, "SELECT journal_id, rule FROM rule_hits GROUP BY journal_id, rule HAVING COUNT(*) > 1")
    assert dupes.empty


def test_system_users_never_hit_time_rules(env):
    conn, _ = env
    hits = db.query(conn, f"""
        SELECT DISTINCT h.journal_id FROM rule_hits AS h
        JOIN silver_gl AS g ON g.journal_id = h.journal_id
        WHERE h.rule IN ('weekend_holiday', 'after_hours')
          AND g.created_by IN ({rules._in_list(cfg.SYSTEM_USERS)})
    """)
    assert hits.empty


def test_needles_score_above_threshold(env):
    conn, truth = env
    needles = list(truth.loc[truth["anomaly_type"] == "multi_flag", "journal_id"])
    scores = db.query(conn, f"""
        SELECT journal_id, SUM(weight) AS score FROM rule_hits
        WHERE journal_id IN ({rules._in_list(needles)})
        GROUP BY journal_id
    """)
    assert len(scores) == len(needles)
    assert (scores["score"] >= cfg.RISK_SCORE_THRESHOLD).all()
