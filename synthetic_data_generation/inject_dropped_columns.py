"""
Randomly drops columns from a CSV file at multiple specified percentages.

- For each provided percentage, it generates a new CSV and a sidecar JSON log.
- A sidecar JSON log is saved per file recording exactly which columns were removed.
- Validated to ensure at least one column remains (never drops everything).
- A fixed random seed makes everything reproducible.

Usage:
    python synthetic_data_generation/inject_dropped_columns.py \
        --input-file data_science/utils/data/your_file.csv \
        --error-pcts 5 10 20 40

Options:
    --input-file    Path to the anonymized CSV file (required)
    --error-pcts    List of error percentages to inject (default: 5 10 20 40)
    --columns       Pool of columns to consider for dropping (default: all)
    --seed          Random seed for reproducibility (default: 42)
    --output-dir    Output directory (default: same folder as input)
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def inject_errors(
    df: pd.DataFrame,
    error_pct: float,
    pool: list[str],
    rng: np.random.Generator,
) -> tuple[pd.DataFrame, list[dict]]:
    """
    Randomly drops columns from `df` and returns (modified df, error log).
    """
    n_cols = len(pool)
    n_inject = max(1, int(round(n_cols * error_pct / 100))) if error_pct > 0 else 0

    error_log = []
    df = df.copy()

    if n_inject > 0:
        # Pick random columns to drop from the pool
        # Ensure we don't drop ALL columns if the pool is the entire df
        max_to_drop = min(
            n_inject,
            len(pool) - 1 if len(pool) == len(df.columns) else len(pool),
        )

        chosen = rng.choice(
            pool,
            size=max_to_drop,
            replace=False,
        )

        for col in chosen:
            if col in df.columns:
                error_log.append(
                    {
                        "column": col,
                        "error_type": "dropped_column",
                        "error_pct": round(error_pct, 4),
                    },
                )
                df = df.drop(columns=[col])

    return df, error_log


def main(
    input_file: str,
    error_pcts: list[float],
    columns: list[str] | None,
    seed: int,
    output_dir: str | None,
) -> None:
    src_file = Path(input_file)
    if not src_file.exists():
        raise FileNotFoundError(f"Input file not found: {src_file}")

    df_base = pd.read_csv(src_file)
    file_stem = src_file.stem

    # Output directory
    if output_dir:
        out_dir = Path(output_dir)
    else:
        out_dir = src_file.parent / f"{file_stem}_dropped_columns_injected"
    out_dir.mkdir(exist_ok=True, parents=True)

    print(f"Input file : {src_file}")
    print(f"Output dir : {out_dir}")
    print(f"Error %s   : {error_pcts} (seed={seed})\n")

    for pct in error_pcts:
        # Seeded RNG
        rng = np.random.default_rng(seed)

        # Determine column pool (default = all)
        pool = columns if columns else list(df_base.columns)

        df_injected, error_log = inject_errors(
            df=df_base,
            error_pct=pct,
            pool=pool,
            rng=rng,
        )

        pct_label = f"drop_{round(pct)}_pt"

        # Strip original long base name if present
        base_to_strip = "our_training_dataset_sample_anonymized"
        prefix = "" if file_stem == base_to_strip else f"{file_stem}_"

        csv_name = f"{prefix}{pct_label}.csv"
        log_name = f"{prefix}{pct_label}.json"

        # Save injected CSV
        df_injected.to_csv(out_dir / csv_name, index=False)

        # Save sidecar error log
        with open(out_dir / log_name, "w") as f:
            json.dump(error_log, f, indent=2)

        print(
            f"  {pct:>2}%: {len(error_log):>5} columns dropped "
            f"({pct:.2f}% target) → {csv_name}",
        )

    print(f"\n✅  Done! Injected CSVs + error logs saved to: {out_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Randomly drop columns from a CSV file",
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
        help="Error percentages to inject (default: 5 10 20 40)",
    )
    parser.add_argument(
        "--columns",
        nargs="+",
        default=None,
        help="Pool of columns to consider for dropping (default: all)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed (default: 42)",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory",
    )
    args = parser.parse_args()

    main(
        input_file=args.input_file,
        error_pcts=args.error_pcts,
        columns=args.columns,
        seed=args.seed,
        output_dir=args.output_dir,
    )
