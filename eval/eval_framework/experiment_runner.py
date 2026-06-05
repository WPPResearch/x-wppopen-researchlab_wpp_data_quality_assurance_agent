"""
Core experiment runner for auditor agent evaluation.

Provides reusable functions to:
  - Set up the agent with a specific prompt level
  - Run the auditor against a table
  - Evaluate output with Gemini-as-Judge
  - Save structured results to disk

Used by all experiment scripts (run_prompt_comparison.py, etc.).
"""

import os
import json
import logging
import warnings
from datetime import datetime, timezone

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

from data_science.sub_agents.auditor.tools import call_bigquery_agent  # noqa: E402
from google.adk.tools.load_memory_tool import LoadMemoryTool  # noqa: E402


from data_science.sub_agents.auditor.agent import auditor_agent  # noqa: E402
from eval.eval_framework.experiment_configs import (  # noqa: E402
    TABLES,
    PROMPT_LEVELS,
    MEMORY_MODES,
    build_audit_query,
    get_ground_truth_prompt,
)

# Force-suppress absolutely ALL INFO and WARNING logs globally
logging.disable(logging.WARNING)

GCP_PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
REGION = os.getenv("GOOGLE_CLOUD_LOCATION")

# ── Results directory ────────────────────────────────────────────────────
EVAL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(EVAL_DIR, "results")


def _get_memory_service():
    """Initialize and return the Vertex AI memory service, or None."""
    memory_uri = os.getenv("MEMORY_SERVICE_URI", "")
    if not memory_uri or not GCP_PROJECT_ID:
        print("⚠️  MEMORY_SERVICE_URI not set — memory features disabled.")
        return None

    print("\n🔧 Setting up memory service...")
    print(f"   Memory URI: {memory_uri}")
    print(f"   GCP Project: {GCP_PROJECT_ID}")
    print(f"   Region: {REGION or 'us-central1'}")

    if "://" in memory_uri:
        agent_engine_id = memory_uri.split("://")[1]
    elif "/reasoningEngines/" in memory_uri:
        agent_engine_id = memory_uri.split("/")[-1]
    else:
        agent_engine_id = memory_uri

    vertexai.init(project=GCP_PROJECT_ID, location=REGION or "us-central1")
    svc = VertexAiMemoryBankService(
        agent_engine_id=agent_engine_id,
        project=GCP_PROJECT_ID,
        location=REGION or "us-central1",
    )
    print(f"✅ Memory service connected (engine: {agent_engine_id})")
    print("   Tools enabled: call_bigquery_agent, LoadMemoryTool\n")
    return svc


def _setup_runner(memory_mode: str = "no_memory"):
    """Create a fresh Runner with optional memory service."""
    session_service = InMemorySessionService()
    artifact_service = InMemoryArtifactService()

    memory_service = None
    if memory_mode == "load_memory":
        memory_service = _get_memory_service()

    if memory_mode == "no_memory":
        auditor_agent.tools = [call_bigquery_agent]
    elif memory_mode == "load_memory":
        auditor_agent.tools = [call_bigquery_agent, LoadMemoryTool()]

    runner = Runner(
        app_name="data_science",
        agent=auditor_agent,
        artifact_service=artifact_service,
        session_service=session_service,
        memory_service=memory_service,
    )
    return runner, session_service


