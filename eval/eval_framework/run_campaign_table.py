"""
Run auditor agent on campaign_table.

This script audits the campaign_table in BigQuery to assess its data quality.
Configure the table location via BQ_DATA_PROJECT_ID and BQ_DATASET_ID environment variables.

Usage:
    uv run python eval/eval_framework/run_campaign_table.py
    uv run python eval/eval_framework/run_campaign_table.py --prompt simple
    uv run python eval/eval_framework/run_campaign_table.py --memory load_memory
"""

import os
import sys
import asyncio
import argparse
from datetime import datetime, timezone

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

# Note: We implement the audit logic directly in this script
# rather than using run_single_audit which expects table_key to be in TABLES dict

# Campaign table configuration - read from environment
_project = os.getenv("BQ_DATA_PROJECT_ID", "YOUR-PROJECT-ID")
_dataset = os.getenv("BQ_DATASET_ID", "synthetic_data")
_full_table_name = f"{_project}.{_dataset}.campaign_table"

CAMPAIGN_TABLE_CONFIG = {
    "full_name": _full_table_name,
    "short_name": "campaign_table",
    "description": "Campaign performance table in synthetic_data dataset",
    "ground_truth": {
        "structural_errors": [],  # Unknown - to be discovered
        "logical_errors": [],  # Unknown - to be discovered
    },
}


def build_campaign_audit_query(
    prompt_level: str = "complex",
    memory_mode: str = "no_memory",
) -> str:
    """Build the audit query for campaign_table based on prompt level."""
    table_name = "campaign_table"

    # Memory prefix if needed
    prefix = ""
    if memory_mode == "load_memory":
        prefix = "load memories about auditing tables then "

    # Build query based on prompt level
    if prompt_level == "simple":
        base = f"Check if there are any errors for table {table_name}?"
    elif prompt_level == "medium":
        base = f"""Perform a structured data quality assessment on table {table_name}.

Check for:
1. Physical Integrity: missing values (NULLs), duplicate rows
2. Numerical Sanity: outliers, values outside logical bounds (e.g., negative metrics)
3. Categorical Validity: invalid categories or malformed values

Summarize your findings by data quality pillar and quantify the impact."""
    elif prompt_level == "complex":
        base = f"""Conduct a comprehensive forensic data quality audit on table {table_name}.

Perform the following checks:

1. **Missing Values**: Identify unexpected NULLs across all columns
2. **Duplicate Rows**: Find exact row matches and primary key violations
3. **Outliers**: Detect statistically anomalous values (extreme max/min values)
4. **Categorical Errors**: Discover invalid categories, random strings, or cardinality anomalies
5. **Logical Inconsistencies**: Test cross-column relationships and business rules:
   - Check if clicks > impressions (impossible)
   - Check if conversions > clicks (impossible for click-attributed conversions)
   - Check if spend > 0 while impressions = 0 (illogical)
   - Check if video completions > video plays (impossible)
   - Check if purchases occur without add-to-cart events (funnel violation)
   - Check if landing page views > clicks (impossible)
   - Check for negative values in performance metrics (impossible)
   - Check video completion percentage progression (25% >= 50% >= 75% >= 100%)

For each issue found, quantify the exact percentage and absolute count of affected rows. Provide forensic explanations of why each violation is logically impossible."""
    else:
        base = f"Check if there are any errors for table {table_name}?"

    return f"{prefix}{base}"


