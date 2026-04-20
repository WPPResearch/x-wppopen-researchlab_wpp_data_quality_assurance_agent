"""
Centralized experiment configuration for auditor agent evaluation.

Defines all tables, ground truth errors, prompt levels, memory modes,
and query templates used by the experiment scripts.
"""

import csv
import os

# ── BigQuery Tables ──────────────────────────────────────────────────────
# Read from environment variables, with fallback for backwards compatibility
_project = os.getenv("BQ_DATA_PROJECT_ID", "YOUR-PROJECT-ID")
_dataset = os.getenv("BQ_DATASET_ID", "synthetic_data")
PROJECT_DATASET = f"{_project}.{_dataset}"


# Load ground truth from CSV
def load_ground_truth():
    """Load ground truth from ground_truth_eval_table.csv"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(
        script_dir,
        "..",
        "eval_data",
        "ground_truth_eval_table.csv",
    )

    ground_truth_data = {}

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            table_name = row["Table_description_name"]

            # Parse structural errors
            structural_errors = []
            if row["number_of_injected_structural_errors"] != "0":
                error_type = row["type_of_structural_error"]
                if error_type and error_type != "-":
                    # Split comma-separated errors
                    structural_errors = [e.strip() for e in error_type.split(",")]

            # Parse logical errors
            logical_errors = []
            if row["number_of_injected_logical_errors"] != "0":
                error_type = row["type_of_logical_error"]
                if error_type and error_type != "-":
                    # Split comma-separated errors
                    logical_errors = [e.strip() for e in error_type.split(",")]

            ground_truth_data[table_name] = {
                "structural": structural_errors,
                "logical": logical_errors,
            }

    return ground_truth_data


# Build TABLES dict from ground truth
GROUND_TRUTH_DATA = load_ground_truth()

# Define the 12 tables for evaluation (5% error rate only)
TABLE_CONFIGS = [
    (
        "categorical_error_5pct",
        "our_training_dataset_sample_anonymized_categorical_error_5_percent",
        "5% categorical errors",
    ),
    (
        "dropped_5pct",
        "our_training_dataset_sample_anonymized_dropped_5_percent",
        "5% dropped columns",
    ),
    (
        "duplicate_5pct",
        "our_training_dataset_sample_anonymized_duplicate_5_percent",
        "5% duplicate rows",
    ),
    (
        "logical_error_1_5pct",
        "our_training_dataset_sample_anonymized_logical_error_1_5_percent",
        "5% clicks exceed impressions",
    ),
    (
        "logical_error_2_5pct",
        "our_training_dataset_sample_anonymized_logical_error_2_5_percent",
        "5% conversions exceed clicks",
    ),
    (
        "logical_error_3_5pct",
        "our_training_dataset_sample_anonymized_logical_error_3_5_percent",
        "5% spend with zero impressions",
    ),
    (
        "logical_error_4_5pct",
        "our_training_dataset_sample_anonymized_logical_error_4_5_percent",
        "5% video completions exceed plays",
    ),
    (
        "logical_error_5_5pct",
        "our_training_dataset_sample_anonymized_logical_error_5_5_percent",
        "5% purchases without add to cart",
    ),
    (
        "logical_error_6_5pct",
        "our_training_dataset_sample_anonymized_logical_error_6_5_percent",
        "5% landing page views exceed clicks",
    ),
    (
        "logical_error_7_5pct",
        "our_training_dataset_sample_anonymized_logical_error_7_5_percent",
        "5% negative metric values",
    ),
    (
        "missing_5pct",
        "our_training_dataset_sample_anonymized_missing_5_percent",
        "5% missing values (NULLs)",
    ),
    (
        "outlier_error_5pct",
        "our_training_dataset_sample_anonymized_outlier_error_5_percent",
        "5% outlier errors",
    ),
]

# Define synthetic tables with multiple errors (examples 49-59)
SYNTHETIC_TABLE_CONFIGS = [
    (
        "synthetic_1_log_error",
        "log_1_5_pt",
        "Synthetic: 1 logical error (clicks exceed impressions)",
    ),
    (
        "synthetic_2_log_errors",
        "log_1_5_pt_log_2_5_pt",
        "Synthetic: 2 logical errors",
    ),
    (
        "synthetic_3_log_errors",
        "log_1_5_pt_log_2_5_pt_log_3_5_pt",
        "Synthetic: 3 logical errors",
    ),
    (
        "synthetic_4_log_errors",
        "log_1_5_pt_log_2_5_pt_log_3_5_pt_log_4_5_pt",
        "Synthetic: 4 logical errors",
    ),
    (
        "synthetic_5_log_errors",
        "log_1_5_pt_log_2_5_pt_log_3_5_pt_log_4_5_pt_log_5_5_pt",
        "Synthetic: 5 logical errors",
    ),
    (
        "synthetic_6_log_errors",
        "log_1_5_pt_log_2_5_pt_log_3_5_pt_log_4_5_pt_log_5_5_pt_log_6_5_pt",
        "Synthetic: 6 logical errors",
    ),
    (
        "synthetic_7_log_errors",
        "log_1_5_pt_log_2_5_pt_log_3_5_pt_log_4_5_pt_log_5_5_pt_log_6_5_pt_log_7_5_pt",
        "Synthetic: 7 logical errors (all types)",
    ),
    (
        "synthetic_7_log_1_struct",
        "log_1_5_pt_log_2_5_pt_log_3_5_pt_log_4_5_pt_log_5_5_pt_log_6_5_pt_log_7_5_pt_miss_5_pt",
        "Synthetic: 7 logical + 1 structural (null values)",
    ),
    (
        "synthetic_7_log_2_struct",
        "log_1_5_pt_log_2_5_pt_log_3_5_pt_log_4_5_pt_log_5_5_pt_log_6_5_pt_log_7_5_pt_miss_5_pt_out_5_pt",
        "Synthetic: 7 logical + 2 structural (nulls, outliers)",
    ),
    (
        "synthetic_7_log_3_struct",
        "log_1_5_pt_log_2_5_pt_log_3_5_pt_log_4_5_pt_log_5_5_pt_log_6_5_pt_log_7_5_pt_miss_5_pt_out_5_pt_dup_5_pt",
        "Synthetic: 7 logical + 3 structural (nulls, outliers, duplicates)",
    ),
    (
        "synthetic_7_log_4_struct",
        "log_1_5_pt_log_2_5_pt_log_3_5_pt_log_4_5_pt_log_5_5_pt_log_6_5_pt_log_7_5_pt_miss_5_pt_out_5_pt_dup_5_pt_cat_5_pt",
        "Synthetic: 7 logical + 4 structural (nulls, outliers, duplicates, categorical)",
    ),
    # Error rate sweep tables (examples 60-63)
    (
        "error_rate_5pct",
        "log_1_5_pt",
        "Error Rate: 5% clicks exceed impressions",
    ),
    (
        "error_rate_10pct",
        "log_1_10_pt",
        "Error Rate: 10% clicks exceed impressions",
    ),
    (
        "error_rate_20pct",
        "log_1_20_pt",
        "Error Rate: 20% clicks exceed impressions",
    ),
    (
        "error_rate_40pct",
        "log_1_40_pt",
        "Error Rate: 40% clicks exceed impressions",
    ),
]

TABLES = {}
for key, short_name, description in TABLE_CONFIGS:
    gt = GROUND_TRUTH_DATA.get(short_name, {"structural": [], "logical": []})
    TABLES[key] = {
        "full_name": f"{PROJECT_DATASET}.{short_name}",
        "short_name": short_name,
        "description": description,
        "ground_truth": {
            "structural_errors": gt["structural"],
            "logical_errors": gt["logical"],
        },
    }

# Add synthetic tables
for key, short_name, description in SYNTHETIC_TABLE_CONFIGS:
    gt = GROUND_TRUTH_DATA.get(short_name, {"structural": [], "logical": []})
    TABLES[key] = {
        "full_name": f"{PROJECT_DATASET}.{short_name}",
        "short_name": short_name,
        "description": description,
        "ground_truth": {
            "structural_errors": gt["structural"],
            "logical_errors": gt["logical"],
        },
    }


# ── Prompt Levels ────────────────────────────────────────────────────────
# These match the three prompt levels defined in
# data_science/sub_agents/auditor/prompts.py

PROMPT_LEVELS = {
    "simple": {
        "label": "Level 1 — Simple (Basic Health Check)",
        "description": "Explore, verify, report. Minimal guidance on what to look for.",
    },
    "medium": {
        "label": "Level 2 — Medium (Structured Assessment)",
        "description": "Structured pillars: physical integrity + numerical sanity.",
    },
    "complex": {
        "label": "Level 3 — Complex (Forensic Autonomy & Deep Analytical Reasoning)",
        "description": "Full forensic audit with cross-column hypotheses and memory.",
    },
}


# ── Memory Modes ─────────────────────────────────────────────────────────
MEMORY_MODES = {
    "no_memory": {
        "label": "No Memory",
        "query_prefix": "",
        "description": "Pure cold-start audit, no memory loaded or saved.",
    },
    "load_memory": {
        "label": "With Memory",
        "query_prefix": "load memories about auditing tables then ",
        "description": "Load past memories about auditing tables before starting.",
    },
}


def build_audit_query(
    table_key: str,
    memory_mode: str = "no_memory",
    prompt_level: str = "simple",
) -> str:
    """Build the audit query string for a given table, memory mode, and prompt level."""
    table_short = TABLES[table_key]["short_name"]
    mode_cfg = MEMORY_MODES[memory_mode]

    prefix = mode_cfg.get("query_prefix", "")
    suffix = mode_cfg.get("query_suffix", "")

    # Build base query depending on prompt level
    if prompt_level == "simple":
        base = f"Check if there are any errors for table {table_short}?"
    elif prompt_level == "medium":
        base = f"""Perform a structured data quality assessment on table {table_short}.

