"""
Inspect memories stored in the Vertex AI memory bank.

This script queries the memory bank for specific topics and displays what's stored.

Usage:
    uv run python eval/eval_framework/inspect_memories.py
    uv run python eval/eval_framework/inspect_memories.py --query "data quality"
"""

import os
import sys
import asyncio
import argparse

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")

# Remove conflicting API keys
if "GOOGLE_API_KEY" in os.environ:
    del os.environ["GOOGLE_API_KEY"]
if "GEMINI_API_KEY" in os.environ:
    del os.environ["GEMINI_API_KEY"]

import vertexai  # noqa: E402
from google.adk.memory import VertexAiMemoryBankService  # noqa: E402

GCP_PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
REGION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
MEMORY_URI = os.getenv("MEMORY_SERVICE_URI", "")


async def inspect_memories(query: str = "table errors"):
    """Query the memory bank and display results."""

    print("=" * 80)
    print("  MEMORY BANK INSPECTION")
    print("=" * 80)
    print(f"  Query: '{query}'")
    print(f"  Project: {GCP_PROJECT_ID}")
    print(f"  Region: {REGION}")
    print("=" * 80)
    print()

    # Validate environment
    if not MEMORY_URI or not GCP_PROJECT_ID:
        print(
            "❌ Error: MEMORY_SERVICE_URI and GOOGLE_CLOUD_PROJECT must be set in .env",
        )
        return

    # Parse memory URI
    if "://" in MEMORY_URI:
        agent_engine_id = MEMORY_URI.split("://")[1]
    elif "/reasoningEngines/" in MEMORY_URI:
        agent_engine_id = MEMORY_URI.split("/")[-1]
    else:
        agent_engine_id = MEMORY_URI

    print("🔧 Connecting to memory service...")
    print(f"   Memory URI: {MEMORY_URI}")
    print(f"   Engine ID: {agent_engine_id}")
    print()

    # Initialize Vertex AI
    vertexai.init(project=GCP_PROJECT_ID, location=REGION)

    # Connect to memory service
    memory_service = VertexAiMemoryBankService(
        agent_engine_id=agent_engine_id,
        project=GCP_PROJECT_ID,
        location=REGION,
    )

    print("✅ Connected to memory service")
    print()

    # Search for memories
    print(f"🔍 Searching for memories matching: '{query}'...")
    print()

    try:
        # Search memories using the correct API
        # The memory service searches by app_name and user_id
        search_result = await memory_service.search_memory(
            app_name="data_science",
            user_id="user",
            query=query,
        )

        memories = search_result.memories

        print("─" * 80)
        print(f"  RESULTS: Found {len(memories)} memories")
        print("─" * 80)
        print()

        if len(memories) == 0:
            print("⚠️  No memories found matching this query.")
            print()
            print("Possible reasons:")
            print("  1. The memory bank is empty")
            print("  2. No memories match the search query")
            print("  3. Memories are stored under a different user/session")
            print()
            print("To populate memories, you can:")
            print("  - Run audits with memory saving enabled")
            print("  - Use the save_memory tool during agent execution")
            print("  - Manually store memories via the ADK API")
        else:
            for i, memory in enumerate(memories, 1):
                print(f"{'=' * 80}")
                print(f"  MEMORY #{i}")
                print(f"{'=' * 80}")
                print()

                # Display memory attributes
                if hasattr(memory, "text"):
                    print(f"Text: {memory.text}")
                    print()

                if hasattr(memory, "metadata"):
                    print(f"Metadata: {memory.metadata}")
                    print()

                if hasattr(memory, "timestamp"):
                    print(f"Timestamp: {memory.timestamp}")
                    print()

                if hasattr(memory, "relevance_score"):
                    print(f"Relevance Score: {memory.relevance_score}")
                    print()

                # Print raw memory object for debugging
                print("─" * 80)
                print("Raw Memory Object:")
                print("─" * 80)
                print(memory)
                print()

        print("=" * 80)
        print("  INSPECTION COMPLETE")
        print("=" * 80)

    except Exception as e:
        print(f"❌ Error searching memories: {e}")
        print()
        import traceback

        traceback.print_exc()


async def main():
    parser = argparse.ArgumentParser(
        description="Inspect memories in the Vertex AI memory bank",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--query",
        type=str,
        default="table errors",
        help="Search query for memories (default: 'table errors')",
    )

    args = parser.parse_args()

    await inspect_memories(query=args.query)


if __name__ == "__main__":
    asyncio.run(main())
