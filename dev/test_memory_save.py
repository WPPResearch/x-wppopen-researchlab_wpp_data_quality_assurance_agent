"""Test script to verify that the `save_memory` tool
correctly persists facts to the Vertex AI Memory Bank after a user turn.

Usage:
    uv run dev/test_memory_save.py [--query "user preferences or data quality"]

The script:
1. Creates a VertexAiSessionService session (required for Memory Bank integration).
2. Sends a message containing a data-quality issue and a user preference — both
   are custom topics configured in the Memory Bank. Also asks the agent to save this to memory.
3. The agent receives the message, invokes the `save_memory` tool, which triggers
   background memory extraction.
4. Polls the Memory Bank every 15 s (up to 8 attempts) to confirm the fact was
   persisted and indexed.
"""

import asyncio
import logging
import os
import time
import argparse

import vertexai
from dotenv import load_dotenv

# Load env variables from .env before any ADK imports
load_dotenv(dotenv_path=".env")

# Remove conflicting API keys that break Vertex AI SDK initialisation
for _key in ("GOOGLE_API_KEY", "GEMINI_API_KEY"):
    os.environ.pop(_key, None)

from google.adk.runners import Runner  # noqa: E402
from google.adk.sessions import VertexAiSessionService  # noqa: E402

from google.adk.artifacts import InMemoryArtifactService  # noqa: E402
from google.genai import types  # noqa: E402

from data_science.agent import root_agent  # noqa: E402

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _build_resource_name(project: str, location: str, memory_uri: str) -> str:
    """Return the full reasoningEngines resource name from MEMORY_SERVICE_URI."""
    if memory_uri.startswith("agentengine://"):
        agent_engine_id = memory_uri.split("://")[1]
        return (
            f"projects/{project}/locations/{location}"
            f"/reasoningEngines/{agent_engine_id}"
        )
    if "/reasoningEngines/" in memory_uri:
        return memory_uri
    raise ValueError(f"Unrecognised MEMORY_SERVICE_URI format: {memory_uri!r}")


