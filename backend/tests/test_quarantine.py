"""Tests για την καραντίνα: κάθε βρώμικο journal πιάνεται, και τίποτα δεν χάνεται."""
import pytest

from audit_ai import data_quality as dq
from audit_ai import generator


@pytest.fixture(scope="module")
def result():
    gl, _, truth = generator.generate()
    clean, q, summary = dq.quarantine(gl)
    return gl, truth, clean, q, summary


def test_every_dirty_journal_is_quarantined(result):
    _, truth, _, q, _ = result
    dirty = truth[truth["anomaly_type"].str.startswith("dq_")]
    assert set(dirty["journal_id"]) <= set(q["journal_id"])


def test_only_dirty_journals_are_quarantined(result):
    _, truth, _, q, _ = result
    dirty = truth[truth["anomaly_type"].str.startswith("dq_")]
    assert set(q["journal_id"]) == set(dirty["journal_id"])


def test_nothing_is_lost(result):
    gl, _, clean, q, _ = result
    assert len(clean) + len(q) == len(gl)


def test_whole_journal_goes_to_quarantine(result):
    _, _, clean, q, _ = result
    assert not set(clean["journal_id"]) & set(q["journal_id"])


def test_clean_journals_are_balanced(result):
    _, _, clean, _, _ = result
    sums = clean.groupby("journal_id")[["debit", "credit"]].sum()
    assert ((sums["debit"] - sums["credit"]).abs() <= 0.01).all()


def test_each_check_finds_its_planted_problem(result):
    *_, summary = result
    assert len(summary) == 5 and (summary["failed_journals"] >= 1).all()
