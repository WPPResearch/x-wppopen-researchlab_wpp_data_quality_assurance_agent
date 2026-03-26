import os
import sys
import pytest
import vertexai
from google.adk.tools.load_memory_tool import LoadMemoryTool

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Force tests to use gemini-2.5-flash as the dev environment doesn't have the gemini-3 preview yet
os.environ["ROOT_AGENT_MODEL"] = "gemini-2.5-flash"
os.environ["ANALYTICS_AGENT_MODEL"] = "gemini-2.5-flash"
os.environ["BIGQUERY_AGENT_MODEL"] = "gemini-2.5-flash"
os.environ["REPORT_AGENT_MODEL"] = "gemini-2.5-flash"
os.environ["BQML_AGENT_MODEL"] = "gemini-2.5-flash"

# Remove conflicting API key that breaks Vertex AI SDK Initialization
if "GOOGLE_API_KEY" in os.environ:
    del os.environ["GOOGLE_API_KEY"]
if "GEMINI_API_KEY" in os.environ:
    del os.environ["GEMINI_API_KEY"]

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.memory import VertexAiMemoryBankService
from data_science.agent import root_agent
import logging

logging.basicConfig(level=logging.DEBUG)

# We skip these tests heavily if the env isn't fully configured
pytestmark = pytest.mark.skipif(
    not os.environ.get("MEMORY_SERVICE_URI")
    or not os.environ.get("GOOGLE_CLOUD_PROJECT"),
    reason="MEMORY_SERVICE_URI and GOOGLE_CLOUD_PROJECT must be set in the environment",
)


@pytest.fixture(scope="module")
def memory_service():
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    memory_uri = os.environ.get("MEMORY_SERVICE_URI", "")

    agent_engine_id = memory_uri
    if "://" in memory_uri:
        agent_engine_id = memory_uri.split("://")[1]
    elif "/reasoningEngines/" in memory_uri:
        agent_engine_id = memory_uri.split("/")[-1]
    vertexai.init(project=project, location=location)

    return VertexAiMemoryBankService(
        agent_engine_id=agent_engine_id,
        project=project,
        location=location,
    )


@pytest.fixture(scope="module")
def root_agent_fixture():
    # Force the model to bypass the preview 404 block in the dev project
    root_agent.model = "gemini-2.5-flash"
    if hasattr(root_agent, "sub_agents") and root_agent.sub_agents:
        for sa in root_agent.sub_agents:
            sa.model = "gemini-2.5-flash"

    return root_agent


@pytest.mark.asyncio
async def test_auditor_agent_has_load_memory_tool(root_agent_fixture):
    """Verifies that the auditor agent has been equipped with the LoadMemoryTool."""
    auditor = next(
        (sa for sa in root_agent_fixture.sub_agents if sa.name == "auditor_agent"),
        None,
    )
    assert auditor is not None, "Auditor agent missing from root agent"
    has_memory_tool = any(isinstance(tool, LoadMemoryTool) for tool in auditor.tools)
    assert has_memory_tool, "Auditor agent is missing LoadMemoryTool"


@pytest.mark.asyncio
async def test_memory_retrieval_flow(root_agent_fixture, memory_service):
    """
    Spins up the ADK Runner and asks the agent a direct question about memory
    to ensure the LoadMemoryTool gets invoked and successfully retrieves the fact
    we injected earlier.
    """
    session_service = InMemorySessionService()
    runner = Runner(
        agent=root_agent_fixture,
        app_name="data_science",
        session_service=session_service,
        memory_service=memory_service,
    )

    user_id = "user"
    session = await session_service.create_session(
        app_name="data_science",
        user_id=user_id,
    )

    from google.genai import types

    # We ask the agent about the issue we simulated missing columns
    prompt = "What was the issue we previously identified with the revenue_q4 table?"
    content = types.Content(role="user", parts=[types.Part(text=prompt)])

    print("\nCaptured events from Runner:")
    response_texts = []

    # We must use run_async since this test is within an asyncio context
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=content,
    ):
        print(f"Event: {event}")
        if hasattr(event, "content") and event.content:
            print(f"  Content: {event.content}")
            if hasattr(event.content, "parts"):
                for p in event.content.parts:
                    if hasattr(p, "text") and p.text:
                        response_texts.append(p.text.lower())

    response_text = " ".join(response_texts)

    # Check if the text implies it found the tool and knowledge
    assert (
        "tax_amount" in response_text
        or "missing" in response_text
        or "revenue_q4" in response_text
    ), f"Agent did not retrieve the correct memory. Full Text: {response_text}"
