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


def test_every_high_risk_journal_has_reasons():
    rows = client.get("/anomalies").json()
    assert all(len(r["rules"]) > 0 for r in rows)


def test_benford_has_nine_digits():
    assert len(client.get("/benford").json()["digits"]) == 9


def test_ask_endpoint_calls_agent(monkeypatch):
    import audit_ai.agent as agent
    monkeypatch.setattr(agent, "ask", lambda q, **kw: {"answer": "ok:" + q, "tools_used": []})
    r = client.post("/ask", json={"question": "hi"}).json()
    assert r["answer"] == "ok:hi"


def test_ask_fails_gracefully(monkeypatch):
    import audit_ai.agent as agent
    import audit_ai.api as api

    def boom(q, **kw):
        raise RuntimeError("503 model overloaded")

    monkeypatch.setattr(agent, "ask", boom)
    monkeypatch.setattr(api.time, "sleep", lambda s: None)
    r = client.post("/ask", json={"question": "hi"})
    assert r.status_code == 200
    assert "busy" in r.json()["answer"]

def test_high_risk_by_user_adds_up():
    rows = client.get("/high-risk-by-user").json()
    counts = [r["high_risk_journals"] for r in rows]
    assert sum(counts) == 19
    assert counts == sorted(counts, reverse=True)


def test_same_question_is_answered_from_cache(monkeypatch):
    import audit_ai.agent as agent
    calls = []

    def fake(q, **kw):
        calls.append(q)
        return {"answer": "19", "tools_used": ["get_stats"]}

    monkeypatch.setattr(agent, "ask", fake)
    client.post("/ask", json={"question": "Cache   me please"})
    client.post("/ask", json={"question": "cache me please"})
    assert len(calls) == 1
