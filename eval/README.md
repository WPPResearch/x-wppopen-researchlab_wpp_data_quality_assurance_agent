# Evaluation Framework

This folder tests the **auditor agent** — an AI that autonomously audits BigQuery tables for data quality issues. We measure how well it detects errors by running it against tables with **known injected errors** (ground truth) and grading its output.

---

## How It Works

```
┌───────────────────────────────────────────────────────────────┐
│                      EVALUATION PIPELINE                      │
│                                                               │
│  1. Synthetic Data     Tables in BigQuery with injected       │
│     (ground truth)     errors: NULLs, duplicates, outliers,   │
│                        categorical errors, logical violations │
│                                                               │
│  2. Run Auditor        4 experiments test different factors:  │
│     Agent                                                     │
│                        Exp 1: Prompt Comparison               │
│                          → Simple vs Medium vs Complex query  │
│                        Exp 2: Memory Ablation                 │
│                          → Cold start vs loading past audits  │
│                        Exp 3: Table Sweep                     │
│                          → All tables, one error type each    │
│                        Exp 4: Consistency                     │
│                          → Same config N times (variance)     │
│                                                               │
│                        Agent uses tools to run SQL queries    │
│                        → Produces an audit report per run     │
│                                                               │
│  3. LLM-as-Judge       Gemini Flash compares the agent's      │
│     (Gemini Flash)     report against the ground truth        │
│                        → Scores each error: ✅ detected / ❌   │
│                                                               │
│  4. Metrics            Parse scorecards → compute             │
│     Generation         precision, recall, F1 per error type   │
│                        → Save to CSV                          │
└───────────────────────────────────────────────────────────────┘
```

### What Are "Ground Truth" Errors?

The synthetic data has **11 known error types** injected at controlled rates:

| Category | Error Type | Example |
|---|---|---|
| **Structural** | Missing Values (Nulls) | Cells set to NULL |
| **Structural** | Duplicate Rows | Exact row copies |
| **Structural** | Outliers | Extreme max values injected |
| **Structural** | Categorical Errors | Random alphanumeric strings in category fields |
| **Logical** | Clicks > Impressions | Impossible: you can't click what you didn't see |
| **Logical** | Conversions > Clicks | Impossible: can't convert without clicking |
| **Logical** | Spend > 0 with 0 Impressions | Illogical: paying for nothing |
| **Logical** | Video Completions > Plays | Impossible: can't finish without starting |
| **Logical** | Purchases without Add-to-Cart | Funnel violation |
| **Logical** | Landing Page Views > Clicks | Impossible: more landings than clicks |
| **Logical** | Negative Metric Values | Performance metrics can't be negative |

---

## Quick Start

All commands are run from the **project root** directory:

```bash
# Run individual experiments
uv run python eval/eval_framework/run_prompt_comparison.py      # Experiment 1
uv run python eval/eval_framework/run_memory_ablation.py        # Experiment 2
uv run python eval/eval_framework/run_table_sweep.py            # Experiment 3
uv run python eval/eval_framework/run_consistency.py             # Experiment 4
uv run python eval/eval_framework/run_simple_memory_experiment.py

# Generate CSV metrics from results (precision, recall, F1)
uv run python eval/eval_framework/generate_metrics_csv.py

# Compare results against ground truth (text + CSV reports)
uv run python eval/eval_framework/compare_ground_truth.py

# Generate a consolidated text report across all experiments
uv run python eval/generate_report.py
```

### Prerequisites

- A `.env` file with `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, and optionally `MEMORY_SERVICE_URI`
- Access to a BigQuery dataset (configure via `BQ_DATA_PROJECT_ID` and `BQ_DATASET_ID` in `.env`)
- Python dependencies installed via `uv`

---

## Unified Experiment Runner

For ad-hoc experiments and custom table testing, use the unified `run_experiment.py` script:

```bash
# List all available experiments and tables
uv run python eval/eval_framework/run_experiment.py --list-experiments
uv run python eval/eval_framework/run_experiment.py --list-tables

# Run predefined experiments
uv run python eval/eval_framework/run_experiment.py --experiment error_rate_sweep
uv run python eval/eval_framework/run_experiment.py --experiment synthetic_sweep
uv run python eval/eval_framework/run_experiment.py --experiment synthetic_batch1

# Run a single table
uv run python eval/eval_framework/run_experiment.py --table synthetic_1_log_error
uv run python eval/eval_framework/run_experiment.py --table error_rate_10pct

# Run tables matching a pattern
uv run python eval/eval_framework/run_experiment.py --pattern "synthetic_7_*"
uv run python eval/eval_framework/run_experiment.py --pattern "error_rate_*"

# Run specific tables
uv run python eval/eval_framework/run_experiment.py --tables synthetic_1_log_error synthetic_2_log_errors

