"""
Injects Rule 3 logical errors: spend_with_zero_impressions into a CSV file.

Description:
    This script violates the logical requirement that an ad cannot have Spend if it had 0 Impressions.
    It targets a specific percentage of rows, forcing Impressions to 0 and Spend to a positive value.

Rule Details:
    Violation: [performance__spend_usd] > 0 AND [performance__impressions] == 0

Null Handling Logic:
    - The injected 'performance__spend_usd' is a random value from [$1.0, $10000.0].
    - The 'performance__impressions' is FORCED to 0.

Usage:
    python synthetic_data_generation/inject_logical_error_3_spend_with_zero_impressions.py \\
        --input-file /path/to/data.csv \\
        --error-pcts 5 10 20 40
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

RULE_ID = 3
RULE_NAME = "spend_with_zero_impressions"


def inject_rule(
    df: pd.DataFrame,
    chosen: np.ndarray,
    rng: np.random.Generator,
) -> list[dict]:
    errors = []
    for row_idx in chosen:
        original_impressions = df.at[row_idx, "performance__impressions"]
        original_spend = df.at[row_idx, "performance__spend_usd"]

        new_spend = round(float(rng.uniform(1.0, 10000.0)), 2)

        errors.append(
            {
                "row_index": int(row_idx),
                "rule": RULE_NAME,
                "columns_affected": [
                    "performance__impressions",
                    "performance__spend_usd",
                ],
                "original_values": {
                    "performance__impressions": float(original_impressions)
                    if not pd.isna(original_impressions)
                    else None,
                    "performance__spend_usd": float(original_spend)
                    if not pd.isna(original_spend)
                    else None,
                },
                "injected_values": {
                    "performance__impressions": 0,
                    "performance__spend_usd": new_spend,
                },
                "error_type": "logical_error",
            },
        )
        # Force the violation: impressions=0, spend>0
        df.at[row_idx, "performance__impressions"] = 0
        df.at[row_idx, "performance__spend_usd"] = new_spend
    return errors


def main(
    input_file: str,
    error_pcts: list[float],
    seed: int,
    output_dir: str | None,
) -> None:
    src_file = Path(input_file)
    if not src_file.exists():
        raise FileNotFoundError(f"Input file not found: {src_file}")

    df_base = pd.read_csv(src_file)
    file_stem = src_file.stem

    if output_dir:
        out_dir = Path(output_dir)
    else:
        out_dir = src_file.parent / f"{file_stem}_logical_error_{RULE_ID}_injected"
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
        base_to_strip = "OI_training_data_sample_20260203_anonymized"
        prefix = "" if file_stem == base_to_strip else f"{file_stem}_"

        csv_name = f"{prefix}{pct_label}.csv"
        log_name = f"{prefix}{pct_label}.json"

        df_injected.to_csv(out_dir / csv_name, index=False)
        with open(out_dir / log_name, "w") as f:
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
