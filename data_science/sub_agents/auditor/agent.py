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

import os

from data_science.sub_agents.bigquery.tools import (
    get_database_settings as get_bq_database_settings,
)
from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.genai import types
from google.adk.tools.load_memory_tool import LoadMemoryTool
from data_science.tools import save_memory

from .prompts import return_instructions_auditor
from .tools import call_bigquery_agent


def setup_before_agent_call(callback_context: CallbackContext):
    """Setup the auditor agent with database schema context."""

    if "database_settings" not in callback_context.state:
        callback_context.state["database_settings"] = {
            "bigquery": get_bq_database_settings(),
        }
    elif "bigquery" not in callback_context.state["database_settings"]:
        callback_context.state["database_settings"]["bigquery"] = (
            get_bq_database_settings()
        )

    schema = callback_context.state["database_settings"]["bigquery"]["schema"]

    callback_context._invocation_context.agent.instruction = (
        return_instructions_auditor()
        + f"""
<DATABASE_CONTEXT>
Use the following BigQuery schema to investigate and audit tables.

<SCHEMA>
{schema}
</SCHEMA>
</DATABASE_CONTEXT>
"""
    )


auditor_agent = LlmAgent(
    model=os.getenv("AUDITOR_AGENT_MODEL") or "gemini-2.5-flash",
    name="auditor_agent",
    instruction=return_instructions_auditor(),
    before_agent_callback=setup_before_agent_call,
    tools=[call_bigquery_agent, LoadMemoryTool(), save_memory],
    generate_content_config=types.GenerateContentConfig(temperature=0.01),
)
