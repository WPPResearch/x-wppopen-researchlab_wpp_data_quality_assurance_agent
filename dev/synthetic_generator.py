import csv
import random
import re
import argparse
from pathlib import Path


def _parse_value_block(block: str):
    """Parse a block of text containing column values."""
    block = block.strip()
    if not block:
        return []

    # Extract quoted strings
    quoted = re.findall(r"'([^']*)'|\"([^\"]*)\"", block)
    if quoted:
        values = [a or b for a, b in quoted]
        # Check if 'nan' appears in the block
        if re.search(r"\bnan\b", block, flags=re.IGNORECASE):
            values.append(None)
        return values

    # Parse numeric values and nan
    values = []
    if re.search(r"\bnan\b", block, flags=re.IGNORECASE):
        values.append(None)

    for token in re.findall(r"-?\d+(?:\.\d+)?", block):
        if "." in token:
            values.append(float(token))
        else:
            values.append(int(token))
    return values


def parse_columns_v1(file_path: Path):
    """Parse the columns_v1.txt file and extract all column values."""
    columns = {}
    current_col = None
    current_lines = []

    for raw in file_path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if not line:
            # Empty line - process accumulated data
            if current_col is not None and current_lines:
                columns[current_col] = _parse_value_block(" ".join(current_lines))
            current_col = None
            current_lines = []
            continue

        # Check if this is a header line (column name)
        match = re.match(r"^(.+?):\s+\d+\s+unique values", line)
        if match:
            # Save previous column if exists
            if current_col is not None and current_lines:
                columns[current_col] = _parse_value_block(" ".join(current_lines))
            current_col = match.group(1).strip()
            current_lines = []
            continue

        # Accumulate value lines for current column
        if current_col is not None:
            current_lines.append(line)

    # Process last column
    if current_col is not None and current_lines:
        columns[current_col] = _parse_value_block(" ".join(current_lines))

    return columns


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
    """Main function to generate synthetic dataset from schema file."""
    parser = argparse.ArgumentParser(
        description="Generate synthetic dataset from schema file",
    )
    parser.add_argument("schema_file", help="Path to the schema file")
    parser.add_argument(
        "-n",
        "--num-rows",
        type=int,
        default=1000,
        help="Number of rows to generate",
    )
    parser.add_argument(
        "-s",
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducibility",
    )

    args = parser.parse_args()

    schema_file = validate_path(args.schema_file)
    num_rows = args.num_rows

    # Set random seed if provided
    if args.seed is not None:
        random.seed(args.seed)

    if not schema_file.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_file}")

    # Generate output filename in the same directory as the schema file
    output_file = schema_file.stem.replace("schema", "synthetic_dataset") + ".csv"
    output_path = validate_path(str(schema_file.parent / output_file))

    # Parse schema and generate CSV
    columns = parse_columns_v1(schema_file)
    if not columns:
        raise ValueError(f"No columns parsed from {schema_file}")

    print(f"Loaded {len(columns)} columns from {schema_file}")
    print(f"Generating {num_rows} rows to {output_path}")

    with open(output_path, mode="w", newline="") as file:
        writer = csv.writer(file, quoting=csv.QUOTE_ALL)
        writer.writerow(list(columns.keys()))

        for _ in range(num_rows):
            row = [
                random.choice(values) if values else None
                for values in [columns.get(col, []) for col in columns.keys()]
            ]
            writer.writerow(row)

    print("Done!")


if __name__ == "__main__":
    main()
