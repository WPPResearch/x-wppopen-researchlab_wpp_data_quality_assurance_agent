# Troubleshooting

## General Issues

*   If you face `500 Internal Server Errors` when running the agent, simply
    re-run your last command. That should fix the issue.
*   If you encounter issues with the code interpreter, review the logs to
    understand the errors. Make sure you're using base-64 encoding for
    files/images if interacting directly with a code interpreter extension
    instead of through the agent's helper functions.
*   If you see errors in the SQL generated, try the following:
    - including clear descriptions in your tables and columns help boost
      performance
    - if your database is large, try setting up a RAG pipeline for schema
      linking by storing your table schema details in a vector store

## UI Agent Not Responding to Messages

**Symptom:** When you send a message in the UI, you get no response and see errors in Cloud Run logs like:
```
google.genai.errors.ClientError: 400 INVALID_ARGUMENT. 'Invalid ReasoningEngine resource name.'
```

**Cause:** The `MEMORY_SERVICE_URI` environment variable has quotes around it.

**Solution:**
1. In your deployment settings (e.g., Cloud Run env vars or CI/CD variables)
2. Find `MEMORY_SERVICE_URI`
3. Ensure the value has **NO quotes**:
   - Wrong: `'projects/123/locations/us-central1/reasoningEngines/456'`
   - Correct: `projects/123/locations/us-central1/reasoningEngines/456`
4. Redeploy the service

## Session Storage vs Memory Storage

The agent uses two types of storage:

- **Session Storage**: Stores conversation history and context
  - If `SESSION_SERVICE_URI` is not set, uses `MEMORY_SERVICE_URI` (Agent Engine) as fallback
  - Sessions persist across container restarts when using Agent Engine

- **Memory Storage**: Stores long-term facts and knowledge using LoadMemoryTool
  - Configured via `MEMORY_SERVICE_URI`
  - Requires a Vertex AI Reasoning Engine

**Current setup**: Both session and memory use the same `MEMORY_SERVICE_URI` (Agent Engine).
