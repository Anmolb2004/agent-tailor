# masaic AgentSuit Skill

## What this provides

- Installable Python CLI for your API
- Structured JSON responses for agent loops (`ok`, `data`, `meta` on success)
- CLI auth commands for API key + OAuth-like workflow

## Setup

```bash
pip install -e .
export MASAIC_API_KEY=YOUR_API_KEY
```

Optional OAuth-style login:

```bash
masaic-suit auth login
masaic-suit auth status
```

## Command surface

### agents
- `masaic-suit agents get` -> `GET /v1/agents/{agentName}`
- `masaic-suit agents create` -> `POST /v1/agents`
- `masaic-suit agents update` -> `PUT /v1/agents/{agentName}`
- `masaic-suit agents list` -> `GET /v1/agents`
- `masaic-suit agents delete` -> `DELETE /v1/agents/{agentName}`
- `masaic-suit agents chat` -> `POST /v1/agents/agent-builder/chat`
- `masaic-suit agents ask` -> `POST /v1/agents/{agentName}/ask`

### responses
- `masaic-suit responses create` -> `POST /v1/responses`
- `masaic-suit responses get` -> `GET /v1/responses/{responseId}`
- `masaic-suit responses delete` -> `DELETE /v1/responses/{responseId}`
- `masaic-suit responses list-input-items` -> `GET /v1/responses/{responseId}/input_items`

## Agent loop guidance

1. Call list/get commands to gather state.
2. Use create/update/delete commands to apply changes.
3. Parse JSON from stdout and branch on `ok`.
4. On non-zero exit codes, inspect stderr JSON with `error.status_code` for retry logic.
5. For streaming commands (`--stream`), read each line as an independent JSON event envelope.