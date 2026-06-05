"""
Ground Truth Comparison Tool

Loads ground truth from CSV and compares against agent audit results.
Generates side-by-side comparison reports.
"""

import os
import csv
import json
import re


def resolve_table_name_to_key(table_name: str) -> str | None:
    """Map a full table name to a table key."""
    name_lower = table_name.lower()

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


def load_ground_truth_csv(csv_path: str) -> dict:
    """Load ground truth from CSV file, keyed by table_key."""
    ground_truth = {}

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Use Table_description_name as the full table name
            table_name = row["Table_description_name"]

            # Resolve to table key
            table_key = resolve_table_name_to_key(table_name)
            if not table_key:
                continue

            # Parse counts
            structural_count = int(row["number_of_injected_structural_errors"])
            logical_count = int(row["number_of_injected_logical_errors"])

            # Get error type descriptions
            structural_details = (
                row["type_of_structural_error"]
                if row["type_of_structural_error"] != "-"
                else "None"
            )
            logical_details = (
                row["type_of_logical_error"]
                if row["type_of_logical_error"] != "-"
                else "None"
            )

            ground_truth[table_key] = {
                "table_name": table_name,
                "structural_count": structural_count,
                "logical_count": logical_count,
                "total_count": structural_count + logical_count,
                "structural_details": structural_details,
                "logical_details": logical_details,
            }

    return ground_truth


def extract_detection_counts(
    scorecard_text: str,
    table_name: str,
    prompt_level: str = None,
    memory_mode: str = None,
) -> dict:
    """Extract detected error counts from scorecard text for a specific run configuration."""
    # Build pattern to match specific report based on prompt and memory (account for spaces around =)
    # Capture everything from after "----------------" separator until "\n---\n" (section separator)
    # Use -{10,} to match the long separator under "Report:" header

    # For experiments with prompt/memory in Report line (e.g., prompt_comparison, memory_ablation)
    if prompt_level and memory_mode:
        pattern = rf"Report:.*{re.escape(table_name)}.*prompt\s*=\s*{prompt_level}.*memory\s*=\s*{memory_mode}.*?[\r\n]+-{{10,}}[\r\n]+(.*?)[\r\n]+---[\r\n]+"
    elif prompt_level:
        pattern = rf"Report:.*{re.escape(table_name)}.*prompt\s*=\s*{prompt_level}.*?[\r\n]+-{{10,}}[\r\n]+(.*?)[\r\n]+---[\r\n]+"
    elif memory_mode:
        pattern = rf"Report:.*{re.escape(table_name)}.*memory\s*=\s*{memory_mode}.*?[\r\n]+-{{10,}}[\r\n]+(.*?)[\r\n]+---[\r\n]+"
    else:
        # For experiments without prompt/memory in Report line (e.g., table_sweep, consistency)
        # Match table name followed by dashes, then content until "---"
        pattern = rf"Report:\s*{re.escape(table_name)}\s*[\r\n]+-{{10,}}[\r\n]+(.*?)[\r\n]+---[\r\n]+"

    match = re.search(pattern, scorecard_text, re.DOTALL | re.MULTILINE)

    if not match:
        return {
            "structural_detected": 0,
            "logical_detected": 0,
            "total_detected": 0,
            "detected_items": [],
            "missed_items": [],
            "report_found": False,
        }

    report_section = match.group(1)

    # Extract structural errors count
    structural_match = re.search(
        r"Structural Errors:\s*(\d+)\s*/\s*(\d+)",
        report_section,
    )
    structural_detected = int(structural_match.group(1)) if structural_match else 0

    # Extract logical errors count
    logical_match = re.search(r"Logical Errors:\s*(\d+)\s*/\s*(\d+)", report_section)
    logical_detected = int(logical_match.group(1)) if logical_match else 0

    total_detected = structural_detected + logical_detected

    # Extract detected items
    detected_items = re.findall(r"\*\s+(.*?)\s*✅", report_section)
    missed_items = re.findall(r"\*\s+(.*?)\s*❌", report_section)

    return {
        "structural_detected": structural_detected,
        "logical_detected": logical_detected,
        "total_detected": total_detected,
        "detected_items": detected_items,
        "missed_items": missed_items,
        "report_found": True,
    }


def calculate_accuracy(detected: int, expected: int) -> float:
    """Calculate detection accuracy percentage."""
    if expected == 0:
        return 100.0 if detected == 0 else 0.0
    return (detected / expected) * 100.0


