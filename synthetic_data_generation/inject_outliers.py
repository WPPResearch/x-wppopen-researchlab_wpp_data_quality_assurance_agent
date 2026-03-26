"""
Injects Outlier errors into a CSV file.

Description:
    This script introduces statistical outliers into numerical columns.
    It uses mean and standard deviation to calculate values that are far outside
    the normal distribution (e.g., 10x-30x std).

Column Selection:
    It targets all columns with numeric data types (int, float). Prefix filtering
    (like performance__) has been removed to favor pure type-based detection.

Injection Logic:
    - Errors are injected into each detected numeric column individually.
    - For non-zero/non-null values: Uses the formula `mean ± (multiplier × std)`.
    - For zero or NULL values: Injects a large random value from an extreme interval ($10^6$ to $10^8$).

Usage:
    python synthetic_data_generation/inject_outliers.py \
        --input-file /path/to/data.csv \
        --error-pcts 5 10 20 40 \
        --multiplier 10.0
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def inject_errors(
    df: pd.DataFrame,
    error_pct: float,
    rng: np.random.Generator,
    multiplier: float = 10.0,
) -> tuple[pd.DataFrame, list[dict]]:
    # Target all numeric columns
    cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if not cols:
        print("    Warning: No numerical performance columns found.")
        return df, []

    df = df.copy()
    error_log = []

    n_rows = len(df)
    n_inject_per_col = (
        max(1, int(round(n_rows * error_pct / 100))) if error_pct > 0 else 0
    )

    for c in cols:
        # Calculate stats for this column
        mean = df[c].mean()
        std = df[c].std()

        if std == 0 or np.isnan(std):
            # Fallback for constant columns
            mean = mean if not np.isnan(mean) else 0.0
            std = 1.0

        # Pick random rows (including zeros and nulls)
        chosen_rows = rng.choice(
            df.index,
            size=min(n_inject_per_col, n_rows),
            replace=False,
        )

        # Upcast integer columns to float64 so outlier decimals are preserved
        if pd.api.types.is_integer_dtype(df[c]):
            df[c] = df[c].astype("float64")

        for r in chosen_rows:
            original = df.at[r, c]

            if pd.isna(original) or original == 0:
                # Large value from interval for zero/null values
                outlier_val = round(rng.uniform(1000000, 100000000), 6)
                direction = "extreme"
            else:
                # Statistical multiplier logic for non-zero values
                direction_val = rng.choice([-1, 1])
                cell_multiplier = rng.uniform(multiplier, multiplier * 3)
                outlier_val = round(mean + direction_val * cell_multiplier * std, 6)
                direction = "high" if direction_val == 1 else "low"

            df.at[r, c] = outlier_val
            error_log.append(
                {
                    "row_index": int(r),
                    "column": c,
                    "original_value": float(original)
                    if not pd.isna(original)
                    else None,
                    "injected_value": outlier_val,
                    "direction": direction,
                    "error_type": "outlier",
                    "multiplier": multiplier,
                },
            )

    return df, error_log

    return df, error_log


def main(
    input_file: str,
    error_pcts: list[float],
    seed: int,
    output_dir: str | None,
    multiplier: float = 10.0,
) -> None:
    src_file = Path(input_file)
    if not src_file.exists():
        raise FileNotFoundError(f"Input file not found: {src_file}")

    df_base = pd.read_csv(src_file)
    file_stem = src_file.stem

    if output_dir:
        out_dir = Path(output_dir)
    else:
        out_dir = src_file.parent / f"{file_stem}_outlier_errors_injected"
    out_dir.mkdir(exist_ok=True, parents=True)

    print(f"Input file : {src_file}")
    print(f"Output dir : {out_dir}")
    print(f"Error %s   : {error_pcts} (seed={seed})\n")

    for pct in error_pcts:
        rng = np.random.default_rng(seed)
        df_injected, error_log = inject_errors(
            df=df_base,
            error_pct=pct,
            rng=rng,
            multiplier=multiplier,
        )

        pct_label = f"out_{round(pct)}_pt"

        # Strip original long base name if present
        base_to_strip = "OI_training_data_sample_20260203_anonymized"
        prefix = "" if file_stem == base_to_strip else f"{file_stem}_"

        csv_name = f"{prefix}{pct_label}.csv"
        log_name = f"{prefix}{pct_label}.json"

        df_injected.to_csv(out_dir / csv_name, index=False)
        with open(out_dir / log_name, "w") as f:
            json.dump(error_log, f, indent=2)

        print(f"  {pct:>2}%: {len(error_log):>4} cells outliered  → {csv_name}")

    print(f"\n✅  Done! Injected CSVs + error logs saved to: {out_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Inject outlier errors into a CSV file",
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
    parser.add_argument(
        "--multiplier",
        type=float,
        default=10.0,
        help="Outlier multiplier (factor of std)",
    )
    args = parser.parse_args()

    main(
        input_file=args.input_file,
        error_pcts=args.error_pcts,
        seed=args.seed,
        output_dir=args.output_dir,
        multiplier=args.multiplier,
    )
