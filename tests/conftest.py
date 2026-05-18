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

"""Pytest configuration and fixtures for tests."""

import os

import dotenv

# Load .env file first
dotenv.load_dotenv(override=True)

# MOCK load_dotenv so application code doesn't reload .env and overwrite our testing overrides
# (like data_science/__init__.py and llm_utils.py which call it internally)
dotenv.load_dotenv = lambda *args, **kwargs: None

# Set dummy env vars for tests that don't need real BigQuery access
os.environ.setdefault("BQ_DATASET_ID", "dummy")
os.environ.setdefault("BQ_DATA_PROJECT_ID", "dummy")

# Force tests to use gemini-2.5-flash as the dev environment doesn't have the gemini-3 preview yet
os.environ["ROOT_AGENT_MODEL"] = "gemini-2.5-flash"
os.environ["ANALYTICS_AGENT_MODEL"] = "gemini-2.5-flash"
os.environ["BIGQUERY_AGENT_MODEL"] = "gemini-2.5-flash"
os.environ["REPORT_AGENT_MODEL"] = "gemini-2.5-flash"
os.environ["BQML_AGENT_MODEL"] = "gemini-2.5-flash"

# Remove conflicting API keys that break Vertex AI SDK initialization logic.
# The user's .env uses both ML Dev (google_api_key) and Vertex, which crashes genai.Client() validations in tests
if "GOOGLE_API_KEY" in os.environ:
    del os.environ["GOOGLE_API_KEY"]
if "GEMINI_API_KEY" in os.environ:
    del os.environ["GEMINI_API_KEY"]
