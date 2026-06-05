"""
Injects Missing Values into a CSV file.

Description:
    This script introduces NULLs (missing values) into a dataset to simulate data loss.
    It targets non-null cells and applies the error percentage to each column individually.

Targeting Logic:
    - It iterates through every column in the dataset.
    - For each column, it calculates how many cells should be nulled (N = total_rows * error_pct).
    - It prioritizes cells that currently contain valid data to ensure the target is reached.
    - If a column is already mostly NULL, it nulls all remaining valid cells in that column.

Usage:
    python synthetic_data_generation/inject_missing_values.py \
        --input-file /path/to/data.csv \
        --error-pcts 5 10 20 40
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def inject_missing_values(
    df: pd.DataFrame,
    error_pct: float,
    rng: np.random.Generator,
) -> tuple[pd.DataFrame, list[dict]]:
    """
    Inject missing values by targeting non-null cells, per column.
    """
    df = df.copy()
    error_log = []
    n_rows = len(df)
    n_to_null_per_col = (
        max(1, int(round(n_rows * error_pct / 100))) if error_pct > 0 else 0
    )

    for c in df.columns:
        # Find available non-null cells in this specific column
        valid_indices = df[df[c].notna()].index.tolist()

        if not valid_indices:
            continue

        # Determine how many to null in THIS column
        n_col = min(n_to_null_per_col, len(valid_indices))

        if n_col == 0:
            continue

        chosen_indices = rng.choice(valid_indices, size=n_col, replace=False)

        for r in chosen_indices:
            original_val = df.at[r, c]
            df.at[r, c] = np.nan
            error_log.append(
                {
                    "row_index": int(r),
                    "column": c,
                    "original_value": str(original_val),
                    "injected_value": None,
                    "error_type": "missing_value",
                },
            )

    return df, error_log


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
            str(src_file.parent / f"{file_stem}_missing_values_injected"),
        )
    out_dir.mkdir(exist_ok=True, parents=True)

    print(f"Input file : {src_file}")
    print(f"Output dir : {out_dir}")
    print(f"Error %s   : {error_pcts} (seed={seed})\n")

    for pct in error_pcts:
        rng = np.random.default_rng(seed)
        df_injected, error_log = inject_missing_values(
            df=df_base,
            error_pct=pct,
            rng=rng,
        )

        pct_label = f"miss_{round(pct)}_pt"

        # Strip original long base name if present
        base_to_strip = "our_training_dataset_sample_anonymized"
        prefix = "" if file_stem == base_to_strip else f"{file_stem}_"

        csv_name = f"{prefix}{pct_label}.csv"
        log_name = f"{prefix}{pct_label}.json"

        df_injected.to_csv(validate_path(str(out_dir / csv_name)), index=False)
        with open(validate_path(str(out_dir / log_name)), "w") as f:
            json.dump(error_log, f, indent=2)

        print(
            f"  {pct:>2}%: {len(error_log):>4} cells nulled  ({(len(error_log)/df_base.size)*100:.2f}% of targeted cells)  → {csv_name}",
        )

    print(f"\n✅  Done! Injected CSVs + error logs saved to: {out_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Inject missing values into a CSV file",
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
