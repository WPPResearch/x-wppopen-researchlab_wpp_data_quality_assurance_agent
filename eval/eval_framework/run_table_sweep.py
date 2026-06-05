"""
Experiment 3 — Table Sweep.

Runs the auditor (complex prompt, no memory) across all 7 tables to test
detection against each individual error type, the combined table, the clean
baseline, and the synthetic datasets.

Usage:
    uv run python eval/eval_framework/run_table_sweep.py          (from project root)
"""

import os
import sys
import asyncio

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from eval.eval_framework.experiment_configs import TABLES  # noqa: E402
from eval.eval_framework.experiment_runner import (  # noqa: E402
    run_single_audit,
    evaluate_with_gemini_judge,
    save_experiment_results,
)

EXPERIMENT_NAME = "table_sweep"
PROMPT_LEVEL = "complex"
MEMORY_MODE = "no_memory"


async def main():
    print("=" * 60)
    print("  EXPERIMENT 3: Table Sweep")
    print(f"  Prompt: {PROMPT_LEVEL}")
    print(f"  Memory: {MEMORY_MODE}")
    print(f"  Tables: {len(TABLES)}")
    print("=" * 60)

    results = []

    for table_key in TABLES:
        table_info = TABLES[table_key]
        print(f"\n{'=' * 60}")
        print(f"  Table: {table_info['short_name']}")
        print(f"  Description: {table_info['description']}")
        print(f"{'=' * 60}")

        result = await run_single_audit(
            table_key=table_key,
            prompt_level=PROMPT_LEVEL,
            memory_mode=MEMORY_MODE,
        )
        results.append(result)

    # Evaluate all results together
    scorecard = evaluate_with_gemini_judge(results, EXPERIMENT_NAME)

    # Save
    save_experiment_results(EXPERIMENT_NAME, results, scorecard)

    if scorecard:
        print("\n" + "=" * 60)
        print(scorecard)


if __name__ == "__main__":
    asyncio.run(main())
