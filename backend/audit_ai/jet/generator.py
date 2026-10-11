"""Συνθετικό GL (journals με χρεώσεις/πιστώσεις) + Ισοζύγιο + ground truth.

Κάθε journal είναι ισοσκελισμένο (Σ Χρεώσεων = Σ Πιστώσεων). Φυτεύουμε:
- ανωμαλίες ISA 240 (μία ομάδα ανά κανόνα + journals με πολλές σημαίες μαζί),
- επινοημένα ποσά από τον ACC_04 (για τον Benford ανά χρήστη),
- "βρώμικα" δεδομένα (για το Data Quality).
"""
from pathlib import Path

import numpy as np
import pandas as pd

from audit_ai import config as cfg

ACC_USERS = ("ACC_01", "ACC_02", "ACC_03", "ACC_04")
VENDORS = tuple(f"V{i:03d}" for i in range(1, 61))
VAT = 0.24

# Υπόλοιπα έναρξης ισολογισμού (θετικό = χρεωστικό). Ο 40.00 ισοσκελίζει.
OPENING_BALANCES = {
    "14.00": 600_000, "20.00": 250_000, "30.00": 400_000, "38.03": 350_000,
    "50.00": -300_000, "53.00": -50_000, "54.00": -60_000, "55.00": -40_000,
}


class _Ledger:
    """Μαζεύει journals. Κάθε γραμμή = (account, debit, credit)."""

    def __init__(self, rng):
        self.rng = rng
        self.lines = []
        self.truth = []
        self._next = 0
        holidays = pd.to_datetime(cfg.GREEK_HOLIDAYS_2025)
        self.workdays = pd.bdate_range(cfg.FISCAL_YEAR_START, cfg.FISCAL_YEAR_END).difference(holidays)
        days_left = (self.workdays + pd.offsets.MonthEnd(0) - self.workdays).days
        self.mid_month = self.workdays[days_left > cfg.PERIOD_END_WINDOW_DAYS]
        self.month_end = self.workdays[days_left <= 5]

    # --- τυχαίες τιμές -------------------------------------------------
    def amount(self, mean=7.0, sigma=1.4):
        # lognormal με αρκετό εύρος (σ) ώστε να ισχύει ο νόμος του Benford
        return round(float(self.rng.lognormal(mean, sigma)), 2)

    def pick(self, seq):
        return seq[self.rng.integers(len(seq))]

    def at(self, day, hour=None, minute=None):
        if hour is None:
            hour = self.rng.integers(*cfg.WORK_HOURS)
        if minute is None:
            minute = self.rng.integers(60)
        return pd.Timestamp(day) + pd.Timedelta(hours=int(hour), minutes=int(minute))

    # --- καταχώρηση ----------------------------------------------------
    def post(self, lines, posting_date, entry_datetime, created_by, source, description,
             approved_by=None, vendor_id=None, anomaly=None):
        self._next += 1
        tmp_id = self._next
        for line_id, (account, debit, credit) in enumerate(lines, 1):
            self.lines.append({
                "_tmp": tmp_id, "line_id": line_id,
                "posting_date": pd.Timestamp(posting_date).normalize(),
                "entry_datetime": pd.Timestamp(entry_datetime),
                "account": account, "debit": round(debit, 2), "credit": round(credit, 2),
                "created_by": created_by, "approved_by": approved_by, "source": source,
                "description": description, "vendor_id": vendor_id,
            })
        if anomaly:
            self.truth.append((tmp_id, anomaly))
        return tmp_id

    def manual(self, lines, day, entry=None, user=None, description="Λογιστική τακτοποίηση",
               vendor_id=None, anomaly=None):
        user = user or self.pick(ACC_USERS)
        approver = "CFO" if user == "FIN_MGR" else "FIN_MGR"
        return self.post(lines, day, entry if entry is not None else self.at(day), user, "Manual",
                         description, approver, vendor_id, anomaly)


# --- Κανονικές συναλλαγές ---------------------------------------------

