"""Βάση δεδομένων (SQLite): εδώ αποθηκεύονται όλα τα στρώματα, για να τα ρωτάμε με SQL.

Πίνακες (medallion):
  bronze_gl, bronze_tb       -> ό,τι έστειλε ο πελάτης, όπως ήρθε
  dq_quarantine, dq_summary, dq_reconciliation -> αποτελέσματα ποιότητας
  silver_gl                  -> καθαρές γραμμές με τις ετικέτες του transform
"""
import sqlite3

import pandas as pd

from audit_ai import config as cfg


def connect(db_path=cfg.DB_PATH):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(db_path)


def save_table(conn, name, df):
    """Γράφει έναν πίνακα. Οι ημερομηνίες γίνονται κείμενο ISO ('2025-12-31 21:30:00'),
    που η SQLite ξέρει να συγκρίνει και να ταξινομεί σωστά."""
    out = df.copy()
    for col in out.select_dtypes(include="datetime").columns:
        out[col] = out[col].dt.strftime("%Y-%m-%d %H:%M:%S")
    out.to_sql(name, conn, if_exists="replace", index=False)


def query(conn, sql, params=()):
    """Τρέχει SQL και επιστρέφει πίνακα pandas."""
    return pd.read_sql_query(sql, conn, params=params)
