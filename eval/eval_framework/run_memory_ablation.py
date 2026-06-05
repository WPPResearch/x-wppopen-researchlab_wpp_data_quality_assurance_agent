"""
Experiment 2 — Memory Ablation.

Tests the impact of memory on audit quality using the complex prompt
against the combined-errors table. Two conditions:
  1. No memory (cold-start baseline)
  2. With memory (load memories)

Usage:
    uv run python eval/eval_framework/run_memory_ablation.py          (from project root)
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

EXPERIMENT_NAME = "memory_ablation"

# Always complex prompt — we're testing memory, not prompt level
TARGET_TABLE = "logical_error_6_5pct"
PROMPT_LEVEL = "complex"


async def main():
    print("=" * 60)
    print("  EXPERIMENT 2: Memory Ablation")
    print(f"  Table: {TABLES[TARGET_TABLE]['short_name']}")
    print(f"  Prompt: {PROMPT_LEVEL}")
    print("=" * 60)

    results = []

    for mode_key in MEMORY_MODES:
        print(f"\n{'=' * 60}")
        print(f"  Running with memory mode: {MEMORY_MODES[mode_key]['label']}")
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

    # Evaluate
    scorecard = evaluate_with_gemini_judge(results, EXPERIMENT_NAME)

    # Save
    save_experiment_results(EXPERIMENT_NAME, results, scorecard)

    if scorecard:
        print("\n" + "=" * 60)
        print(scorecard)


if __name__ == "__main__":
    asyncio.run(main())
