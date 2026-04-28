import os
import json
import csv

# This script generates a summary CSV of the synthetic data generation outputs.
# It identifies sample files and summarizes error types at a high level.

# Get paths relative to script location
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
# Root path where the dataset folders are located. Change this if your data is elsewhere.
base_path = os.path.join(project_root, "data_science/utils/data")

results = []
count = 1

# Automatically find all directories ending in _injected
if not os.path.exists(base_path):
    print(f"Error: Base path {base_path} does not exist.")
    exit(1)

dirs = [
    d
    for d in os.listdir(base_path)
    if os.path.isdir(os.path.join(base_path, d))
    and (d.endswith("_injected") or d == "mixed_11_errors_stacked")
]
dirs.sort()

# Mapping from short prefixes to readable rules
RULE_MAP = {
    "log_1": "clicks_exceed_impressions",
    "log_2": "conversions_exceed_clicks",
    "log_3": "spend_with_zero_impressions",
    "log_4": "video_completions_exceed_plays",
    "log_5": "purchases_without_add_to_cart",
    "log_6": "landing_page_views_exceed_clicks",
    "log_7": "negative_metric_values",
    "miss": "null values",
    "out": "outliers",
    "dup": "duplicates",
    "cat": "categorical errors",
    "drop": "dropped columns",
}

# We want a variety of samples, but especially the multiple percentages for each type.
for d in dirs:
    path = os.path.join(base_path, d)
    files_in_dir = os.listdir(path)
    csv_files = [f for f in files_in_dir if f.endswith(".csv")]
    csv_files.sort()

    for csv_f in csv_files:
        if count > 100:  # Increased limit for more coverage
            break

        base_name = csv_f.replace(".csv", "")
        # Skip the original base file if it's in a mixed dir
        if base_name == "our_training_dataset_sample_anonymized":
            continue

        logical_rules = set()
        structural_types = set()

        # Parse from filename tokens
        tokens = base_name.split("_")
        i = 0
        while i < len(tokens):
            token = tokens[i]
            if token == "log" and i + 1 < len(tokens):
                key = f"log_{tokens[i+1]}"
                if key in RULE_MAP:
                    logical_rules.add(RULE_MAP[key])
                i += 1
            elif token in RULE_MAP:
                if token.startswith("log_"):
                    logical_rules.add(RULE_MAP[token])
                else:
                    structural_types.add(RULE_MAP[token])
            i += 1

        # Also check the associated JSON for more precise/extra info
        json_f = f"{base_name}.json"
        if json_f in files_in_dir:
            try:
                with open(os.path.join(path, json_f), "r") as jf:
                    errors_data = json.load(jf)
                    for err in errors_data:
                        if err.get("error_type") == "logical_error":
                            logical_rules.add(err.get("rule", "unknown_logical"))
                        else:
                            rule = err.get("rule")
                            if not rule:
                                e_type = err.get("error_type")
                                if e_type == "missing_value":
                                    rule = "null values"
                                elif e_type == "outlier":
                                    rule = "outliers"
                                elif "miss" in base_name:
                                    rule = "null values"
                                elif "out" in base_name:
                                    rule = "outliers"
                                elif "dup" in base_name:
                                    rule = "duplicates"
                                elif "cat" in base_name:
                                    rule = "categorical errors"
                                elif "drop" in base_name:
                                    rule = "dropped columns"
                                else:
                                    rule = "structural"
                            structural_types.add(rule)
            except Exception:
                pass

        # Determine Ground Truth based on directory name or stacked filename
        is_mixed = "mixed" in d
        if is_mixed:
            # For mixed, GT is based on what's actually in the name tokens
            logical_gt = str(len(logical_rules))
            structural_gt = str(len(structural_types))
        else:
            is_logical = "logical" in d
            logical_gt = "1" if is_logical else "0"  # Each dir has only 1 type now
            # Handle special cases if it's not a logical dir
            if not is_logical:
                structural_gt = "1"
            else:
                structural_gt = "0"

        # Final counts
        injected_logical_count = len(logical_rules)
        injected_structural_count = len(structural_types)

        # "Max" logic as requested: if any injected, show total potential (7/4)
        max_logical = "7" if injected_logical_count > 0 else "0"
        max_structural = "4" if injected_structural_count > 0 else "0"

        type_logical = ", ".join(sorted(list(logical_rules))) if logical_rules else "-"
        type_structural = (
            ", ".join(sorted(list(structural_types))) if structural_types else "-"
        )

        results.append(
            [
                f"example_{count:02d}",
                base_name,
                max_logical,
                injected_logical_count,
                type_logical,
                max_structural,
                injected_structural_count,
                type_structural,
            ],
        )
        count += 1

output_file = os.path.join(script_dir, "synthetic_data_generation_summary.csv")
headers = [
    "Table_name",
    "Table_description_name",
    "max_number_of_logical_errors",
    "number_of_injected_logical_errors",
    "type_of_logical_error",
    "max_number_of_structural_errors",
    "number_of_injected_structural_errors",
    "type_of_structural_error",
]

with open(output_file, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(headers)
    writer.writerows(results)

print(f"CSV generated: {output_file} with {len(results)} rows.")
