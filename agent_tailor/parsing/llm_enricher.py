from __future__ import annotations

import json
import os

import httpx

from agent_tailor.models import ApiSurface


def _build_prompt(surface: ApiSurface) -> str:
    schema_hint = {
        "product_name": "string",
        "base_url": "string",
        "auth": {"supports_api_key": "bool", "supports_oauth": "bool", "api_key_env_var": "string"},
        "resources": [
            {
                "name": "string",
                "operations": [
                    {
                        "operation_id": "string",
                        "method": "GET|POST|PUT|PATCH|DELETE",
                        "path": "string",
                        "summary": "string",
                        "request_body_type": "string|null",
                        "response_type": "string|null",
                        "params": [{"name": "string", "source": "path|query|header|body", "required": "bool", "data_type": "string"}],
                    }
                ],
            }
        ],
    }
    return (
        "You are a strict API surface normalizer. Improve operation summaries only. "
        "Return strict JSON matching this schema shape and preserve all fields.\n"
        f"Schema shape: {json.dumps(schema_hint)}\n"
        f"Input JSON: {surface.model_dump_json()}"
    )


def _call_openai(prompt: str) -> dict:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required for OpenAI enrichment.")
    response = httpx.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": os.getenv("AGENT_TAILOR_OPENAI_MODEL", "gpt-4o-mini"),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        },
        timeout=60.0,
    )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    return json.loads(content)


def _call_anthropic(prompt: str) -> dict:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is required for Anthropic enrichment.")
    response = httpx.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": os.getenv("AGENT_TAILOR_ANTHROPIC_MODEL", "claude-3-5-haiku-latest"),
            "max_tokens": 4000,
            "temperature": 0,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=60.0,
    )
    response.raise_for_status()
    text = "".join(block.get("text", "") for block in response.json()["content"] if block.get("type") == "text")
    return json.loads(text)


def enrich_surface_with_llm(surface: ApiSurface) -> ApiSurface:
    provider = os.getenv("AGENT_TAILOR_PROVIDER", "openai").lower()
    prompt = _build_prompt(surface)
    if provider == "anthropic":
        result = _call_anthropic(prompt)
    else:
        result = _call_openai(prompt)
    return ApiSurface.model_validate(result)