def _normal_activity(led):
    rng = led.rng
    for _ in range(1000):  # τιμολόγια πώλησης
        a = led.amount(7.3); vat = round(a * VAT, 2); day = led.pick(led.workdays)
        led.post([("30.00", a + vat, 0), (led.pick(["70.00", "71.00"]), 0, a), ("54.00", 0, vat)],
                 day, led.at(day), led.pick(ACC_USERS), "Automatic", "Τιμολόγιο πώλησης")

    purchases = []
    for _ in range(800):  # τιμολόγια αγοράς
        a = led.amount(); vat = round(a * VAT, 2); day = led.pick(led.workdays)
        expense = rng.choice(["20.00", "20.00", "61.00", "62.00", "64.00"])
        lines = [(expense, a, 0), ("54.00", vat, 0), ("50.00", 0, a + vat)]
        user, vendor = led.pick(ACC_USERS), led.pick(VENDORS)
        led.post(lines, day, led.at(day), user, "Automatic", "Τιμολόγιο αγοράς", vendor_id=vendor)
        purchases.append((lines, day, user, vendor))

    for _ in range(600):  # πληρωμές προμηθευτών (χειροκίνητες, με έγκριση)
        a = led.amount(); day = led.pick(led.workdays)
        led.manual([("50.00", a, 0), ("38.03", 0, a)], day, description="Πληρωμή προμηθευτή",
                   vendor_id=led.pick(VENDORS))

    for _ in range(900):  # εισπράξεις (αυτόματα από την τράπεζα)
        a = led.amount(7.3); day = led.pick(led.workdays)
        led.post([("38.03", a, 0), ("30.00", 0, a)], day, led.at(day), led.pick(ACC_USERS),
                 "Automatic", "Είσπραξη από πελάτη")

    for _ in range(150):  # προβλέψεις εξόδων
        a = led.amount(); day = led.pick(led.workdays)
        led.manual([(led.pick(["62.00", "64.00"]), a, 0), ("53.00", 0, a)], day,
                   user=led.pick(ACC_USERS + ("FIN_MGR",)), description="Πρόβλεψη εξόδων")

    for month_end in pd.date_range(cfg.FISCAL_YEAR_START, cfg.FISCAL_YEAR_END, freq="ME"):
        # Μισθοδοσία: τελευταία εργάσιμη του μήνα, batch στις 03:00
        payday = led.workdays[led.workdays <= month_end][-1]
        gross = round(float(rng.uniform(80_000, 95_000)), 2); efka = round(gross * 0.22, 2)
        led.post([("60.00", gross, 0), ("55.00", 0, efka), ("38.03", 0, gross - efka)],
                 payday, led.at(payday, 3), "SYS_PAYROLL", "Automatic", "Μισθοδοσία μήνα")
        # Αποσβέσεις: τελευταία ημερολογιακή μέρα (μπορεί να είναι ΣΚ), batch στις 02:00
        led.post([("66.00", 4_166.67, 0), ("14.00", 0, 4_166.67)],
                 month_end, led.at(month_end, 2), "SYS_BATCH", "Automatic", "Αποσβέσεις μήνα")

    return purchases


# --- Φυτεμένες ανωμαλίες (ISA 240) --------------------------------------

