"""Tests για το robust z-score: πρώτα σε μικρά παραδείγματα, μετά στο GL μας."""
import numpy as np
import pytest

from audit_ai import database as db
from audit_ai import generator, outliers, pipeline


def test_robust_z_flags_the_extreme_value():
    z = outliers.robust_z([10, 11, 9, 10, 12, 10, 11, 500])
    assert abs(z[-1]) > 3.5 and (np.abs(z[:-1]) <= 3.5).all()


def test_robust_z_is_not_fooled_by_the_outlier_itself():
    """Με απλό z-score, μια τεράστια τιμή «φουσκώνει» την τυπική απόκλιση και κρύβει μια δεύτερη."""
    values = np.array([10, 11, 9, 10, 12, 10, 11, 10, 100, 100_000], dtype=float)
    plain = (values - values.mean()) / values.std()
    robust = outliers.robust_z(values)
    assert abs(plain[-2]) < 3.5          # το απλό z ΔΕΝ βλέπει το 100
    assert abs(robust[-2]) > 3.5         # το robust z το βλέπει


def test_identical_values_give_zero():
    assert (outliers.robust_z([5, 5, 5, 5]) == 0).all()


@pytest.fixture(scope="module")
def env(tmp_path_factory):
    folder = tmp_path_factory.mktemp("audit")
    gl, tb, truth = generator.generate()
    paths = generator.save(gl, tb, truth, raw_dir=folder)
    conn = db.connect(pipeline.run(paths["gl"], paths["tb"], folder / "audit.db"))
    return conn, truth


def test_finds_exactly_the_planted_outliers(env):
    conn, truth = env
    found = set(db.query(conn, "SELECT journal_id FROM rule_hits WHERE rule = 'robust_z_outlier'")["journal_id"])
    planted = set(truth.loc[truth["anomaly_type"] == "robust_z_outlier", "journal_id"])
    assert found == planted


def test_rerun_does_not_duplicate_hits(env):
    conn, _ = env
    outliers.run_robust_z(conn)
    n = db.query(conn, "SELECT COUNT(*) AS n FROM rule_hits WHERE rule = 'robust_z_outlier'")["n"].iloc[0]
    assert n == 4
