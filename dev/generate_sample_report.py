import asyncio
import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

load_dotenv()

from google.adk.runners import Runner  # noqa: E402
from google.adk.sessions import InMemorySessionService  # noqa: E402
from google.adk.artifacts import InMemoryArtifactService  # noqa: E402
from google.genai import types  # noqa: E402

from data_science.sub_agents.report.agent import report_agent  # noqa: E402


async def main():
    print("Initializing Report Agent (Full Flow)...")
    session_service = InMemorySessionService()
    artifact_service = InMemoryArtifactService()

    runner = Runner(
        app_name="DataAgent",
        agent=report_agent,
        artifact_service=artifact_service,
        session_service=session_service,
    )

    session = await session_service.create_session(
        app_name="DataAgent",
        user_id="user",
    )

    query = """
    Generate a comprehensive PDF report analyzing the sales performance.

    Data:
    - Month: Jan, Feb, Mar, Apr, May
    - Sales: 100, 150, 200, 180, 250
    - Costs: 80, 100, 120, 110, 140

    Please include:
    1. A table showing the data with a calculated 'Profit' column.
    2. Key statistics (min, max, mean).
    3. A clear narrative summary.

    Save the final report as 'report.pdf' using the tool.
    """

    print(f"Sending query: {query}")

    content = types.Content(role="user", parts=[types.Part(text=query)])

    print("Running agent...")

    for event in runner.run(
        user_id="user",
        session_id=session.id,
        new_message=content,
    ):
        # Check for artifact delta
        if hasattr(event, "actions") and event.actions and event.actions.artifact_delta:
            print(f"Artifact created: {event.actions.artifact_delta}")

    print("Agent execution finished.")

    # Retrieve artifact from artifact service
    print("\nRetrieving artifact from service...")
    try:
        artifact = await artifact_service.load_artifact(
            app_name="DataAgent",
            user_id="user",
            session_id=session.id,
            filename="report.pdf",
        )
        if artifact:
            # Write the artifact to disk
            content_bytes = artifact.inline_data.data
            with open("report.pdf", "wb") as f:
                f.write(content_bytes)
            print(f"SUCCESS: report.pdf saved to disk ({len(content_bytes)} bytes)")
        else:
            print("FAILURE: Artifact not found in service")
    except Exception as e:
        print(f"Error retrieving artifact: {e}")


if __name__ == "__main__":
    asyncio.run(main())
