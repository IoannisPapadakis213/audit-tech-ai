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


# ======================= Μέρος Γ: φυτεμένες ανωμαλίες =======================

def plant_anomalies(led, rng):
    """Φυτεύει ύποπτες εγγραφές, μία ομάδα για κάθε κανόνα ISA 240.

    Επιστρέφει το ground truth: λίστα από (journal_id, anomaly_type).
    """
    truth = []
    days = working_days()

    def plant(kind, lines, entry, user, source="Manual", description="Λογιστική τακτοποίηση", **extra):
        journal_id = led.add_journal(lines, entry, user, source, description, **extra)
        truth.append((journal_id, kind))
        return journal_id

    def accrual(amount, debit_account="64.00"):
        """Χειροκίνητη πρόβλεψη εξόδου: Χ έξοδο / Π πιστωτές."""
        return [(debit_account, amount, 0.0), ("53.00", 0.0, amount)]

    def some_day():
        return days[int(rng.integers(0, len(days)))]

    # 1. Post-close: γράφτηκε Ιαν-Φεβ 2026, αλλά «κάθεται» στις 31/12/2025
    for _ in range(5):
        entry = pd.Timestamp("2026-01-05") + pd.Timedelta(days=int(rng.integers(0, 50)), hours=11)
        plant("post_close", accrual(random_amount(rng, 3_000)), entry, "ACC_02",
              posting_date=cfg.FISCAL_YEAR_END)

    # 2. Η διοίκηση περνάει η ίδια εγγραφές (management override)
    for _ in range(4):
        plant("senior_mgmt_user", accrual(random_amount(rng, 4_000)), office_time(rng, some_day()), "CFO")

    # 3. Χρήστης που δεν είναι στη λίστα των εξουσιοδοτημένων
    for _ in range(4):
        plant("unauthorized_user", accrual(random_amount(rng, 2_000)), office_time(rng, some_day()), "TEMP_USER")

    # 4. Χειροκίνητη εγγραφή στις τελευταίες μέρες του Δεκεμβρίου
    december_end = days[(days.month == 12) & (days.day >= 22)]
    for _ in range(5):
        day = december_end[int(rng.integers(0, len(december_end)))]
        plant("period_end_manual", accrual(random_amount(rng, 5_000)), office_time(rng, day), "FIN_MGR")

    # 5. Διπλή πληρωμή: ίδιος προμηθευτής, ίδιο ποσό, 2 μέρες μετά
    for _ in range(3):
        day, amount, vendor = some_day(), random_amount(rng, 2_500), str(rng.choice(VENDORS))
        for shift in (0, 2):
            plant("duplicate", [("50.00", amount, 0.0), ("38.03", 0.0, amount)],
                  office_time(rng, day + pd.Timedelta(days=shift)), "ACC_03",
                  description="Πληρωμή προμηθευτή", approved_by="FIN_MGR", vendor_id=vendor)

    # 6. Στρογγυλό ποσό (ακέραιες χιλιάδες, πάνω από 10.000)
    for _ in range(6):
        plant("round_amount", accrual(float(rng.integers(11, 60)) * 1_000), office_time(rng, some_day()), "ACC_01")

    # 7. Σαββατοκύριακο ή αργία
    odd_days = [pd.Timestamp(d) for d in ("2025-02-15", "2025-05-01", "2025-06-22", "2025-08-15",
                                           "2025-09-13", "2025-10-28", "2025-11-30", "2025-12-25")]
    for day in odd_days:
        plant("weekend_holiday", accrual(random_amount(rng, 1_500)), office_time(rng, day), "ACC_04")

    # 8. Σπάνιος λογαριασμός: «Έκτακτα αποτελέσματα» χρησιμοποιείται μόνο 3 φορές
    for _ in range(3):
        plant("rare_account", accrual(random_amount(rng, 3_000), debit_account="81.00"),
              office_time(rng, some_day()), "ACC_02")

    # 9. Ακραίο ποσό για τον λογαριασμό: αγορά εμπορευμάτων ~80 φορές μεγαλύτερη από το σύνηθες
    for _ in range(4):
        net = random_amount(rng, 50_000)
        plant("robust_z_outlier", [("20.00", net, 0.0), ("50.00", 0.0, net)], office_time(rng, some_day()),
              "ACC_03", source="Automatic", description="Τιμολόγιο αγοράς", vendor_id=str(rng.choice(VENDORS)))

    # 10. Εκτός ωραρίου (βράδυ ή ξημερώματα)
    for hour in (20, 21, 22, 2, 5):
        plant("after_hours", accrual(random_amount(rng, 1_500)), some_day() + pd.Timedelta(hours=hour), "ACC_01")

    # 11. Κενή αιτιολογία
    for _ in range(5):
        plant("no_description", accrual(random_amount(rng, 1_500)), office_time(rng, some_day()), "ACC_02",
              description=None)

    # 12. Η «βελόνα στα άχυρα»: πολλά red flags μαζί -> πρέπει να βγει ΠΡΩΤΗ στη λίστα
    for entry in ("2025-12-28 22:10", "2026-01-11 21:30", "2025-06-22 23:05",
                  "2026-02-01 20:45", "2025-12-21 19:40"):        # όλες Κυριακή βράδυ
        entry = pd.Timestamp(entry)
        posting = cfg.FISCAL_YEAR_END if entry.year == 2026 else None
        plant("multi_flag", accrual(float(rng.integers(20, 90)) * 1_000), entry, "CFO",
              posting_date=posting, description=None)

    # 13. Benford: ο ACC_04 «φτιάχνει» πληρωμές λίγο κάτω από το όριο έγκρισης των 5.000 €
    for _ in range(150):
        amount = round(float(rng.uniform(4_800, 4_999)), 2)
        plant("benford_fabricated", [("50.00", amount, 0.0), ("38.03", 0.0, amount)],
              office_time(rng, some_day()), "ACC_04", description="Πληρωμή προμηθευτή",
              approved_by="FIN_MGR", vendor_id=str(rng.choice(VENDORS)))

    return pd.DataFrame(truth, columns=["journal_id", "anomaly_type"])
