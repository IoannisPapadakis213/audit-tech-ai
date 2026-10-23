# Databricks notebook source
# MAGIC %sql
# MAGIC SELECT COUNT(*) AS lines,
# MAGIC        COUNT(DISTINCT journal_id) AS journals
# MAGIC FROM fact_journal_lines

# COMMAND ----------

# MAGIC %md
# MAGIC cell 2:IΣΟΣΚΕΛΙΖΕΙ ΤΟ ΚΑΘΟΛΙΚΟ
# MAGIC

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT ROUND(SUM(debit), 2)               AS total_debit,
# MAGIC        ROUND(SUM(credit), 2)              AS total_credit,
# MAGIC        ROUND(SUM(debit) - SUM(credit), 2) AS difference
# MAGIC FROM fact_journal_lines

# COMMAND ----------

# MAGIC %md
# MAGIC Cell 3: Αυτο-έγκριση (segregation of duties)

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT COUNT(DISTINCT journal_id) AS self_approved_journals
# MAGIC FROM fact_journal_lines
# MAGIC WHERE created_by = approved_by

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT COUNT(DISTINCT journal_id) AS unapproved_journals
# MAGIC FROM fact_journal_lines
# MAGIC WHERE approved_by IS NULL

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT created_by,
# MAGIC        COUNT(DISTINCT journal_id) AS high_risk_journals
# MAGIC FROM fact_journal_lines
# MAGIC WHERE is_high_risk = 1
# MAGIC GROUP BY created_by
# MAGIC ORDER BY high_risk_journals DESC

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE gold_rule_hits AS
# MAGIC SELECT DISTINCT journal_id, 'self_approved' AS rule
# MAGIC FROM fact_journal_lines
# MAGIC WHERE created_by = approved_by
# MAGIC UNION ALL
# MAGIC SELECT DISTINCT journal_id, 'weekend_manual' AS rule
# MAGIC FROM fact_journal_lines
# MAGIC WHERE is_weekend = 1 AND is_manual = 1
# MAGIC UNION ALL
# MAGIC SELECT DISTINCT journal_id, 'year_end_manual' AS rule
# MAGIC FROM fact_journal_lines
# MAGIC WHERE is_manual = 1 AND days_to_year_end BETWEEN 0 AND 10

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT rule, COUNT(*) AS journals
# MAGIC FROM gold_rule_hits
# MAGIC GROUP BY rule
# MAGIC ORDER BY journals DESC

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT r.rule,
# MAGIC        COUNT(DISTINCT r.journal_id) AS journals_hit,
# MAGIC        COUNT(DISTINCT CASE WHEN f.is_high_risk = 1 THEN r.journal_id END) AS of_which_high_risk
# MAGIC FROM gold_rule_hits r
# MAGIC JOIN fact_journal_lines f ON r.journal_id = f.journal_id
# MAGIC GROUP BY r.rule
# MAGIC ORDER BY journals_hit DESC

# COMMAND ----------

from pyspark.sql import functions as F

lines = spark.table("fact_journal_lines")

by_user = (
    lines.filter("is_high_risk = 1")
         .groupBy("created_by")
         .agg(F.countDistinct("journal_id").alias("high_risk_journals"))
         .orderBy(F.desc("high_risk_journals"))
)
display(by_user)