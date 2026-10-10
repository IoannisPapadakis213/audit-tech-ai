"""Τρέχει όλο το pipeline σε προσωρινό φάκελο και ελέγχει ότι οι κανόνες βρίσκουν τις φυτεμένες ανωμαλίες."""
import pytest

from audit_ai import audit_queries, data_generator, etl


@pytest.fixture(scope="module")
def pipeline(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("audit")
    csv, truth_csv, db = tmp / "gl.csv", tmp / "truth.csv", tmp / "audit.db"
    gl, truth = data_generator.generate_gl(num_records=2_000, seed=7)
    data_generator.save(gl, truth, csv, truth_csv)
    clean, quarantine, results = etl.run(csv, db)
    return {"db": db, "truth": truth, "clean": clean, "quarantine": quarantine, "results": results}


def found_ids(pipeline, query):
    return set(audit_queries.run_query(query, pipeline["db"])["transaction_id"])


def planted_ids(pipeline, anomaly_type):
    truth = pipeline["truth"]
    return set(truth.loc[truth["anomaly_type"] == anomaly_type, "transaction_id"])


def test_dirty_rows_are_quarantined(pipeline):
    assert len(pipeline["quarantine"]) == 10
    assert not pipeline["clean"]["transaction_id"].duplicated().any()


@pytest.mark.parametrize("anomaly_type, query", [
    ("round_amount", "round_amounts"),
    ("weekend_entry", "weekend_entries"),
    ("after_hours", "after_hours_entries"),
    ("duplicate_payment", "duplicate_payments"),
])
def test_rule_finds_every_planted_anomaly(pipeline, anomaly_type, query):
    # Recall = 100%: δεν πρέπει να ξεφύγει καμία φυτεμένη ανωμαλία
    assert planted_ids(pipeline, anomaly_type) <= found_ids(pipeline, query)


def test_user_activity_covers_all_users(pipeline):
    users = audit_queries.run_query("user_activity", pipeline["db"])
    assert users["total_entries"].sum() == len(pipeline["clean"])
