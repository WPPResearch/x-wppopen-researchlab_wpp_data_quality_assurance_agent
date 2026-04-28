"""
Unified experiment runner for auditor agent evaluation.

Replaces all individual experiment scripts with a single parameterized runner.

Usage Examples:
    # Run a single table
    uv run python eval/eval_framework/run_experiment.py --table synthetic_1_log_error

    # Run a predefined experiment
    uv run python eval/eval_framework/run_experiment.py --experiment error_rate_sweep
    uv run python eval/eval_framework/run_experiment.py --experiment synthetic_sweep

    # Run specific tables by pattern
    uv run python eval/eval_framework/run_experiment.py --pattern "error_rate_*"
    uv run python eval/eval_framework/run_experiment.py --pattern "synthetic_7_*"

    # Run tables from a list
    uv run python eval/eval_framework/run_experiment.py --tables synthetic_1_log_error synthetic_2_log_errors

    # Customize prompt and memory mode
    uv run python eval/eval_framework/run_experiment.py --table synthetic_1_log_error --prompt simple --memory load_memory

    # Test memory conditions on a specific table
    uv run python eval/eval_framework/run_experiment.py --table synthetic_7_log_4_struct --memory-sweep
"""

import os
import sys
import asyncio
import argparse
import fnmatch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from eval.eval_framework.experiment_configs import TABLES, MEMORY_MODES, PROMPT_LEVELS  # noqa: E402
from eval.eval_framework.experiment_runner import (  # noqa: E402
    run_single_audit,
    evaluate_with_gemini_judge,
    save_experiment_results,
)


# ── Predefined Experiments ───────────────────────────────────────────────
EXPERIMENTS = {
    "error_rate_sweep": {
        "description": "Test error detection across different error rates (5%, 10%, 20%, 40%)",
        "tables": [
            "error_rate_5pct",
            "error_rate_10pct",
            "error_rate_20pct",
            "error_rate_40pct",
        ],
        "prompt_level": "complex",
        "memory_mode": "no_memory",
    },
    "synthetic_sweep": {
        "description": "Test all synthetic tables with multiple errors",
        "tables": [key for key in TABLES.keys() if key.startswith("synthetic_")],
        "prompt_level": "complex",
        "memory_mode": "no_memory",
    },
    "synthetic_batch1": {
        "description": "Synthetic tables with 1-4 logical errors",
        "tables": [
            "synthetic_1_log_error",
            "synthetic_2_log_errors",
            "synthetic_3_log_errors",
            "synthetic_4_log_errors",
        ],
        "prompt_level": "complex",
        "memory_mode": "no_memory",
    },
    "synthetic_batch2": {
        "description": "Synthetic tables with 5-7 logical errors",
        "tables": [
            "synthetic_5_log_errors",
            "synthetic_6_log_errors",
            "synthetic_7_log_errors",
        ],
        "prompt_level": "complex",
        "memory_mode": "no_memory",
    },
    "synthetic_batch3": {
        "description": "Synthetic tables with 7 logical + structural errors",
        "tables": [
            "synthetic_7_log_1_struct",
            "synthetic_7_log_2_struct",
            "synthetic_7_log_3_struct",
            "synthetic_7_log_4_struct",
        ],
        "prompt_level": "complex",
        "memory_mode": "no_memory",
    },
    "memory_comparison": {
        "description": "Compare memory vs no-memory on complex table",
        "tables": ["synthetic_7_log_4_struct"],
        "prompt_level": "complex",
        "memory_modes": ["no_memory", "load_memory"],  # Special: test multiple modes
    },
}


def get_tables_by_pattern(pattern: str) -> list[str]:
    """Get table keys matching a glob pattern."""
    return [key for key in TABLES.keys() if fnmatch.fnmatch(key, pattern)]


def print_experiment_info(
    experiment_name: str,
    tables: list[str],
    prompt_level: str,
    memory_mode: str,
):
    """Print experiment configuration."""
    print("=" * 60)
    print(f"  EXPERIMENT: {experiment_name}")
    print("=" * 60)
    print(f"  Prompt Level: {PROMPT_LEVELS[prompt_level]['label']}")
    print(f"  Memory Mode: {MEMORY_MODES[memory_mode]['label']}")
    print(f"  Tables: {len(tables)}")
    for i, table_key in enumerate(tables, 1):
        table_info = TABLES[table_key]
        gt = table_info["ground_truth"]
        n_logical = len(gt["logical_errors"])
        n_structural = len(gt["structural_errors"])
        print(
            f"    {i}. {table_info['short_name']} ({n_logical}L + {n_structural}S errors)",
        )
    print("=" * 60)


