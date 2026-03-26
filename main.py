# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
This file initializes a FastAPI application for Data Science agent
using get_fast_api_app() from ADK. Session service URI and a flag
for a web interface configured via environment variables.
It can then be run using Uvicorn, which listens on a port specified by
the PORT environment variable or defaults to 8080.
This approach offers more flexibility, particularly if you want to
embed Data Science agent within a custom FastAPI application.
It is used for Cloud Run deployment with standard gcloud run deploy command.
"""

import os

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app
from google.cloud import logging as google_cloud_logging

# Load environment variables from .env file
load_dotenv()

logging_client = google_cloud_logging.Client()
logger = logging_client.logger(__name__)

AGENT_DIR = os.path.dirname(os.path.abspath(__file__))

# Get Enable Web interface serving flag from environment variables
# Set web=True if you intend to serve a web interface, False otherwise
web_interface_enabled = os.getenv("SERVE_WEB_INTERFACE", "True").lower() in (
    "true",
    "1",
)

# Determine session service URI
session_uri = os.getenv("SESSION_SERVICE_URI")

# Fallback to Memory Engine only if SESSION_SERVICE_URI is NOT set
if (
    not session_uri
    and os.getenv("GOOGLE_CLOUD_PROJECT")
    and os.getenv("MEMORY_SERVICE_URI")
):
    _m_uri = os.getenv("MEMORY_SERVICE_URI")
    if _m_uri.startswith("agentengine://"):
        session_uri = _m_uri
    else:
        _engine_id = _m_uri.split("/")[-1]
        session_uri = f"agentengine://{_engine_id}"

# Prepare arguments for get_fast_api_app
app_args = {
    "agents_dir": AGENT_DIR,
    "web": web_interface_enabled,
    "session_service_uri": session_uri,
}

# Configure artifact service URI for storing reports, images, and other files
artifact_bucket = os.getenv("ARTIFACT_BUCKET_NAME", None)

if artifact_bucket:
    app_args["artifact_service_uri"] = f"gs://{artifact_bucket}"
    logger.log_text(
        f"Using GCS artifact service with bucket: {artifact_bucket}",
        severity="INFO",
    )
else:
    logger.log_text(
        "ARTIFACT_BUCKET_NAME not provided. Using in-memory artifact service. "
        "All artifacts will be lost when the server restarts.",
        severity="WARNING",
    )

# Configure Memory Bank from environment variables
# get_fast_api_app accepts a memory_service_uri string with the agentengine:// scheme.
# It wires up LoadMemoryTool retrieval AND session-start memory preloading automatically.
memory_bank_uri = os.getenv("MEMORY_SERVICE_URI", None)

# Resolve to agentengine:// format that the ADK service registry understands.
_memory_service_uri_for_adk = None
if memory_bank_uri:
    if memory_bank_uri.startswith("agentengine://"):
        _memory_service_uri_for_adk = memory_bank_uri
    elif "/reasoningEngines/" in memory_bank_uri:
        _agent_engine_id = memory_bank_uri.split("/")[-1]
        _memory_service_uri_for_adk = f"agentengine://{_agent_engine_id}"

if _memory_service_uri_for_adk:
    app_args["memory_service_uri"] = _memory_service_uri_for_adk
    logger.log_text(
        f"Using Vertex AI Memory Bank: {_memory_service_uri_for_adk}",
        severity="INFO",
    )
else:
    logger.log_text(
        "MEMORY_SERVICE_URI not set — LoadMemoryTool and memory preloading will be disabled.",
        severity="WARNING",
    )

# Create FastAPI app with appropriate arguments
try:
    logger.log_text(f"Initializing ADK app with args: {app_args}", severity="INFO")
    app: FastAPI = get_fast_api_app(**app_args)
    app.title = "data_science"
    app.description = "Data Science Agent"
except Exception as e:
    import traceback

    error_msg = f"Failed to initialize ADK app: {str(e)}\n{traceback.format_exc()}"
    logger.log_text(error_msg, severity="ERROR")
    # Create a dummy app so the container doesn't crash but shows the error
    app = FastAPI(title="Error")

    init_error_msg = str(e)

    @app.get("/")
    def error_page():
        return {"error": "Initialization failed", "message": init_error_msg}


if __name__ == "__main__":
    # Use the PORT environment variable provided by Cloud Run, defaulting to 8080
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
