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

"""Report Agent: generate reports in various formats."""

import os

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools import FunctionTool
from google.genai.types import GenerateContentConfig

from .tools import (
    save_report_markdown,
    save_report_html,
    save_report_pdf,
    list_session_artifacts,
    json_statistical_analysis,
)
from .prompts import return_instructions_report


def setup_before_agent_call(callback_context: CallbackContext):
    """Setup the agent by injecting database schema into instructions."""
    if "database_settings" not in callback_context.state:
        return

    schema = (
        callback_context.state["database_settings"]
        .get("bigquery", {})
        .get("schema", {})
    )
    if not schema:
        return

    callback_context._invocation_context.agent.instruction = (
        return_instructions_report()
        + f"""
<DATABASE_CONTEXT>
The following BigQuery schema details the tables and columns available. Use this to identify tables and understand their structure.

<SCHEMA>
{schema}
</SCHEMA>
</DATABASE_CONTEXT>
"""
    )


report_agent = Agent(
    model=os.getenv("REPORT_AGENT_MODEL") or "gemini-2.5-flash",
    name="report_agent",
    instruction=return_instructions_report(),
    before_agent_callback=setup_before_agent_call,
    tools=[
        FunctionTool(list_session_artifacts),
        FunctionTool(save_report_markdown),
        FunctionTool(save_report_html),
        FunctionTool(save_report_pdf),
        FunctionTool(json_statistical_analysis),
        __import__(
            "google.adk.tools.preload_memory_tool",
            fromlist=["1"],
        ).PreloadMemoryTool(),
    ],
    generate_content_config=GenerateContentConfig(
        temperature=0.3,
    ),
)
