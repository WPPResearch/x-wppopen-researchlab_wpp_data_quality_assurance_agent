# Agent-to-Agent (A2A) API Interface

The deployed agent exposes an A2A API compatible with the `google-adk` library, allowing optimized communication between agents. You can also interact with it directly via HTTP.

## Checking Agent Metadata
To verify the agent is running and check its configuration (Agent Card):

```bash
curl https://YOUR-SERVICE-URL.run.app/.well-known/agent-card.json | jq
```

## Sending a Message via Curl
You can send a JSON-RPC message to the agent using `curl`. This is useful for testing connectivity and basic responses.

```bash
curl -v --request POST \
  --url https://YOUR-SERVICE-URL.run.app/ \
  --header 'content-type: application/json' \
  --data '{
    "jsonrpc": "2.0",
    "id": 33,
    "method": "message/send",
    "params": {
        "message": {
            "role": "user",
            "parts": [{"type": "text", "text": "hello"}],
            "messageId": "foo5",
            "kind": "message"
        }
    }
}' | jq
```
