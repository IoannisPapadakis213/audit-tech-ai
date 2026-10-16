"""Οι κανόνες ISA 240 σε SQL. Κάθε κανόνας επιστρέφει τα journal_id που «χτυπάει».

Τα ευρήματα γράφονται στον πίνακα rule_hits: μία γραμμή ανά (journal, κανόνας), με το βάρος του.
Ένα journal μετράει ΜΙΑ φορά ανά κανόνα, όσες γραμμές κι αν έχει.
"""
import pandas as pd

from audit_ai import config as cfg
from audit_ai import database as db


def _in_list(values):
    """Μετατρέπει ('CFO', 'CEO') σε "'CFO', 'CEO'" για χρήση μέσα σε SQL IN (...)."""
    return ", ".join(f"'{v}'" for v in values)


ALLOWED_USERS = cfg.AUTHORIZED_POSTERS + cfg.SYSTEM_USERS + cfg.SENIOR_MANAGEMENT

RULES = {
    # 1. Γράφτηκε μετά το κλείσιμο, αλλά «κάθεται» μέσα στη χρήση
    "post_close": f"""
        SELECT DISTINCT journal_id FROM silver_gl
        WHERE entry_datetime > '{cfg.FISCAL_YEAR_END} 23:59:59'
          AND posting_date  <= '{cfg.FISCAL_YEAR_END} 23:59:59'
    """,
    # 2. Management override: η διοίκηση περνάει η ίδια εγγραφές
    "senior_mgmt_user": f"""
        SELECT DISTINCT journal_id FROM silver_gl
        WHERE created_by IN ({_in_list(cfg.SENIOR_MANAGEMENT)})
    """,
    # 3. Χρήστης που δεν είναι σε καμία εγκεκριμένη λίστα
    "unauthorized_user": f"""
        SELECT DISTINCT journal_id FROM silver_gl
        WHERE created_by NOT IN ({_in_list(ALLOWED_USERS)})
    """,
    # 4. Χειροκίνητη εγγραφή στις τελευταίες μέρες της χρήσης
    "period_end_manual": f"""
        SELECT DISTINCT journal_id FROM silver_gl
        WHERE is_manual = 1
          AND days_to_year_end BETWEEN 0 AND {cfg.PERIOD_END_WINDOW_DAYS}
    """,
    # 5. Πιθανή διπλή πληρωμή: ίδιος προμηθευτής, λογαριασμός και ποσό, άλλο journal, μέσα σε Ν μέρες
    "duplicate": f"""
        SELECT DISTINCT a.journal_id FROM silver_gl AS a
        JOIN silver_gl AS b
          ON  a.vendor_id  = b.vendor_id
          AND a.account    = b.account
          AND a.amount     = b.amount
          AND a.debit > 0 AND b.debit > 0
          AND a.journal_id <> b.journal_id
          AND ABS(julianday(a.posting_date) - julianday(b.posting_date)) <= {cfg.DUPLICATE_WINDOW_DAYS}
    """,
    # 6. Στρογγυλό ποσό (η ετικέτα έρχεται από το transform)
    "round_amount": """
        SELECT DISTINCT journal_id FROM silver_gl WHERE is_round_amount = 1
    """,
    # 7. Σαββατοκύριακο ή αργία (οι χρήστες συστήματος εξαιρούνται ήδη στο transform)
    "weekend_holiday": """
        SELECT DISTINCT journal_id FROM silver_gl WHERE is_weekend = 1 OR is_holiday = 1
    """,
    # 8. Σπάνιος λογαριασμός: χρησιμοποιήθηκε σε ελάχιστα journals όλη τη χρονιά
    "rare_account": f"""
        WITH usage AS (
            SELECT account, COUNT(DISTINCT journal_id) AS uses
            FROM silver_gl GROUP BY account
        )
        SELECT DISTINCT g.journal_id
        FROM silver_gl AS g JOIN usage AS u ON g.account = u.account
        WHERE u.uses <= {cfg.RARE_ACCOUNT_MAX_USES}
    """,
    # 9. Εκτός ωραρίου
    "after_hours": """
        SELECT DISTINCT journal_id FROM silver_gl WHERE is_after_hours = 1
    """,
    # 10. Χωρίς αιτιολογία
    "no_description": """
        SELECT DISTINCT journal_id FROM silver_gl
        WHERE description IS NULL OR TRIM(description) = ''
    """,
}


def run_rules(conn):
    """Τρέχει όλους τους κανόνες, γράφει τον πίνακα rule_hits και τον επιστρέφει."""
    hits = []
    for rule, sql in RULES.items():
        found = db.query(conn, sql)
        found["rule"] = rule
        found["weight"] = cfg.RULE_WEIGHTS[rule]
        hits.append(found)
    rule_hits = pd.concat(hits, ignore_index=True)[["journal_id", "rule", "weight"]]
    db.save_table(conn, "rule_hits", rule_hits)
    return rule_hits


if __name__ == "__main__":
    with db.connect() as conn:
        hits = run_rules(conn)
        print(db.query(conn, """
            SELECT rule AS κανόνας, weight AS βάρος, COUNT(*) AS journals
            FROM rule_hits GROUP BY rule ORDER BY weight DESC, journals DESC
        """).to_string(index=False))
