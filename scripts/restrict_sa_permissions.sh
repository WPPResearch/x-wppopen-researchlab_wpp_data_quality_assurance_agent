#!/bin/bash

# ==============================================================================
# Script to restrict permissions of the default Compute Engine service account
# to follow the Principle of Least Privilege for the Data Science Agent.
#
# WARNING: This script removes the 'roles/editor' role from the default
# Compute Engine service account. This will affect any other VMs or Cloud Run
# services in this project that are currently relying on the default SA having
# Editor access.
# ==============================================================================

# Exit on any error
set -e

# Default variables
PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-""}
# Compute the default Compute Engine service account email from project
# Format: PROJECT_NUMBER-compute@developer.gserviceaccount.com
# If SA_EMAIL is not set, will need to be provided or computed from project
SA_EMAIL=${SA_EMAIL:-""}

# Check if project ID is provided
if [ -z "$PROJECT_ID" ]; then
    echo "Error: GOOGLE_CLOUD_PROJECT environment variable is not set."
    echo "Please run: export GOOGLE_CLOUD_PROJECT=your-project-id"
    exit 1
fi

# Check if SA_EMAIL is provided
if [ -z "$SA_EMAIL" ]; then
    echo "Error: SA_EMAIL environment variable is not set."
    echo "Please set it to your Compute Engine service account email:"
    echo "  export SA_EMAIL=PROJECT_NUMBER-compute@developer.gserviceaccount.com"
    echo ""
    echo "You can find your project number with:"
    echo "  gcloud projects describe \$GOOGLE_CLOUD_PROJECT --format='value(projectNumber)'"
    exit 1
fi

echo "================================================================="
echo "Configuring Least Privilege for Service Account:"
echo "Project: $PROJECT_ID"
echo "Service Account: $SA_EMAIL"
echo "================================================================="

echo ""
echo "[1/3] Adding specific required granular roles..."

# 1. AI & LLM Capabilities (Vertex AI)
echo "  -> Adding roles/aiplatform.user..."
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/aiplatform.user" \
    --condition=None \
    --quiet >/dev/null

# 2. Data Access (BigQuery)
echo "  -> Adding roles/bigquery.user..."
# Allows running jobs (queries, ML training)
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/bigquery.user" \
    --condition=None \
    --quiet >/dev/null

echo "  -> Adding roles/bigquery.dataEditor..."
# Allows reading current data and writing new data (reports, ML models)
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/bigquery.dataEditor" \
    --condition=None \
    --quiet >/dev/null

# 3. Artifact Storage (Google Cloud Storage)
echo "  -> Adding roles/storage.objectAdmin..."
# Required to read, write, and delete artifacts in GCS
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/storage.objectAdmin" \
    --condition=None \
    --quiet >/dev/null

# 4. Session State (Cloud SQL)
echo "  -> Adding roles/cloudsql.client..."
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/cloudsql.client" \
    --condition=None \
    --quiet >/dev/null

echo "  -> Adding roles/cloudsql.instanceUser..."
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/cloudsql.instanceUser" \
    --condition=None \
    --quiet >/dev/null

# 5. Observability (Cloud Logging)
echo "  -> Adding roles/logging.logWriter..."
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/logging.logWriter" \
    --condition=None \
    --quiet >/dev/null


echo ""
echo "[2/3] Checking for over-privileged roles to remove..."

# Get current IAM policy, specifically looking for the SA and the editor/owner roles
POLICY_OUTPUT=$(gcloud projects get-iam-policy "$PROJECT_ID" --flatten="bindings[].members" --format="json" | grep -A 2 -B 2 "$SA_EMAIL") || true

if echo "$POLICY_OUTPUT" | grep -q "roles/editor"; then
    echo "  ! Found 'roles/editor' attached to this service account."
    echo "  -> Removing roles/editor..."
    gcloud projects remove-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:$SA_EMAIL" \
        --role="roles/editor" \
        --condition=None \
        --quiet >/dev/null
    echo "  ✓ roles/editor removed successfully."
else
    echo "  ✓ Service account does not have the 'roles/editor' role."
fi


if echo "$POLICY_OUTPUT" | grep -q "roles/owner"; then
    echo "  ! Found 'roles/owner' attached to this service account. (This is highly unusual for a default compute SA)"
    echo "  -> Removing roles/owner..."
    gcloud projects remove-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:$SA_EMAIL" \
        --role="roles/owner" \
        --condition=None \
        --quiet >/dev/null
    echo "  ✓ roles/owner removed successfully."
else
    echo "  ✓ Service account does not have the 'roles/owner' role."
fi

echo ""
echo "[3/3] Verification..."
echo "Current roles granted to $SA_EMAIL:"
gcloud projects get-iam-policy "$PROJECT_ID" \
    --flatten="bindings[].members" \
    --format="table(bindings.role)" \
    --filter="bindings.members:serviceAccount:$SA_EMAIL"

echo "================================================================="
echo "Done! The service account is now configured with Least Privilege."
echo "================================================================="
