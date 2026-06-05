"""
Generate a comprehensive metrics report from agent_performance_metrics.csv

Creates a formatted markdown report showing:
1. Per-table detailed metrics (TP, FP, FN, Precision, Recall, F1)
2. Overall aggregated metrics across all experiments

Usage:
    uv run python eval/eval_framework/generate_metrics_report.py
"""

import csv
import os
from collections import defaultdict


def load_metrics(csv_path):
    """Load metrics from CSV and return list of dicts."""
    metrics = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Convert numeric fields
            row["expected"] = int(row["expected"])
            row["detected"] = int(row["detected"])
            row["TP"] = int(row["TP"])
            row["FP"] = int(row["FP"])
            row["FN"] = int(row["FN"])
            row["precision"] = float(row["precision"])
            row["recall"] = float(row["recall"])
            row["f1_score"] = float(row["f1_score"])
            metrics.append(row)
    return metrics


def filter_overall_metrics(metrics):
    """Filter to only 'overall' category rows."""
    return [m for m in metrics if m["error_category"] == "overall"]


def compute_overall_aggregates(metrics):
    """Compute aggregated metrics across all experiments."""
    total_tp = sum(m["TP"] for m in metrics)
    total_fp = sum(m["FP"] for m in metrics)
    total_fn = sum(m["FN"] for m in metrics)
    total_expected = sum(m["expected"] for m in metrics)
    total_detected = sum(m["detected"] for m in metrics)

    # Calculate TN (True Negatives)
    # TN = cases where no error expected and none detected
    total_tn = sum(1 for m in metrics if m["expected"] == 0 and m["detected"] == 0)

    # Compute precision, recall, F1
    precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )

    # Compute accuracy
    total_predictions = total_tp + total_fp + total_fn + total_tn
    accuracy = (
        (total_tp + total_tn) / total_predictions if total_predictions > 0 else 0.0
    )

    return {
        "total_experiments": len(metrics),
        "total_tp": total_tp,
        "total_fp": total_fp,
        "total_fn": total_fn,
        "total_tn": total_tn,
        "total_expected": total_expected,
        "total_detected": total_detected,
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "accuracy": accuracy,
    }


def group_by_experiment(metrics):
    """Group metrics by experiment name."""
    grouped = defaultdict(list)
    for m in metrics:
        grouped[m["experiment"]].append(m)
    return grouped


