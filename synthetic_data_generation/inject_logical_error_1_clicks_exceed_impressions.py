"""
Injects Rule 1 logical errors: clicks_exceed_impressions into a CSV file.

Description:
    This script violates the fundamental logical requirement that Clicks cannot exceed Impressions.
    It targets a specific percentage of rows and modifies the 'performance__clicks' column.

Rule Details:
    Violation: [performance__clicks] > [performance__impressions]

Null Handling Logic:
    - If 'performance__impressions' is NULL or 0:
        The injected 'performance__clicks' is a fixed random value from [100, 1000].
        The NULL 'performance__impressions' value is PRESERVED as NULL.
    - If 'performance__impressions' is NOT NULL:
        The injected 'performance__clicks' is round(impressions * factor), where factor is [2.0, 10.0].

Usage:
    python synthetic_data_generation/inject_logical_error_1_clicks_exceed_impressions.py \\
        --input-file /path/to/data.csv \\
        --error-pcts 5 10 20 40
"""

import argparse
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
from werkzeug.security import safe_join

RULE_ID = 1
RULE_NAME = "clicks_exceed_impressions"


def inject_rule(
    df: pd.DataFrame,
    chosen: np.ndarray,
    rng: np.random.Generator,
) -> list[dict]:
    errors = []
    for row_idx in chosen:
        impressions = df.at[row_idx, "performance__impressions"]
        original_clicks = df.at[row_idx, "performance__clicks"]

        if pd.isna(impressions) or impressions == 0:
            new_clicks = int(rng.integers(100, 1000))
        else:
            factor = rng.uniform(2.0, 10.0)
            new_clicks = int(round(impressions * factor))

        errors.append(
            {
                "row_index": int(row_idx),
                "rule": RULE_NAME,
                "columns_affected": ["performance__clicks"],
                "original_values": {
                    "performance__clicks": float(original_clicks)
                    if not pd.isna(original_clicks)
                    else None,
                },
                "injected_values": {"performance__clicks": new_clicks},
                "error_type": "logical_error",
            },
        )
        df.at[row_idx, "performance__clicks"] = new_clicks
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
        # Sanitize via safe_join before pathlib.Path
        parent_str, name = os.path.split(path_str)
        parent_str = os.path.abspath(parent_str) if parent_str else os.getcwd()
        safe_str = safe_join(parent_str, name)
        if safe_str is None:
            raise ValueError(f"Security Alert: Invalid path: {path_str}")
        p = Path(safe_str).resolve()
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

        csv_path_str = safe_join(str(out_dir), csv_name)
        if csv_path_str is None:
            raise ValueError(f"Security Alert: Invalid CSV filename: {csv_name}")
        df_injected.to_csv(Path(csv_path_str), index=False)
        log_path_str = safe_join(str(out_dir), log_name)
        if log_path_str is None:
            raise ValueError(f"Security Alert: Invalid log filename: {log_name}")
        with open(Path(log_path_str), "w") as f:
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
