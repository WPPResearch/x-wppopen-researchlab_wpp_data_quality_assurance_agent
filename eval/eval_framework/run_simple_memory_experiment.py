"""
Memory vs No-Memory Experiment with Simple Prompt on Complex Table.

This experiment tests whether memory helps the agent when using a SIMPLE prompt
on a COMPLEX table (7 logical + 4 structural errors = 11 total errors).

The goal is to isolate the impact of memory by:
- Using the simplest possible prompt: "Check if there are any errors for table X?"
- Using the most complex table available with maximum error diversity
- Comparing no_memory vs load_memory conditions

Table: synthetic_7_log_4_struct
  - 7 logical errors: clicks>impressions, conversions>clicks, spend with zero impressions,
    video completions>plays, purchases without add-to-cart, landing page views>clicks,
    negative metrics
  - 4 structural errors: nulls, outliers, duplicates, categorical errors
  - Total: 11 distinct error types at 5% error rate each

Usage:
    uv run python eval/eval_framework/run_simple_memory_experiment.py
"""

import os
import sys
import asyncio

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from eval.eval_framework.experiment_configs import MEMORY_MODES, TABLES  # noqa: E402
from eval.eval_framework.experiment_runner import (  # noqa: E402
    run_single_audit,
    evaluate_with_gemini_judge,
    save_experiment_results,
)

EXPERIMENT_NAME = "simple_memory_experiment"

# Use the most complex table: 7 logical + 4 structural errors
TARGET_TABLE = "synthetic_7_log_4_struct"

# Use the simplest prompt to test if memory alone helps
PROMPT_LEVEL = "simple"


async def main():
    print("=" * 60)
    print("  MEMORY vs NO-MEMORY EXPERIMENT")
    print("  Simple Prompt on Complex Table")
    print("=" * 60)
    print(f"  Table: {TABLES[TARGET_TABLE]['short_name']}")
    print(f"  Description: {TABLES[TARGET_TABLE]['description']}")
    print(f"  Prompt Level: {PROMPT_LEVEL} (minimalist)")
    print("=" * 60)
    print()
    print("Hypothesis:")
    print("  If memory helps, the agent should detect more errors with")
    print("  load_memory even when given minimal instructions.")
    print("=" * 60)

    results = []

    for mode_key in MEMORY_MODES:
        print(f"\n{'=' * 60}")
        print(f"  Running with: {MEMORY_MODES[mode_key]['label']}")
        print(f"  {MEMORY_MODES[mode_key]['description']}")
        print(f"{'=' * 60}")

        result = await run_single_audit(
            table_key=TARGET_TABLE,
            prompt_level=PROMPT_LEVEL,
            memory_mode=mode_key,
        )
        results.append(result)

        print(f"\n✓ Completed experiment with {MEMORY_MODES[mode_key]['label']}")
        print(f"{'=' * 60}\n")

    # Evaluate with Gemini judge
    print("\n" + "=" * 60)
    print("  EVALUATING RESULTS WITH GEMINI JUDGE")
    print("=" * 60)
    scorecard = evaluate_with_gemini_judge(results, EXPERIMENT_NAME)

    # Save results
    save_experiment_results(EXPERIMENT_NAME, results, scorecard)

    # Display scorecard
    if scorecard:
        print("\n" + "=" * 60)
        print("  FINAL SCORECARD")
        print("=" * 60)
        print(scorecard)
        print("=" * 60)
    else:
        print("\n⚠️  No scorecard generated.")

    print("\n✅ Experiment complete!")


if __name__ == "__main__":
    asyncio.run(main())
