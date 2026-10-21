"""AI agent για Journal Entry Testing (Gemini).
Απαντά σε ερωτήσεις ελεγκτή χρησιμοποιώντας ΜΟΝΟ εργαλεία ανάγνωσης (τα endpoints του API)."""
import os
from pathlib import Path

from dotenv import load_dotenv

from audit_ai import api

load_dotenv(Path(__file__).resolve().parents[2] / ".env")   # το .env στον κεντρικό φάκελο

# Κύριο μοντέλο πρώτο, εφεδρικό δεύτερο. Αλλάζει από το .env χωρίς αλλαγή κώδικα.
MODELS = os.getenv("AUDIT_AI_MODELS", "gemini-3.5-flash-lite,gemini-2.5-flash").split(",")
MAX_ANOMALIES = 50

SYSTEM = """Είσαι βοηθός ελεγκτή για Journal Entry Testing κατά ISA 240.
Απαντάς ΜΟΝΟ με βάση τα αποτελέσματα των εργαλείων. Αν κάτι δεν προκύπτει από αυτά, λες ότι δεν το ξέρεις.
Μπορείς να μετράς, να ταξινομείς και να συγκρίνεις τα αποτελέσματα που επιστρέφουν τα εργαλεία.
Δεν συμπεραίνεις ότι υπάρχει απάτη· επισημαίνεις κινδύνους για περαιτέρω έλεγχο από τον ελεγκτή.
Όταν αναφέρεις ύποπτα journals, εξηγείς ποιοι κανόνες χτύπησαν (πεδίο rules).
Απαντάς στη γλώσσα της ερώτησης, σύντομα, και αναφέρεις ποια νούμερα χρησιμοποίησες."""

TOOLS = [
    {"name": "get_stats",
     "description": "Συνολικά νούμερα: journals, γραμμές, high-risk journals, διαφορά Καθολικού-Ισοζυγίου."},
    {"name": "get_anomalies",
     "description": "High-risk journals ταξινομημένα κατά risk_score "
                    "(journal_id, created_by, posting_date, risk_score, amount, rules).",
     "parameters": {"type": "object",
                    "properties": {"limit": {"type": "integer",
                                             "description": f"Πόσα journals (1-{MAX_ANOMALIES})"}}}},
    {"name": "get_high_risk_by_user",
     "description": "Πλήθος high-risk journals ανά χρήστη που τα καταχώρησε (created_by), "
                    "ταξινομημένο από τον χρήστη με τα περισσότερα."},
    {"name": "get_benford",
     "description": "Ανάλυση Benford πρώτου ψηφίου: MAD και αναμενόμενο/πραγματικό ποσοστό ανά ψηφίο."},
]


def run_tool(name: str, args: dict):
    """Εκτελεί ένα εργαλείο. Άγνωστο εργαλείο = άρνηση, όχι σφάλμα."""
    if name == "get_stats":
        return api.stats()
    if name == "get_anomalies":
        return api.anomalies(limit=min(int((args or {}).get("limit", 10)), MAX_ANOMALIES))
    if name == "get_high_risk_by_user":
        return api.high_risk_by_user()
    if name == "get_benford":
        return api.benford()
    return {"error": f"unknown tool: {name}"}


def ask(question: str, client=None, max_turns: int = 5, model: str | None = None) -> dict:
    from google.genai import types
    model = model or MODELS[0]
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
        resp = client.models.generate_content(model=model, contents=contents, config=config)
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