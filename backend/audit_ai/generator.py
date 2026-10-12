"""Generator: φτιάχνει συνθετικό Γενικό Καθολικό (GL) και Ισοζύγιο για τον έλεγχο."""
import numpy as np
import pandas as pd

from audit_ai import config as cfg


def random_amount(rng, typical):
    """Τυχαίο ποσό γύρω από το 'typical'. Lognormal: πολλά μικρά, λίγα μεγάλα ποσά."""
    return round(float(rng.lognormal(mean=np.log(typical), sigma=0.8)), 2)


class Ledger:
    """Μαζεύει journals γραμμή-γραμμή και στο τέλος τα δίνει ως πίνακα (DataFrame)."""

    def __init__(self):
        self.rows = []
        self.next_id = 1

    def add_journal(self, lines, entry_datetime, user, source, description,
                    posting_date=None, approved_by=None, vendor_id=None):
        """lines = λίστα από (λογαριασμός, χρέωση, πίστωση). Επιστρέφει το journal_id."""
        journal_id = f"JE-{self.next_id:06d}"
        self.next_id += 1
        entry_datetime = pd.Timestamp(entry_datetime)
        if posting_date is None:
            posting_date = entry_datetime.normalize()
        for line_no, (account, debit, credit) in enumerate(lines, start=1):
            self.rows.append({
                "journal_id": journal_id, "line_id": line_no,
                "posting_date": pd.Timestamp(posting_date), "entry_datetime": entry_datetime,
                "account": account, "debit": debit, "credit": credit,
                "created_by": user, "approved_by": approved_by, "source": source,
                "description": description, "vendor_id": vendor_id,
            })
        return journal_id

    def to_frame(self):
        return pd.DataFrame(self.rows, columns=cfg.GL_COLUMNS)
