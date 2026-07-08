import os
import argparse
from pathlib import Path

import pandas as pd
from werkzeug.security import safe_join


def validate_path(path_str: str | None) -> Path | None:
    """Resolve and validate the path to prevent directory traversal."""
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


def main():
    parser = argparse.ArgumentParser(description="Extract schema from a CSV file")
    parser.add_argument(
        "input_file",
        help="Path to the CSV file to extract schema from",
    )
    args = parser.parse_args()

    input_path = validate_path(args.input_file)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    df = pd.read_csv(input_path)
    base = input_path.stem
    out_path_str = safe_join(str(input_path.parent), f"{base}_schema.txt")
    if out_path_str is None:
        raise ValueError(f"Security Alert: Invalid schema filename for base: {base}")
    out_path = Path(out_path_str)

    with open(out_path, "w") as f:
        for col in df.columns:
            if df[col].nunique() < len(df):
                f.write(f"\n{col}: {df[col].nunique()} unique values\n")
                f.write(str(df[col].unique()) + "\n")

    print(f"Schema extracted to {out_path}")


if __name__ == "__main__":
    main()
