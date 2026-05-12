"""
Reads a CSV, anonymizes sensitive columns, and saves
<same_dir>/<original_stem>_anonymized.csv next to the source file.

Usage:
    python synthetic_data_generation/anonymize_csv.py --input path/to/file.csv
"""

import argparse
from pathlib import Path

import pandas as pd

# Provide the absolute path to your input CSV file here (e.g. "/path/to/your_data.csv")
INPUT_CSV = ""

ANONYMIZE_MAP = {
    "sensitive_column_1": "label_1",
    "sensitive_column_2": "label_2",
    "sensitive_column_3": "label_3",
    "sensitive_column_4": "label_4",
    "sensitive_column_5": "label_5",
}


def anonymize(df: pd.DataFrame) -> pd.DataFrame:
    for col, prefix in ANONYMIZE_MAP.items():
        if col not in df.columns:
            print(f"  [skip] column '{col}' not found")
            continue
        unique_vals = [v for v in df[col].unique() if v == v]  # exclude NaN
        mapping = {val: f"{prefix}{i + 1}" for i, val in enumerate(unique_vals)}
        df[col] = df[col].map(mapping)  # NaN rows stay NaN
        print(f"  {col}: {len(mapping)} values mapped")
    return df


def main(input_path: str) -> None:
    src = Path(input_path)
    output_path = src.parent / f"{src.stem}_anonymized.csv"

    print(f"Reading: {src}")
    df = pd.read_csv(src)
    print(f"Rows: {len(df):,}  |  Columns: {len(df.columns)}")

    print("\nAnonymizing columns ...")
    df = anonymize(df)

    df.to_csv(output_path, index=False)
    print(f"\n✅ Saved anonymized CSV → {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=INPUT_CSV, help="Path to source CSV")
    args = parser.parse_args()
    main(args.input)
