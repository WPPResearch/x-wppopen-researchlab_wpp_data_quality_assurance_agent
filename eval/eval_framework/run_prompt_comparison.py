"""
Experiment 1 — Prompt Level Comparison.

Runs the auditor against the combined-errors table using all 3 prompt levels
(simple, medium, complex) to measure how prompt sophistication impacts
error detection.

Usage:
    uv run python eval/eval_framework/run_prompt_comparison.py          (from project root)
"""

import os
import sys
import asyncio

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from eval.eval_framework.experiment_configs import PROMPT_LEVELS, TABLES  # noqa: E402
from eval.eval_framework.experiment_runner import (  # noqa: E402
    run_single_audit,
    evaluate_with_gemini_judge,
    save_experiment_results,
)

EXPERIMENT_NAME = "prompt_comparison"

# The table with logical error 3 (5% spend with zero impressions)
TARGET_TABLE = "logical_error_3_5pct"
MEMORY_MODE = "no_memory"

# ── Prompt-level switcher ───────────────────────────────────────────────
# The auditor agent's prompt is set by return_instructions_auditor().
# To switch prompt levels we dynamically patch the function.

_PROMPT_TEXTS = {}


def _load_prompt_texts():
    """Extract the three prompt levels from prompts.py source."""
    import data_science.sub_agents.auditor.prompts as prompts_module

    src_path = prompts_module.__file__
    with open(src_path, "r", encoding="utf-8") as f:
        source = f.read()  # noqa: F841

    # Simple prompt
    _PROMPT_TEXTS["simple"] = """
    <CONTEXT>
        <TASK>
            You are a Data Quality Auditor. Your role is to find errors and anomalies in BigQuery tables.

            **Workflow:**
            1.  **Explore**: Look at the table schema and data.
            2.  **Verify**: Use the `call_bigquery_agent` tool to run SQL queries and check for broken data (e.g., nulls, duplicates, impossible values).
            3.  **Report**: Tell the user what you found. Provide the SQL logic used ONLY if explicitly requested.

            **Tool Usage:**
            *   `call_bigquery_agent`: Pass natural language to this tool to run queries.
        </TASK>
    </CONTEXT>
    """

    # Medium prompt
    _PROMPT_TEXTS["medium"] = """
    <CONTEXT>
        <TASK>
            You are an experienced Data Quality Engineer. Your role is to perform a structured assessment of BigQuery tables to ensure data integrity.

            **Workflow:**
            1.  **Explore**: Analyze the table schema to understand the data types and expected contents.
            2.  **Hypothesize**: Formulate questions based on standard data quality pillars:
                *   *Physical Integrity*: Are there unexpected NULLs or duplicate records?
                *   *Numerical Sanity*: Are numeric fields within logical bounds (e.g., no negative revenue)?
            3.  **Verify**: Use the `call_bigquery_agent` tool to test your hypotheses. Request specific SQL checks.
            4.  **Report**: Summarize your findings by data quality pillar. Provide the SQL logic used ONLY if explicitly requested.

            **Tool Usage:**
            *   `call_bigquery_agent`: Your primary interface for BigQuery. Use it to run investigative queries.

            **IMPORTANT:**
            *   **Transparency**: Explain your reasoning for flagging any data.
            *   **Precision**: Quantify your findings (e.g., "5% of rows have NULLs").
        </TASK>
    </CONTEXT>
    """

    # Complex prompt — read from the live source (it's the active one)
    from data_science.sub_agents.auditor.prompts import return_instructions_auditor

    _PROMPT_TEXTS["complex"] = return_instructions_auditor()


def _patch_prompt_level(level: str):
    """Monkey-patch the auditor agent's instruction to use a specific prompt level."""
    if not _PROMPT_TEXTS:
        _load_prompt_texts()

    import data_science.sub_agents.auditor.agent as agent_module

    agent_module.auditor_agent.instruction = _PROMPT_TEXTS[level]


async def main():
    print("=" * 60)
    print("  EXPERIMENT 1: Prompt Level Comparison")
    print(f"  Table: {TABLES[TARGET_TABLE]['short_name']}")
    print(f"  Memory: {MEMORY_MODE}")
    print("=" * 60)

    results = []

    for level in PROMPT_LEVELS:
        print(f"\n{'='*60}")
        print(f"  Running with prompt level: {PROMPT_LEVELS[level]['label']}")
        print(f"{'='*60}")

        _patch_prompt_level(level)

        result = await run_single_audit(
            table_key=TARGET_TABLE,
            prompt_level=level,
            memory_mode=MEMORY_MODE,
        )
        results.append(result)

        print(f"\n✓ Completed experiment with {PROMPT_LEVELS[level]['label']}")
        print(f"{'='*60}\n")

    # Reset to complex
    _patch_prompt_level("complex")

    # Evaluate
    scorecard = evaluate_with_gemini_judge(results, EXPERIMENT_NAME)

    # Save
    save_experiment_results(EXPERIMENT_NAME, results, scorecard)

    if scorecard:
        print("\n" + "=" * 60)
        print(scorecard)


if __name__ == "__main__":
    asyncio.run(main())
