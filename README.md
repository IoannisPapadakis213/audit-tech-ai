# Audit Tech AI

Audit analytics για **Journal Entry Testing** πάνω σε General Ledger: ETL pipeline με
data quality controls, κανόνες ανίχνευσης κινδύνου σε SQL και (σύντομα) API, React dashboard
και AI βοηθό με Gemini.

## Αρχιτεκτονική

```
data_generator ─► extract ─► data quality ─► transform ─► load (SQLite)
                                  │                            │
                            dq_quarantine              audit_queries (SQL rules)
```

| Module | Ρόλος |
|---|---|
| `audit_ai/config.py` | Ρυθμίσεις: paths, λογιστικό σχέδιο, κατώφλια κανόνων |
| `audit_ai/data_generator.py` | Συνθετικό GL με φυτεμένες ανωμαλίες και ground truth |
| `audit_ai/data_quality.py` | Έλεγχοι ποιότητας, καραντίνα προβληματικών εγγραφών |
| `audit_ai/etl.py` | Extract → Validate → Transform → Load |
| `audit_ai/audit_queries.py` | Κανόνες JE testing σε SQL (window functions) |

## Εκτέλεση

```bash
python -m venv venv && source venv/bin/activate
pip install -r backend/requirements.txt
cd backend
python -m audit_ai          # όλο το pipeline
python -m pytest            # tests
```

## Roadmap

- [x] Φάση 1: ETL, Data Quality, SQL audit rules, tests
- [ ] Φάση 2: Στατιστική ανίχνευση (Benford, z-score, Isolation Forest)
- [ ] Φάση 3: FastAPI backend
- [ ] Φάση 4: React dashboard
- [ ] Φάση 5: AI βοηθός με Gemini
- [ ] Φάση 6: Deploy σε Azure
- [ ] Φάση 7: Databricks / PySpark
