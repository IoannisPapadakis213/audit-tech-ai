"""Δύο γραφήματα για το README από τα πραγματικά αποτελέσματα."""
import pandas as pd
import matplotlib.pyplot as plt
from audit_ai.config import POWERBI_DIR

lines = pd.read_csv(POWERBI_DIR / "fact_journal_lines.csv")
digits = pd.read_csv(POWERBI_DIR / "dim_digit.csv")

# 1. Benford: πραγματικό vs αναμενόμενο
fig, ax = plt.subplots(figsize=(8, 4))
ax.bar(digits["digit"], digits["actual"], label="Actual")
ax.plot(digits["digit"], digits["expected"], "o-", color="black", label="Benford expected")
ax.set_title("Benford's Law – first digit"); ax.set_xlabel("First digit"); ax.legend()
fig.tight_layout(); fig.savefig("../docs/benford.png", dpi=150)

# 2. Υψηλού κινδύνου journals ανά ώρα καταχώρησης
hr = lines[lines["is_high_risk"] == 1].drop_duplicates("journal_id")
counts = hr.groupby("entry_hour").size().reindex(range(24), fill_value=0)
fig, ax = plt.subplots(figsize=(8, 4))
ax.bar(counts.index, counts.values, color="#c0392b")
ax.axvspan(-0.5, 7.5, alpha=0.1); ax.axvspan(17.5, 23.5, alpha=0.1)
ax.set_title("High-risk journals by entry hour (shaded = outside 08–18)")
ax.set_xlabel("Hour"); ax.set_ylabel("Journals")
fig.tight_layout(); fig.savefig("../docs/high_risk_by_hour.png", dpi=150)
print("✅ docs/benford.png, docs/high_risk_by_hour.png")
