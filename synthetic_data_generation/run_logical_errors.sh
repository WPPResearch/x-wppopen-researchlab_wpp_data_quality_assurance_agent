#!/bin/bash
set -e

# Project root
cd "$(dirname "$0")/.."

# Path to the source anonymized CSV file. Change this to your input file path.
INPUT="data_science/utils/data/our_training_dataset_sample_anonymized.csv"
# Percentages of error injection to run.
PCTS="5 10 20 40"

echo "=== Running Rule 1 ==="
python synthetic_data_generation/inject_logical_error_1_clicks_exceed_impressions.py \
    --input-file "$INPUT" --error-pcts $PCTS --seed 42

echo "=== Running Rule 2 ==="
python synthetic_data_generation/inject_logical_error_2_conversions_exceed_clicks.py \
    --input-file "$INPUT" --error-pcts $PCTS --seed 43

echo "=== Running Rule 3 ==="
python synthetic_data_generation/inject_logical_error_3_spend_with_zero_impressions.py \
    --input-file "$INPUT" --error-pcts $PCTS --seed 44

echo "=== Running Rule 4 ==="
python synthetic_data_generation/inject_logical_error_4_video_completions_exceed_plays.py \
    --input-file "$INPUT" --error-pcts $PCTS --seed 45

echo "=== Running Rule 5 ==="
python synthetic_data_generation/inject_logical_error_5_purchases_without_add_to_cart.py \
    --input-file "$INPUT" --error-pcts $PCTS --seed 46

echo "=== Running Rule 6 ==="
python synthetic_data_generation/inject_logical_error_6_landing_page_views_exceed_clicks.py \
    --input-file "$INPUT" --error-pcts $PCTS --seed 47

echo "=== Running Rule 7 ==="
python synthetic_data_generation/inject_logical_error_7_negative_metric_values.py \
    --input-file "$INPUT" --error-pcts $PCTS --seed 48

echo "All 7 logical error variations injected for percentages: $PCTS"
