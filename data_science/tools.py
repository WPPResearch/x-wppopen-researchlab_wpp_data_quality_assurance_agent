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

"""Tools for the ADK Sampmles Data Science Agent."""

import logging

from google.adk.tools import ToolContext
from google.adk.tools.agent_tool import AgentTool

from .sub_agents import alloydb_agent, analytics_agent, bigquery_agent

logger = logging.getLogger(__name__)


async def call_bigquery_agent(
    question: str,
    tool_context: ToolContext,
):
    """Tool to call bigquery database (nl2sql) agent."""
    logger.debug("call_bigquery_agent: %s", question)

    agent_tool = AgentTool(agent=bigquery_agent)

    bigquery_agent_output = await agent_tool.run_async(
        args={"request": question},
        tool_context=tool_context,
    )
    tool_context.state["bigquery_agent_output"] = bigquery_agent_output
    return bigquery_agent_output


async def call_alloydb_agent(
    question: str,
    tool_context: ToolContext,
):
    """Tool to call alloydb database (nl2sql) agent."""
    logger.debug("call_alloydb_agent: %s", question)

    agent_tool = AgentTool(agent=alloydb_agent)

    alloydb_agent_output = await agent_tool.run_async(
        args={"request": question},
        tool_context=tool_context,
    )
    tool_context.state["alloydb_agent_output"] = alloydb_agent_output
    return alloydb_agent_output


async def call_analytics_agent(
    question: str,
    tool_context: ToolContext,
):
    """
    This tool can generate Python code to process and analyze a dataset.

    Some of the tasks it can do in Python include:
    * Creating graphics for data visualization;
    * Processing or filtering existing datasets;
    * Combining datasets to create a joined dataset for further analysis.

    The Python modules available to it are:
    * io
    * math
    * re
    * matplotlib.pyplot
    * numpy
    * pandas

    The tool DOES NOT have the ability to retrieve additional data from
    a database. Only the data already retrieved will be analyzed.

    Args:
        question (str): Natural language question or analytics request.
        tool_context (ToolContext): The tool context to use for generating the
            SQL query.

    Returns:
        Response from the analytics agent.

    """
    logger.debug("call_analytics_agent: %s", question)

    # if question == "N/A":
    #    return tool_context.state["db_agent_output"]

    bigquery_data = ""
    alloydb_data = ""

    if "bigquery_query_result" in tool_context.state:
        bigquery_data = tool_context.state["bigquery_query_result"]
    if "alloydb_query_result" in tool_context.state:
        alloydb_data = tool_context.state["alloydb_query_result"]

    question_with_data = f"""
  Question to answer: {question}

  Actual data to analyze this question is available in the following data
  tables:

  <BIGQUERY>
  {bigquery_data}
  </BIGQUERY>

  <ALLOYDB>
  {alloydb_data}
  </ALLOYDB>

  """

    agent_tool = AgentTool(agent=analytics_agent)

    analytics_agent_output = await agent_tool.run_async(
        args={"request": question_with_data},
        tool_context=tool_context,
    )
    tool_context.state["analytics_agent_output"] = analytics_agent_output
    return analytics_agent_output


async def save_memory(
    tool_context: ToolContext,
):
    """
    Manually trigger saving the current conversation facts and preferences to the Memory Bank.
    Call this tool when a user explicitly mentions a report, or when important conclusions
    or preferences have been reached that should be remembered.
    """
    import os
    import vertexai

    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    memory_uri = os.environ.get("MEMORY_SERVICE_URI", "")

    if not project or not memory_uri:
        logger.debug(
            "save_memory: skipped — GOOGLE_CLOUD_PROJECT or "
            "MEMORY_SERVICE_URI not set.",
        )
        return "Memory saving is not configured."

    if memory_uri.startswith("agentengine://"):
        agent_engine_id = memory_uri.split("://")[1]
        resource_name = (
            f"projects/{project}/locations/{location}"
            f"/reasoningEngines/{agent_engine_id}"
        )
    elif "/reasoningEngines/" in memory_uri:
        resource_name = memory_uri
    else:
        logger.warning(
            f"save_memory: unrecognised MEMORY_SERVICE_URI format: {memory_uri}",
        )
        return "Invalid memory configuration."

    session = tool_context.session
    if not session:
        return "No session available to save."

    session_id = session.id

    if not str(session_id).isdigit():
        logger.debug(
            "save_memory: skipped — session %r is not a Vertex AI session.",
            session_id,
        )
        return (
            "Local sessions (UUID) cannot be saved to the Vertex AI Memory Bank. "
            "To enable memory saving in the web interface, please run with a Vertex AI "
            "session service (e.g., use `./run_web.sh` or pass "
            "`--session_service_uri agentengine://<id>` to `adk web`)."
        )

    session_resource_name = f"{resource_name}/sessions/{session_id}"
    user_id = tool_context.user_id or os.environ.get("USER_ID", "user")
    app_name = getattr(
        tool_context._invocation_context,
        "app_name",
        None,
    ) or os.environ.get("APP_NAME", "data_science")

    vertexai.init(project=project, location=location)
    client = vertexai.Client()

    try:
        client.agent_engines.memories.generate(
            name=resource_name,
            vertex_session_source={"session": session_resource_name},
            scope={
                "app_name": app_name,
                "user_id": user_id,
            },
            config={"wait_for_completion": False},
        )
        logger.info(
            "Memory extraction triggered — "
            f"user={user_id!r}, app={app_name!r}, session={session_resource_name}",
        )
        return f"Memory extraction triggered for app '{app_name}' and user '{user_id}'."
    except Exception as e:
        logger.error("Failed to trigger memory extraction: %s", e)
        return f"Failed to trigger memory extraction: {e}"
