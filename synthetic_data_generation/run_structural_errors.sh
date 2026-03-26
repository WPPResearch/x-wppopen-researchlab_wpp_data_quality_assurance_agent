#!/bin/bash
set -e

# Project root - move up one level from the script's directory
cd "$(dirname "$0")/.."

INPUT="data_science/utils/data/OI_training_data_sample_20260203_anonymized.csv"
PCTS="5 10 20 40"

echo "=== Running Step 3: Missing values ==="
python synthetic_data_generation/inject_missing_values.py \
    --input-file "$INPUT" --error-pcts $PCTS --seed 100

echo "=== Running Step 4: Outliers ==="
python synthetic_data_generation/inject_outliers.py \
    --input-file "$INPUT" --error-pcts $PCTS --seed 101

echo "=== Running Step 5: Duplicate rows ==="
python synthetic_data_generation/inject_duplicates.py \
    --input-file "$INPUT" --error-pcts $PCTS --seed 102

echo "=== Running Step 6: Categorical errors ==="
python synthetic_data_generation/inject_categorical_errors.py \
    --input-file "$INPUT" --error-pcts $PCTS --seed 103

echo "=== Running Step 8: Dropped columns (not used in experiments) ==="
python synthetic_data_generation/inject_dropped_columns.py \
    --input-file "$INPUT" --error-pcts $PCTS --seed 104

echo "All structural error variations injected for percentages: $PCTS"