def print_table_detail(table_key: str, index: int, total: int):
    """Print detailed info for a single table run."""
    table_info = TABLES[table_key]
    gt = table_info["ground_truth"]
    n_logical = len(gt["logical_errors"])
    n_structural = len(gt["structural_errors"])

    print(f"\n{'='*60}")
    print(f"  [{index}/{total}] Table: {table_info['short_name']}")
    print(f"  Description: {table_info['description']}")
    print(f"  Ground Truth: {n_logical} logical, {n_structural} structural errors")

    if gt["logical_errors"]:
        preview = ", ".join(gt["logical_errors"][:3])
        if n_logical > 3:
            preview += "..."
        print(f"    Logical: {preview}")
    if gt["structural_errors"]:
        print(f"    Structural: {', '.join(gt['structural_errors'])}")

    print(f"{'='*60}")


async def run_experiment(
    experiment_name: str,
    tables: list[str],
    prompt_level: str = "complex",
    memory_mode: str = "no_memory",
    memory_modes: list[str] = None,
):
    """
    Run an experiment on one or more tables.

    Args:
        experiment_name: Name for saving results
        tables: List of table keys to audit
        prompt_level: Prompt level to use (simple, medium, complex)
        memory_mode: Memory mode to use (no_memory, load_memory)
        memory_modes: If provided, run with multiple memory modes (overrides memory_mode)
    """
    # Handle memory sweep
    if memory_modes:
        print(f"\n🔄 Running memory sweep with modes: {memory_modes}")
        results = []

        for mode in memory_modes:
            print(f"\n{'='*60}")
            print(f"  MEMORY MODE: {MEMORY_MODES[mode]['label']}")
            print(f"  {MEMORY_MODES[mode]['description']}")
            print(f"{'='*60}")

            for i, table_key in enumerate(tables, 1):
                print_table_detail(table_key, i, len(tables))

                result = await run_single_audit(
                    table_key=table_key,
                    prompt_level=prompt_level,
                    memory_mode=mode,
                )
                results.append(result)

                print(f"\n✅ Completed {i}/{len(tables)}")

            print(f"\n✓ Completed all tables with {MEMORY_MODES[mode]['label']}")
    else:
        # Standard run with single memory mode
        print_experiment_info(experiment_name, tables, prompt_level, memory_mode)

        results = []
        for i, table_key in enumerate(tables, 1):
            print_table_detail(table_key, i, len(tables))

            result = await run_single_audit(
                table_key=table_key,
                prompt_level=prompt_level,
                memory_mode=memory_mode,
            )
            results.append(result)

            print(f"\n✅ Completed {i}/{len(tables)}")

    # Evaluate all results together
    print("\n" + "=" * 60)
    print("  Evaluating results with Gemini Judge...")
    print("=" * 60)
    scorecard = evaluate_with_gemini_judge(results, experiment_name)

    # Save
    save_experiment_results(experiment_name, results, scorecard)

    print("\n" + "=" * 60)
    print("  EXPERIMENT COMPLETE")
    print("=" * 60)
    print(f"  Tables processed: {len(results)}")
    print(f"  Results saved to: eval/results/{experiment_name}/")

    if scorecard:
        print("\n" + "=" * 60)
        print("  SCORECARD")
        print("=" * 60)
        print(scorecard)


