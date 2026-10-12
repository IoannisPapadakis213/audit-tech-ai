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


# ======================= Μέρος Β: κανονική δραστηριότητα =======================

VENDORS = [f"V{n:03d}" for n in range(1, 41)]          # 40 προμηθευτές: V001...V040
CLERKS = ("ACC_01", "ACC_02", "ACC_03", "ACC_04")


def working_days():
    """Εργάσιμες ημέρες της χρήσης: Δευτέρα-Παρασκευή, χωρίς αργίες."""
    days = pd.bdate_range(cfg.FISCAL_YEAR_START, cfg.FISCAL_YEAR_END)
    return days[~days.isin(pd.to_datetime(list(cfg.GREEK_HOLIDAYS_2025)))]


def office_time(rng, day):
    """Τυχαία ώρα μέσα στο ωράριο γραφείου (08:00-17:59) της ημέρας 'day'."""
    start, end = cfg.WORK_HOURS
    return day + pd.Timedelta(hours=int(rng.integers(start, end)), minutes=int(rng.integers(0, 60)))


def normal_activity(led, rng):
    """Γεμίζει το Ledger με μια χρονιά συνηθισμένων, «καθαρών» εγγραφών."""
    for day in working_days():
        # Κάθε εργάσιμη: μερικές πωλήσεις, αγορές, εισπράξεις και πληρωμές
        for _ in range(rng.poisson(4)):
            net = random_amount(rng, 1_000)
            vat = round(net * 0.24, 2)
            led.add_journal([("30.00", round(net + vat, 2), 0.0), ("70.00", 0.0, net), ("54.00", 0.0, vat)],
                            office_time(rng, day), str(rng.choice(CLERKS)), "Automatic", "Τιμολόγιο πώλησης")
        for _ in range(rng.poisson(3)):
            net = random_amount(rng, 600)
            vat = round(net * 0.24, 2)
            vendor = str(rng.choice(VENDORS))
            led.add_journal([("20.00", net, 0.0), ("54.00", vat, 0.0), ("50.00", 0.0, round(net + vat, 2))],
                            office_time(rng, day), str(rng.choice(CLERKS)), "Automatic", "Τιμολόγιο αγοράς",
                            vendor_id=vendor)
        for _ in range(rng.poisson(3)):
            amount = random_amount(rng, 1_100)
            led.add_journal([("38.03", amount, 0.0), ("30.00", 0.0, amount)],
                            office_time(rng, day), str(rng.choice(CLERKS)), "Automatic", "Είσπραξη από πελάτη")
        for _ in range(rng.poisson(2)):
            amount = random_amount(rng, 700)
            led.add_journal([("50.00", amount, 0.0), ("38.03", 0.0, amount)],
                            office_time(rng, day), str(rng.choice(CLERKS)), "Manual", "Πληρωμή προμηθευτή",
                            approved_by="FIN_MGR", vendor_id=str(rng.choice(VENDORS)))

    # Μία φορά τον μήνα: μισθοδοσία και αποσβέσεις, από το σύστημα, το βράδυ της τελευταίας μέρας
    for month_end in pd.date_range(cfg.FISCAL_YEAR_START, cfg.FISCAL_YEAR_END, freq="ME"):
        gross = random_amount(rng, 60_000)
        insurance = round(gross * 0.22, 2)
        led.add_journal([("60.00", gross, 0.0), ("55.00", 0.0, insurance), ("38.03", 0.0, round(gross - insurance, 2))],
                        month_end + pd.Timedelta(hours=23), "SYS_PAYROLL", "Automatic", "Μισθοδοσία μήνα")
        depreciation = random_amount(rng, 8_000)
        led.add_journal([("66.00", depreciation, 0.0), ("14.00", 0.0, depreciation)],
                        month_end + pd.Timedelta(hours=23, minutes=30), "SYS_BATCH", "Automatic", "Αποσβέσεις μήνα")
