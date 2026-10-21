"""REST API: δίνει τα αποτελέσματα του JET σε frontend και AI agent.
Επιστρέφει μόνο ό,τι έχει ήδη υπολογίσει το pipeline – δεν υπολογίζει κάτι νέο."""
import logging
import os
import time
from functools import lru_cache
from pathlib import Path

import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from audit_ai.config import POWERBI_DIR

log = logging.getLogger("audit_ai")

app = FastAPI(title="Audit Tech AI – JET API")

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS,
                   allow_methods=["GET", "POST"], allow_headers=["*"])


@lru_cache
def load(name: str) -> pd.DataFrame:
    return pd.read_csv(POWERBI_DIR / f"{name}.csv")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/stats")
def stats():
    lines = load("fact_journal_lines")
    tb = load("trial_balance")
    high = lines[lines["is_high_risk"] == 1]
    return {
        "total_lines": len(lines),
        "total_journals": int(lines["journal_id"].nunique()),
        "high_risk_journals": int(high["journal_id"].nunique()),
        "gl_vs_tb_difference": float((tb["diff_debit"].abs() + tb["diff_credit"].abs()).sum()),
    }


@app.get("/anomalies")
def anomalies(limit: int = 50):
    lines = load("fact_journal_lines")
    high = lines[lines["is_high_risk"] == 1]
    journals = (
        high.groupby("journal_id")
        .agg(created_by=("created_by", "first"),
             posting_date=("posting_date", "first"),
             risk_score=("risk_score", "max"),
             amount=("debit", "sum"))
        .reset_index()
        .sort_values("risk_score", ascending=False)
        .head(limit)
    )
    # Τεκμηρίωση: ποιοι κανόνες χτύπησαν σε κάθε journal
    hits = load("fact_rule_hits")
    reasons = hits.groupby("journal_id")["rule"].apply(lambda s: sorted(set(s))).to_dict()
    journals["rules"] = journals["journal_id"].map(lambda j: reasons.get(j, []))
    return journals.to_dict(orient="records")


@app.get("/high-risk-by-user")
def high_risk_by_user():
    """Πόσα high-risk journals καταχώρησε κάθε χρήστης (συγκεντρωτικά, όχι γραμμές)."""
    lines = load("fact_journal_lines")
    high = lines[lines["is_high_risk"] == 1]
    out = (high.groupby("created_by")["journal_id"].nunique()
           .sort_values(ascending=False)
           .reset_index(name="high_risk_journals"))
    return out.to_dict(orient="records")


@app.get("/benford")
def benford():
    d = load("dim_digit")
    mad = float((d["actual"] - d["expected"]).abs().mean())
    return {"mad": round(mad, 4),
            "digits": d[["digit", "expected", "actual"]].to_dict(orient="records")}


class Question(BaseModel):
    question: str


# Μνήμη απαντήσεων: ίδια ερώτηση = ίδια απάντηση, χωρίς νέα κλήση στο AI (τα δεδομένα δεν αλλάζουν).
ANSWER_CACHE: dict[str, dict] = {}
MAX_CACHE = 200


@app.post("/ask")
def ask_agent(q: Question):
    """Πρώτα η μνήμη, μετά το κύριο μοντέλο, μετά το εφεδρικό. Αν αποτύχουν όλα, απαντά ευγενικά."""
    from audit_ai.agent import MODELS, ask
    question = q.question[:500]
    key = " ".join(question.lower().split())
    if key in ANSWER_CACHE:
        return ANSWER_CACHE[key]
    for model in MODELS:
        try:
            result = ask(question, model=model.strip())
            if result.get("tools_used") and len(ANSWER_CACHE) < MAX_CACHE:
                ANSWER_CACHE[key] = result      # κρατάμε μόνο απαντήσεις που στηρίχτηκαν σε εργαλεία
            return result
        except Exception as e:
            log.warning("AI model %s failed: %s", model, e)
            time.sleep(1)
    return {"answer": "The AI model is busy right now. Please try again in a minute.",
            "tools_used": []}


# Η σελίδα React (αν έχει γίνει build). Μπαίνει ΤΕΛΕΥΤΑΙΑ, ώστε τα /stats, /ask κ.λπ. να έχουν προτεραιότητα.
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")