def _plant_anomalies(led, purchases):
    rng = led.rng

    def expense_lines(a, debit="64.00", credit="53.00"):
        return [(debit, a, 0), (credit, 0, a)]

    for _ in range(5):  # καταχώρηση μετά το κλείσιμο, με ημερομηνία 31/12
        entry_day = led.pick(pd.bdate_range("2026-01-12", "2026-02-27"))
        led.manual(expense_lines(led.amount()), cfg.FISCAL_YEAR_END, led.at(entry_day),
                   anomaly="post_close")

    for _ in range(4):  # ανώτατη διοίκηση
        day = led.pick(led.mid_month)
        led.manual(expense_lines(led.amount(), "61.00", "38.03"), day, user=led.pick(["CFO", "CEO"]),
                   vendor_id=led.pick(VENDORS), anomaly="senior_mgmt_user")

    for _ in range(4):  # χρήστης χωρίς δικαίωμα καταχώρησης
        day = led.pick(led.mid_month)
        led.manual(expense_lines(led.amount()), day, user=led.pick(["IT_ADMIN", "TEMP_01"]),
                   anomaly="unauthorized_user")

    for _ in range(5):  # χειροκίνητη στο τέλος μήνα
        led.manual(expense_lines(led.amount()), led.pick(led.month_end), anomaly="period_end_manual")

    for i in rng.choice(len(purchases), 6, replace=False):  # διπλά τιμολόγια
        lines, day, user, vendor = purchases[i]
        later = led.workdays[led.workdays > day]
        if len(later) < 2:
            continue
        again = later[1]  # 2 εργάσιμες αργότερα
        led.post(lines, again, led.at(again), user, "Automatic", "Τιμολόγιο αγοράς",
                 vendor_id=vendor, anomaly="duplicate")

    for _ in range(6):  # στρογγυλά ποσά
        a = float(rng.choice([10_000, 15_000, 20_000, 30_000]))
        led.manual(expense_lines(a, "64.00", "38.03"), led.pick(led.mid_month), anomaly="round_amount")

    weekends = pd.date_range("2025-01-11", "2025-12-14", freq="W-SAT")
    for _ in range(5):  # Σαββατοκύριακο
        day = led.pick(weekends) + pd.Timedelta(days=int(rng.integers(2)))
        led.manual(expense_lines(led.amount()), day, anomaly="weekend_holiday")
    for day in ("2025-03-25", "2025-05-01", "2025-08-15"):  # αργίες
        led.manual(expense_lines(led.amount()), day, anomaly="weekend_holiday")

    for _ in range(3):  # σπάνιος λογαριασμός
        led.manual(expense_lines(led.amount(), "81.00", "38.03"), led.pick(led.mid_month),
                   anomaly="rare_account")

    for _ in range(4):  # ακραίο ποσό για τον λογαριασμό
        a = round(float(rng.uniform(180_000, 320_000)), 2)
        led.manual(expense_lines(a), led.pick(led.mid_month), anomaly="robust_z_outlier")

    for _ in range(5):  # εκτός ωραρίου
        day = led.pick(led.mid_month)
        led.manual(expense_lines(led.amount()), day, led.at(day, rng.choice([22, 23, 0, 1, 2, 3, 4])),
                   anomaly="after_hours")

    for _ in range(5):  # χωρίς αιτιολογία
        led.manual(expense_lines(led.amount()), led.pick(led.mid_month), description="",
                   anomaly="no_description")

    # "Βελόνες": πολλές σημαίες μαζί -> πρέπει να βγουν ψηλά στη λίστα του ελεγκτή
    T = pd.Timestamp
    led.manual(expense_lines(50_000), "2025-12-31", T("2026-01-11 23:10"), "CFO",
               "Year-end adjustment", anomaly="multi_flag")
    led.manual(expense_lines(25_000, "81.00", "38.03"), "2025-12-28", T("2025-12-28 10:00"),
               "TEMP_01", "", anomaly="multi_flag")
    led.manual(expense_lines(237_412.18, "61.00", "38.03"), "2025-06-14", T("2025-06-14 21:30"),
               "CEO", "Συμβουλευτικές υπηρεσίες", vendor_id="V999", anomaly="multi_flag")
    led.manual(expense_lines(20_000, "62.00", "53.00"), "2025-09-30", T("2025-09-30 23:40"),
               "ACC_02", "", anomaly="multi_flag")
    led.manual(expense_lines(40_000, "20.00", "50.00"), "2025-12-31", T("2026-02-14 11:00"),
               "FIN_MGR", "Τιμολόγιο αγοράς", vendor_id="V010", anomaly="multi_flag")

    # Benford: ο ACC_04 "επινοεί" πληρωμές λίγο κάτω από το όριο έγκρισης των 5.000 €
    for _ in range(150):
        a = round(float(rng.uniform(4_800, 4_999.99)), 2)
        led.manual([("50.00", a, 0), ("38.03", 0, a)], led.pick(led.workdays), user="ACC_04",
                   description="Πληρωμή προμηθευτή", vendor_id=led.pick(VENDORS),
                   anomaly="benford_fabricated")


# --- Βρώμικα δεδομένα (για το Data Quality) ----------------------------

def _inject_dirty_data(led, gl):
    """Χαλάει λίγα κανονικά journals (in place). Επιστρέφει τα _tmp ids τους."""
    planted = {tmp for tmp, _ in led.truth}
    normal = gl.loc[~gl["_tmp"].isin(planted)]
    sales = normal.loc[normal["description"] == "Τιμολόγιο πώλησης", "_tmp"].unique()
    purchases = normal.loc[normal["description"] == "Τιμολόγιο αγοράς", "_tmp"].unique()
    receipts = normal.loc[normal["description"] == "Είσπραξη από πελάτη", "_tmp"].unique()
    accruals = normal.loc[normal["description"] == "Πρόβλεψη εξόδων", "_tmp"].unique()
    rng = led.rng
    s1, s2, s3 = rng.choice(sales, 3, replace=False)
    p1 = rng.choice(purchases)
    r1 = rng.choice(receipts)
    a1 = rng.choice(accruals)

    first_line = gl["line_id"] == 1
    gl.loc[(gl["_tmp"] == s1) & first_line, "created_by"] = np.nan          # 1. κενό πεδίο
    gl.loc[(gl["_tmp"] == s2) & first_line, "source"] = np.nan              # 1. κενό πεδίο
    gl.loc[(gl["_tmp"] == p1) & (gl["line_id"] == 2), "line_id"] = 1        # 2. διπλό line ID
    gl.loc[gl["_tmp"] == s3, "entry_datetime"] = pd.Timestamp("2026-03-10 10:00")  # 3. μετά το post-close
    gl.loc[(gl["_tmp"] == a1) & first_line, "account"] = "64.99"            # 4. άγνωστος λογαριασμός
    gl.loc[(gl["_tmp"] == r1) & (gl["line_id"] == 2), "credit"] += 100.0    # 5. μη ισοσκελισμένο
    return {s1, s2, s3, p1, r1, a1}


