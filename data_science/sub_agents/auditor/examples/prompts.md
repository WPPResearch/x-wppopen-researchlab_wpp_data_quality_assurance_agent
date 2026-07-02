# Auditor Agent: Final Prompt Complexity Ladder

Use these 5 prompts to test the "Agentic" depth of the Auditor sub-agent. The prompts are ordered by increasing reasoning requirements.

## Level 1: Basic Health Check
> Check if there are any errors for table $NAME_TABLE

## Level 2: Senior Analyst Persona
> You are a senior data analyst and you have to check for any errors in the table $NAME_TABLE

## Level 3: Structured Auditor (Physical & Numerical)
> As an experienced auditor perform a structured data quality assessment on table $NAME_TABLE on physical integrity , numerical sanity and logical consistency between related columns.

## Level 4: Metrics Specialist (Statistical Consistency)
> Perform a specialized analysis of the metrics in $NAME_TABLE. Identify any statistical outliers, impossible ranges, or inconsistencies in how metrics are aggregated (e.g., averages that don't match totals). Provide a risk-rated summary of any anomalies found and the SQL queries you used to identify them.

## Level 5: Forensic Data Scientist (Exhaustive & Blackbox)
> You are a Forensic Data Scientist tasked with an exhaustive, blackbox audit of table $NAME_TABLE. Your mission is to proactively hunt for data corruption without assuming any predefined rules. Instead, analyze the schema to infer complex dependencies, including hierarchical parent-child relationships, temporal consistency, and cumulative 'waterfall' logic. Investigate any records that violate these inferred constraints or present significant statistical anomalies. Finally, deliver a comprehensive report detailing the rules you deduced, the exact SQL logic used for verification, the total count/percentage of violations, and specific examples of the corrupted records.
