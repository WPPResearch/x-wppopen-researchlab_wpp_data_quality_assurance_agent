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

"""Test cases for the report agent."""

import os
import sys
import unittest

import pytest

# Load env vars BEFORE importing data_science modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from dotenv import load_dotenv

load_dotenv()
os.environ.setdefault("BQ_DATASET_ID", "dummy")
os.environ.setdefault("BQ_DATA_PROJECT_ID", "dummy")

# Now safe to import data_science modules
from google.adk.artifacts import InMemoryArtifactService  # noqa: E402
from google.adk.runners import Runner  # noqa: E402
from google.adk.sessions import InMemorySessionService  # noqa: E402
from google.genai import types  # noqa: E402

from data_science.sub_agents.report.agent import report_agent  # noqa: E402


class TestReportAgent(unittest.IsolatedAsyncioTestCase):
    """Test cases for the report agent."""

    async def asyncSetUp(self):
        """Set up for test methods."""
        super().setUp()
        self.session_service = InMemorySessionService()
        self.artifact_service = InMemoryArtifactService()
        self.session = await self.session_service.create_session(
            app_name="DataAgent",
            user_id="test_user",
        )
        self.user_id = "test_user"
        self.session_id = self.session.id

    def _run_agent(self, agent, query):
        """Helper method to run an agent and get the final response."""
        runner = Runner(
            app_name="DataAgent",
            agent=agent,
            artifact_service=self.artifact_service,
            session_service=self.session_service,
        )
        content = types.Content(role="user", parts=[types.Part(text=query)])

        artifact_created = None
        for event in runner.run(
            user_id=self.user_id,
            session_id=self.session_id,
            new_message=content,
        ):
            # Check for artifact creation
            if (
                hasattr(event, "actions")
                and event.actions
                and event.actions.artifact_delta
            ):
                artifact_created = event.actions.artifact_delta

        return artifact_created

    @pytest.mark.report_agent
    async def test_report_agent_generates_pdf(self):
        """Test calling the report agent to generate a PDF report."""
        query = """
        Generate a PDF report analyzing this sales data.

        Data:
        - Country: USA, UK, Canada
        - Sales: 100, 80, 60

        Save as 'test_report.pdf'.
        """
        artifact = self._run_agent(report_agent, query)
        print(f"Artifact created: {artifact}")

        # Check that an artifact was created
        self.assertIsNotNone(artifact, "No artifact was created")
        self.assertIn(
            "test_report.pdf",
            str(artifact) if artifact else "",
            "Expected PDF report was not created",
        )

    @pytest.mark.report_agent
    async def test_report_agent_markdown_format(self):
        """Test that the report agent can generate a markdown report."""
        query = """
        Generate a simple report with this data as a markdown file.

        Data:
        - Product: A, B, C
        - Revenue: 500, 300, 200

        Save as 'test_report.md'.
        """
        artifact = self._run_agent(report_agent, query)
        print(f"Artifact created: {artifact}")

        # Check that an artifact was created
        self.assertIsNotNone(artifact, "No artifact was created")
        self.assertIn(
            "test_report.md",
            str(artifact) if artifact else "",
            "Expected markdown report was not created",
        )
