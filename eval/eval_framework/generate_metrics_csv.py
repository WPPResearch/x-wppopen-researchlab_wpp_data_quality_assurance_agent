"""
Generate performance metrics CSV from eval scorecards.

Parses all experiment scorecards, compares against ground truth,
and outputs a detailed CSV with TP/FP/FN/precision/recall/F1 per run.

The CSV includes one row per (experiment, table, prompt, memory, error_category)
where error_category is one of: structural, logical, overall.

Usage:
    uv run python eval/eval_framework/generate_metrics_csv.py

Output:
    eval/eval_data/agent_performance_metrics.csv
"""

import csv
import os
import re
import sys

# Add eval directory to path to import experiment_configs
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from experiment_configs import TABLES

# Build ground truth dict from TABLES
GROUND_TRUTH = {}
for key, table_info in TABLES.items():
    gt = table_info["ground_truth"]
    GROUND_TRUTH[key] = {
        "structural": gt.get("structural_errors", []),
        "logical": gt.get("logical_errors", []),
    }


def parse_scorecard(scorecard_text: str) -> list[dict]:
    """
    Parse a scorecard.txt and extract per-report detection results.

    Returns a list of dicts, each with:
        table_name, prompt_level, memory_mode,
        structural_detected, structural_expected,
        logical_detected, logical_expected,
        detected_items, missed_items
    """
    reports = []

    # Split into report sections. Each report starts with "Report:"
    # and ends before the next "Report:" or "OVERALL COMPARISON"
    report_blocks = re.split(r"(?=Report:)", scorecard_text)

    for block in report_blocks:
        if not block.strip().startswith("Report:"):
            continue

        report = {}

        # Extract header line: "Report: <table_name> | prompt=X | memory=Y"
        # or "Report: <table_name> (Run N)"
        header_match = re.match(r"Report:\s*(.+?)(?:\s*\n)", block)
        if not header_match:
            continue

        header = header_match.group(1).strip()

        # Parse prompt and memory from header if present
        prompt_match = re.search(r"prompt\s*=\s*(\w+)", header)
        memory_match = re.search(r"memory\s*=\s*(\w+)", header)
        run_match = re.search(r"\(Run\s+(\d+)\)", header)

        report["prompt_level"] = prompt_match.group(1) if prompt_match else "complex"
        report["memory_mode"] = memory_match.group(1) if memory_match else "no_memory"
        report["run_number"] = int(run_match.group(1)) if run_match else None

        # Extract table name (everything before the first |)
        table_name = header.split("|")[0].strip()
        # Remove (Run N) suffix if present
        table_name = re.sub(r"\s*\(Run\s+\d+\)", "", table_name).strip()
        report["table_name"] = table_name

        # Extract structural errors: "Structural Errors: X / Y"
        struct_match = re.search(r"Structural Errors:\s*(\d+)\s*/\s*(\d+)", block)
        if struct_match:
            report["structural_detected"] = int(struct_match.group(1))
            report["structural_expected"] = int(struct_match.group(2))
        else:
            report["structural_detected"] = 0
            report["structural_expected"] = 0

        # Extract logical errors: "Logical Errors: X / Y"
        logic_match = re.search(r"Logical Errors:\s*(\d+)\s*/\s*(\d+)", block)
        if logic_match:
            report["logical_detected"] = int(logic_match.group(1))
            report["logical_expected"] = int(logic_match.group(2))
        else:
            report["logical_detected"] = 0
            report["logical_expected"] = 0

        # Count ✅ and ❌ items
        report["detected_items"] = re.findall(r"\*\s+(.+?)\s*✅", block)
        report["missed_items"] = re.findall(r"\*\s+(.+?)\s*❌", block)

        # Count false positives from ❌ items in the missed list
        # that say "Ground Truth (No)" — these are FPs the agent reported
        # that weren't injected
        fp_items = []
        for item in report.get("detected_items", []):
            if "Ground Truth (No)" in item or "not injected" in item.lower():
                fp_items.append(item)
        report["false_positive_items"] = fp_items

        reports.append(report)

    return reports


