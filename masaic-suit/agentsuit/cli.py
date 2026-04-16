from __future__ import annotations

import json
import os

import typer

from .auth import clear_oauth_credentials, oauth_login_via_local_callback, read_oauth_credentials, save_oauth_credentials
from .http_client import request_json, request_stream


app = typer.Typer(help="masaic AgentSuit CLI")
auth_app = typer.Typer(help="Authentication commands")
app.add_typer(auth_app, name="auth")
BASE_URL = os.getenv("AGENTSUIT_BASE_URL", "http://localhost:8080")


@auth_app.command("login")
def auth_login(
    token: str | None = typer.Option(None, "--token", help="OAuth access token override (skips browser/callback)."),
    start_url: str = typer.Option("", "--start-url", help="Optional OAuth authorize URL."),
    no_browser: bool = typer.Option(False, "--no-browser", help="Do not open a browser; wait for local callback instead."),
):
    """
    Mark-1 OAuth flow (local callback):
    - Opens auth URL in browser (unless --no-browser)
    - Captures token from a localhost callback GET request (unless --token is provided)
    """
    if token:
        save_oauth_credentials(token, source="cli_token", start_url=start_url or None)
    else:
        oauth_login_via_local_callback(start_url=start_url or None, open_browser=not no_browser)
    creds = read_oauth_credentials()
    print(
        json.dumps(
            {
                "ok": True,
                "data": {
                    "api_key_env_var": "MASAIC_API_KEY",
                    "api_key_present": bool(os.getenv("MASAIC_API_KEY")),
                    "oauth_logged_in": bool(creds.get("access_token")),
                    "oauth_source": creds.get("source"),
                    "oauth_start_url": creds.get("start_url") or (start_url or None),
                },
                "meta": {"command": "auth.login"},
            },
            indent=2,
        )
    )


@auth_app.command("status")
def auth_status():
    key_present = bool(os.getenv("MASAIC_API_KEY"))
    creds = read_oauth_credentials()
    print(
        json.dumps(
            {
                "ok": True,
                "data": {
                    "api_key_env_var": "MASAIC_API_KEY",
                    "api_key_present": key_present,
                    "oauth_logged_in": bool(creds.get("access_token")),
                    "oauth_source": creds.get("source"),
                    "oauth_start_url": creds.get("start_url"),
                },
            },
            indent=2,
        )
    )


@auth_app.command("logout")
def auth_logout():
    removed = clear_oauth_credentials()
    print(json.dumps({"ok": True, "data": {"oauth_logged_out": removed}}))

agents_app = typer.Typer(help="agents operations")
app.add_typer(agents_app, name="agents")

@agents_app.command("get")
def agents_get_agent(
    agentName: str = typer.Option(..., "--agentName", help="path parameter"),
    json_body: str = typer.Option("", "--json", help="Raw JSON request body."),
    api_key: str = typer.Option("", "--api-key", help="API key override."),
):
    path = "/v1/agents/{agentName}"
    path = path.replace("{agentName}", agentName)

    query = {
    }
    body = json.loads(json_body) if json_body else None
    result = request_json("GET", BASE_URL, path, params=query, body=body, api_key=api_key or None)
    print(json.dumps(result, indent=2))

@agents_app.command("create")
def agents_save_agent(
    json_body: str = typer.Option("", "--json", help="Raw JSON request body."),
    api_key: str = typer.Option("", "--api-key", help="API key override."),
):
    path = "/v1/agents"

    query = {
    }
    body = json.loads(json_body) if json_body else None
    result = request_json("POST", BASE_URL, path, params=query, body=body, api_key=api_key or None)
    print(json.dumps(result, indent=2))

@agents_app.command("update")
def agents_update_agent(
    agentName: str = typer.Option(..., "--agentName", help="path parameter"),
    json_body: str = typer.Option("", "--json", help="Raw JSON request body."),
    api_key: str = typer.Option("", "--api-key", help="API key override."),
):
    path = "/v1/agents/{agentName}"
    path = path.replace("{agentName}", agentName)

    query = {
    }
    body = json.loads(json_body) if json_body else None
    result = request_json("PUT", BASE_URL, path, params=query, body=body, api_key=api_key or None)
    print(json.dumps(result, indent=2))

@agents_app.command("list")
def agents_list_agents(
    json_body: str = typer.Option("", "--json", help="Raw JSON request body."),
    api_key: str = typer.Option("", "--api-key", help="API key override."),
):
    path = "/v1/agents"

    query = {
    }
    body = json.loads(json_body) if json_body else None
    result = request_json("GET", BASE_URL, path, params=query, body=body, api_key=api_key or None)
    print(json.dumps(result, indent=2))