def generate_markdown_report(metrics, output_path):
    """Generate a comprehensive markdown report."""
    overall_metrics = filter_overall_metrics(metrics)
    aggregates = compute_overall_aggregates(overall_metrics)

    report = []
    report.append("# Auditor Agent Performance Metrics Report")
    report.append("")
    report.append(f"**Generated:** {os.path.basename(output_path)}")
    report.append(f"**Total Experiments:** {aggregates['total_experiments']}")
    report.append("")

    # Overall Summary
    report.append("## Overall Performance Summary")
    report.append("")
    report.append("| Metric | Value |")
    report.append("|--------|-------|")
    report.append(f"| **Total Expected Errors** | {aggregates['total_expected']} |")
    report.append(f"| **Total Detected Errors** | {aggregates['total_detected']} |")
    report.append(f"| **True Positives (TP)** | {aggregates['total_tp']} |")
    report.append(f"| **False Positives (FP)** | {aggregates['total_fp']} |")
    report.append(f"| **False Negatives (FN)** | {aggregates['total_fn']} |")
    report.append(f"| **True Negatives (TN)** | {aggregates['total_tn']} |")
    report.append(f"| **Precision** | {aggregates['precision']:.3f} |")
    report.append(f"| **Recall** | {aggregates['recall']:.3f} |")
    report.append(f"| **F1 Score** | {aggregates['f1_score']:.3f} |")
    report.append(f"| **Accuracy** | {aggregates['accuracy']:.3f} |")
    report.append("")

    # Per-Table Detailed Metrics
    report.append("## Per-Table Performance Metrics")
    report.append("")
    report.append(
        "| Table Name | Experiment | Expected | Detected | TP | FP | FN | Precision | Recall | F1 Score |",
    )
    report.append(
        "|------------|------------|----------|----------|----|----|-------|-----------|--------|----------|",
    )

    for m in overall_metrics:
        table = m["table_key"]
        exp = m["experiment"]
        expected = m["expected"]
        detected = m["detected"]
        tp = m["TP"]
        fp = m["FP"]
        fn = m["FN"]
        precision = m["precision"]
        recall = m["recall"]
        f1 = m["f1_score"]

        report.append(
            f"| {table} | {exp} | {expected} | {detected} | {tp} | {fp} | {fn} | {precision:.3f} | {recall:.3f} | {f1:.3f} |",
        )

    report.append("")

    # Breakdown by Error Category
    report.append("## Performance by Error Category")
    report.append("")

    # Structural errors
    structural_metrics = [m for m in metrics if m["error_category"] == "structural"]
    if structural_metrics:
        struct_agg = compute_overall_aggregates(structural_metrics)
        report.append("### Structural Errors")
        report.append("")
        report.append("| Metric | Value |")
        report.append("|--------|-------|")
        report.append(f"| Expected | {struct_agg['total_expected']} |")
        report.append(f"| Detected | {struct_agg['total_detected']} |")
        report.append(f"| TP | {struct_agg['total_tp']} |")
        report.append(f"| FP | {struct_agg['total_fp']} |")
        report.append(f"| FN | {struct_agg['total_fn']} |")
        report.append(f"| Precision | {struct_agg['precision']:.3f} |")
        report.append(f"| Recall | {struct_agg['recall']:.3f} |")
        report.append(f"| F1 Score | {struct_agg['f1_score']:.3f} |")
        report.append("")

    # Logical errors
    logical_metrics = [m for m in metrics if m["error_category"] == "logical"]
    if logical_metrics:
        logic_agg = compute_overall_aggregates(logical_metrics)
        report.append("### Logical Errors")
        report.append("")
        report.append("| Metric | Value |")
        report.append("|--------|-------|")
        report.append(f"| Expected | {logic_agg['total_expected']} |")
        report.append(f"| Detected | {logic_agg['total_detected']} |")
        report.append(f"| TP | {logic_agg['total_tp']} |")
        report.append(f"| FP | {logic_agg['total_fp']} |")
        report.append(f"| FN | {logic_agg['total_fn']} |")
        report.append(f"| Precision | {logic_agg['precision']:.3f} |")
        report.append(f"| Recall | {logic_agg['recall']:.3f} |")
        report.append(f"| F1 Score | {logic_agg['f1_score']:.3f} |")
        report.append("")

    # Synthetic Tables Performance
    report.append("## Synthetic Tables Performance (Examples 49-59)")
    report.append("")
    synthetic_metrics = [
        m for m in overall_metrics if m["table_key"].startswith("synthetic_")
    ]

    if synthetic_metrics:
        report.append(
            "| Table | Errors | Expected | Detected | TP | FP | FN | Precision | Recall | F1 |",
        )
        report.append(
            "|-------|--------|----------|----------|----|----|-------|-----------|--------|-----|",
        )

        for m in synthetic_metrics:
            table = m["table_key"]
            # Extract error count from table name
            if "log_1_struct" in table:
                errors = "7L+1S"
            elif "log_2_struct" in table:
                errors = "7L+2S"
            elif "log_3_struct" in table:
                errors = "7L+3S"
            elif "log_4_struct" in table:
                errors = "7L+4S"
            elif "7_log_errors" in table:
                errors = "7L"
            elif "6_log_errors" in table:
                errors = "6L"
            elif "5_log_errors" in table:
                errors = "5L"
            elif "4_log_errors" in table:
                errors = "4L"
            elif "3_log_errors" in table:
                errors = "3L"
            elif "2_log_errors" in table:
                errors = "2L"
            elif "1_log_error" in table:
                errors = "1L"
            else:
                errors = "-"

            report.append(
                f"| {table} | {errors} | {m['expected']} | {m['detected']} | {m['TP']} | {m['FP']} | {m['FN']} | {m['precision']:.3f} | {m['recall']:.3f} | {m['f1_score']:.3f} |",
            )

        # Aggregate synthetic metrics
        synth_agg = compute_overall_aggregates(synthetic_metrics)
        report.append("")
        report.append("**Synthetic Tables Summary:**")
        report.append(f"- Total Tables: {synth_agg['total_experiments']}")
        report.append(f"- Overall Precision: {synth_agg['precision']:.3f}")
        report.append(f"- Overall Recall: {synth_agg['recall']:.3f}")
        report.append(f"- Overall F1 Score: {synth_agg['f1_score']:.3f}")
        report.append("")

    # Success Rate Analysis
    report.append("## Success Rate Analysis")
    report.append("")
    perfect_f1 = sum(1 for m in overall_metrics if m["f1_score"] == 1.0)
    failed_f1 = sum(1 for m in overall_metrics if m["f1_score"] == 0.0)
    total_runs = len(overall_metrics)

    report.append(
        f"- **Perfect Detection (F1=1.0):** {perfect_f1}/{total_runs} ({perfect_f1 / total_runs * 100:.1f}%)",
    )
    report.append(
        f"- **Complete Failure (F1=0.0):** {failed_f1}/{total_runs} ({failed_f1 / total_runs * 100:.1f}%)",
    )
    report.append(
        f"- **Partial Success (0<F1<1):** {total_runs - perfect_f1 - failed_f1}/{total_runs} ({(total_runs - perfect_f1 - failed_f1) / total_runs * 100:.1f}%)",
    )
    report.append("")

    return "\n".join(report)


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    eval_dir = os.path.dirname(script_dir)
    csv_path = os.path.join(eval_dir, "eval_data", "agent_performance_metrics.csv")
    output_path = os.path.join(eval_dir, "eval_data", "agent_performance_report.md")

    print("=" * 70)
    print("  GENERATING PERFORMANCE METRICS REPORT")
    print("=" * 70)
    print()

    if not os.path.exists(csv_path):
        print(f"❌ Metrics CSV not found: {csv_path}")
        print("   Run generate_metrics_csv.py first!")
        return

    # Load metrics
    metrics = load_metrics(csv_path)
    print(f"✅ Loaded {len(metrics)} metric rows from CSV")

    # Generate report
    report_content = generate_markdown_report(metrics, output_path)

    # Save report
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_content)

    print(f"✅ Report saved: {output_path}")
    print()

    # Also print to console
    print("=" * 70)
    print(report_content)
    print("=" * 70)


if __name__ == "__main__":
    main()
