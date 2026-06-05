import pandas as pd
import argparse
from pathlib import Path


def validate_path(path_str: str | None) -> Path | None:
    """Resolve and validate the path to prevent directory traversal."""
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
    out_path = validate_path(str(input_path.parent / f"{base}_schema.txt"))

    with open(out_path, "w") as f:
        for col in df.columns:
            if df[col].nunique() < len(df):
                f.write(f"\n{col}: {df[col].nunique()} unique values\n")
                f.write(str(df[col].unique()) + "\n")

    print(f"Schema extracted to {out_path}")


if __name__ == "__main__":
    main()