def resolve_table_key(table_name: str) -> str | None:
    """Map a table_name from scorecard to a ground truth table_key."""
    name_lower = table_name.lower()

    # Match synthetic tables
    if name_lower == "log_1_5_pt":
        return "synthetic_1_log_error"
    if name_lower == "log_1_5_pt_log_2_5_pt":
        return "synthetic_2_log_errors"
    if name_lower == "log_1_5_pt_log_2_5_pt_log_3_5_pt":
        return "synthetic_3_log_errors"
    if name_lower == "log_1_5_pt_log_2_5_pt_log_3_5_pt_log_4_5_pt":
        return "synthetic_4_log_errors"
    if name_lower == "log_1_5_pt_log_2_5_pt_log_3_5_pt_log_4_5_pt_log_5_5_pt":
        return "synthetic_5_log_errors"
    if (
        name_lower
        == "log_1_5_pt_log_2_5_pt_log_3_5_pt_log_4_5_pt_log_5_5_pt_log_6_5_pt"
    ):
        return "synthetic_6_log_errors"
    if (
        name_lower
        == "log_1_5_pt_log_2_5_pt_log_3_5_pt_log_4_5_pt_log_5_5_pt_log_6_5_pt_log_7_5_pt"
    ):
        return "synthetic_7_log_errors"
    if (
        name_lower
        == "log_1_5_pt_log_2_5_pt_log_3_5_pt_log_4_5_pt_log_5_5_pt_log_6_5_pt_log_7_5_pt_miss_5_pt"
    ):
        return "synthetic_7_log_1_struct"
    if (
        name_lower
        == "log_1_5_pt_log_2_5_pt_log_3_5_pt_log_4_5_pt_log_5_5_pt_log_6_5_pt_log_7_5_pt_miss_5_pt_out_5_pt"
    ):
        return "synthetic_7_log_2_struct"
    if (
        name_lower
        == "log_1_5_pt_log_2_5_pt_log_3_5_pt_log_4_5_pt_log_5_5_pt_log_6_5_pt_log_7_5_pt_miss_5_pt_out_5_pt_dup_5_pt"
    ):
        return "synthetic_7_log_3_struct"
    if (
        name_lower
        == "log_1_5_pt_log_2_5_pt_log_3_5_pt_log_4_5_pt_log_5_5_pt_log_6_5_pt_log_7_5_pt_miss_5_pt_out_5_pt_dup_5_pt_cat_5_pt"
    ):
        return "synthetic_7_log_4_struct"

    # Match specific error type tables (5% only)
    if "categorical_error_5" in name_lower:
        return "categorical_error_5pct"
    if "dropped_5" in name_lower:
        return "dropped_5pct"
    if "duplicate_5" in name_lower:
        return "duplicate_5pct"
    if "logical_error_1_5" in name_lower:
        return "logical_error_1_5pct"
    if "logical_error_2_5" in name_lower:
        return "logical_error_2_5pct"
    if "logical_error_3_5" in name_lower:
        return "logical_error_3_5pct"
    if "logical_error_4_5" in name_lower:
        return "logical_error_4_5pct"
    if "logical_error_5_5" in name_lower:
        return "logical_error_5_5pct"
    if "logical_error_6_5" in name_lower:
        return "logical_error_6_5pct"
    if "logical_error_7_5" in name_lower:
        return "logical_error_7_5pct"
    if "missing_5" in name_lower and "duplicate" not in name_lower:
        return "missing_5pct"
    if "outlier_error_5" in name_lower:
        return "outlier_error_5pct"

    return None


def compute_metrics(tp: int, fp: int, fn: int) -> dict:
    """Compute precision, recall, F1 from TP/FP/FN."""
    precision = tp / (tp + fp) if (tp + fp) > 0 else (1.0 if fn == 0 else 0.0)
    recall = tp / (tp + fn) if (tp + fn) > 0 else (1.0 if fp == 0 else 0.0)
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )
    return {"precision": precision, "recall": recall, "f1_score": f1}


