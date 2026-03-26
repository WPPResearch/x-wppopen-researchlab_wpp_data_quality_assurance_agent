#!/bin/bash
# Convenience script to run adk web with GCS artifact storage and Vertex AI Memory Bank.
# Reads ARTIFACT_BUCKET_NAME and MEMORY_SERVICE_URI from .env automatically.

BUCKET=$(grep -E "^ARTIFACT_BUCKET_NAME=" .env | sed "s/.*=//;s/['\"]//g")
MEMORY_URI_RAW=$(grep -E "^MEMORY_SERVICE_URI=" .env | head -1 | sed "s/.*=//;s/['\"]//g")

# Build the agentengine:// URI that adk web expects.
# Supports both agentengine://<id> and projects/.../reasoningEngines/<id> formats.
if echo "$MEMORY_URI_RAW" | grep -q "^agentengine://"; then
    MEMORY_ARG="$MEMORY_URI_RAW"
elif echo "$MEMORY_URI_RAW" | grep -q "/reasoningEngines/"; then
    ENGINE_ID=$(echo "$MEMORY_URI_RAW" | sed 's|.*/||')
    MEMORY_ARG="agentengine://$ENGINE_ID"
else
    MEMORY_ARG=""
fi

ADK_ARGS=""
if [ -n "$BUCKET" ]; then
    echo "Using GCS artifact storage: gs://$BUCKET"
    ADK_ARGS="$ADK_ARGS --artifact_service_uri gs://$BUCKET"
else
    echo "No ARTIFACT_BUCKET_NAME found in .env — using in-memory artifacts"
fi

if [ -n "$MEMORY_ARG" ]; then
    echo "Using Vertex AI Memory Bank: $MEMORY_ARG"
    ADK_ARGS="$ADK_ARGS --memory_service_uri $MEMORY_ARG --session_service_uri $MEMORY_ARG"
else
    echo "No MEMORY_SERVICE_URI found in .env — LoadMemoryTool will not be connected"
fi

uv run adk web $ADK_ARGS .