# --- Ισοζύγιο -------------------------------------------------------------

def build_trial_balance(gl):
    """Υπόλοιπο αρχής + κινήσεις χρήσης = υπόλοιπο τέλους, ανά λογαριασμό."""
    start, end = pd.Timestamp(cfg.FISCAL_YEAR_START), pd.Timestamp(cfg.FISCAL_YEAR_END)
    in_year = gl[gl["posting_date"].between(start, end)]
    movements = in_year.groupby("account")[["debit", "credit"]].sum()

    opening = pd.Series(OPENING_BALANCES, dtype=float)
    opening["40.00"] = -opening.sum()  # μετοχικό κεφάλαιο: ισοσκελίζει το ισοζύγιο έναρξης

    accounts = sorted(set(cfg.JET_CHART_OF_ACCOUNTS) | set(movements.index))
    tb = pd.DataFrame(index=pd.Index(accounts, name="account"))
    tb["account_name"] = [cfg.JET_CHART_OF_ACCOUNTS.get(a, ("Άγνωστος λογαριασμός",))[0] for a in accounts]
    tb["opening_balance"] = opening.reindex(accounts, fill_value=0.0)
    tb["period_debit"] = movements["debit"].reindex(accounts, fill_value=0.0).round(2)
    tb["period_credit"] = movements["credit"].reindex(accounts, fill_value=0.0).round(2)
    tb["closing_balance"] = (tb["opening_balance"] + tb["period_debit"] - tb["period_credit"]).round(2)
    return tb.reset_index()


# --- Δημόσιο API -----------------------------------------------------------

def generate(seed=42, break_tb=False):
    """Επιστρέφει (gl, trial_balance, ground_truth).

    break_tb=True: αφαιρεί journals από το GL ΜΕΤΑ τη δημιουργία του Ισοζυγίου,
    δηλαδή προσομοιώνει ελλιπές extract (πρέπει να σταματήσει το DQ).
    """
    led = _Ledger(np.random.default_rng(seed))
    purchases = _normal_activity(led)
    _plant_anomalies(led, purchases)
    # 3. ημερομηνία εκτός χρήσης: ένα journal της προηγούμενης χρήσης μέσα στο extract
    led.manual([("64.00", 812.40, 0), ("53.00", 0, 812.40)], "2024-12-31", pd.Timestamp("2025-01-02 09:30"))
    gl = pd.DataFrame(led.lines)
    _inject_dirty_data(led, gl)

    tb = build_trial_balance(gl)

    # Αριθμούμε τα journals με τη σειρά καταχώρησης, ώστε τα IDs να μη "μαρτυρούν" τις ανωμαλίες
    first_entry = gl.groupby("_tmp")["entry_datetime"].min().sort_values(kind="stable")
    new_ids = {tmp: f"JE-{i:06d}" for i, tmp in enumerate(first_entry.index, 1)}
    gl.insert(0, "journal_id", gl["_tmp"].map(new_ids))
    truth = pd.DataFrame([(new_ids[t], a) for t, a in led.truth], columns=["journal_id", "anomaly_type"])

    if break_tb:
        planted = set(truth["journal_id"])
        candidates = sorted(set(gl["journal_id"]) - planted)
        dropped = led.rng.choice(candidates, 3, replace=False)
        gl = gl[~gl["journal_id"].isin(dropped)]

    gl = gl.drop(columns="_tmp").sort_values(["journal_id", "line_id"], kind="stable")
    return gl[list(cfg.GL_COLUMNS)].reset_index(drop=True), tb, truth


def save(gl, tb, truth, raw_dir=cfg.JET_RAW_DIR):
    raw_dir = Path(raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "gl": raw_dir / cfg.JET_GL_CSV.name,
        "tb": raw_dir / cfg.JET_TB_CSV.name,
        "truth": raw_dir / cfg.JET_GROUND_TRUTH_CSV.name,
    }
    gl.assign(posting_date=gl["posting_date"].dt.strftime("%Y-%m-%d")).to_csv(
        paths["gl"], index=False, date_format="%Y-%m-%d %H:%M:%S")
    tb.to_csv(paths["tb"], index=False)
    truth.to_csv(paths["truth"], index=False)
    return paths


if __name__ == "__main__":
    gl, tb, truth = generate()
    paths = save(gl, tb, truth)
    print(f"✅ GL: {gl['journal_id'].nunique()} journals, {len(gl)} γραμμές -> {paths['gl']}")
    print(f"✅ Ισοζύγιο: {len(tb)} λογαριασμοί -> {paths['tb']}")
    print(f"✅ Ground truth: {len(truth)} φυτεμένα journals -> {paths['truth']}")
