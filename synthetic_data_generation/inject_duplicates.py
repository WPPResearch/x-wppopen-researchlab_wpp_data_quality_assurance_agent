"""
Injects duplicate rows into a CSV file at multiple specified percentages.

- For each provided percentage, it generates a new CSV and a sidecar JSON log.
- Duplicated rows are inserted at random positions within the file.
- A sidecar JSON log records which row was duplicated and where it was inserted.
- A fixed random seed makes everything fully reproducible.

Usage:
    python synthetic_data_generation/inject_duplicates.py \
        --input-file data_science/utils/data/your_file.csv \
        --error-pcts 5 10 20 40

Options:
    --input-file    Path to the anonymized CSV file (required)
    --error-pcts    List of error percentages to inject (default: 5 10 20 40)
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
    rng: np.random.Generator,
) -> tuple[pd.DataFrame, list[dict]]:
    """
    Picks N rows at random, duplicates them, and inserts each copy at a
    random position in the dataframe.
    """
    n_rows = len(df)
    n_dups = max(1, int(round(n_rows * error_pct / 100))) if error_pct > 0 else 0

    error_log = []
    df = df.copy().reset_index(drop=True)

    # Pick source rows to duplicate
    source_indices = rng.choice(
        df.index.tolist(),
        size=min(n_dups, n_rows),
        # replace=False means we don't pick the same row index twice as a SOURCE,
        # but the duplicate itself could theoretically be picked in a chained process.
        replace=False,
    )

    # Build list of (insert_position, source_index) to apply
    inserts = []
    for src_idx in source_indices:
        # Insert position: anywhere in the current df (including end)
        insert_pos = int(rng.integers(0, n_rows + len(inserts) + 1))
        inserts.append((insert_pos, src_idx))
        error_log.append(
            {
                "source_row_index": int(src_idx),
                "inserted_at_position": insert_pos,
                "error_type": "duplicate_row",
                "error_pct": round(error_pct, 4),
            },
        )

    # Apply inserts: build the new df by slicing and concatenating
    # Sort by insert position so we can process them in order
    inserts_sorted = sorted(inserts, key=lambda x: x[0])
    parts = []
    prev = 0
    for insert_pos, src_idx in inserts_sorted:
        parts.append(df.iloc[prev:insert_pos])
        parts.append(df.iloc[[src_idx]])
        prev = insert_pos
    parts.append(df.iloc[prev:])

    df_out = pd.concat(parts, ignore_index=True)
    return df_out, error_log


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

    # Output directory
    if output_dir:
        out_dir = Path(output_dir)
    else:
        out_dir = src_file.parent / f"{file_stem}_duplicates_injected"
    out_dir.mkdir(exist_ok=True, parents=True)

    print(f"Input file : {src_file}")
    print(f"Output dir : {out_dir}")
    print(f"Error %s   : {error_pcts} (seed={seed})\n")

    for pct in error_pcts:
        # Seeded RNG
        rng = np.random.default_rng(seed)

        df_injected, error_log = inject_errors(
            df=df_base,
            error_pct=pct,
            rng=rng,
        )

        pct_label = f"dup_{round(pct)}_pt"

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
            f"  {pct:>2}%: {len(error_log):>4} rows duplicated  "
            f"({len(df_base)} → {len(df_injected)} rows)  → {csv_name}",
        )

    print(f"\n✅  Done! Injected CSVs + error logs saved to: {out_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Inject duplicate rows into a CSV file",
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
        seed=args.seed,
        output_dir=args.output_dir,
    )