async def run_campaign_table_audit(
    prompt_level: str = "complex",
    memory_mode: str = "no_memory",
):
    """Run the auditor agent on campaign_table."""

    print("=" * 60)
    print("  CAMPAIGN TABLE AUDIT")
    print("=" * 60)
    print(f"  Table:  {CAMPAIGN_TABLE_CONFIG['short_name']}")
    print(f"  Full name: {CAMPAIGN_TABLE_CONFIG['full_name']}")
    print(f"  Prompt: {prompt_level}")
    print(f"  Memory: {memory_mode}")
    print("=" * 60)

    # Import here to use the configuration
    import warnings

    warnings.filterwarnings("ignore")

    from dotenv import load_dotenv

    load_dotenv(dotenv_path=".env")

    # Remove conflicting API keys
    if "GOOGLE_API_KEY" in os.environ:
        del os.environ["GOOGLE_API_KEY"]
    if "GEMINI_API_KEY" in os.environ:
        del os.environ["GEMINI_API_KEY"]

    import vertexai
    from google.adk.artifacts import InMemoryArtifactService
    from google.adk.memory import VertexAiMemoryBankService
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types
    from google.adk.tools.load_memory_tool import LoadMemoryTool
    from data_science.sub_agents.auditor.agent import auditor_agent
    from data_science.sub_agents.auditor.tools import call_bigquery_agent

    GCP_PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
    REGION = os.getenv("GOOGLE_CLOUD_LOCATION")

    # Set up memory service if needed
    memory_service = None
    if memory_mode == "load_memory":
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
            print("⚠️  MEMORY_SERVICE_URI not set — memory features disabled.")

    # Configure agent tools based on memory mode
    if memory_mode == "no_memory":
        auditor_agent.tools = [call_bigquery_agent]
    elif memory_mode == "load_memory":
        auditor_agent.tools = [call_bigquery_agent, LoadMemoryTool()]

    # Set up runner
    session_service = InMemorySessionService()
    artifact_service = InMemoryArtifactService()

    runner = Runner(
        app_name="data_science",
        agent=auditor_agent,
        artifact_service=artifact_service,
        session_service=session_service,
        memory_service=memory_service,
    )

    # Create session
    session = await session_service.create_session(
        app_name="data_science",
        user_id="user",
    )

    # Build query
    query = build_campaign_audit_query(prompt_level, memory_mode)

    print(f"\nQuery: {query[:150]}...")
    print(f"\n{'─'*60}")

    # Warmup
    print("Agent warming up...")
    warmup = types.Content(role="user", parts=[types.Part(text="Hello!")])
    for _ in runner.run(user_id="user", session_id=session.id, new_message=warmup):
        pass

    # Run audit
    print("\nRunning audit...\n")
    content = types.Content(role="user", parts=[types.Part(text=query)])

    response_text = ""
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
                    response_text += part.text
                elif getattr(part, "function_call", None):
                    print(f"\n[Agent requested tool: {part.function_call.name}]\n")
        elif (
            hasattr(event, "message_delta")
            and event.message_delta
            and hasattr(event.message_delta, "parts")
        ):
            for part in event.message_delta.parts:
                if getattr(part, "text", None):
                    print(part.text, end="", flush=True)
                    response_text += part.text
                elif getattr(part, "function_call", None):
                    print(f"\n[Agent requested tool: {part.function_call.name}]\n")

    print("\n\n" + "=" * 60)
    print("  AUDIT COMPLETE")
    print("=" * 60)

    # Prepare result structure
    result = {
        "table_key": "campaign_table",
        "table_name": CAMPAIGN_TABLE_CONFIG["short_name"],
        "full_table_name": CAMPAIGN_TABLE_CONFIG["full_name"],
        "prompt_level": prompt_level,
        "memory_mode": memory_mode,
        "query": query,
        "response_text": response_text,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Save results
    experiment_name = f"campaign_table_{prompt_level}_{memory_mode}"

    # Create results directory
    eval_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    results_dir = os.path.join(eval_dir, "results", experiment_name)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(results_dir, timestamp)
    os.makedirs(output_dir, exist_ok=True)

    # Save response text
    response_file = os.path.join(output_dir, f"response_{experiment_name}.txt")
    with open(response_file, "w", encoding="utf-8") as f:
        f.write(response_text)

    # Save metadata
    metadata_file = os.path.join(output_dir, "metadata.json")
    import json

    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"\n✅ Results saved to: {output_dir}")
    print(f"   - Response: {response_file}")
    print(f"   - Metadata: {metadata_file}")

    return result


async def main():
    parser = argparse.ArgumentParser(
        description="Run auditor agent on campaign_table",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--prompt",
        choices=["simple", "medium", "complex"],
        default="complex",
        help="Prompt level to use (default: complex)",
    )
    parser.add_argument(
        "--memory",
        choices=["no_memory", "load_memory"],
        default="no_memory",
        help="Memory mode to use (default: no_memory)",
    )

    args = parser.parse_args()

    await run_campaign_table_audit(
        prompt_level=args.prompt,
        memory_mode=args.memory,
    )


if __name__ == "__main__":
    asyncio.run(main())
