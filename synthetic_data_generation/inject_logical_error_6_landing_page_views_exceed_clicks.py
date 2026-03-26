"""
Injects Rule 6 logical errors: landing_page_views_exceed_clicks into a CSV file.

Description:
    This script violates the logical requirement that Landing Page Views cannot exceed Clicks.
    It targets a specific percentage of rows and modifies the 'performance__landing_page_views' column.

Rule Details:
    Violation: [performance__landing_page_views] > [performance__clicks]

Null Handling Logic:
    - If 'performance__clicks' is NULL or 0:
        The injected 'performance__landing_page_views' is a fixed random value from [100, 1000].
        The NULL 'performance__clicks' value is PRESERVED as NULL.
    - If 'performance__clicks' is NOT NULL:
        The injected 'performance__landing_page_views' is round(clicks * factor), where factor is [2.0, 10.0].

Usage:
    python synthetic_data_generation/inject_logical_error_6_landing_page_views_exceed_clicks.py \\
        --input-file /path/to/data.csv \\
        --error-pcts 5 10 20 40
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

RULE_ID = 6
RULE_NAME = "landing_page_views_exceed_clicks"


def inject_rule(
    df: pd.DataFrame,
    chosen: np.ndarray,
    rng: np.random.Generator,
) -> list[dict]:
    errors = []
    for row_idx in chosen:
        clicks = df.at[row_idx, "performance__clicks"]
        original_lpv = df.at[row_idx, "performance__landing_page_views"]

        if pd.isna(clicks) or clicks == 0:
            new_lpv = int(rng.integers(100, 1000))
        else:
            factor = rng.uniform(2.0, 10.0)
            new_lpv = int(round(clicks * factor))

        errors.append(
            {
                "row_index": int(row_idx),
                "rule": RULE_NAME,
                "columns_affected": ["performance__landing_page_views"],
                "original_values": {
                    "performance__landing_page_views": float(original_lpv)
                    if not pd.isna(original_lpv)
                    else None,
                },
                "injected_values": {"performance__landing_page_views": new_lpv},
                "error_type": "logical_error",
            },
        )
        df.at[row_idx, "performance__landing_page_views"] = new_lpv
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
