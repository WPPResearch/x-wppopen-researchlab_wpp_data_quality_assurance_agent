import os
import asyncio
import logging
import warnings

# Completely disable OpenTelemetry globally before anything else loads
os.environ["OTEL_SDK_DISABLED"] = "true"

# Suppress standard Python warnings early before imports trigger them
warnings.filterwarnings("ignore")

# Need to set these before loading the models
from dotenv import load_dotenv  # noqa: E402

load_dotenv(dotenv_path=".env")

# Remove conflicting API keys that break Vertex AI SDK initialization
if "GOOGLE_API_KEY" in os.environ:
    del os.environ["GOOGLE_API_KEY"]
if "GEMINI_API_KEY" in os.environ:
    del os.environ["GEMINI_API_KEY"]

import vertexai  # noqa: E402
from google.adk.artifacts import InMemoryArtifactService  # noqa: E402
from google.adk.memory import VertexAiMemoryBankService  # noqa: E402
from google.adk.runners import Runner  # noqa: E402
from google.adk.sessions import InMemorySessionService  # noqa: E402
from google.genai import types  # noqa: E402

from data_science.sub_agents.auditor.agent import auditor_agent  # noqa: E402

# Force-suppress absolutely ALL INFO and WARNING logs globally
logging.disable(logging.WARNING)

GCP_PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
REGION = os.getenv("GOOGLE_CLOUD_LOCATION")

# ── Memory service setup ────────────────────────────────────────────────
memory_service = None
memory_uri = os.getenv("MEMORY_SERVICE_URI", "")
if memory_uri and GCP_PROJECT_ID:
    if "://" in memory_uri:
        agent_engine_id = memory_uri.split("://")[1]
    elif "/reasoningEngines/" in memory_uri:
        agent_engine_id = memory_uri.split("/")[-1]
    else:
        agent_engine_id = memory_uri

    vertexai.init(project=GCP_PROJECT_ID, location=REGION or "us-central1")
    memory_service = VertexAiMemoryBankService(
        agent_engine_id=agent_engine_id,
        project=GCP_PROJECT_ID,
        location=REGION or "us-central1",
    )
    print(f"✅ Memory service connected (engine: {agent_engine_id})")
else:
    print("⚠️  MEMORY_SERVICE_URI not set — LoadMemoryTool will not work.")

# ── Agent runner setup ──────────────────────────────────────────────────
session_service = InMemorySessionService()
artifact_service = InMemoryArtifactService()
runner = Runner(
    app_name="data_science",
    agent=auditor_agent,
    artifact_service=artifact_service,
    session_service=session_service,
    memory_service=memory_service,
)


async def create_session():
    print("Setting up services...")
    session = await session_service.create_session(
        app_name="data_science",
        user_id="user",
    )
    return session


async def run_agent(session_id, query, output_file=None):
    print(f"\nUser: {query}")
    print("Auditor Agent Executing...\n")

    # Optionally open file for appending transcript logs
    f = open(output_file, "a", encoding="utf-8") if output_file else None

    content = types.Content(role="user", parts=[types.Part(text=query)])

    for event in runner.run(
        user_id="user",
        session_id=session_id,
        new_message=content,
    ):
        if (
            hasattr(event, "content")
            and event.content
            and hasattr(event.content, "parts")
        ):
            for part in event.content.parts:
                if getattr(part, "text", None):
                    print(part.text, end="", flush=True)
                    if f:
                        f.write(part.text)
                elif getattr(part, "function_call", None):
                    msg = f"\n[Agent requested tool: {part.function_call.name}]\n"
                    print(msg)
        elif (
            hasattr(event, "message_delta")
            and event.message_delta
            and hasattr(event.message_delta, "parts")
        ):
            for part in event.message_delta.parts:
                if getattr(part, "text", None):
                    print(part.text, end="", flush=True)
                    if f:
                        f.write(part.text)
                elif getattr(part, "function_call", None):
                    msg = f"\n[Agent requested tool: {part.function_call.name}]\n"
                    print(msg)

    print("\n\nExecution finished.")
    if f:
        f.close()


async def main():
    session = await create_session()

    # Save the file alongside this script in the eval/ folder
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_filename = os.path.join(script_dir, "audit_reports/auditor_response.txt")

    # Clear file entirely at start of new run if it exists
    open(
        output_filename,
        "w",
        encoding="utf-8",
    ).close()

    # Test 3 different user prompts
    print("\n" + "=" * 60)
    print("  PROMPT 1: hi")
    print("=" * 60)
    await run_agent(session.id, "hi", output_file=output_filename)

    print("\n" + "=" * 60)
    print("  PROMPT 2: what tables do you have?")
    print("=" * 60)
    await run_agent(session.id, "what tables do you have?", output_file=output_filename)

    print("\n" + "=" * 60)
    print(
        "  PROMPT 3: transfer to auditor agent, load all table memories with the auditor agent",
    )
    print("=" * 60)
    await run_agent(
        session.id,
        "transfer to auditor agent, load all table memories with the auditor agent",
        output_file=output_filename,
    )

    print("\n" + "=" * 60)
    print("  PROMPT 4: audit table our_training_dataset_sample_anonymized_batch_1")
    print("=" * 60)
    await run_agent(
        session.id,
        "audit table our_training_dataset_sample_anonymized_batch_1",
        output_file=output_filename,
    )


if __name__ == "__main__":
    asyncio.run(main())
