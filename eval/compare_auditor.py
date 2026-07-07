"""
Comparative Auditor Evaluation Script.

Runs the auditor agent with two different prompts and evaluates both outputs
side-by-side using a Gemini LLM-as-a-Judge scorecard.

Prompt A (no memory):  "Check if there are any errors for table synthetic_marketing_data?"
Prompt B (with memory): "load memories then Check if there are any errors for table synthetic_marketing_data?"

Usage:
    python eval/compare_auditor.py          (from project root)
"""

import os
import asyncio
import logging
import warnings

from werkzeug.security import safe_join

# Completely disable OpenTelemetry globally before anything else loads
os.environ["OTEL_SDK_DISABLED"] = "true"

# Suppress standard Python warnings early before imports trigger them
warnings.filterwarnings("ignore")

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
from vertexai import init  # noqa: E402
from vertexai.generative_models import GenerativeModel  # noqa: E402

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
    session = await session_service.create_session(
        app_name="data_science",
        user_id="user",
    )
    return session


async def run_agent(session_id, query, output_file=None):
    print(f"\nUser: {query}")
    print("Auditor Agent Executing...\n")

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


# ── Evaluation (inlined from evaluate_auditor.py) ──────────────────────
def evaluate_with_gemini_judge(reports: dict) -> str:
    """Evaluate the Auditor agent's reports using Gemini Flash LLM-as-a-Judge."""
    if not GCP_PROJECT_ID or not REGION:
        print(
            "Skipping evaluation: GOOGLE_CLOUD_PROJECT or GOOGLE_CLOUD_LOCATION not set.",
        )
        return ""

    init(project=GCP_PROJECT_ID, location=REGION)
    gemini_model = GenerativeModel("gemini-2.5-flash")

    base_prompt = """
    You are an expert Data Quality Assessor grading an autonomous AI Auditor Agent.

    You must evaluate the agent's data quality audit reports against a known Ground Truth of injected errors.

    Goal: Assess if the agent successfully identified the specific error classes we injected and summarize its performance.

    ---
    **Ground Truth Errors Injected:**

    **Structural Errors (4):**
    1. Missing Values (Nulls)
    2. Duplicate Rows
    3. Outliers (Extreme max values)
    4. Categorical Errors (Random alphanumeric strings)

    **Logical Errors (7):**
    1. Clicks > Impressions
    2. Conversions > Clicks
    3. Spend > 0 while Impressions = 0
    4. Video Completions > Plays
    5. Purchases without Add to Cart
    6. Landing Page Views > Clicks
    7. Negative Metric Values
    ---

    **Auditor Agent's Final Reports:**
    """

    for filename, report_text in reports.items():
        base_prompt += f"\n    [REPORT: {filename}]\n    {report_text}\n"

    base_prompt += """
    ---

    Please write a comprehensive evaluation scorecard in plain text format (do not use .md file blocks).
    Use headers, bullet points, and checkmarks (✅/❌) to indicate if the agent successfully detected each error from the Ground Truth injected list above for EACH report.

    Structure your evaluation identically to this format:

    Auditor Agent Evaluation Scorecard
    ================================

    Report: [Filename]
    ----------------
    Structural Errors: X / 4
    * [List ALL 4 structural errors and whether it found them, explaining briefly what it found or missed]

    Logical Errors: Y / 7
    * [List ALL 7 logical errors and whether it found them]

    Summary: [A brief one-paragraph summary of the agent's performance, what it did well, and what it completely missed.]

    Report: [Next Filename]
    ----------------
    ...
    """

    print(
        f"\n🧠 Using Gemini Flash Judge to formulate the scorecard for {len(reports)} reports...",
    )

    try:
        response = gemini_model.generate_content(base_prompt)
        return response.text.strip()
    except Exception as e:
        print(f"❌ Error during Gemini evaluation: {e}")
        return ""


# ── Main ────────────────────────────────────────────────────────────────
async def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # ── Prompt definitions ──────────────────────────────────────────────
    prompt_no_memory = (
        "Check if there are any errors for table synthetic_marketing_data?"
    )
    prompt_with_memory = "load memories then Check if there are any errors for table synthetic_marketing_data?"

    runs = [
        ("no_memory", prompt_no_memory),
        ("with_memory", prompt_with_memory),
    ]

    output_files = {}

    for label, prompt in runs:
        _out_str = safe_join(script_dir, f"auditor_response_{label}.txt")
        if _out_str is None:
            raise ValueError(f"Invalid label for output filename: {label!r}")
        output_filename = _out_str
        # Clear the output file at start of each run
        open(output_filename, "w", encoding="utf-8").close()

        print(f"\n{'=' * 60}")
        print(f"  RUN: {label}")
        print(f"  PROMPT: {prompt}")
        print(f"{'=' * 60}\n")

        # Create a fresh session for each run so they are independent
        session = await create_session()

        # Warmup
        await run_agent(session.id, "Hello!")

        # Actual audit prompt → save output
        await run_agent(session.id, prompt, output_file=output_filename)

        output_files[label] = output_filename

    # ── Evaluate both outputs side-by-side ──────────────────────────────
    print(f"\n{'=' * 60}")
    print("  EVALUATION: Comparing both runs")
    print(f"{'=' * 60}\n")

    reports = {}
    for label, filepath in output_files.items():
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()
        if text.strip():
            reports[f"auditor_response_{label}.txt"] = text
        else:
            print(f"⚠️  Warning: {filepath} is empty, skipping from evaluation.")

    if not reports:
        print("⚠️  No reports to evaluate. Aborting.")
        return

    evaluation_result = evaluate_with_gemini_judge(reports)

    if evaluation_result:
        _score_str = safe_join(script_dir, "comparison_scorecard.txt")
        if _score_str is None:
            raise ValueError("Invalid script_dir for scorecard path construction")
        scorecard_path = _score_str
        print(f"\n💾 Saving comparison scorecard to {scorecard_path}...")
        with open(scorecard_path, "w", encoding="utf-8") as f:
            f.write(evaluation_result)
            f.write("\n")
        print("✅ Results saved!")
        print("\n" + "=" * 60 + "\n")
        print(evaluation_result)


if __name__ == "__main__":
    asyncio.run(main())
