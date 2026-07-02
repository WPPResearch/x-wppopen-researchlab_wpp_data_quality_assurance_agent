"""Test script to verify artifact access in reports.

This script:
1. Pre-populates a session with a chart artifact
2. Runs the report agent asking it to include the chart
3. Verifies the PDF includes the embedded image
"""

import asyncio
import io
import os
import sys

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
from google.genai.types import Blob, Part  # noqa: E402

from data_science.sub_agents.report.agent import report_agent  # noqa: E402


def generate_sample_chart() -> bytes:
    """Generate a sample matplotlib chart and return as PNG bytes."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    months = ["Jan", "Feb", "Mar", "Apr", "May"]
    sales = [100, 150, 200, 180, 250]
    costs = [80, 100, 120, 110, 140]

    plt.figure(figsize=(10, 6))
    plt.plot(months, sales, marker="o", label="Sales", linewidth=2)
    plt.plot(months, costs, marker="s", label="Costs", linewidth=2)
    plt.title("Sales vs Costs Over Time")
    plt.xlabel("Month")
    plt.ylabel("Amount ($)")
    plt.legend()
    plt.grid(True, alpha=0.3)

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=100, bbox_inches="tight")
    plt.close()
    buf.seek(0)
    return buf.getvalue()


async def main():
    print("=" * 60)
    print("Testing Report Agent with Session Artifacts")
    print("=" * 60)

    # Initialize services
    session_service = InMemorySessionService()
    artifact_service = InMemoryArtifactService()

    runner = Runner(
        app_name="DataAgent",
        agent=report_agent,
        artifact_service=artifact_service,
        session_service=session_service,
    )

    # Create session
    session = await session_service.create_session(
        app_name="DataAgent",
        user_id="user",
    )

    # Pre-populate session with a chart artifact (simulating previous analysis)
    print("\n1. Pre-populating session with chart artifact...")
    chart_bytes = generate_sample_chart()
    chart_artifact = Part(inline_data=Blob(data=chart_bytes, mime_type="image/png"))

    await artifact_service.save_artifact(
        app_name="DataAgent",
        user_id="user",
        session_id=session.id,
        filename="sales_chart.png",
        artifact=chart_artifact,
    )
    print(f"   ✓ Saved 'sales_chart.png' ({len(chart_bytes)} bytes)")

    # Also save a second artifact
    await artifact_service.save_artifact(
        app_name="DataAgent",
        user_id="user",
        session_id=session.id,
        filename="costs_analysis.png",
        artifact=chart_artifact,  # Same chart for demo
    )
    print("   ✓ Saved 'costs_analysis.png'")

    # Query asking to use existing artifacts
    query = """
    Create a PDF report about sales performance.

    I already have some charts from my previous analysis saved in this session.
    Please check what artifacts are available and include any relevant charts in the report.

    Also include this data in a table:
    - Month: Jan, Feb, Mar, Apr, May
    - Sales: 100, 150, 200, 180, 250
    - Costs: 80, 100, 120, 110, 140

    Save as 'report_with_artifacts.pdf'.
    """

    print("\n2. Running agent with query about existing artifacts...")
    print(f"   Query: {query[:80]}...")

    content = types.Content(role="user", parts=[types.Part(text=query)])

    for event in runner.run(
        user_id="user",
        session_id=session.id,
        new_message=content,
    ):
        # Show key events
        if hasattr(event, "actions") and event.actions:
            if event.actions.artifact_delta:
                print(f"   → Artifact created: {event.actions.artifact_delta}")
        if hasattr(event, "content") and event.content:
            for part in event.content.parts:
                if hasattr(part, "function_call") and part.function_call:
                    print(f"   → Tool called: {part.function_call.name}")
                if hasattr(part, "function_response") and part.function_response:
                    resp = part.function_response.response
                    if isinstance(resp, dict) and resp.get("status"):
                        print(
                            f"   → Response: {resp.get('message', resp.get('status'))}",
                        )
                if hasattr(part, "text") and part.text:
                    # Show final model response
                    text = (
                        part.text[:200] + "..." if len(part.text) > 200 else part.text
                    )
                    print(f"   → Model said: {text}")
        if hasattr(event, "finish_reason") and event.finish_reason:
            print(f"   → Finish reason: {event.finish_reason}")

    print("\n3. Retrieving generated report...")

    # Try to load the report
    report_artifact = await artifact_service.load_artifact(
        app_name="DataAgent",
        user_id="user",
        session_id=session.id,
        filename="report_with_artifacts.pdf",
    )

    if report_artifact:
        content_bytes = report_artifact.inline_data.data
        with open("report_with_artifacts.pdf", "wb") as f:
            f.write(content_bytes)
        print(
            f"   ✓ SUCCESS: report_with_artifacts.pdf saved ({len(content_bytes)} bytes)",
        )
    else:
        # Try the default name
        report_artifact = await artifact_service.load_artifact(
            app_name="DataAgent",
            user_id="user",
            session_id=session.id,
            filename="report.pdf",
        )
        if report_artifact:
            content_bytes = report_artifact.inline_data.data
            with open("report_with_artifacts.pdf", "wb") as f:
                f.write(content_bytes)
            print(
                f"   ✓ SUCCESS: report.pdf saved as report_with_artifacts.pdf ({len(content_bytes)} bytes)",
            )
        else:
            print("   ✗ FAILURE: Report artifact not found")

    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