def generate_comparison_report(experiment_dir: str, ground_truth: dict) -> str:
    """Generate comparison report between ground truth and agent predictions."""

    scorecard_path = os.path.join(experiment_dir, "scorecard.txt")
    if not os.path.exists(scorecard_path):
        return f"❌ Scorecard not found: {scorecard_path}"

    with open(scorecard_path, "r", encoding="utf-8") as f:
        scorecard_text = f.read()

    metadata_path = os.path.join(experiment_dir, "metadata.json")
    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    experiment_name = metadata.get("experiment", "Unknown")
    timestamp = metadata.get("timestamp", "Unknown")

    # Check if scorecard has prompt= and memory= in Report lines
    has_prompt_memory_format = bool(
        re.search(r"Report:.*\|.*prompt\s*=.*memory\s*=", scorecard_text),
    )

    # Build comparison report
    report = []
    report.append("=" * 80)
    report.append("  GROUND TRUTH vs AGENT PREDICTIONS COMPARISON")
    report.append(f"  Experiment: {experiment_name}")
    report.append(f"  Timestamp: {timestamp}")
    report.append("=" * 80)
    report.append("")

    total_expected = 0
    total_detected = 0
    total_tables = 0

    for run in metadata.get("runs", []):
        table_key = run.get("table_key")
        table_name = run.get("table_name")
        prompt_level = run.get("prompt_level")
        memory_mode = run.get("memory_mode")

        if table_key not in ground_truth:
            continue

        gt = ground_truth[table_key]

        # Only use prompt/memory parameters if scorecard format includes them
        if has_prompt_memory_format:
            predictions = extract_detection_counts(
                scorecard_text,
                table_name,
                prompt_level,
                memory_mode,
            )
        else:
            predictions = extract_detection_counts(scorecard_text, table_name)

        if not predictions.get("report_found"):
            continue

        total_tables += 1
        total_expected += gt["total_count"]
        total_detected += predictions["total_detected"]

        # Calculate accuracies
        structural_acc = calculate_accuracy(
            predictions["structural_detected"],
            gt["structural_count"],
        )
        logical_acc = calculate_accuracy(
            predictions["logical_detected"],
            gt["logical_count"],
        )
        overall_acc = calculate_accuracy(
            predictions["total_detected"],
            gt["total_count"],
        )

        # Table header
        report.append("-" * 80)
        report.append(f"Table: {table_key}")
        if prompt_level:
            report.append(f"Prompt Level: {prompt_level}")
        if memory_mode:
            report.append(f"Memory Mode: {memory_mode}")
        report.append(f"Name: {table_name[:80]}...")
        report.append("-" * 80)
        report.append("")

        # Summary comparison
        report.append("SUMMARY:")
        report.append(
            f"  Expected:  {gt['structural_count']} structural + {gt['logical_count']} logical = {gt['total_count']} total",
        )
        report.append(
            f"  Detected:  {predictions['structural_detected']} structural + {predictions['logical_detected']} logical = {predictions['total_detected']} total",
        )
        report.append(
            f"  Accuracy:  {overall_acc:.1f}% ({predictions['total_detected']}/{gt['total_count']})",
        )
        report.append("")

        # Detailed breakdown
        report.append("STRUCTURAL ERRORS:")
        report.append(
            f"  Expected: {gt['structural_count']} - {gt['structural_details']}",
        )
        report.append(
            f"  Detected: {predictions['structural_detected']} ({structural_acc:.1f}% accuracy)",
        )
        report.append("")

        report.append("LOGICAL ERRORS:")
        report.append(f"  Expected: {gt['logical_count']} - {gt['logical_details']}")
        report.append(
            f"  Detected: {predictions['logical_detected']} ({logical_acc:.1f}% accuracy)",
        )
        report.append("")

        # What was found vs missed
        if predictions["detected_items"]:
            report.append(f"✅ DETECTED ({len(predictions['detected_items'])}):")
            for item in predictions["detected_items"][:10]:  # Limit to first 10
                report.append(f"   • {item}")
            if len(predictions["detected_items"]) > 10:
                report.append(
                    f"   ... and {len(predictions['detected_items']) - 10} more",
                )
            report.append("")

        if predictions["missed_items"]:
            report.append(f"❌ MISSED ({len(predictions['missed_items'])}):")
            for item in predictions["missed_items"][:10]:  # Limit to first 10
                report.append(f"   • {item}")
            if len(predictions["missed_items"]) > 10:
                report.append(
                    f"   ... and {len(predictions['missed_items']) - 10} more",
                )
            report.append("")

        report.append("")

    # Overall summary
    overall_accuracy = calculate_accuracy(total_detected, total_expected)

    report.append("=" * 80)
    report.append("OVERALL SUMMARY")
    report.append("=" * 80)
    report.append(f"Tables Evaluated: {total_tables}")
    report.append(f"Total Expected Errors: {total_expected}")
    report.append(f"Total Detected Errors: {total_detected}")
    report.append(
        f"Overall Accuracy: {overall_accuracy:.1f}% ({total_detected}/{total_expected})",
    )
    report.append("")

    return "\n".join(report)