def process_experiment(
    experiment_name: str,
    experiment_dir: str,
) -> list[dict]:
    """Process a single experiment directory and return metric rows."""
    scorecard_path = os.path.join(experiment_dir, "scorecard.txt")

    if not os.path.exists(scorecard_path):
        print(f"  ⚠️  No scorecard.txt in {experiment_dir}")
        return []

    with open(scorecard_path, "r", encoding="utf-8") as f:
        scorecard_text = f.read()

    reports = parse_scorecard(scorecard_text)
    if not reports:
        print(f"  ⚠️  No reports parsed from {scorecard_path}")
        return []

    rows = []
    for report in reports:
        table_key = resolve_table_key(report["table_name"])
        if not table_key or table_key not in GROUND_TRUTH:
            print(f"  ⚠️  Could not resolve table: {report['table_name']}")
            continue

        gt = GROUND_TRUTH[table_key]
        if gt.get("note"):
            # Skip tables with unknown ground truth
            continue

        n_struct_expected = len(gt["structural"])
        n_logic_expected = len(gt["logical"])
        n_struct_detected = report["structural_detected"]
        n_logic_detected = report["logical_detected"]

        # Build experiment label for consistency runs
        exp_label = experiment_name
        if report["run_number"] is not None:
            exp_label = f"{experiment_name}_run{report['run_number']}"

        # --- Structural metrics ---
        struct_tp = min(n_struct_detected, n_struct_expected)
        struct_fn = max(0, n_struct_expected - n_struct_detected)
        struct_fp = max(0, n_struct_detected - n_struct_expected)
        struct_metrics = compute_metrics(struct_tp, struct_fp, struct_fn)

        rows.append(
            {
                "experiment": exp_label,
                "table_key": table_key,
                "prompt_level": report["prompt_level"],
                "memory_mode": report["memory_mode"],
                "error_category": "structural",
                "expected": n_struct_expected,
                "detected": n_struct_detected,
                "TP": struct_tp,
                "FP": struct_fp,
                "FN": struct_fn,
                "precision": round(struct_metrics["precision"], 3),
                "recall": round(struct_metrics["recall"], 3),
                "f1_score": round(struct_metrics["f1_score"], 3),
            },
        )

        # --- Logical metrics ---
        logic_tp = min(n_logic_detected, n_logic_expected)
        logic_fn = max(0, n_logic_expected - n_logic_detected)
        logic_fp = max(0, n_logic_detected - n_logic_expected)
        logic_metrics = compute_metrics(logic_tp, logic_fp, logic_fn)

        rows.append(
            {
                "experiment": exp_label,
                "table_key": table_key,
                "prompt_level": report["prompt_level"],
                "memory_mode": report["memory_mode"],
                "error_category": "logical",
                "expected": n_logic_expected,
                "detected": n_logic_detected,
                "TP": logic_tp,
                "FP": logic_fp,
                "FN": logic_fn,
                "precision": round(logic_metrics["precision"], 3),
                "recall": round(logic_metrics["recall"], 3),
                "f1_score": round(logic_metrics["f1_score"], 3),
            },
        )

        # --- Overall metrics ---
        total_expected = n_struct_expected + n_logic_expected
        total_detected = n_struct_detected + n_logic_detected
        total_tp = struct_tp + logic_tp
        total_fp = struct_fp + logic_fp
        total_fn = struct_fn + logic_fn
        overall_metrics = compute_metrics(total_tp, total_fp, total_fn)

        rows.append(
            {
                "experiment": exp_label,
                "table_key": table_key,
                "prompt_level": report["prompt_level"],
                "memory_mode": report["memory_mode"],
                "error_category": "overall",
                "expected": total_expected,
                "detected": total_detected,
                "TP": total_tp,
                "FP": total_fp,
                "FN": total_fn,
                "precision": round(overall_metrics["precision"], 3),
                "recall": round(overall_metrics["recall"], 3),
                "f1_score": round(overall_metrics["f1_score"], 3),
            },
        )

    return rows


def get_overview_rows(detailed_rows: list[dict]) -> list[dict]:
    """Extract 'overall' category rows for quick overview display."""
    return [row for row in detailed_rows if row["error_category"] == "overall"]


def main():
    """Main entry point."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    eval_dir = os.path.dirname(script_dir)  # Go up from eval_framework/ to eval/
    results_dir = os.path.join(eval_dir, "results")
    output_dir = os.path.join(eval_dir, "eval_data")

    print("=" * 70)
    print("  GENERATING PERFORMANCE METRICS FROM EVAL SCORECARDS")
    print("=" * 70)
    print()

    # Discover all experiments
    all_rows = []

    for exp_type in sorted(os.listdir(results_dir)):
        exp_path = os.path.join(results_dir, exp_type)
        if not os.path.isdir(exp_path):
            continue

        # Get latest run (or all runs for consistency)
        runs = sorted(
            [
                d
                for d in os.listdir(exp_path)
                if os.path.isdir(os.path.join(exp_path, d))
            ],
            reverse=True,
        )

        if not runs:
            continue

        # Use the most recent run
        latest_run_dir = os.path.join(exp_path, runs[0])
        print(f"📂 {exp_type} (run: {runs[0]})")

        rows = process_experiment(exp_type, latest_run_dir)
        all_rows.extend(rows)
        print(f"   → {len(rows)} metric rows extracted")
        print()

    if not all_rows:
        print("❌ No metrics extracted. Check that scorecards exist in eval/results/.")
        return

    # Write detailed CSV
    detailed_path = os.path.join(output_dir, "agent_performance_metrics.csv")
    fieldnames = [
        "experiment",
        "table_key",
        "prompt_level",
        "memory_mode",
        "error_category",
        "expected",
        "detected",
        "TP",
        "FP",
        "FN",
        "precision",
        "recall",
        "f1_score",
    ]

    with open(detailed_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"✅ Metrics saved: {detailed_path}")
    print(f"   ({len(all_rows)} rows)")
    print()

    # Print a quick overview table (overall category only)
    overview_rows = get_overview_rows(all_rows)
    print("=" * 70)
    print("  QUICK OVERVIEW (Overall F1 & Recall per condition)")
    print("=" * 70)
    print(
        f"{'Experiment':<20} {'Table':<25} {'Prompt':<10} {'Memory':<12} {'F1':>6} {'Recall':>8}",
    )
    print("-" * 70)
    for row in overview_rows:
        exp = row["experiment"]
        table = row["table_key"]
        prompt = row["prompt_level"]
        memory = row["memory_mode"]
        f1 = row["f1_score"]
        recall = row["recall"]
        print(
            f"{exp:<20} {table:<25} {prompt:<10} {memory:<12} {f1:>6.3f} {recall:>8.3f}",
        )
    print()


if __name__ == "__main__":
    main()
