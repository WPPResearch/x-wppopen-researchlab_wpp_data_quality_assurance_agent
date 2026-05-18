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

"""Artifact Manager Agent definition."""

import os

from google.adk.agents import Agent
from google.adk.tools import FunctionTool
from google.adk.tools.load_artifacts_tool import load_artifacts_tool
from google.genai.types import GenerateContentConfig

from .prompts import return_instructions_artifact
from .tools import (
    list_all_artifacts,
    save_file_artifact,
    save_file_from_chat,
)

artifact_agent = Agent(
    model=os.getenv("ANALYTICS_AGENT_MODEL") or "gemini-2.5-flash",
    name="artifact_agent",
    instruction=return_instructions_artifact(),
    tools=[
        FunctionTool(save_file_artifact),
        FunctionTool(save_file_from_chat),
        FunctionTool(list_all_artifacts),
        load_artifacts_tool,
    ],
    generate_content_config=GenerateContentConfig(
        temperature=0.1,
    ),
)
