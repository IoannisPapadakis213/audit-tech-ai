"""Run log: κάθε εκτέλεση αφήνει «αποτύπωμα», ώστε να μπορεί να αναπαραχθεί και να ελεγχθεί.

Καταγράφουμε ΤΙ τρέξαμε (git commit), ΜΕ ΠΟΙΕΣ ρυθμίσεις (hash του config),
ΠΑΝΩ ΣΕ ΤΙ (hash των αρχείων του πελάτη) και ΤΙ βγήκε (πλήθη).
Αν σε έναν χρόνο κάποιος ρωτήσει «πώς βγήκε αυτή η λίστα;», η απάντηση είναι εδώ.
"""
import hashlib
import subprocess
import uuid
from datetime import datetime
from pathlib import Path

import pandas as pd

from audit_ai import config as cfg
from audit_ai import database as db


def file_hash(path):
    """SHA-256 ενός αρχείου: αν αλλάξει έστω ένας χαρακτήρας, αλλάζει όλο το hash."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def git_commit():
    """Το commit του κώδικα που έτρεξε. 'unknown' αν δεν είμαστε σε git repo."""
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=cfg.REPO_ROOT,
                             capture_output=True, text=True, check=True)
        return out.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def write_run_log(conn, gl_path, tb_path, started_at):
    """Προσθέτει μία γραμμή στον πίνακα run_log και την επιστρέφει."""
    counts = db.query(conn, """
        SELECT (SELECT COUNT(*) FROM bronze_gl)                      AS lines_received,
               (SELECT COUNT(*) FROM dq_quarantine)                  AS lines_quarantined,
               (SELECT COUNT(DISTINCT journal_id) FROM silver_gl)    AS journals_analyzed,
               (SELECT COUNT(*) FROM high_risk_journals)             AS high_risk_journals
    """).iloc[0]
    row = pd.DataFrame([{
        "run_id": str(uuid.uuid4()),
        "started_at": started_at.strftime("%Y-%m-%d %H:%M:%S"),
        "finished_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "client": cfg.CLIENT_NAME,
        "git_commit": git_commit(),
        "config_hash": file_hash(Path(cfg.__file__))[:16],
        "gl_file_hash": file_hash(gl_path)[:16],
        "tb_file_hash": file_hash(tb_path)[:16],
        "random_state": cfg.ISOLATION_FOREST["random_state"],
        "risk_threshold": cfg.RISK_SCORE_THRESHOLD,
        **{k: int(v) for k, v in counts.items()},
    }])
    row.to_sql("run_log", conn, if_exists="append", index=False)     # append: κρατάμε ΟΛΟ το ιστορικό
    return row.iloc[0]