# Test memory modes on a table
uv run python eval/eval_framework/run_experiment.py --table synthetic_7_log_4_struct --memory-sweep

# Custom configurations
uv run python eval/eval_framework/run_experiment.py \
  --table synthetic_1_log_error \
  --prompt simple \
  --memory load_memory \
  --name my_custom_test
```

### Predefined Experiments

| Experiment | Description | Tables |
|------------|-------------|--------|
| `error_rate_sweep` | Test error detection across different error rates (5%, 10%, 20%, 40%) | 4 tables |
| `synthetic_sweep` | Test all synthetic tables with multiple errors | 15 tables |
| `synthetic_batch1` | Synthetic tables with 1-4 logical errors | 4 tables |
| `synthetic_batch2` | Synthetic tables with 5-7 logical errors | 3 tables |
| `synthetic_batch3` | Synthetic tables with 7 logical + structural errors | 4 tables |
| `memory_comparison` | Compare memory vs no-memory on complex table | 1 table, 2 modes |

### Options

- `--experiment, -e`: Run a predefined experiment
- `--table, -t`: Run a single table
- `--tables, -ts`: Run multiple specific tables
- `--pattern, -p`: Run tables matching a glob pattern (e.g., `"synthetic_7_*"`)
- `--prompt`: Set prompt level (`simple`, `medium`, `complex`) - default: `complex`
- `--memory`: Set memory mode (`no_memory`, `load_memory`) - default: `no_memory`
- `--memory-sweep`: Test both memory modes
- `--name, -n`: Custom experiment name for results
- `--list-experiments`: List all predefined experiments
- `--list-tables`: List all available tables

---

## The 4 Experiments

Each experiment isolates a **single variable** to understand what affects the auditor agent's detection quality.

### Experiment 1: Prompt Comparison (`run_prompt_comparison.py`)

**Question:** *Does giving the agent a more detailed prompt improve error detection?*

Runs the agent 3 times on the same table (`all_errors_5pct`, 11 injected errors), each time with a different user query style:

| Prompt Level | What the user asks | Agent's system instruction |
|---|---|---|
| **Simple** | "Check if there are any errors for table X" | Stays constant (forensic mode) |
| **Medium** | "Perform a structured assessment checking physical integrity, numerical sanity, categorical validity" | Stays constant |
| **Complex** | "Conduct a forensic audit checking for 11 specific error types with detailed cross-column logical checks" | Stays constant |

> **Key insight from results:** The complex prompt achieves F1=0.900 vs. F1=0.778 for simple.
---

### Experiment 2: Memory Ablation (`run_memory_ablation.py`)

**Question:** *Does loading past audit memories help the agent perform better?*

Runs the agent twice on the same table with the complex prompt:

| Condition | What happens |
|---|---|
| **No Memory** | Cold start — agent has no context from prior audits |
| **With Memory** | Agent loads past findings from Vertex AI memory before auditing |

---

### Experiment 3: Table Sweep (`run_table_sweep.py`)

**Question:** *How well does the agent detect different types of errors?*

Runs the agent (complex prompt, no memory) against **all 7 BigQuery tables**, each with different error profiles:

| Table | What's injected | Expected errors |
|---|---|---|
| Clean baseline | Nothing | 0 |
| Dropped 5% | 5% of columns dropped | 1 structural |
| Logical error 5% | 7 logical rule violations | 7 logical |
| Missing 5% | 5% NULLs | 1 structural |
| All errors 5% | All 4 structural + 7 logical | 11 total |
| Synthetic v1 | Unknown (exploratory) | Unknown |
| Synthetic marketing | All error types | 11 total |

---

### Experiment 4: Consistency Check (`run_consistency.py`)

**Question:** *If we run the exact same audit N times, do we get the same results?*

Runs the identical configuration (complex prompt, no memory, `all_errors_5pct` table) multiple times (default: 3):

```bash
uv run python eval/eval_framework/run_consistency.py              # 3 runs
uv run python eval/eval_framework/run_consistency.py --runs 5     # custom
```
---

### Simple Memory Experiment (`run_simple_memory_experiment.py`)

**Question:** *Does memory help the agent when given minimal instructions on a highly complex table?*

Isolates the impact of memory by using the simplest possible user prompt ("Check if there are any errors for table X?") on the most complex table available (`synthetic_7_log_4_struct`, with 11 total errors). Compares "No Memory" against "With Memory" conditions.

---

## File-by-File Guide

### `eval_framework/` — Core Infrastructure & Experiments

| File | Purpose |
|---|---|
| `experiment_configs.py` | All BigQuery tables, ground truth error definitions, 3 prompt levels, 2 memory modes, query builder |
| `experiment_runner.py` | Shared engine: sets up the ADK runner, sends queries to the agent, captures output, evaluates with Gemini Flash, saves results |
| `run_experiment.py` | **Unified runner**: Run any table, experiment, or pattern with customizable prompt/memory modes |
| `generate_metrics_csv.py` | Parses scorecards → computes TP/FP/FN/precision/recall/F1 → writes CSV files |
| `compare_ground_truth.py` | Compares scorecard detections against ground truth CSV → produces per-experiment accuracy reports |
| `run_prompt_comparison.py` | Exp 1: Simple vs Medium vs Complex user queries |
| `run_memory_ablation.py` | Exp 2: No Memory vs With Memory |
| `run_table_sweep.py` | Exp 3: All tables |
| `run_consistency.py` | Exp 4: N identical runs for reproducibility |
| `run_simple_memory_experiment.py` | Memory vs no-memory with simple prompt on a complex table |
| `run_campaign_table.py` | Run auditor on the specific `campaign_table` |
| `inspect_memories.py` | Utility to inspect the agent's memories |

### `eval/` — Legacy Scripts & Report Generation

| File | Purpose |
|---|---|
| `generate_report.py` | Reads all experiment results → writes a consolidated `summary_report.txt` |
| `run_auditor.py` | Simple single-run test of the auditor agent |
| `compare_auditor.py` | Compares two prompts (no memory vs with memory) on `synthetic_marketing_data` |
| `evaluate_auditor.py` | Standalone LLM-as-Judge scorer for pre-existing response files |

### Data Files (`eval_data/`)

| File | Purpose |
|---|---|
| `ground_truth.csv` | One row per table: expected structural/logical error counts and descriptions |
| `synthetic_data_generation_summary.csv` | Catalogue of all 48 synthetic tables and their injected error types/rates |
| `agent_performance_metrics.csv` | *Generated by `generate_metrics_csv.py`* — Detailed TP/FP/FN/precision/recall/F1 per run |
| `experiment_summary_metrics.csv` | *Generated by `generate_metrics_csv.py`* — Summary metrics per experiment condition |

---

## Output Structure

When you run an experiment, results are saved to a timestamped directory:

```
eval/results/
├── prompt_comparison/
│   └── 20260316_142653/
│       ├── metadata.json                                    # Config: tables, prompts, timestamps
│       ├── response_all_errors_5pct_simple_no_memory.txt    # Agent's raw audit report (simple)
│       ├── response_all_errors_5pct_medium_no_memory.txt    # Agent's raw audit report (medium)
│       ├── response_all_errors_5pct_complex_no_memory.txt   # Agent's raw audit report (complex)
│       ├── scorecard.txt                                    # Gemini judge: ✅/❌ per error type
│       ├── ground_truth_comparison.txt                      # Side-by-side GT vs predictions
│       └── ground_truth_comparison.csv                      # Same in CSV format
├── memory_ablation/
│   └── <timestamp>/...
├── table_sweep/
│   └── <timestamp>/...
├── consistency/
│   └── <timestamp>/...
└── summary_report.txt                                       # Consolidated report across all
```

### Key File Types

- **`response_*.txt`** — The agent's full audit report (raw text output)
- **`scorecard.txt`** — Gemini Flash grading: shows `Structural Errors: X / Y` and lists each error with ✅ or ❌
- **`metadata.json`** — Experiment config snapshot: which tables, prompts, memory modes, and timestamps
- **`ground_truth_comparison.*`** — Generated by `compare_ground_truth.py`, compares expected vs detected error counts

---

## Understanding the Metrics

The `generate_metrics_csv.py` script computes standard classification metrics by treating each error type as a binary detection task:

| Metric | Definition | What it tells you |
|---|---|---|
| **TP** (True Positive) | Agent correctly detected an injected error | Agent found a real problem |
| **FP** (False Positive) | Agent reported an error that wasn't injected | Agent hallucinated a problem |
| **FN** (False Negative) | Agent missed an injected error | Agent has a blind spot |
| **Precision** | TP / (TP + FP) | "When the agent flags something, is it real?" |
| **Recall** | TP / (TP + FN) | "Of all injected errors, how many did the agent find?" |
| **F1 Score** | Harmonic mean of precision and recall | Overall detection quality |

### Current Performance Summary

| Experiment | Best Condition | Overall F1 | Overall Recall |
|---|---|---|---|
| Prompt Comparison | Complex prompt | **0.900** | 0.818 |
| Memory Ablation | No memory | **0.625** | 0.455 |
| Table Sweep | All errors 5% table | **0.842** | 0.727 |
| Consistency | Best of 3 runs | **0.778** | 0.636 |

> **Precision is consistently near 1.0** — when the agent detects something, it's almost always a real error. **Recall is the main weakness** — the agent misses injected errors, especially duplicates, "purchases without add-to-cart", and "spend with zero impressions".
