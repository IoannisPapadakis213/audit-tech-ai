"""Tests για τη βάση: ό,τι γράφεται διαβάζεται πίσω ίδιο, και η SQL «βλέπει» σωστά τα δεδομένα."""
import pytest

from audit_ai import database as db
from audit_ai import generator, pipeline


@pytest.fixture(scope="module")
def conn(tmp_path_factory):
    folder = tmp_path_factory.mktemp("audit")
    gl, tb, _ = generator.generate()
    paths = generator.save(gl, tb, gl.head(0), raw_dir=folder)
    db_path = pipeline.run(paths["gl"], paths["tb"], folder / "audit.db")
    return db.connect(db_path)


def test_all_layers_are_stored(conn):
    tables = set(db.query(conn, "SELECT name FROM sqlite_master WHERE type='table'")["name"])
    assert {"bronze_gl", "bronze_tb", "silver_gl", "dq_quarantine", "dq_summary", "dq_reconciliation"} <= tables


def test_bronze_equals_silver_plus_quarantine(conn):
    counts = db.query(conn, """
        SELECT (SELECT COUNT(*) FROM bronze_gl)     AS bronze,
               (SELECT COUNT(*) FROM silver_gl)     AS silver,
               (SELECT COUNT(*) FROM dq_quarantine) AS quarantine
    """).iloc[0]
    assert counts["bronze"] == counts["silver"] + counts["quarantine"]


def test_dates_compare_correctly_in_sql(conn):
    late = db.query(conn, "SELECT COUNT(*) AS n FROM silver_gl WHERE entry_datetime > '2025-12-31 23:59:59'")
    assert late["n"].iloc[0] > 0          # οι post-close εγγραφές του 2026


def test_silver_journals_balance_in_sql(conn):
    unbalanced = db.query(conn, """
        SELECT journal_id FROM silver_gl
        GROUP BY journal_id
        HAVING ABS(SUM(debit) - SUM(credit)) > 0.01
    """)
    assert unbalanced.empty