Check for:
1. Physical Integrity: missing values (NULLs), duplicate rows
2. Numerical Sanity: outliers, values outside logical bounds (e.g., negative metrics)
3. Categorical Validity: invalid categories or malformed values

Summarize your findings by data quality pillar and quantify the impact."""
    elif prompt_level == "complex":
        base = f"""Conduct a comprehensive forensic data quality audit on table {table_short}.

Perform the following checks:

1. **Missing Values**: Identify unexpected NULLs across all columns
2. **Duplicate Rows**: Find exact row matches and primary key violations
3. **Outliers**: Detect statistically anomalous values (extreme max/min values)
4. **Categorical Errors**: Discover invalid categories, random strings, or cardinality anomalies
5. **Logical Inconsistencies**: Test cross-column relationships and business rules:
   - Check if clicks > impressions (impossible)
   - Check if conversions > clicks (impossible for click-attributed conversions)
   - Check if spend > 0 while impressions = 0 (illogical)
   - Check if video completions > video plays (impossible)
   - Check if purchases occur without add-to-cart events (funnel violation)
   - Check if landing page views > clicks (impossible)
   - Check for negative values in performance metrics (impossible)
   - Check video completion percentage progression (25% >= 50% >= 75% >= 100%)

For each issue found, quantify the exact percentage and absolute count of affected rows. Provide forensic explanations of why each violation is logically impossible."""
    else:
        base = f"Check if there are any errors for table {table_short}?"

    return f"{prefix}{base}{suffix}"


def get_ground_truth_prompt(table_key: str) -> str:
    """Build the ground-truth section for the Gemini judge prompt."""
    gt = TABLES[table_key]["ground_truth"]
    structural = gt.get("structural_errors", [])
    logical = gt.get("logical_errors", [])
    note = gt.get("note", "")

    if note:
        return f"    **Note:** {note}\n"

    lines = []
    lines.append(f"    **Structural Errors ({len(structural)}):**")
    if structural:
        for i, e in enumerate(structural, 1):
            lines.append(f"    {i}. {e}")
    else:
        lines.append("    None")

    lines.append(f"\n    **Logical Errors ({len(logical)}):**")
    if logical:
        for i, e in enumerate(logical, 1):
            lines.append(f"    {i}. {e}")
    else:
        lines.append("    None")

    return "\n".join(lines)


# ── Quick self-test ──────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== Experiment Configs Self-Test ===\n")
    for key, tbl in TABLES.items():
        print(f"  [{key}]")
        print(f"    Table: {tbl['short_name']}")
        gt = tbl["ground_truth"]
        n_struct = len(gt.get("structural_errors", []))
        n_logic = len(gt.get("logical_errors", []))
        print(f"    Ground truth: {n_struct} structural, {n_logic} logical")
        print(
            f"    Errors: {gt.get('structural_errors', [])} / {gt.get('logical_errors', [])}",
        )
        print()
    print(f"✅ All {len(TABLES)} tables configured.")
