"""
Experiment 4 — Consistency Check.

Runs the exact same configuration N times to measure response variance.
Helps understand how reliable/reproducible the auditor's findings are.

Usage:
    uv run python eval/eval_framework/run_consistency.py              (3 runs, default)
    uv run python eval/eval_framework/run_consistency.py --runs 5     (custom number)
"""

import os
import sys
import asyncio
import argparse

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from eval.eval_framework.experiment_configs import TABLES  # noqa: E402
from eval.eval_framework.experiment_runner import (  # noqa: E402
    run_single_audit,
    evaluate_with_gemini_judge,
    save_experiment_results,
)

EXPERIMENT_NAME = "consistency"
TARGET_TABLE = "outlier_error_5pct"
PROMPT_LEVEL = "complex"
MEMORY_MODE = "no_memory"
DEFAULT_RUNS = 3


async def main():
    parser = argparse.ArgumentParser(
        description="Run consistency experiment (N identical runs)",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=DEFAULT_RUNS,
        help=f"Number of identical runs (default: {DEFAULT_RUNS})",
    )
    args = parser.parse_args()
    num_runs = args.runs

    print("=" * 60)
    print("  EXPERIMENT 4: Consistency Check")
    print(f"  Table:  {TABLES[TARGET_TABLE]['short_name']}")
    print(f"  Prompt: {PROMPT_LEVEL}")
    print(f"  Memory: {MEMORY_MODE}")
    print(f"  Runs:   {num_runs}")
    print("=" * 60)

    results = []

    for i in range(1, num_runs + 1):
        print(f"\n{'='*60}")
        print(f"  Run {i} of {num_runs}")
        print(f"{'='*60}")

        result = await run_single_audit(
            table_key=TARGET_TABLE,
            prompt_level=PROMPT_LEVEL,
            memory_mode=MEMORY_MODE,
        )
        result["run_number"] = i
        results.append(result)

        print(f"\n✓ Completed run {i}/{num_runs}")
        print(f"{'='*60}\n")

    # Evaluate — the judge will compare all runs and note variance
    scorecard = evaluate_with_gemini_judge(
        results,
        f"{EXPERIMENT_NAME}_{num_runs}_runs",
    )

    # Save
    save_experiment_results(EXPERIMENT_NAME, results, scorecard)

    if scorecard:
        print("\n" + "=" * 60)
        print(scorecard)


if __name__ == "__main__":
    asyncio.run(main())