def main():
    parser = argparse.ArgumentParser(
        description="Unified experiment runner for auditor agent evaluation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run a single table
  %(prog)s --table synthetic_1_log_error

  # Run a predefined experiment
  %(prog)s --experiment error_rate_sweep

  # Run tables matching a pattern
  %(prog)s --pattern "synthetic_7_*"

  # Run specific tables
  %(prog)s --tables synthetic_1_log_error synthetic_2_log_errors

  # Test memory conditions
  %(prog)s --table synthetic_7_log_4_struct --memory-sweep

  # List available experiments and tables
  %(prog)s --list-experiments
  %(prog)s --list-tables
        """,
    )

    # Mutually exclusive group for what to run
    what_group = parser.add_mutually_exclusive_group(required=False)
    what_group.add_argument(
        "--experiment",
        "-e",
        choices=list(EXPERIMENTS.keys()),
        help="Run a predefined experiment",
    )
    what_group.add_argument(
        "--table",
        "-t",
        choices=list(TABLES.keys()),
        help="Run a single table",
    )
    what_group.add_argument(
        "--tables",
        "-ts",
        nargs="+",
        choices=list(TABLES.keys()),
        help="Run specific tables (space-separated)",
    )
    what_group.add_argument(
        "--pattern",
        "-p",
        help="Run tables matching glob pattern (e.g., 'error_rate_*')",
    )

    # Configuration options
    parser.add_argument(
        "--prompt",
        choices=["simple", "medium", "complex"],
        default="complex",
        help="Prompt level to use (default: complex)",
    )
    parser.add_argument(
        "--memory",
        choices=["no_memory", "load_memory"],
        default="no_memory",
        help="Memory mode to use (default: no_memory)",
    )
    parser.add_argument(
        "--memory-sweep",
        action="store_true",
        help="Test both memory modes (no_memory and load_memory)",
    )
    parser.add_argument(
        "--name",
        "-n",
        help="Custom experiment name for saving results",
    )

    # Listing options
    parser.add_argument(
        "--list-experiments",
        action="store_true",
        help="List all available experiments",
    )
    parser.add_argument(
        "--list-tables",
        action="store_true",
        help="List all available tables",
    )

    args = parser.parse_args()

    # Handle listing options
    if args.list_experiments:
        print("\nAvailable Experiments:")
        print("=" * 60)
        for exp_name, exp_config in EXPERIMENTS.items():
            print(f"\n{exp_name}:")
            print(f"  {exp_config['description']}")
            print(f"  Tables: {len(exp_config['tables'])}")
        print("\n" + "=" * 60)
        return

    if args.list_tables:
        print("\nAvailable Tables:")
        print("=" * 60)
        for key, table_info in TABLES.items():
            gt = table_info["ground_truth"]
            n_logical = len(gt["logical_errors"])
            n_structural = len(gt["structural_errors"])
            print(
                f"  {key:<30} {table_info['description']:<50} ({n_logical}L + {n_structural}S)",
            )
        print("=" * 60)
        return

    # Determine what to run
    tables = []
    experiment_name = args.name

    if args.experiment:
        exp_config = EXPERIMENTS[args.experiment]
        tables = exp_config["tables"]
        experiment_name = experiment_name or args.experiment
        prompt_level = exp_config.get("prompt_level", args.prompt)
        memory_mode = exp_config.get("memory_mode", args.memory)

        # Special case: experiment defines multiple memory modes
        memory_modes = exp_config.get("memory_modes", None)
        if memory_modes:
            args.memory_sweep = True
    elif args.table:
        tables = [args.table]
        experiment_name = experiment_name or f"single_{args.table}"
        prompt_level = args.prompt
        memory_mode = args.memory
        memory_modes = None
    elif args.tables:
        tables = args.tables
        experiment_name = experiment_name or f"custom_{len(tables)}_tables"
        prompt_level = args.prompt
        memory_mode = args.memory
        memory_modes = None
    elif args.pattern:
        tables = get_tables_by_pattern(args.pattern)
        if not tables:
            print(f"❌ No tables match pattern: {args.pattern}")
            return
        experiment_name = experiment_name or f"pattern_{args.pattern.replace('*', 'x')}"
        prompt_level = args.prompt
        memory_mode = args.memory
        memory_modes = None
    else:
        parser.print_help()
        return

    # Handle memory sweep
    if args.memory_sweep:
        memory_modes = ["no_memory", "load_memory"]
    elif "memory_modes" not in locals():
        memory_modes = None

    # Run the experiment
    asyncio.run(
        run_experiment(
            experiment_name=experiment_name,
            tables=tables,
            prompt_level=prompt_level,
            memory_mode=memory_mode,
            memory_modes=memory_modes,
        ),
    )


if __name__ == "__main__":
    main()
