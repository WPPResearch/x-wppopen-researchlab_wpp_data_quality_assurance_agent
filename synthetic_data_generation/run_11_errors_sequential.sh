#!/bin/bash
set -e

# Project root - move up one level from the script's directory
cd "$(dirname "$0")/.."

# Default to 5% if no argument provided
PCT=${1:-5}
# 11 Errors (7 Logical + 4 Structural)
NUM_ERRORS=11
INPUT="data_science/utils/data/OI_training_data_sample_20260203_anonymized.csv"
OUT_DIR="data_science/utils/data/mixed_${NUM_ERRORS}_errors_stacked"

# Ensure output directory exists
mkdir -p "$OUT_DIR"

echo "=== Starting Sequential Mixed Injection (Errors: $NUM_ERRORS, Percentage: $PCT%) ==="

# Copy base file to start the chain
CURRENT_FILE="$OUT_DIR/OI_training_data_sample_20260203_anonymized.csv"
cp "$INPUT" "$CURRENT_FILE"

# Function to update CURRENT_FILE and STEM
update_current() {
    suffix=$1
    STEM=$(basename "$CURRENT_FILE" .csv)
    # If the STEM is the original long name, the Python script stripped it
    if [[ "$STEM" == "OI_training_data_sample_20260203_anonymized" ]]; then
        CURRENT_FILE="$OUT_DIR/${suffix}_${PCT}_pt.csv"
    else
        CURRENT_FILE="$OUT_DIR/${STEM}_${suffix}_${PCT}_pt.csv"
    fi
}

# --- LOGICAL ERRORS (7) ---

# 1. Logical Error Rule 1 (Clicks Exceed Impressions)
echo "--- [1/11] Injecting Logical Error Rule 1 ---"
python synthetic_data_generation/inject_logical_error_1_clicks_exceed_impressions.py \
    --input-file "$CURRENT_FILE" --error-pcts $PCT --output-dir "$OUT_DIR" --seed 42
update_current "log_1"

# 2. Logical Error Rule 2 (Conversions Exceed Clicks)
echo "--- [2/11] Injecting Logical Error Rule 2 ---"
python synthetic_data_generation/inject_logical_error_2_conversions_exceed_clicks.py \
    --input-file "$CURRENT_FILE" --error-pcts $PCT --output-dir "$OUT_DIR" --seed 43
update_current "log_2"

# 3. Logical Error Rule 3 (Spend with Zero Impressions)
echo "--- [3/11] Injecting Logical Error Rule 3 ---"
python synthetic_data_generation/inject_logical_error_3_spend_with_zero_impressions.py \
    --input-file "$CURRENT_FILE" --error-pcts $PCT --output-dir "$OUT_DIR" --seed 44
update_current "log_3"

# 4. Logical Error Rule 4 (Video Completions Exceed Plays)
echo "--- [4/11] Injecting Logical Error Rule 4 ---"
python synthetic_data_generation/inject_logical_error_4_video_completions_exceed_plays.py \
    --input-file "$CURRENT_FILE" --error-pcts $PCT --output-dir "$OUT_DIR" --seed 45
update_current "log_4"

# 5. Logical Error Rule 5 (Purchases without Add to Cart)
echo "--- [5/11] Injecting Logical Error Rule 5 ---"
python synthetic_data_generation/inject_logical_error_5_purchases_without_add_to_cart.py \
    --input-file "$CURRENT_FILE" --error-pcts $PCT --output-dir "$OUT_DIR" --seed 46
update_current "log_5"

# 6. Logical Error Rule 6 (Landing Page Views Exceed Clicks)
echo "--- [6/11] Injecting Logical Error Rule 6 ---"
python synthetic_data_generation/inject_logical_error_6_landing_page_views_exceed_clicks.py \
    --input-file "$CURRENT_FILE" --error-pcts $PCT --output-dir "$OUT_DIR" --seed 47
update_current "log_6"

# 7. Logical Error Rule 7 (Negative Metric Values)
echo "--- [7/11] Injecting Logical Error Rule 7 ---"
python synthetic_data_generation/inject_logical_error_7_negative_metric_values.py \
    --input-file "$CURRENT_FILE" --error-pcts $PCT --output-dir "$OUT_DIR" --seed 48
update_current "log_7"

# --- STRUCTURAL ERRORS (4) ---

# 8. Missing Values
echo "--- [8/11] Injecting Missing Values ---"
python synthetic_data_generation/inject_missing_values.py \
    --input-file "$CURRENT_FILE" --error-pcts $PCT --output-dir "$OUT_DIR" --seed 100
update_current "miss"

# 9. Outliers
echo "--- [9/11] Injecting Outliers ---"
python synthetic_data_generation/inject_outliers.py \
    --input-file "$CURRENT_FILE" --error-pcts $PCT --output-dir "$OUT_DIR" --seed 101
update_current "out"

# 10. Duplicates
echo "--- [10/11] Injecting Duplicates ---"
python synthetic_data_generation/inject_duplicates.py \
    --input-file "$CURRENT_FILE" --error-pcts $PCT --output-dir "$OUT_DIR" --seed 102
update_current "dup"

# 11. Categorical Errors
echo "--- [11/11] Injecting Categorical Errors ---"
python synthetic_data_generation/inject_categorical_errors.py \
    --input-file "$CURRENT_FILE" --error-pcts $PCT --output-dir "$OUT_DIR" --seed 103
update_current "cat"

echo ""
echo "✅ Done! Final stacked file: $CURRENT_FILE"
echo "All intermediate logs and CSVs are saved in: $OUT_DIR"
