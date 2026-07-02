The process has two main stages: **anonymize**, then optionally **inject errors** for evaluation purposes using isolated run scripts.

---

## Step 1 — Anonymize Sensitive Columns

**Script:** `anonymize_csv.py`

Replaces real values in the following columns with generic labels to remove PII / commercially sensitive data:

| Column                       | Mapped to                                    |
| ---------------------------- | -------------------------------------------- |
| `sensitive_column_1`        | `label_1`, `label_1`, …                      |
| `sensitive_column_2`        | `label_2`, `label_2`, …                      |
| `sensitive_column_3`        | `label_3`, `label_3`, …                      |
| `sensitive_column_4`        | `label_4`, `label_4`, …                      |
| `sensitive_column_5`        | `label_5`, `label_5`, …                      |

- Mapping is deterministic (same input → same output).
- `NaN` values are preserved as-is.

**Run:**

```bash
uv run python synthetic_data_generation/anonymize_csv.py \
  --input path/to/your_file.csv
```

---


## Step 2 — Inject Missing Values

Injects `NaN` values into the dataset to simulate data quality degradation.

- Injection rate: specify one or more percentage values (e.g., `--error-pcts 5 10 20 40`)
- Targets all columns by default, or specify with `--columns`
- Reproducible via `--seed` (default: 42)
- Output: injected CSV + sidecar `.json` per percentage

> [!IMPORTANT]
> **Target % Attainment**: In sparse datasets (those already containing many `NaN` values), the script may not reach the exact requested error percentage. This is because the injection logic only targets **non-null** cells to ensure new errors are actually created. For example, requesting a 5.0% increase in nulls on a sparse table might only result in ~3.8% of targeted cells being nulled.

**Output folder:** `<file_stem>_missing_values_injected/`
**Output files:** `miss_N_pt.csv` + `miss_N_pt.json` (e.g., `miss_5_pt.csv`)

