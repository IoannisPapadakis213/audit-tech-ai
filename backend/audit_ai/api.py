"""REST API: δίνει τα αποτελέσματα του JET σε frontend και AI agent.
Επιστρέφει μόνο ό,τι έχει ήδη υπολογίσει το pipeline – δεν υπολογίζει κάτι νέο."""
from functools import lru_cache

import pandas as pd
from fastapi import FastAPI

from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from audit_ai.config import POWERBI_DIR

app = FastAPI(title="Audit Tech AI – JET API")

app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"],
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
    return journals.to_dict(orient="records")


@app.get("/benford")
def benford():
    d = load("dim_digit")
    mad = float((d["actual"] - d["expected"]).abs().mean())
    return {"mad": round(mad, 4),
            "digits": d[["digit", "expected", "actual"]].to_dict(orient="records")}

class Question(BaseModel):
    question: str


@app.post("/ask")
def ask_agent(q: Question):
    from audit_ai.agent import ask
    return ask(q.question[:500])