@agents_app.command("delete")
def agents_delete_agent(
    agentName: str = typer.Option(..., "--agentName", help="path parameter"),
    json_body: str = typer.Option("", "--json", help="Raw JSON request body."),
    api_key: str = typer.Option("", "--api-key", help="API key override."),
):
    path = "/v1/agents/{agentName}"
    path = path.replace("{agentName}", agentName)

    query = {
    }
    body = json.loads(json_body) if json_body else None
    result = request_json("DELETE", BASE_URL, path, params=query, body=body, api_key=api_key or None)
    print(json.dumps(result, indent=2))

@agents_app.command("chat")
def agents_chat_with_agent_builder(
    json_body: str = typer.Option("", "--json", help="Raw JSON request body."),
    stream: bool = typer.Option(False, "--stream", help="Stream SSE response as NDJSON."),
    api_key: str = typer.Option("", "--api-key", help="API key override."),
):
    path = "/v1/agents/agent-builder/chat"

    query = {
    }
    body = json.loads(json_body) if json_body else None
    if stream:
        for event in request_stream("POST", BASE_URL, path, params=query, body=body, api_key=api_key or None):
            print(json.dumps(event))
        return
    result = request_json("POST", BASE_URL, path, params=query, body=body, api_key=api_key or None)
    print(json.dumps(result, indent=2))

@agents_app.command("ask")
def agents_ask_agent(
    agentName: str = typer.Option(..., "--agentName", help="path parameter"),
    json_body: str = typer.Option("", "--json", help="Raw JSON request body."),
    api_key: str = typer.Option("", "--api-key", help="API key override."),
):
    path = "/v1/agents/{agentName}/ask"
    path = path.replace("{agentName}", agentName)

    query = {
    }
    body = json.loads(json_body) if json_body else None
    result = request_json("POST", BASE_URL, path, params=query, body=body, api_key=api_key or None)
    print(json.dumps(result, indent=2))

responses_app = typer.Typer(help="responses operations")
app.add_typer(responses_app, name="responses")

@responses_app.command("create")
def responses_create_response(
    json_body: str = typer.Option("", "--json", help="Raw JSON request body."),
    stream: bool = typer.Option(False, "--stream", help="Stream SSE response as NDJSON."),
    api_key: str = typer.Option("", "--api-key", help="API key override."),
):
    path = "/v1/responses"

    query = {
    }
    body = json.loads(json_body) if json_body else None
    if stream:
        for event in request_stream("POST", BASE_URL, path, params=query, body=body, api_key=api_key or None):
            print(json.dumps(event))
        return
    result = request_json("POST", BASE_URL, path, params=query, body=body, api_key=api_key or None)
    print(json.dumps(result, indent=2))

@responses_app.command("get")
def responses_get_response(
    responseId: str = typer.Option(..., "--responseId", help="path parameter"),
    json_body: str = typer.Option("", "--json", help="Raw JSON request body."),
    api_key: str = typer.Option("", "--api-key", help="API key override."),
):
    path = "/v1/responses/{responseId}"
    path = path.replace("{responseId}", responseId)

    query = {
    }
    body = json.loads(json_body) if json_body else None
    result = request_json("GET", BASE_URL, path, params=query, body=body, api_key=api_key or None)
    print(json.dumps(result, indent=2))

@responses_app.command("delete")
def responses_delete_response(
    responseId: str = typer.Option(..., "--responseId", help="path parameter"),
    json_body: str = typer.Option("", "--json", help="Raw JSON request body."),
    api_key: str = typer.Option("", "--api-key", help="API key override."),
):
    path = "/v1/responses/{responseId}"
    path = path.replace("{responseId}", responseId)

    query = {
    }
    body = json.loads(json_body) if json_body else None
    result = request_json("DELETE", BASE_URL, path, params=query, body=body, api_key=api_key or None)
    print(json.dumps(result, indent=2))

@responses_app.command("list-input-items")
def responses_list_input_items(
    responseId: str = typer.Option(..., "--responseId", help="path parameter"),
    limit: str | None = typer.Option(None, "--limit", help="query parameter"),
    order: str | None = typer.Option(None, "--order", help="query parameter"),
    after: str | None = typer.Option(None, "--after", help="query parameter"),
    before: str | None = typer.Option(None, "--before", help="query parameter"),
    json_body: str = typer.Option("", "--json", help="Raw JSON request body."),
    api_key: str = typer.Option("", "--api-key", help="API key override."),
):
    path = "/v1/responses/{responseId}/input_items"
    path = path.replace("{responseId}", responseId)

    query = {
        "limit": limit,
        "order": order,
        "after": after,
        "before": before,
    }
    body = json.loads(json_body) if json_body else None
    result = request_json("GET", BASE_URL, path, params=query, body=body, api_key=api_key or None)
    print(json.dumps(result, indent=2))

