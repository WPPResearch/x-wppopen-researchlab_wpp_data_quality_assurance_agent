import asyncio
import base64
import os
import sys
import uuid

import httpx
from a2a.client.client import ClientConfig
from a2a.client.client_factory import ClientFactory
from a2a.types import TransportProtocol
from google.adk.agents.remote_a2a_agent import (
    A2ACardResolver,
    A2AMessage,
    A2APart,
)

# Increase recursion depth
sys.setrecursionlimit(2000)

# Configure the agent endpoint
AGENT_BASE_URL = os.getenv("AGENT_URL", "")


async def main():
    print(f"Connecting to agent at: {AGENT_BASE_URL}")

    async with httpx.AsyncClient(
        base_url=AGENT_BASE_URL,
        timeout=120.0,
        follow_redirects=True,
    ) as client:
        try:
            resolver = A2ACardResolver(base_url=AGENT_BASE_URL, httpx_client=client)
            card = await resolver.get_agent_card()
            print(f"Fetched Agent Card for: {card.name}")
            # Override the URL from the card to ensure we connect to the Cloud Run instance
            card.url = AGENT_BASE_URL
        except Exception as e:
            print(f"Error fetching card: {e}")
            return

        # Initialize the A2A client using Factory
        client_config = ClientConfig(
            httpx_client=client,
            streaming=True,
            polling=False,
            supported_transports=[TransportProtocol.jsonrpc],
        )
        factory = ClientFactory(config=client_config)
        agent = factory.create(card)

        session_id = str(uuid.uuid4())
        print(f"Starting session: {session_id}")

        # 1. Ask for a report
        print("\n--- Requesting Report ---")
        prompt = "Generate a sample report for the sticker sales"
        message = A2AMessage(
            role="user",
            parts=[A2APart(type="text", text=prompt)],
            messageId=str(uuid.uuid4()),
            kind="message",
        )

        try:
            response = None
            async for update in agent.send_message(request=message):
                if isinstance(update, tuple):
                    task, event = update
                    # Check for new artifacts in the task
                    if task.artifacts:
                        print(f"Found {len(task.artifacts)} artifacts.")
                        for artifact in task.artifacts:
                            print(f"  Artifact ID: {artifact.artifact_id}")
                            print(f"  Artifact Name: {artifact.name}")
                            if artifact.parts:
                                for part in artifact.parts:
                                    print(f"    Part Kind: {part.root.kind}")
                                    if part.root.kind == "file":
                                        file_part = part.root.file
                                        if hasattr(file_part, "bytes"):
                                            print(
                                                f"    Found binary file content for: {file_part.name or 'unknown'}",
                                            )
                                            try:
                                                file_data = base64.b64decode(
                                                    file_part.bytes,
                                                )
                                                filename = (
                                                    file_part.name
                                                    or f"artifact_{artifact.artifact_id}.bin"
                                                )
                                                # Ensure it ends with pdf if mime type matches
                                                if (
                                                    file_part.mime_type
                                                    == "application/pdf"
                                                    and not filename.endswith(".pdf")
                                                ):
                                                    filename += ".pdf"

                                                with open(filename, "wb") as f:
                                                    f.write(file_data)
                                                print(
                                                    f"    Saved artifact to: {os.path.abspath(filename)}",
                                                )
                                            except Exception as e:
                                                print(f"    Error saving artifact: {e}")
                                        elif hasattr(file_part, "uri"):
                                            print(
                                                f"    Found file URI: {file_part.uri}",
                                            )
                                    elif part.root.kind == "text":
                                        print(
                                            f"    Text Content: {part.root.text[:100]}...",
                                        )

                    # Store the final task state
                    if event is None:
                        response = task  # Treat the task as the response container
                elif isinstance(update, A2AMessage):
                    response = update

            print(
                f"Response type: {type(response)}",
            )

            if hasattr(response, "artifacts") and response.artifacts:
                print(f"Found {len(response.artifacts)} artifacts.")
                for artifact in response.artifacts:
                    for part in artifact.parts:
                        if hasattr(part.root, "text"):
                            print(f"Artifact Text: {part.root.text[:100]}...")
                        # Check for inline data in artifact parts (if structured that way)

            # Print the last message from history if it's a Task
            if hasattr(response, "history") and response.history:
                last_msg = response.history[-1]
                if (
                    str(last_msg.role) == "agent" or str(last_msg.role) == "Role.agent"
                ):  # Check role enum string or object
                    for part in last_msg.parts:
                        if hasattr(part.root, "text"):
                            print(f"Agent: {part.root.text}")
                        elif hasattr(part, "text"):
                            print(f"Agent: {part.text}")

            # Legacy A2AMessage check
            if response and hasattr(response, "parts"):
                for part in response.parts:
                    # Check for text
                    if hasattr(part, "text") and part.text:
                        print(f"Agent: {part.text}")
                    elif isinstance(part, dict) and part.get("text"):
                        print(f"Agent: {part['text']}")

                    # Check for inline data
                    # Assuming A2APart has inline_data attribute or dict
                    inline_data = None
                    if hasattr(part, "inline_data"):
                        inline_data = part.inline_data
                    elif isinstance(part, dict):
                        inline_data = part.get("inline_data")

                    if inline_data:
                        # Inline data might be an object or dict
                        mime_type = (
                            inline_data.mime_type
                            if hasattr(inline_data, "mime_type")
                            else inline_data.get("mime_type")
                        )
                        data_b64 = (
                            inline_data.data
                            if hasattr(inline_data, "data")
                            else inline_data.get("data")
                        )

                        print(f"Received artifact: {mime_type}")
                        if mime_type == "application/pdf":
                            filename = "downloaded_report.pdf"
                            with open(filename, "wb") as f:
                                f.write(base64.b64decode(data_b64))
                            print(f"Saved PDF report to: {os.path.abspath(filename)}")

        except Exception as e:
            print(f"Error requesting report: {e}")
            import traceback

            traceback.print_exc()

        # 2. Continue session
        print("\n--- Continuing Session ---")
        follow_up = "What is the summary of that report?"
        message = A2AMessage(
            role="user",
            parts=[A2APart(type="text", text=follow_up)],
            messageId=str(uuid.uuid4()),
            kind="message",
        )

        try:
            response = None
            async for update in agent.send_message(request=message):
                if isinstance(update, A2AMessage):
                    response = update

            if response and hasattr(response, "parts"):
                for part in response.parts:
                    if hasattr(part, "text") and part.text:
                        print(f"Agent: {part.text}")
                    elif isinstance(part, dict) and part.get("text"):
                        print(f"Agent: {part['text']}")

        except Exception as e:
            print(f"Error in follow-up: {e}")


if __name__ == "__main__":
    asyncio.run(main())