def generate_csv_comparison(experiment_dir: str, ground_truth: dict) -> str:
    """Generate CSV format comparison."""
    scorecard_path = os.path.join(experiment_dir, "scorecard.txt")
    if not os.path.exists(scorecard_path):
        return ""

    with open(scorecard_path, "r", encoding="utf-8") as f:
        scorecard_text = f.read()

    metadata_path = os.path.join(experiment_dir, "metadata.json")
    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    # Check if scorecard has prompt= and memory= in Report lines
    has_prompt_memory_format = bool(
        re.search(r"Report:.*\|.*prompt\s*=.*memory\s*=", scorecard_text),
    )

    csv_lines = []
    csv_lines.append(
        "table_key,prompt_level,memory_mode,structural_expected,structural_detected,logical_expected,logical_detected,total_expected,total_detected,accuracy,detected_details,missed_details",
    )

    for run in metadata.get("runs", []):
        table_key = run.get("table_key")
        table_name = run.get("table_name")
        prompt_level = run.get("prompt_level", "N/A")
        memory_mode = run.get("memory_mode", "N/A")

        if table_key not in ground_truth:
            continue

        gt = ground_truth[table_key]

        # Only use prompt/memory parameters if scorecard format includes them
        if has_prompt_memory_format:
            predictions = extract_detection_counts(
                scorecard_text,
                table_name,
                prompt_level,
                memory_mode,
            )
        else:
            predictions = extract_detection_counts(scorecard_text, table_name)

        if not predictions.get("report_found"):
            continue

        accuracy = calculate_accuracy(predictions["total_detected"], gt["total_count"])

        detected_str = "; ".join(
            predictions["detected_items"][:5],
        )  # Limit to 5 for readability
        missed_str = "; ".join(predictions["missed_items"][:5])

        csv_lines.append(
            f"{table_key},{prompt_level},{memory_mode},"
            f"{gt['structural_count']},{predictions['structural_detected']},"
            f"{gt['logical_count']},{predictions['logical_detected']},"
            f"{gt['total_count']},{predictions['total_detected']},"
            f'{accuracy:.1f}%,"{detected_str}","{missed_str}"',
        )

    return "\n".join(csv_lines)


def main():
    """Main entry point."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    eval_dir = os.path.dirname(script_dir)  # Go up from eval_framework/ to eval/
    results_dir = os.path.join(eval_dir, "results")
    ground_truth_csv = os.path.join(
        eval_dir,
        "eval_data",
        "ground_truth_eval_table.csv",
    )

    print(f"Loading ground truth from: {ground_truth_csv}")
    ground_truth = load_ground_truth_csv(ground_truth_csv)
    print(f"✅ Loaded {len(ground_truth)} tables from ground truth\n")

    # Find all experiment directories
    experiments = {}
    for exp_type in os.listdir(results_dir):
        exp_path = os.path.join(results_dir, exp_type)
        if not os.path.isdir(exp_path):
            continue

        # Get latest run
        runs = sorted(
            [
                d
                for d in os.listdir(exp_path)
                if os.path.isdir(os.path.join(exp_path, d))
            ],
            reverse=True,
        )
        if runs:
            latest_run = os.path.join(exp_path, runs[0])
            experiments[exp_type] = latest_run

    print(f"Found {len(experiments)} experiments with results:\n")
    for exp_type, exp_dir in experiments.items():
        print(f"  • {exp_type}: {os.path.basename(exp_dir)}")
    print()

    # Generate comparison for each experiment
    for exp_type, exp_dir in experiments.items():
        print("=" * 80)
        print(f"Generating comparison for: {exp_type}")
        print("=" * 80)

        # Text format
        comparison = generate_comparison_report(exp_dir, ground_truth)
        output_path = os.path.join(exp_dir, "ground_truth_comparison.txt")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(comparison)
        print(f"✅ Saved text comparison to: {output_path}")

        # CSV format
        csv_comparison = generate_csv_comparison(exp_dir, ground_truth)
        if csv_comparison:
            csv_output_path = os.path.join(exp_dir, "ground_truth_comparison.csv")
            with open(csv_output_path, "w", encoding="utf-8") as f:
                f.write(csv_comparison)
            print(f"✅ Saved CSV comparison to: {csv_output_path}")

        print()


if __name__ == "__main__":
    main()
