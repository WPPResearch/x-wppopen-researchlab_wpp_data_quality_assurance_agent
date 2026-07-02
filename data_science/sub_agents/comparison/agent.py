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

"""Comparison Agent: make comparisons between tables of datasets."""

import os
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from .prompts import return_instructions_comparison

from data_science.sub_agents.bigquery.tools import (
    get_database_settings as get_bq_database_settings,
)
from .tools import compare_table_columns, get_volume_metrics


def setup_before_agent_call(callback_context: CallbackContext):
    """Setup the agent."""

    if "database_settings" not in callback_context.state:
        db_settings = {
            "bigquery": get_bq_database_settings(),
        }
        callback_context.state["database_settings"] = db_settings
    elif "bigquery" not in callback_context.state["database_settings"]:
        callback_context.state["database_settings"]["bigquery"] = (
            get_bq_database_settings()
        )

    schema = callback_context.state["database_settings"]["bigquery"]["schema"]

    callback_context._invocation_context.agent.instruction = (
        return_instructions_comparison()
        + f"""
<DATABASE_CONTEXT>
The following BigQuery schema details the tables and columns available for comparison. Use this information to identify tables requested by the user and to understand their structure before calling any tools.

<SCHEMA>
{schema}
</SCHEMA>
</DATABASE_CONTEXT>
"""
    )


comparison_agent = Agent(
    model=os.getenv("ANALYTICS_AGENT_MODEL") or "gemini-2.5-flash",
    name="comparison_agent",
    instruction=return_instructions_comparison(),
    before_agent_callback=setup_before_agent_call,
    tools=[compare_table_columns, get_volume_metrics],
)
