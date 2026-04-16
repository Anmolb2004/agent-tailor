from __future__ import annotations

import json
import sys

import httpx

from .auth import get_auth_header


def _error_payload(status_code: int, method: str, url: str, message: str) -> dict:
    return {
        "ok": False,
        "error": {
            "status_code": status_code,
            "method": method,
            "url": url,
            "message": message,
        },
    }


def request_json(method: str, base_url: str, path: str, params: dict | None = None, body: dict | None = None, api_key: str | None = None):
    headers = {"Content-Type": "application/json"}
    headers.update(get_auth_header(api_key=api_key))

    filtered_params = {k: v for k, v in (params or {}).items() if v is not None}
    url = f"{base_url.rstrip('/')}{path}"
    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.request(
                method=method,
                url=url,
                params=filtered_params,
                json=body,
                headers=headers,
            )
    except httpx.RequestError as exc:
        err = _error_payload(0, method, url, f"transport_error: {exc}")
        print(json.dumps(err), file=sys.stderr)
        raise SystemExit(1)

    if response.status_code >= 400:
        err = _error_payload(response.status_code, method, url, response.text)
        print(json.dumps(err), file=sys.stderr)
        raise SystemExit(1)

    try:
        payload = response.json()
    except Exception:
        payload = {"raw": response.text}
    return {
        "ok": True,
        "data": payload,
        "meta": {
            "status_code": response.status_code,
            "method": method,
            "url": url,
        },
    }


def request_stream(method: str, base_url: str, path: str, params: dict | None = None, body: dict | None = None, api_key: str | None = None):
    headers = {"Content-Type": "application/json", "Accept": "text/event-stream"}
    headers.update(get_auth_header(api_key=api_key))
    filtered_params = {k: v for k, v in (params or {}).items() if v is not None}
    url = f"{base_url.rstrip('/')}{path}"

    try:
        with httpx.Client(timeout=60.0) as client:
            with client.stream(
                method=method,
                url=url,
                params=filtered_params,
                json=body,
                headers=headers,
            ) as response:
                if response.status_code >= 400:
                    err = _error_payload(response.status_code, method, url, response.text)
                    print(json.dumps(err), file=sys.stderr)
                    raise SystemExit(1)
                event_index = 0
                for line in response.iter_lines():
                    if not line:
                        continue
                    if line.startswith("data:"):
                        payload = line[5:].strip()
                    else:
                        payload = line.strip()
                    if not payload:
                        continue
                    try:
                        data = json.loads(payload)
                    except Exception:
                        data = {"raw": payload}
                    yield {
                        "ok": True,
                        "stream": True,
                        "event_index": event_index,
                        "data": data,
                        "meta": {
                            "status_code": response.status_code,
                            "method": method,
                            "url": url,
                        },
                    }
                    event_index += 1
    except httpx.RequestError as exc:
        err = _error_payload(0, method, url, f"transport_error: {exc}")
        print(json.dumps(err), file=sys.stderr)
        raise SystemExit(1)