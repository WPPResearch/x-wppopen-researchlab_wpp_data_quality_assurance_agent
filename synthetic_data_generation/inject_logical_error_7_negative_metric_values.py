"""
Injects Rule 7 logical errors: negative_metric_values into a CSV file.

Description:
    This script violates the rule that performance metrics (Impressions, Clicks, Spend, Conversions)
    must always be non-negative. It targets a specific percentage of rows.

Rule Details:
    Violation: Target Metric < 0

Null Handling Logic:
    - If the target metric is NULL or 0:
        The injected value is a fixed random negative value from -[100, 1000].
    - If the target metric is NOT NULL:
        The injected value is -abs(original_value).
        If the value was 0, it is set to -100.0.

Usage:
    python synthetic_data_generation/inject_logical_error_7_negative_metric_values.py \\
        --input-file /path/to/data.csv \\
        --error-pcts 5 10 20 40
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

RULE_ID = 7
RULE_NAME = "negative_metric_values"


def inject_rule(
    df: pd.DataFrame,
    chosen: np.ndarray,
    rng: np.random.Generator,
) -> list[dict]:
    candidates = [
        "performance__impressions",
        "performance__clicks",
        "performance__spend_usd",
        "performance__conversions",
    ]
    errors = []
    for row_idx in chosen:
        # Pick one random metric column to make negative
        col = candidates[int(rng.integers(0, len(candidates)))]
        original = df.at[row_idx, col]

        if pd.isna(original) or original == 0:
            # Force a negative value if it was null/0
            new_val = -float(rng.integers(100, 1000))
        else:
            new_val = -abs(float(original))
            # Ensure it's not actually 0
            if new_val == 0:
                new_val = -100.0

        errors.append(
            {
                "row_index": int(row_idx),
                "rule": RULE_NAME,
                "columns_affected": [col],
                "original_values": {
                    col: float(original) if not pd.isna(original) else None,
                },
                "injected_values": {col: new_val},
                "error_type": "logical_error",
            },
        )
        df.at[row_idx, col] = new_val
    return errors


def main(
    input_file: str,
    error_pcts: list[float],
    seed: int,
    output_dir: str | None,
) -> None:
    def validate_path(path_str: str | None) -> Path | None:
        if path_str is None:
            return None
        p = Path(path_str).resolve()
        safe_bases = [
            Path.cwd().resolve(),
            Path.home().resolve(),
            Path("/tmp").resolve(),
        ]
        if not any(p.is_relative_to(base) for base in safe_bases):
            raise ValueError(f"Path traversal detected: {path_str}")
        return p

    src_file = validate_path(input_file)
    if not src_file.exists():
        raise FileNotFoundError(f"Input file not found: {src_file}")

    df_base = pd.read_csv(src_file)
    file_stem = src_file.stem

    if output_dir:
        out_dir = validate_path(output_dir)
    else:
        out_dir = validate_path(
            str(src_file.parent / f"{file_stem}_logical_error_{RULE_ID}_injected"),
        )
    out_dir.mkdir(exist_ok=True, parents=True)

    print(f"Input file : {src_file}")
    print(f"Output dir : {out_dir}")
    print(f"Rule        : {RULE_ID} — {RULE_NAME}")
    print(f"Error %s   : {error_pcts} (seed={seed})\n")

    for pct in error_pcts:
        rng = np.random.default_rng(seed)
        n_rows = len(df_base)
        n_inject = max(1, int(round(n_rows * pct / 100))) if pct > 0 else 0

        df_injected = df_base.copy()
        available = list(df_injected.index)
        chosen = rng.choice(
            available,
            size=min(n_inject, len(available)),
            replace=False,
        )
        error_log = inject_rule(df_injected, chosen, rng)

        pct_label = f"log_{RULE_ID}_{round(pct)}_pt"

        # Strip original long base name if present
        base_to_strip = "our_training_dataset_sample_anonymized"
        prefix = "" if file_stem == base_to_strip else f"{file_stem}_"

        csv_name = f"{prefix}{pct_label}.csv"
        log_name = f"{prefix}{pct_label}.json"

        df_injected.to_csv(validate_path(str(out_dir / csv_name)), index=False)
        with open(validate_path(str(out_dir / log_name)), "w") as f:
            json.dump(error_log, f, indent=2)

        print(f"  {pct:>2}%: {len(error_log):>4} errors injected  → {csv_name}")

    print(f"\n✅  Done! Injected CSVs + error logs saved to: {out_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=f"Inject logical error Rule {RULE_ID} ({RULE_NAME}) into a CSV file",
    )
    parser.add_argument(
        "--input-file",
        required=True,
        help="Path to the anonymized CSV file",
    )
    parser.add_argument(
        "--error-pcts",
        nargs="+",
        type=float,
        default=[5.0, 10.0, 20.0, 40.0],
        help="Error percentages to inject",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--output-dir", default=None, help="Output directory")
    args = parser.parse_args()

    main(
        input_file=args.input_file,
        error_pcts=args.error_pcts,
        seed=args.seed,
        output_dir=args.output_dir,
    )
