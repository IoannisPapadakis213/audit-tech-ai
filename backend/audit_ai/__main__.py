"""Τρέχει όλο το pipeline: python -m audit_ai"""
from audit_ai import audit_queries, config, data_generator, etl

if __name__ == "__main__":
    gl, truth = data_generator.generate_gl()
    data_generator.save(gl, truth)
    print(f"1️⃣  Generate: {len(gl)} εγγραφές, {len(truth)} φυτεμένες ανωμαλίες")

    clean, quarantine, results = etl.run()
    failed = [r for r in results if not r.passed]
    print(f"2️⃣  ETL + DQ: {len(clean)} καθαρές, {len(quarantine)} σε καραντίνα, "
          f"{len(failed)}/{len(results)} έλεγχοι βρήκαν προβλήματα")

    print("3️⃣  Audit rules:")
    for name in audit_queries.QUERIES:
        print(f"     {name:<22} {len(audit_queries.run_query(name)):>5} γραμμές")
    print(f"\n💾 Βάση: {config.DB_PATH}")
