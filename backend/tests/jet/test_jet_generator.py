import pandas as pd
import pytest

from audit_ai import config as cfg
from audit_ai.jet import generator


@pytest.fixture(scope="module")
def data():
    return generator.generate(seed=42)


def test_schema_matches_spec(data):
    gl, _, _ = data
    assert list(gl.columns) == list(cfg.GL_COLUMNS)


def test_almost_every_journal_is_balanced(data):
    gl, _, _ = data
    diff = gl.groupby("journal_id")[["debit", "credit"]].sum().eval("debit - credit").abs()
    # Μόνο το ένα journal που χαλάσαμε επίτηδες δεν ισοσκελίζεται
    assert (diff > cfg.BALANCE_TOLERANCE).sum() == 1


def test_trial_balance_rolls_forward_from_gl(data):
    gl, tb, _ = data
    in_year = gl[gl["posting_date"].between(cfg.FISCAL_YEAR_START, cfg.FISCAL_YEAR_END)]
    movements = in_year.groupby("account")[["debit", "credit"]].sum().round(2)
    merged = tb.set_index("account").join(movements, how="left").fillna(0)
    assert (merged["period_debit"] - merged["debit"]).abs().max() < cfg.BALANCE_TOLERANCE
    assert (merged["period_credit"] - merged["credit"]).abs().max() < cfg.BALANCE_TOLERANCE


def test_opening_trial_balance_is_balanced(data):
    _, tb, _ = data
    assert abs(tb["opening_balance"].sum()) < cfg.BALANCE_TOLERANCE


def test_ground_truth_covers_every_rule(data):
    _, _, truth = data
    expected = set(cfg.RULE_WEIGHTS) - {"isolation_forest"} | {"multi_flag", "benford_fabricated"}
    assert expected <= set(truth["anomaly_type"])


def test_same_seed_same_data():
    gl1, _, _ = generator.generate(seed=7)
    gl2, _, _ = generator.generate(seed=7)
    pd.testing.assert_frame_equal(gl1, gl2)


def test_break_tb_drops_journals(data):
    gl, _, _ = data
    broken, _, _ = generator.generate(seed=42, break_tb=True)
    assert broken["journal_id"].nunique() == gl["journal_id"].nunique() - 3


def test_bank_closing_balance_is_positive(data):
    # Ρεαλισμός: μια υγιής εταιρεία δεν κλείνει με αρνητική τράπεζα
    _, tb, _ = data
    assert tb.set_index("account").loc["38.03", "closing_balance"] > 0