def _agent_engine_id(memory_uri: str) -> str:
    """Extract the bare agent engine ID from MEMORY_SERVICE_URI."""
    if memory_uri.startswith("agentengine://"):
        return memory_uri.split("://")[1]
    return memory_uri.split("/")[-1]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main() -> None:
    parser = argparse.ArgumentParser(description="Test memory auto-save callback")
    parser.add_argument(
        "--query",
        type=str,
        default="data quality issues table missing column user preferences executive summary",
        help="Similarity search query used when polling the Memory Bank.",
    )
    args = parser.parse_args()

    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    memory_uri = os.environ.get("MEMORY_SERVICE_URI", "")

    if not project:
        raise RuntimeError("GOOGLE_CLOUD_PROJECT env var must be set.")
    if not memory_uri:
        raise RuntimeError("MEMORY_SERVICE_URI env var must be set.")

    engine_id = _agent_engine_id(memory_uri)
    resource_name = _build_resource_name(project, location, memory_uri)

    print(f"\n🔧 Project    : {project}")
    print(f"🔧 Location   : {location}")
    print(f"🔧 Engine ID  : {engine_id}")
    print(f"🔧 Resource   : {resource_name}\n")

    # -----------------------------------------------------------------------
    # Session service — must be VertexAiSessionService so sessions are stored
    # in the same Agent Engine that owns the Memory Bank.
    # -----------------------------------------------------------------------
    session_service = VertexAiSessionService(
        agent_engine_id=engine_id,
        project=project,
        location=location,
    )

    APP_NAME = "data_science_agent"
    USER_ID = "user"

    runner = Runner(
        app_name=APP_NAME,
        agent=root_agent,
        session_service=session_service,
        artifact_service=InMemoryArtifactService(),
    )

    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
    )
    print(f"📋 Session ID : {session.id}")

    # -----------------------------------------------------------------------
    # Craft a test message that hits BOTH custom memory topics:
    #   • data_quality_issues  — mention a concrete table/column problem
    #   • user_preferences     — mention a report formatting preference
    #
    # NOTE: The Memory Bank extracts *clean semantic facts* — it strips any
    # literal TEST-ID markers.  We therefore match on known key phrases from
    # our message instead of a verbatim token.
    # -----------------------------------------------------------------------
    # Unique marker embedded in the message so we can trace in agent logs,
    # but NOT used for fact-matching (the bank strips it).
    test_id = str(int(time.time()))

    # Key phrases we expect to appear in the extracted facts.
    QUALITY_KEYWORDS = {"revenue_q4", "tax_amount"}
    PREF_KEYWORDS = {"executive summary"}

    user_message = (
        f"Hi, I just noticed that the `revenue_q4` table is missing the "
        f"`tax_amount` column — it should be there but it's not. "
        f"Also, please always include an executive summary at the top of "
        f"any reports you generate for me. "
        f"Please explicitly save these facts using your `save_memory` tool. "
        f"[run-id:{test_id}]"  # visible in agent logs only
    )

    print(f"\n💬 User message:\n   {user_message}\n")
    content = types.Content(role="user", parts=[types.Part(text=user_message)])

    # -----------------------------------------------------------------------
    # Run the agent — after_agent_callback fires automatically once the agent
    # finishes responding, triggering background memory extraction.
    # -----------------------------------------------------------------------
    print("🤖 Running agent…")
    response_texts: list[str] = []
    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=session.id,
        new_message=content,
    ):
        if hasattr(event, "content") and event.content:
            if hasattr(event.content, "parts"):
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        response_texts.append(part.text)

    agent_response = "".join(response_texts)
    print(f"\n🤖 Agent response:\n{agent_response}\n")

    # -----------------------------------------------------------------------
    # Poll the Memory Bank — extraction runs asynchronously on Vertex AI so
    # we wait up to 2 minutes (8 × 15 s) for the fact to appear.
    # -----------------------------------------------------------------------
    print("⏳ Polling Memory Bank for the saved fact…")

    vertexai.init(project=project, location=location)
    client = vertexai.Client()

    # -----------------------------------------------------------------------
    # Poll: Memory Bank extraction runs async on Vertex AI — wait up to
    # 2 minutes (8 × 15 s) for the facts to be indexed.
    #
    # SCOPE NOTE: VertexAiSessionService stores sessions with only
    # user_id in scope (no app_name).  Adding app_name here would return
    # zero results.  Use user_id only.
    # -----------------------------------------------------------------------
    quality_found = False
    pref_found = False
    max_attempts = 8
    wait_seconds = 15

    for attempt in range(1, max_attempts + 1):
        print(
            f"   Attempt {attempt}/{max_attempts}: waiting {wait_seconds}s before querying…",
        )
        await asyncio.sleep(wait_seconds)

        try:
            results = client.agent_engines.memories.retrieve(
                name=resource_name,
                # Use only user_id — app_name is NOT stored in session scope
                # by VertexAiSessionService and would return empty results.
                scope={"user_id": USER_ID},
                similarity_search_params={"search_query": args.query},
            )

            any_result = False
            for r in results:
                any_result = True
                fact: str = r.memory.fact if hasattr(r, "memory") else str(r)
                fact_lc = fact.lower()

                # Match by key phrases, not verbatim TEST-ID (bank strips markers)
                is_quality = all(kw in fact_lc for kw in QUALITY_KEYWORDS)
                is_pref = any(kw in fact_lc for kw in PREF_KEYWORDS)

                tag = ""
                if is_quality and not quality_found:
                    quality_found = True
                    tag = " ✅ [data_quality_issues]"
                elif is_pref and not pref_found:
                    pref_found = True
                    tag = " ✅ [user_preferences]"

                print(f"   • {fact}{tag}")

            if not any_result:
                print("   (no memories returned yet)")

            if quality_found and pref_found:
                break

        except Exception as exc:  # pylint: disable=broad-except
            print(f"   ⚠️  Retrieval error on attempt {attempt}: {exc}")

    print()
    if quality_found and pref_found:
        print("🎉 Both memory topics saved successfully!")
        print("   ✅ data_quality_issues: revenue_q4 / tax_amount fact persisted")
        print("   ✅ user_preferences:   executive summary preference persisted")
    elif quality_found:
        print(
            "⚠️  Partial success: data_quality_issues saved, user_preferences NOT found.",
        )
    elif pref_found:
        print(
            "⚠️  Partial success: user_preferences saved, data_quality_issues NOT found.",
        )
    else:
        print(
            f"❌ No matching memories found after {max_attempts * wait_seconds}s.\n"
            "   Check the agent logs for 'Memory extraction triggered' to confirm "
            "the callback fired.",
        )


if __name__ == "__main__":
    asyncio.run(main())
