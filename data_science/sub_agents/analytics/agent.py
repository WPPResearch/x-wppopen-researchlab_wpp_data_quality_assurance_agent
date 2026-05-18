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

"""Analytics Agent: generate nl2py and use code interpreter to run the code."""

import logging
import os

from google.adk.agents import Agent
from google.adk.code_executors import VertexAiCodeExecutor

from .prompts import return_instructions_analytics

_logger = logging.getLogger(__name__)


def _get_code_executor():
    """Create the VertexAiCodeExecutor with graceful error handling.

    Wraps initialization in try/except so the container can still start
    even if the code interpreter extension is inaccessible (e.g. due to
    cross-project permission issues).
    """
    try:
        executor = VertexAiCodeExecutor(
            optimize_data_file=True,
            stateful=True,
            extension=os.getenv("CODE_INTERPRETER_EXTENSION_NAME"),
            location=os.getenv("GOOGLE_CLOUD_LOCATION"),
            project_id=os.getenv("GOOGLE_CLOUD_PROJECT"),
        )
        _logger.info("VertexAiCodeExecutor initialized successfully.")
        return executor
    except Exception as e:
        _logger.error(
            "Failed to initialize VertexAiCodeExecutor: %s. "
            "The analytics agent will not have code execution capability.",
            e,
        )
        return None


analytics_agent = Agent(
    model=os.getenv("ANALYTICS_AGENT_MODEL") or "gemini-2.5-flash",
    name="analytics_agent",
    instruction=return_instructions_analytics(),
    code_executor=_get_code_executor(),
)
