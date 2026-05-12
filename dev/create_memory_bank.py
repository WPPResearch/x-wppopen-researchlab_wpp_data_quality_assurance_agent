import os
import vertexai
from dotenv import load_dotenv

from vertexai._genai.types import MemoryBankCustomizationConfig as CustomizationConfig
from vertexai._genai.types import (
    MemoryBankCustomizationConfigGenerateMemoriesExample as GenerateMemoriesExample,
)
from vertexai._genai.types import (
    MemoryBankCustomizationConfigGenerateMemoriesExampleConversationSource as ConversationSource,
)
from vertexai._genai.types import (
    MemoryBankCustomizationConfigGenerateMemoriesExampleConversationSourceEvent as ConversationSourceEvent,
)
from vertexai._genai.types import (
    MemoryBankCustomizationConfigGenerateMemoriesExampleGeneratedMemory as ExampleGeneratedMemory,
)
from vertexai._genai.types import (
    MemoryBankCustomizationConfigMemoryTopic as MemoryTopic,
)
from vertexai._genai.types import (
    MemoryBankCustomizationConfigMemoryTopicCustomMemoryTopic as CustomMemoryTopic,
)

# Load environment variables
load_dotenv()

PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
MODEL = os.environ.get("ROOT_AGENT_MODEL", "gemini-2.5-flash")

# Force it to gemini-2.5-flash to avoid 404s on preview models not available in the region
if "gemini-3" in MODEL or "preview" in MODEL:
    print(
        f"Downgrading MODEL from {MODEL} to gemini-2.5-flash for Memory Bank generation to ensure availability.",
    )
    MODEL = "gemini-2.5-flash"

if not PROJECT:
    raise ValueError("GOOGLE_CLOUD_PROJECT environment variable must be set.")

vertexai.init(project=PROJECT, location=LOCATION)
client = vertexai.Client(project=PROJECT, location=LOCATION)

# Define Custom Topics
topic_data_quality = MemoryTopic(
    custom_memory_topic=CustomMemoryTopic(
        label="data_quality_issues",
        description="""Any logical errors in the BigQuery tables, missing data issues, null value patterns, schema discrepancies, or statistical outliers identified during data analysis. For example, if a table was missing a column, if dates are offset by a day, or if email addresses are mostly null.""",
    ),
)

topic_user_preferences = MemoryTopic(
    custom_memory_topic=CustomMemoryTopic(
        label="user_preferences",
        description="""User formatting preferences, desired sections, and common topics requested in past reports. For example, if the user always wants an executive summary or prefers markdown tables.""",
    ),
)


# Provide an example for how memories should be extracted
example_data_quality_1 = GenerateMemoriesExample(
    conversation_source=ConversationSource(
        events=[
            ConversationSourceEvent(
                content={
                    "role": "user",
                    "parts": [
                        {
                            "text": "I noticed the daily_users table has a discrepancy where the dates are off by one day compared to the source system. Also, the email_address column in user_profiles is 90% null.",
                        },
                    ],
                },
            ),
        ],
    ),
    generated_memories=[
        ExampleGeneratedMemory(
            fact="The daily_users table has a known discrepancy: dates are off by one day compared to the source system.",
        ),
        ExampleGeneratedMemory(
            fact="The email_address column in the user_profiles table is 90% null.",
        ),
    ],
)

example_data_quality_2 = GenerateMemoriesExample(
    conversation_source=ConversationSource(
        events=[
            ConversationSourceEvent(
                content={
                    "role": "model",
                    "parts": [
                        {
                            "text": "Based on my analysis of the sales_data table, the revenue column contains negative values in 5% of the rows, which seems anomalous.",
                        },
                    ],
                },
            ),
        ],
    ),
    generated_memories=[
        ExampleGeneratedMemory(
            fact="The sales_data table has anomalous negative values in the revenue column in 5% of its rows.",
        ),
    ],
)

example_noop = GenerateMemoriesExample(
    conversation_source=ConversationSource(
        events=[
            ConversationSourceEvent(
                content={
                    "role": "user",
                    "parts": [
                        {
                            "text": "Thanks for the report, it looks good. Let's look at the next dataset.",
                        },
                    ],
                },
            ),
        ],
    ),
    generated_memories=[],
)


def create_memory_bank():
    print(f"Creating Agent Engine in {PROJECT}/{LOCATION} for Memory Bank...")

    # Define the fundamental configuration and topics
    config = {
        "context_spec": {
            "memory_bank_config": {
                "generation_config": {
                    "model": f"projects/{PROJECT}/locations/{LOCATION}/publishers/google/models/{MODEL}",
                },
                "customization_configs": [
                    CustomizationConfig(
                        memory_topics=[topic_data_quality, topic_user_preferences],
                        generate_memories_examples=[
                            example_data_quality_1,
                            example_data_quality_2,
                            example_noop,
                        ],
                    ),
                ],
                "ttl_config": {
                    "default_ttl": f"{60 * 60 * 24 * 365}s",  # 1 year
                },
            },
        },
    }

    try:
        agent_engine = client.agent_engines.create(config=config)

        resource_name = agent_engine.api_resource.name
        agent_engine_id = resource_name.split("/")[-1]
        memory_service_uri = f"agentengine://{agent_engine_id}"

        print("\n✅ Successfully created Agent Engine!")
        print(f"Resource Name: {resource_name}")
        print("-" * 50)
        print("Please add the following line to your .env file:")
        print(f"MEMORY_SERVICE_URI='{memory_service_uri}'")
        print("-" * 50)

    except Exception as e:
        print(f"❌ Failed to create Agent Engine: {e}")


if __name__ == "__main__":
    create_memory_bank()
