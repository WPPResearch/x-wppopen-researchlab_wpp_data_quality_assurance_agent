"""Quick smoke test: run the analytics agent and ask it to generate a plot.

Usage:
    uv run python dev/test_analytics_plot.py

Any images produced by code execution are saved to dev/output/analytics_plot_*.png
and printed to stdout.
"""

import asyncio
import base64
import os
import sys

import dotenv

dotenv.load_dotenv(override=True)

# Remove conflicting API keys that break Vertex AI SDK init
for _key in ("GOOGLE_API_KEY", "GEMINI_API_KEY"):
    os.environ.pop(_key, None)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.adk.artifacts import InMemoryArtifactService  # noqa: E402
from google.adk.runners import Runner  # noqa: E402
from google.adk.sessions import InMemorySessionService  # noqa: E402
from google.genai import types  # noqa: E402

from data_science.sub_agents.analytics.agent import analytics_agent  # noqa: E402

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

QUERY = (
    "Generate a simple bar chart showing five fictional product categories "
    "(A, B, C, D, E) with sales values (120, 85, 200, 60, 150). "
    "Use matplotlib, save as a PNG, and show it."
)


async def main():
    session_service = InMemorySessionService()
    artifact_service = InMemoryArtifactService()

    session = await session_service.create_session(
        app_name="test_analytics",
        user_id="dev",
    )

    runner = Runner(
        app_name="test_analytics",
        agent=analytics_agent,
        artifact_service=artifact_service,
        session_service=session_service,
    )

    content = types.Content(role="user", parts=[types.Part(text=QUERY)])

    print(f"Query: {QUERY}\n{'=' * 60}")

    image_count = 0
    async for event in runner.run_async(
        user_id="dev",
        session_id=session.id,
        new_message=content,
    ):
        if not event.content or not event.content.parts:
            continue

        for part in event.content.parts:
            if part.text:
                print(part.text, end="", flush=True)
            elif part.inline_data and part.inline_data.mime_type.startswith("image/"):
                ext = part.inline_data.mime_type.split("/")[-1]
                path = os.path.join(OUTPUT_DIR, f"analytics_plot_{image_count}.{ext}")
                with open(path, "wb") as f:
                    f.write(base64.b64decode(part.inline_data.data))
                print(f"\n[Image saved: {path}]")
                image_count += 1
            elif part.executable_code:
                print(f"\n[Code]\n{part.executable_code.code}\n")
            elif part.code_execution_result:
                outcome = part.code_execution_result.outcome
                output = part.code_execution_result.output
                print(f"[Execution: {outcome}] {output}")

    # Also pull any images saved as artifacts by the ADK artifact service
    try:
        artifact_names = await artifact_service.list_artifact_keys(
            app_name="test_analytics",
            user_id="dev",
            session_id=session.id,
        )
        for name in artifact_names:
            artifact = await artifact_service.load_artifact(
                app_name="test_analytics",
                user_id="dev",
                session_id=session.id,
                filename=name,
            )
            if (
                artifact
                and artifact.inline_data
                and artifact.inline_data.mime_type.startswith("image/")
            ):
                ext = artifact.inline_data.mime_type.split("/")[-1]
                path = os.path.join(OUTPUT_DIR, f"analytics_plot_{image_count}.{ext}")
                with open(path, "wb") as f:
                    data = artifact.inline_data.data
                    f.write(data if isinstance(data, bytes) else base64.b64decode(data))
                print(f"[Artifact image saved: {path}]")
                image_count += 1
    except Exception as e:
        print(f"[Could not retrieve artifacts: {e}]")

    print(f"\n{'=' * 60}")
    print(f"Done. {image_count} image(s) saved to {OUTPUT_DIR}/")


if __name__ == "__main__":
    asyncio.run(main())
