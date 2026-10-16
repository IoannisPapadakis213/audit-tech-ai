"""Tests για τον Benford: πρώτα με «τέλεια» δεδομένα που ξέρουμε την απάντηση, μετά με το GL μας."""
import numpy as np
import pytest

from audit_ai import benford
from audit_ai import database as db
from audit_ai import generator, pipeline


def test_first_digit():
    assert list(benford.first_digit([4850.20, 0.73, 1000, 99.9])) == [4, 7, 1, 9]


def test_lognormal_amounts_follow_benford():
    amounts = np.random.default_rng(0).lognormal(mean=7, sigma=2.5, size=20_000)
    _, _, verdict, _ = benford.analyze(amounts)
    assert verdict == "close"


def test_amounts_just_below_a_limit_break_benford():
    amounts = np.random.default_rng(0).uniform(4_800, 4_999, size=1_000)
    _, _, verdict, _ = benford.analyze(amounts)
    assert verdict == "nonconformity"


@pytest.fixture(scope="module")
def by_user(tmp_path_factory):
    folder = tmp_path_factory.mktemp("audit")
    gl, tb, truth = generator.generate()
    paths = generator.save(gl, tb, truth, raw_dir=folder)
    conn = db.connect(pipeline.run(paths["gl"], paths["tb"], folder / "audit.db"))
    return db.query(conn, "SELECT * FROM benford_by_user").set_index("created_by")


def test_benford_catches_the_fabricating_clerk(by_user):
    assert by_user.loc["ACC_04", "conformity"] == "nonconformity"
    assert by_user["mad"].drop(index=by_user.index[by_user["conformity"] == "insufficient_sample"]).idxmax() == "ACC_04"


def test_small_samples_are_not_judged(by_user):
    assert by_user.loc["CFO", "conformity"] == "insufficient_sample"
