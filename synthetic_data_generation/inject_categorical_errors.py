"""
Injects Categorical errors into a CSV file.

Description:
    This script introduces corruption into categorical columns by replacing valid values
    with random erroneous strings.

Column Selection:
    It targets all columns with 'object' (string) data types. Prefix filtering (like dim__)
    has been removed to favor pure type-based detection.

Injection Logic:
    - Errors are injected into each detected categorical column individually.
    - For each column, a specific number of cells (based on error_pct) are randomly selected.
    - The original value (whether it's a string, zero, or NULL) is replaced with a corrupt string.

Usage:
    python synthetic_data_generation/inject_categorical_errors.py \
        --input-file /path/to/data.csv \
        --error-pcts 5 10 20 40
"""

import argparse
import json
import random
import string
from pathlib import Path

import numpy as np
import pandas as pd


def generate_corrupt_string(length=12):
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


def inject_errors(
    df: pd.DataFrame,
    error_pct: float,
    rng: np.random.Generator,
) -> tuple[pd.DataFrame, list[dict]]:
    # Target all object/string columns
    cols = df.select_dtypes(include=["object"]).columns.tolist()
    if not cols:
        print("    Warning: No categorical (non-numeric) columns found.")
        return df, []

    df = df.copy()
    error_log = []

    n_rows = len(df)
    n_inject_per_col = (
        max(1, int(round(n_rows * error_pct / 100))) if error_pct > 0 else 0
    )

    for c in cols:
        # Pick random rows for this column
        chosen_rows = rng.choice(
            df.index,
            size=min(n_inject_per_col, n_rows),
            replace=False,
        )

        for r in chosen_rows:
            original = df.at[r, c]
            corrupt_val = generate_corrupt_string()

            df.at[r, c] = corrupt_val
            error_log.append(
                {
                    "row_index": int(r),
                    "column": c,
                    "original_value": str(original) if not pd.isna(original) else None,
                    "injected_value": corrupt_val,
                    "error_type": "categorical_error",
                },
            )

    return df, error_log


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
        out_dir = src_file.parent / f"{file_stem}_categorical_errors_injected"
    out_dir.mkdir(exist_ok=True, parents=True)

    print(f"Input file : {src_file}")
    print(f"Output dir : {out_dir}")
    print(f"Error %s   : {error_pcts} (seed={seed})\n")

    for pct in error_pcts:
        rng = np.random.default_rng(seed)
        df_injected, error_log = inject_errors(df=df_base, error_pct=pct, rng=rng)

        pct_label = f"cat_{round(pct)}_pt"

        # Strip original long base name if present
        base_to_strip = "OI_training_data_sample_20260203_anonymized"
        prefix = "" if file_stem == base_to_strip else f"{file_stem}_"

        csv_name = f"{prefix}{pct_label}.csv"
        log_name = f"{prefix}{pct_label}.json"

        df_injected.to_csv(out_dir / csv_name, index=False)
        with open(out_dir / log_name, "w") as f:
            json.dump(error_log, f, indent=2)

        print(f"  {pct:>2}%: {len(error_log):>4} cells corrupted  → {csv_name}")

    print(f"\n✅  Done! Injected CSVs + error logs saved to: {out_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Inject categorical errors into a CSV file",
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
