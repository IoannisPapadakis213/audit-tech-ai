from fastapi.testclient import TestClient

from audit_ai.api import app

client = TestClient(app)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_stats_match_pipeline():
    s = client.get("/stats").json()
    assert s["total_journals"] == 3173
    assert s["high_risk_journals"] == 19
    assert s["gl_vs_tb_difference"] == 0


def test_anomalies_sorted_by_risk():
    rows = client.get("/anomalies").json()
    assert len(rows) == 19
    scores = [r["risk_score"] for r in rows]
    assert scores == sorted(scores, reverse=True)


def test_benford_has_nine_digits():
    assert len(client.get("/benford").json()["digits"]) == 9
