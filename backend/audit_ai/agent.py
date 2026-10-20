"""AI agent για Journal Entry Testing (Gemini).
Απαντά σε ερωτήσεις ελεγκτή χρησιμοποιώντας ΜΟΝΟ εργαλεία ανάγνωσης (τα endpoints του API)."""
import os
from pathlib import Path

from dotenv import load_dotenv

from audit_ai import api

load_dotenv(Path(__file__).resolve().parents[2] / ".env")   # το .env στον κεντρικό φάκελο

MODEL = os.getenv("AUDIT_AI_MODEL", "gemini-2.5-flash")
MAX_ANOMALIES = 50

SYSTEM = """Είσαι βοηθός ελεγκτή για Journal Entry Testing κατά ISA 240.
Απαντάς ΜΟΝΟ με βάση τα αποτελέσματα των εργαλείων. Αν κάτι δεν προκύπτει από αυτά, λες ότι δεν το ξέρεις.
Δεν συμπεραίνεις ότι υπάρχει απάτη· επισημαίνεις κινδύνους για περαιτέρω έλεγχο από τον ελεγκτή.
Απαντάς στη γλώσσα της ερώτησης, σύντομα, και αναφέρεις ποια νούμερα χρησιμοποίησες."""

TOOLS = [
    {"name": "get_stats",
     "description": "Συνολικά νούμερα: journals, γραμμές, high-risk journals, διαφορά Καθολικού-Ισοζυγίου."},
    {"name": "get_anomalies",
     "description": "High-risk journals ταξινομημένα κατά risk_score "
                    "(journal_id, created_by, posting_date, risk_score, amount).",
     "parameters": {"type": "object",
                    "properties": {"limit": {"type": "integer",
                                             "description": f"Πόσα journals (1-{MAX_ANOMALIES})"}}}},
    {"name": "get_benford",
     "description": "Ανάλυση Benford πρώτου ψηφίου: MAD και αναμενόμενο/πραγματικό ποσοστό ανά ψηφίο."},
]


def run_tool(name: str, args: dict):
    """Εκτελεί ένα εργαλείο. Άγνωστο εργαλείο = άρνηση, όχι σφάλμα."""
    if name == "get_stats":
        return api.stats()
    if name == "get_anomalies":
        return api.anomalies(limit=min(int((args or {}).get("limit", 10)), MAX_ANOMALIES))
    if name == "get_benford":
        return api.benford()
    return {"error": f"unknown tool: {name}"}


def ask(question: str, client=None, max_turns: int = 5) -> dict:
    from google.genai import types
    if client is None:
        from google import genai
        client = genai.Client()                 # διαβάζει το GEMINI_API_KEY
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM,
        tools=[types.Tool(function_declarations=TOOLS)],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )
    contents = [types.Content(role="user", parts=[types.Part(text=question)])]
    used = []
    for _ in range(max_turns):
        resp = client.models.generate_content(model=MODEL, contents=contents, config=config)
        calls = resp.function_calls or []
        if not calls:
            return {"answer": resp.text or "", "tools_used": used}
        contents.append(resp.candidates[0].content)
        parts = []
        for call in calls:
            used.append(call.name)
            output = run_tool(call.name, dict(call.args or {}))
            parts.append(types.Part.from_function_response(name=call.name, response={"result": output}))
        contents.append(types.Content(role="user", parts=parts))
    return {"answer": "Δεν ολοκληρώθηκε μέσα στο όριο βημάτων.", "tools_used": used}


if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) or "Πόσα journals είναι υψηλού κινδύνου και ποια είναι τα 3 πρώτα;"
    r = ask(q)
    print(r["answer"])
    print("\n🔧 Εργαλεία που χρησιμοποιήθηκαν:", r["tools_used"])