<<<<<<< HEAD
Agent Tailor
=======
# AgentTailor (Mark-1)

AgentTailor takes Kotlin Spring REST controllers and generates an agent-ready Python CLI ("AgentSuit") with:

- CLI commands for API operations
- deterministic JSON output envelopes
- API key + OAuth CLI workflows
- generated `SKILLS.md`

## Mark-1 scope (explicit)

### Input contract

- Local Kotlin Spring controller files passed with repeated `--input`.
- Product metadata: `--name` and `--base-url`.
- Auth env var name: `--api-key-env-var` (default: `API_KEY`).

### Output contract

AgentTailor writes these artifacts to `--output`:

- `agentsuit/cli.py`: executable command surface
- `agentsuit/http_client.py`: HTTP wrapper with structured success/error envelopes
- `agentsuit/auth.py`: API key + OAuth credential helpers
- `SKILLS.md`: operational usage guidance for agent loops
- `pyproject.toml`: installable package with `<product>-suit` console script
- `build/ir.json`: parsed API surface (unless `--no-save-ir`)

### Structured JSON contract

- Success: `{ "ok": true, "data": ..., "meta": { "status_code", "method", "url" } }`
- Error (stderr + non-zero exit): `{ "ok": false, "error": { "status_code", "method", "url", "message" } }`
- Stream mode (`--stream`): each line is a JSON event envelope with `ok`, `stream`, `event_index`, `data`, `meta`.

### Authentication contract

- API key mode: read from `--api-key` or `--api-key-env-var`.
- OAuth mode (Mark-1 pragmatic flow):
  - `auth login [--token] [--start-url] [--no-browser]`
  - `auth status` for agent-readable auth state
  - `auth logout` to clear stored OAuth token

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
agent-tailor stitch \
  --name masaic \
  --base-url http://localhost:8080 \
  --api-key-env-var MASAIC_API_KEY \
  --input path/to/AgentsController.kt \
  --input path/to/ResponseController.kt \
  --output ./masaic-suit
```

Install the generated suit and inspect command surface:

```bash
cd masaic-suit
pip install -e .
masaic-suit --help
masaic-suit auth status
```

## Mark-1 acceptance checks

- Stitch succeeds for both reference controllers in one run.
- Generated suit installs and exposes `<product>-suit` command.
- Commands print success envelope on stdout for successful requests.
- Commands print error envelope to stderr and exit non-zero on API failures.
- Auth commands (`login`, `status`, `logout`) run from CLI.
- `SKILLS.md` lists generated commands and loop guidance.

## LLM parser enrichment (optional)

By default, parsing is deterministic from annotations and signatures.  
To enrich summaries/descriptions using an LLM:

```bash
export AGENT_TAILOR_USE_LLM=true
export AGENT_TAILOR_PROVIDER=openai   # or anthropic
export OPENAI_API_KEY=...
```
>>>>>>> e92e0ef (Initial AgentTailor Mark-1 implementation)