async def run_single_audit(
    table_key: str,
    prompt_level: str = "complex",
    memory_mode: str = "no_memory",
) -> dict:
    """
    Run a single auditor experiment and return structured results.

    Returns:
        dict with keys: table_key, prompt_level, memory_mode,
                        query, response_text, timestamp
    """
    runner, session_service = _setup_runner(memory_mode)

    session = await session_service.create_session(
        app_name="data_science",
        user_id="user",
    )

    query = build_audit_query(table_key, memory_mode, prompt_level)
    table_info = TABLES[table_key]

    print(f"\n{'─' * 60}")
    print(f"  Table:  {table_info['short_name']}")
    print(f"  Prompt: {PROMPT_LEVELS[prompt_level]['label']}")
    print(f"  Memory: {MEMORY_MODES[memory_mode]['label']}")
    print(f"  Query:  {query[:100]}...")
    print(f"{'─' * 60}\n")

    # Warmup
    print("Agent warming up...")
    warmup = types.Content(role="user", parts=[types.Part(text="Hello!")])
    for _ in runner.run(user_id="user", session_id=session.id, new_message=warmup):
        pass

    # Main audit query
    print("Auditor Agent Executing...\n")
    content = types.Content(role="user", parts=[types.Part(text=query)])
    response_parts = []
    memory_loaded = False

    for event in runner.run(
        user_id="user",
        session_id=session.id,
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
                    response_parts.append(part.text)
                elif getattr(part, "function_call", None):
                    tool_name = part.function_call.name
                    print(f"\n[Agent requested tool: {tool_name}]")
                    if tool_name == "load_memory":
                        print("  🧠 Loading memories from memory bank...")
                        memory_loaded = True
                    print()
                elif getattr(part, "function_response", None):
                    if part.function_response.name == "load_memory":
                        response_data = part.function_response.response
                        print("  ✅ Memory loaded successfully!")
                        if hasattr(response_data, "get"):
                            memories = response_data.get("memories", [])
                            print(f"  📚 Retrieved {len(memories)} memory items")
                            if memories:
                                print("  Memory preview:")
                                for i, mem in enumerate(memories[:3], 1):
                                    preview = str(mem)[:150]
                                    print(f"    {i}. {preview}...")
        elif (
            hasattr(event, "message_delta")
            and event.message_delta
            and hasattr(event.message_delta, "parts")
        ):
            for part in event.message_delta.parts:
                if getattr(part, "text", None):
                    print(part.text, end="", flush=True)
                    response_parts.append(part.text)
                elif getattr(part, "function_call", None):
                    tool_name = part.function_call.name
                    print(f"\n[Agent requested tool: {tool_name}]")
                    if tool_name == "load_memory":
                        print("  🧠 Loading memories from memory bank...")
                        memory_loaded = True
                    print()
                elif getattr(part, "function_response", None):
                    if part.function_response.name == "load_memory":
                        response_data = part.function_response.response
                        print("  ✅ Memory loaded successfully!")
                        if hasattr(response_data, "get"):
                            memories = response_data.get("memories", [])
                            print(f"  📚 Retrieved {len(memories)} memory items")
                            if memories:
                                print("  Memory preview:")
                                for i, mem in enumerate(memories[:3], 1):
                                    preview = str(mem)[:150]
                                    print(f"    {i}. {preview}...")

    response_text = "".join(response_parts)
    print("\n\n✅ Execution finished.")

    # Verify memory loading if expected
    if memory_mode == "load_memory":
        if memory_loaded:
            print("✅ Memory was successfully loaded during execution")
        else:
            print("⚠️  WARNING: Memory mode was 'load_memory' but no memory was loaded!")

    return {
        "table_key": table_key,
        "table_name": table_info["short_name"],
        "prompt_level": prompt_level,
        "memory_mode": memory_mode,
        "query": query,
        "response_text": response_text,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ── Gemini-as-Judge Evaluation ──────────────────────────────────────────
def evaluate_with_gemini_judge(
    results: list[dict],
    experiment_name: str = "experiment",
) -> str:
    """
    Evaluate one or more audit results using Gemini Flash LLM-as-a-Judge.

    Args:
        results: list of dicts from run_single_audit()
        experiment_name: label for the experiment

    Returns:
        Evaluation scorecard as plain text.
    """
    if not GCP_PROJECT_ID or not REGION:
        print("Skipping evaluation: GCP env vars not set.")
        return ""

    init(project=GCP_PROJECT_ID, location=REGION)
    gemini_model = GenerativeModel("gemini-2.5-flash")

    prompt = f"""
    You are an expert Data Quality Assessor grading an autonomous AI Auditor Agent.
    You must evaluate the agent's data quality audit reports against a known Ground Truth
    of injected errors.

    Experiment: {experiment_name}
    """

    for r in results:
        table_key = r["table_key"]
        gt_block = get_ground_truth_prompt(table_key)

        label = f"{r['table_name']} | prompt={r['prompt_level']} | memory={r['memory_mode']}"

        prompt += f"""
    ---
    **[REPORT: {label}]**

    **Ground Truth Errors Injected:**
{gt_block}

    **Auditor Agent's Report:**
    {r["response_text"]}
    """

    n_structural = max(
        len(TABLES[r["table_key"]]["ground_truth"].get("structural_errors", []))
        for r in results
    )
    n_logical = max(
        len(TABLES[r["table_key"]]["ground_truth"].get("logical_errors", []))
        for r in results
    )

    prompt += f"""
    ---

    Please write a comprehensive evaluation scorecard in plain text format.
    Use headers, bullet points, and checkmarks (✅/❌) to indicate if the agent
    successfully detected each error from the Ground Truth list for EACH report.

    Structure your evaluation identically to this format:

    Auditor Agent Evaluation Scorecard — {experiment_name}
    ================================

    Report: [Label]
    ----------------
    Structural Errors: X / {n_structural}
    * [List ALL structural errors and whether it found them]

    Logical Errors: Y / {n_logical}
    * [List ALL logical errors and whether it found them]

    Summary: [Brief paragraph on the agent's performance]

    ---
    OVERALL COMPARISON: [Compare all reports and highlight key differences
    in detection rates across the experimental conditions.]
    """

    print(
        f"\n🧠 Using Gemini Flash Judge for {len(results)} reports ({experiment_name})...",
    )

    try:
        response = gemini_model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"❌ Error during Gemini evaluation: {e}")
        return ""


# ── Save results ────────────────────────────────────────────────────────
def save_experiment_results(
    experiment_name: str,
    results: list[dict],
    scorecard: str,
) -> str:
    """
    Save experiment results and scorecard to disk.

    Returns:
        Path to the experiment output directory.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    experiment_dir = os.path.join(RESULTS_DIR, experiment_name, timestamp)

    from pathlib import Path

    def validate_path(path_str: str) -> Path:
        p = Path(path_str).resolve()
        safe_bases = [
            Path.cwd().resolve(),
            Path.home().resolve(),
            Path("/tmp").resolve(),
        ]
        if not any(p.is_relative_to(base) for base in safe_bases):
            raise ValueError(f"Path traversal detected: {path_str}")
        return p

    validated_experiment_dir = validate_path(experiment_dir)
    os.makedirs(validated_experiment_dir, exist_ok=True)

    # Save each audit response
    for i, r in enumerate(results):
        label = f"{r['table_key']}_{r['prompt_level']}_{r['memory_mode']}"
        response_file = os.path.join(
            str(validated_experiment_dir),
            f"response_{label}.txt",
        )
        validated_response_file = validate_path(response_file)
        with open(validated_response_file, "w", encoding="utf-8") as f:
            f.write(r["response_text"])

    # Save metadata
    metadata = {
        "experiment": experiment_name,
        "timestamp": timestamp,
        "runs": [{k: v for k, v in r.items() if k != "response_text"} for r in results],
    }
    metadata_file = os.path.join(str(validated_experiment_dir), "metadata.json")
    validated_metadata_file = validate_path(metadata_file)
    with open(validated_metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    # Save scorecard
    if scorecard:
        scorecard_file = os.path.join(str(validated_experiment_dir), "scorecard.txt")
        validated_scorecard_file = validate_path(scorecard_file)
        with open(validated_scorecard_file, "w", encoding="utf-8") as f:
            f.write(scorecard)
            f.write("\n")

    print(f"\n💾 Results saved to: {validated_experiment_dir}")
    return str(validated_experiment_dir)
