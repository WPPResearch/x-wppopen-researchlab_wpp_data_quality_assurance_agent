#!/bin/bash
set -e

# Project root - move up one level from the script's directory
cd "$(dirname "$0")/.."

# Default to 5% if no argument provided
PCT=${1:-5}
INPUT="data_science/utils/data/OI_training_data_sample_20260203_anonymized.csv"
OUT_DIR="data_science/utils/data/mixed_errors_stacked"

# Ensure output directory exists
mkdir -p "$OUT_DIR"

echo "=== Starting Full Sequential Mixed Injection (Percentage: $PCT%) ==="

# Copy base file to start the chain
CURRENT_FILE="$OUT_DIR/OI_training_data_sample_20260203_anonymized.csv"
cp "$INPUT" "$CURRENT_FILE"

# Function to update CURRENT_FILE and STEM
update_current() {
    suffix=$1
    STEM=$(basename "$CURRENT_FILE" .csv)
    CURRENT_FILE="$OUT_DIR/${STEM}_${suffix}_${PCT}_percent.csv"
}

# 1. Logical Error Rule 1 (Clicks Exceed Impressions)
echo "--- Injecting Logical Error Rule 1 ---"
python synthetic_data_generation/inject_logical_error_1_clicks_exceed_impressions.py \
    --input-file "$CURRENT_FILE" --error-pcts $PCT --output-dir "$OUT_DIR" --seed 42
update_current "logical_error_1"

# 2. Logical Error Rule 2 (Conversions Exceed Clicks)
echo "--- Injecting Logical Error Rule 2 ---"
python synthetic_data_generation/inject_logical_error_2_conversions_exceed_clicks.py \
    --input-file "$CURRENT_FILE" --error-pcts $PCT --output-dir "$OUT_DIR" --seed 43
update_current "logical_error_2"

# 3. Logical Error Rule 3 (Spend with Zero Impressions)
echo "--- Injecting Logical Error Rule 3 ---"
python synthetic_data_generation/inject_logical_error_3_spend_with_zero_impressions.py \
    --input-file "$CURRENT_FILE" --error-pcts $PCT --output-dir "$OUT_DIR" --seed 44
update_current "logical_error_3"

# 4. Logical Error Rule 4 (Video Completions Exceed Plays)
echo "--- Injecting Logical Error Rule 4 ---"
python synthetic_data_generation/inject_logical_error_4_video_completions_exceed_plays.py \
    --input-file "$CURRENT_FILE" --error-pcts $PCT --output-dir "$OUT_DIR" --seed 45
update_current "logical_error_4"

# 5. Logical Error Rule 5 (Purchases without Add to Cart)
echo "--- Injecting Logical Error Rule 5 ---"
python synthetic_data_generation/inject_logical_error_5_purchases_without_add_to_cart.py \
    --input-file "$CURRENT_FILE" --error-pcts $PCT --output-dir "$OUT_DIR" --seed 46
update_current "logical_error_5"

# 6. Logical Error Rule 6 (Landing Page Views Exceed Clicks)
echo "--- Injecting Logical Error Rule 6 ---"
python synthetic_data_generation/inject_logical_error_6_landing_page_views_exceed_clicks.py \
    --input-file "$CURRENT_FILE" --error-pcts $PCT --output-dir "$OUT_DIR" --seed 47
update_current "logical_error_6"

# 7. Logical Error Rule 7 (Negative Metric Values)
echo "--- Injecting Logical Error Rule 7 ---"
python synthetic_data_generation/inject_logical_error_7_negative_metric_values.py \
    --input-file "$CURRENT_FILE" --error-pcts $PCT --output-dir "$OUT_DIR" --seed 48
update_current "logical_error_7"

# 8. Missing Values
echo "--- Injecting Missing Values ---"
python synthetic_data_generation/inject_missing_values.py \
    --input-file "$CURRENT_FILE" --error-pcts $PCT --output-dir "$OUT_DIR" --seed 100
update_current "missing"

# 9. Outliers
echo "--- Injecting Outliers ---"
python synthetic_data_generation/inject_outliers.py \
    --input-file "$CURRENT_FILE" --error-pcts $PCT --output-dir "$OUT_DIR" --seed 101
update_current "outlier_error"

# 10. Duplicates
echo "--- Injecting Duplicates ---"
python synthetic_data_generation/inject_duplicates.py \
    --input-file "$CURRENT_FILE" --error-pcts $PCT --output-dir "$OUT_DIR" --seed 102
update_current "duplicate"

# 11. Categorical Errors
echo "--- Injecting Categorical Errors ---"
python synthetic_data_generation/inject_categorical_errors.py \
    --input-file "$CURRENT_FILE" --error-pcts $PCT --output-dir "$OUT_DIR" --seed 103
update_current "categorical_error"

# 12. Dropped Columns
echo "--- Injecting Dropped Columns ---"
python synthetic_data_generation/inject_dropped_columns.py \
    --input-file "$CURRENT_FILE" --error-pcts $PCT --output-dir "$OUT_DIR" --seed 104
update_current "dropped"

echo ""
echo "✅ Done! Full stacked file: $CURRENT_FILE"
echo "All intermediate logs and CSVs are saved in: $OUT_DIR"
echo "The final table name in BigQuery will be derived from this long stacked filename."
