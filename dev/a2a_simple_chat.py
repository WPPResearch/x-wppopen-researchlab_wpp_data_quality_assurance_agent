import asyncio
import uuid
import sys
import httpx  # Need to make sure httpx is installed, usually is with google-adk
from google.adk.agents.remote_a2a_agent import (
    A2AMessage,
    A2APart,
    A2ACardResolver,
)
from a2a.client.client_factory import ClientFactory
from a2a.client.client import ClientConfig
from a2a.types import TransportProtocol

# Increase recursion depth just in case
sys.setrecursionlimit(2000)

# Configure the agent endpoint (e.g., "https://YOUR-SERVICE-NAME-YOUR-PROJECT-ID.REGION.run.app")
AGENT_BASE_URL = ""


async def main():
    print(f"Connecting to agent at: {AGENT_BASE_URL}")

    async with httpx.AsyncClient(
        base_url=AGENT_BASE_URL,
        timeout=30.0,
        follow_redirects=True,
    ) as client:
        try:
            resolver = A2ACardResolver(base_url=AGENT_BASE_URL, httpx_client=client)
            card = await resolver.get_agent_card()
            print(f"Fetched Agent Card for: {card.name}")
            # Override the URL from the card if it points to localhost (common in some deployments)
            # or simply force it to the base URL we know works.
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
        a2a_client = factory.create(card)

        # Generate a random session ID
        session_id = str(uuid.uuid4())
        print(f"Using session ID: {session_id}")

        # Chat loop
        while True:
            try:
                user_input = input("You: ")
                if user_input.lower() in ["exit", "quit"]:
                    break
            except EOFError:
                break

            message = A2AMessage(
                role="user",
                parts=[A2APart(type="text", text=user_input)],
                messageId=str(uuid.uuid4()),
                kind="message",
            )

            print("Agent thinking...")
            try:
                # send_message returns an async iterator yielding updates and finally the response message
                response = None
                async for update in a2a_client.send_message(request=message):
                    if isinstance(update, tuple):
                        task, event = update
                        if event is None:
                            response = task
                    elif isinstance(update, A2AMessage):
                        response = update
                    # We could handle other events here like TaskStatusUpdateEvent

                if response:
                    # If it's a Task
                    if hasattr(response, "history") and response.history:
                        last_msg = response.history[-1]
                        # Check role - simplistic check, might need strict enum check
                        if (
                            str(last_msg.role) == "agent"
                            or str(last_msg.role) == "Role.agent"
                        ):
                            for part in last_msg.parts:
                                if hasattr(part.root, "text"):
                                    print(f"Agent: {part.root.text}")
                                elif hasattr(part, "text"):
                                    print(f"Agent: {part.text}")

                    # If it's an A2AMessage
                    elif hasattr(response, "parts"):
                        for part in response.parts:
                            if hasattr(part, "text") and part.text:
                                print(f"Agent: {part.text}")
                            elif isinstance(part, dict) and part.get("text"):
                                print(f"Agent: {part['text']}")
                            else:
                                print(f"Agent (non-text): {part}")
                else:
                    print(f"Agent response: {response}")

            except Exception as e:
                print(f"Error: {e}")
                import traceback

                traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
