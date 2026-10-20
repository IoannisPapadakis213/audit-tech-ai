from types import SimpleNamespace as NS

from audit_ai.agent import TOOLS, ask, run_tool


def test_tools_are_read_only():
    assert all(t["name"].startswith("get_") for t in TOOLS)


def test_run_tool_stats():
    assert run_tool("get_stats", {})["high_risk_journals"] == 19


def test_limit_is_capped():
    assert len(run_tool("get_anomalies", {"limit": 9999})) == 19


def test_unknown_tool_is_refused():
    assert "error" in run_tool("delete_ledger", {})


class FakeGemini:
    """Παριστάνει το Gemini: 1ος γύρος ζητάει εργαλείο, 2ος απαντάει."""
    def __init__(self):
        self.calls = 0
        self.models = self

    def generate_content(self, model, contents, config):
        self.calls += 1
        if self.calls == 1:
            from google.genai import types
            call = NS(name="get_stats", args={})
            content = types.Content(role="model", parts=[types.Part.from_function_call(name="get_stats", args={})])
            return NS(function_calls=[call], candidates=[NS(content=content)], text=None)
        reply = contents[-1].parts[0].function_response.response["result"]
        assert reply["high_risk_journals"] == 19
        return NS(function_calls=None, text="Υπάρχουν 19 high-risk journals.")


def test_agent_loop_uses_tool_then_answers():
    r = ask("Πόσα ύποπτα journals;", client=FakeGemini())
    assert r["tools_used"] == ["get_stats"]
    assert "19" in r["answer"]