"""
Unified Report Generator for Auditor Experiments.

Scans eval/results/ for completed experiments and produces a consolidated
summary report combining all scorecards.

Usage:
    uv run python eval/generate_report.py          (from project root)
"""

import os
import json
from datetime import datetime


EVAL_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(EVAL_DIR, "results")


EXPERIMENT_DESCRIPTIONS = {
    "prompt_comparison": "Prompt Level Comparison (Simple vs Medium vs Complex)",
    "memory_ablation": "Memory Ablation (No Memory vs Load vs Load+Save)",
    "table_sweep": "Table Sweep (All 7 tables with Complex prompt)",
    "consistency": "Consistency Check (Multiple identical runs)",
}


def find_latest_run(experiment_name: str) -> str | None:
    """Find the most recent results directory for an experiment."""
    exp_dir = os.path.join(RESULTS_DIR, experiment_name)
    if not os.path.isdir(exp_dir):
        return None

    runs = sorted(os.listdir(exp_dir), reverse=True)
    for run in runs:
        run_dir = os.path.join(exp_dir, run)
        if os.path.isdir(run_dir) and os.path.exists(
            os.path.join(run_dir, "scorecard.txt"),
        ):
            return run_dir
    return None


def load_scorecard(run_dir: str) -> str:
    """Load the scorecard text from a run directory."""
    scorecard_path = os.path.join(run_dir, "scorecard.txt")
    with open(scorecard_path, "r", encoding="utf-8") as f:
        return f.read().strip()


def load_metadata(run_dir: str) -> dict:
    """Load metadata from a run directory."""
    meta_path = os.path.join(run_dir, "metadata.json")
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def generate_summary_report() -> str:
    """Generate a consolidated summary report from all available experiments."""
    lines = []
    lines.append("=" * 70)
    lines.append("  AUDITOR AGENT — CONSOLIDATED EXPERIMENT REPORT")
    lines.append(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 70)
    lines.append("")

    found_any = False

    for exp_name, description in EXPERIMENT_DESCRIPTIONS.items():
        run_dir = find_latest_run(exp_name)
        if not run_dir:
            lines.append(f"  [{exp_name}] — No results found.")
            lines.append("")
            continue

        found_any = True
        metadata = load_metadata(run_dir)
        scorecard = load_scorecard(run_dir)
        timestamp = metadata.get("timestamp", os.path.basename(run_dir))

        lines.append("─" * 70)
        lines.append(f"  EXPERIMENT: {description}")
        lines.append(f"  Run timestamp: {timestamp}")
        lines.append(f"  Results dir: {run_dir}")

        # Count runs
        n_runs = len(metadata.get("runs", []))
        if n_runs:
            lines.append(f"  Number of audit runs: {n_runs}")

        lines.append("─" * 70)
        lines.append("")
        lines.append(scorecard)
        lines.append("")
        lines.append("")

    if not found_any:
        lines.append("  No experiment results found in eval/results/.")
        lines.append("  Run experiments first:")
        lines.append("    uv run python eval/run_prompt_comparison.py")
        lines.append("    uv run python eval/run_memory_ablation.py")
        lines.append("    uv run python eval/run_table_sweep.py")
        lines.append("    uv run python eval/run_consistency.py")

    report = "\n".join(lines)
    return report


def main():
    print("Scanning eval/results/ for experiment data...\n")

    report = generate_summary_report()

    # Save report
    os.makedirs(RESULTS_DIR, exist_ok=True)
    report_path = os.path.join(RESULTS_DIR, "summary_report.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
        f.write("\n")

    print(report)
    print(f"\n💾 Report saved to: {report_path}")


if __name__ == "__main__":
    main()