**Run:** See [Orchestration & Execution](#step-8--orchestration--execution) below.

---

## Step 3 — Inject Outliers

**Script:** `inject_outliers.py`

Injects extreme numerical values into all numeric columns.

- Outlier formula per cell: `mean ± (random_multiplier × std)` where `random_multiplier ∈ [multiplier, multiplier×3]`
- Each injected value is unique — direction and magnitude are randomized per cell
- Global mean/std computed across the dataset for stable thresholds

**Output folder:** `<file_stem>_outlier_errors_injected/`
**Output files:** `out_N_pt.csv` + `out_N_pt.json` (e.g., `out_5_pt.csv`)

**Run:** See [Orchestration & Execution](#step-8--orchestration--execution) below.

---

## Step 4 — Inject Duplicate Rows

**Script:** `inject_duplicates.py`

**Output folder:** `<file_stem>_duplicates_injected/`
**Output files:** `dup_N_pt.csv` + `dup_N_pt.json` (e.g., `dup_5_pt.csv`)

**Run:** See [Orchestration & Execution](#step-8--orchestration--execution) below.

**Error log entry:**

```json
{
  "source_row_index": 142,
  "inserted_at_position": 387,
  "error_type": "duplicate_row",
  "duplicate_pct": 5.0
}
```

---

## Step 5 — Inject Categorical Errors

**Script:** `inject_categorical_errors.py`

Replaces values in string/categorical columns with **unique random strings** that are guaranteed not to be valid category values. Each cell gets a different unknown class, creating maximum class diversity.

- Builds the valid category set per column across the dataset before injection
- Each corrupted value is a unique 8-character alphanumeric string outside the valid set

**Output folder:** `<file_stem>_categorical_errors_injected/`
**Output files:** `cat_N_pt.csv` + `cat_N_pt.json` (e.g., `cat_5_pt.csv`)

**Run:** See [Orchestration & Execution](#step-8--orchestration--execution) below.

---

## Step 6 — Inject Dropped Columns

**Script:** `inject_dropped_columns.py`

Randomly drops entire columns from the dataset. This simulates scenarios where a data source fails to provide specific fields for a period of time.

- Progressively drops more columns for higher error percentages
- A sidecar JSON log is saved per run recording exactly which columns were removed.
- Validated to ensure at least one column remains (never drops everything).

> [!NOTE]
> This step is **not used in the core experiments**. Detecting dropped columns is typically impossible in a single-run/snapshot context without access to the table's schema history.

**Output folder:** `<file_stem>_dropped_columns_injected/`
**Output files:** `drop_N_pt.csv` + `drop_N_pt.json` (e.g., `drop_5_pt.csv`)

**Run:** See [Orchestration & Execution](#step-8--orchestration--execution) below.

---

## Step 7 — Inject Logical Errors

**Scripts:** `inject_logical_error_N_*.py`

Injects violations of business rules — relationships between columns that should always hold. These are the hardest errors to detect because individual cell values look valid in isolation. Each rule has its own injection script for granular control and isolated evaluation.

**Available rules and scripts:**

| ID | Rule                                 | Script                                                         | Violation                                     |
| -- | ------------------------------------ | -------------------------------------------------------------- | --------------------------------------------- |
| 1  | `clicks_exceed_impressions`        | `inject_logical_error_1_clicks_exceed_impressions.py`        | clicks > impressions                          |
| 2  | `conversions_exceed_clicks`        | `inject_logical_error_2_conversions_exceed_clicks.py`        | conversions > clicks                          |
| 3  | `spend_with_zero_impressions`      | `inject_logical_error_3_spend_with_zero_impressions.py`      | spend > 0 but impressions = 0                 |
| 4  | `video_completions_exceed_plays`   | `inject_logical_error_4_video_completions_exceed_plays.py`   | completions > plays                           |
| 5  | `purchases_without_add_to_cart`    | `inject_logical_error_5_purchases_without_add_to_cart.py`    | purchase > 0 but add_to_cart = 0              |
| 6  | `landing_page_views_exceed_clicks` | `inject_logical_error_6_landing_page_views_exceed_clicks.py` | page views > clicks                           |
| 7  | `negative_metric_values`           | `inject_logical_error_7_negative_metric_values.py`           | negative impressions/clicks/spend/conversions |

**Output folders:** `<file_stem>_logical_error_N_injected/` (where N is the rule ID)
**Output files:** `log_N_X_pt.csv` + `log_N_X_pt.json` (e.g., `log_1_5_pt.csv`)

**Run:** See [Orchestration & Execution](#step-8--orchestration--execution) below.

---

## Step 8 — Orchestration & Execution

To generate the synthetic evaluation datasets, run the following bash scripts. They provide standardized entry points for injecting errors with unique seeds into the anonymized data.

- **`run_logical_errors.sh`**: Runs all 7 logical business rule injections (Rules 1-7).
- **`run_structural_errors.sh`**: Runs all structural error injections (Missing, Outliers, Duplicates, Categorical).
- **`run_11_errors_sequential.sh`**: Chains 11 different error types (7 logical, 4 structural) sequentially to create complex datasets (e.g., `mixed_11_errors_stacked/log_1_5_pt_..._cat_5_pt.csv`).

### End-to-End Workflow Example

The following sequence uses `anonymize_csv.py` for data preparation, followed by the orchestration scripts:

```bash
# 1. Anonymize
uv run python synthetic_data_generation/anonymize_csv.py \
  --input data_science/utils/data/our_training_dataset_sample.csv

# 2. Inject structural and logical errors
./synthetic_data_generation/run_structural_errors.sh
./synthetic_data_generation/run_logical_errors.sh

# 3. Or generate complex sequentially stacked datasets
./synthetic_data_generation/run_11_errors_sequential.sh 5
```

---

## Step 9 — Generate Summary Table

**Script:** `generate_summary.py`

This script automates the creation of a high-level summary of all generated synthetic datasets. It parses both individual and mixed error folders to provide a clear ground truth comparison for evaluation.

**Key Features:**
- **Auto-discovery**: Automatically finds all `_injected` and `mixed_11_errors_stacked` directories.
- **Error Parsing**: Extracts injected error types from both filenames and sidecar `.json` logs.
- **Reporting**: Generates a CSV showing precisely what errors are present in each file.

**Output Columns:**
- `Table_name`: Identifier for the file (e.g., `example_01`).
- `Table_description_name`: The shortened injected filename (e.g., `log_1_5_pt`).
- `max_number_of_logical_errors`: The total potential logical errors (7) if any are present.
- `number_of_injected_logical_errors`: The actual count of distinct logical rules applied.
- `type_of_logical_error`: A comma-separated list of the specific rules.
- `max_number_of_structural_errors`: The total potential structural errors (4) if any are present.
- `number_of_injected_structural_errors`: The count of structural error types applied.
- `type_of_structural_error`: A list of structural errors (e.g., `null values`, `outliers`).

**Run:**
```bash
uv run python synthetic_data_generation/generate_summary.py
```

**Output file:** `synthetic_data_generation/synthetic_data_generation_summary.csv`

## Evaluation

Every injection step produces a **sidecar JSON file** for each generated CSV:

**Log file:** `[short_name]_N_pt.json`
Records every cell or row that was modified for a specific error percentage, including the original value. Use these as ground truth for evaluating detection accuracy. Note: long dataset prefixes are stripped from generated files to prevent OS file name limits during sequential testing.


---

### Error log examples

**Step 2 — Missing values** (`miss_N_pt.json`)

```json
{
  "row_index": 42,
  "column": "performance__clicks",
  "original_value": 1200.0,
  "error_type": "missing_value",
  "missing_pct": 5.0
}
```

**Step 3 — Outliers** (`out_N_pt.json`)

```json
{
  "row_index": 17,
  "column": "performance__spend_usd",
  "original_value": 45.32,
  "injected_value": 4789.11,
  "direction": "high",
  "multiplier": 8.3,
  "error_type": "outlier"
}
```

**Step 4 — Duplicate rows** (`dup_N_pt.json`)

```json
{
  "source_row_index": 142,
  "inserted_at_position": 387,
  "error_type": "duplicate_row",
  "duplicate_pct": 5.0
}
```

**Step 5 — Categorical errors** (`cat_N_pt.json`)

```json
{
  "row_index": 88,
  "column": "sensitive_column_1",
  "original_value": "label_1_original",
  "injected_value": "xK7pQmRz",
  "error_type": "categorical_error",
  "error_pct": 5.0
}
```

**Step 6 — Dropped columns** (`drop_N_pt.json`)

```json
{
  "column": "performance__spend_usd",
  "error_type": "dropped_column",
  "drop_pct": 5.0
}
```

**Step 7 — Logical errors** (`log_N_X_pt.json`)

```json
{
  "row_index": 204,
  "rule": "clicks_exceed_impressions",
  "columns_affected": ["performance__clicks"],
  "original_values": { "performance__clicks": 320.0 },
  "injected_values": { "performance__clicks": 1187 },
  "error_type": "logical_error"
}
```
