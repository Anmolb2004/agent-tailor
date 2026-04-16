from __future__ import annotations

import re
from pathlib import Path

from agent_tailor.models import ApiSurface, AuthConfig, Operation, Param, Resource

MAPPING_TO_METHOD = {
    "GetMapping": "GET",
    "PostMapping": "POST",
    "PutMapping": "PUT",
    "PatchMapping": "PATCH",
    "DeleteMapping": "DELETE",
}


def _normalize_path(path: str) -> str:
    if not path.startswith("/"):
        path = "/" + path
    return re.sub(r"//+", "/", path)


def _to_snake(name: str) -> str:
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).replace("-", "_").lower()


def _guess_resource(path: str) -> str:
    parts = [p for p in path.split("/") if p and not p.startswith("{")]
    if len(parts) >= 2:
        return parts[1]
    if parts:
        return parts[0]
    return "default"


def _is_framework_collector_param(kotlin_type: str, variable_name: str) -> bool:
    type_normalized = kotlin_type.replace(" ", "")
    if "MultiValueMap<" in type_normalized:
        return True
    if type_normalized.endswith("ServerWebExchange"):
        return True
    if variable_name in {"exchange", "serverWebExchange"}:
        return True
    return False


def _extract_params(signature_block: str) -> list[Param]:
    params: list[Param] = []
    path_pattern = re.compile(
        r"@PathVariable(?:\((.*?)\))?\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*([a-zA-Z0-9_<>,\.\?]+)(?:\s*=\s*([^,\n\)]+))?",
        re.DOTALL,
    )
    for match in path_pattern.finditer(signature_block):
        anno_args, variable_name, kotlin_type, default_value = match.groups()
        explicit_name = _extract_annotation_name(anno_args)
        chosen_name = explicit_name or variable_name
        required = "?" not in kotlin_type and default_value is None
        params.append(Param(name=chosen_name, source="path", required=required, data_type=kotlin_type))

    query_pattern = re.compile(
        r"@RequestParam(?:\((.*?)\))?\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*([a-zA-Z0-9_<>,\.\?]+)(?:\s*=\s*([^,\n\)]+))?",
        re.DOTALL,
    )
    for match in query_pattern.finditer(signature_block):
        anno_args, variable_name, kotlin_type, default_value = match.groups()
        if _is_framework_collector_param(kotlin_type, variable_name):
            continue
        explicit_name = _extract_annotation_name(anno_args)
        forced_required = _extract_boolean_arg(anno_args, "required")
        required = forced_required if forced_required is not None else ("?" not in kotlin_type and default_value is None)
        if _extract_string_arg(anno_args, "defaultValue") is not None:
            required = False
        params.append(
            Param(
                name=explicit_name or variable_name,
                source="query",
                required=required,
                data_type=kotlin_type,
            )
        )

    body_match = re.search(
        r"@RequestBody\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*([a-zA-Z0-9_<>,\.\?]+)(?:\s*=\s*([^,\n\)]+))?",
        signature_block,
    )
    if body_match:
        var_name, kotlin_type, default_value = body_match.groups()
        required = "?" not in kotlin_type and default_value is None
        params.append(Param(name=var_name, source="body", required=required, data_type=kotlin_type))

    return params


def _extract_string_arg(annotation_args: str | None, key: str) -> str | None:
    if not annotation_args:
        return None
    match = re.search(rf"{key}\s*=\s*\"([^\"]+)\"", annotation_args)
    return match.group(1) if match else None


def _extract_boolean_arg(annotation_args: str | None, key: str) -> bool | None:
    if not annotation_args:
        return None
    match = re.search(rf"{key}\s*=\s*(true|false)", annotation_args)
    if not match:
        return None
    return match.group(1) == "true"


def _extract_annotation_name(annotation_args: str | None) -> str | None:
    if not annotation_args:
        return None
    explicit = _extract_string_arg(annotation_args, "name") or _extract_string_arg(annotation_args, "value")
    if explicit:
        return explicit
    positional = re.match(r"\s*\"([^\"]+)\"\s*$", annotation_args)
    return positional.group(1) if positional else None


def parse_kotlin_controllers(
    file_paths: list[Path],
    product_name: str,
    base_url: str,
    api_key_env_var: str,
) -> ApiSurface:
    resources: dict[str, Resource] = {}
    for file_path in file_paths:
        text = file_path.read_text(encoding="utf-8")
        class_base_match = re.search(r"@RequestMapping\(\"([^\"]+)\"\)", text)
        class_base = class_base_match.group(1) if class_base_match else ""

        operation_pattern = re.compile(
            r"@(GetMapping|PostMapping|PutMapping|PatchMapping|DeleteMapping)\((.*?)\)\s*"
            r"suspend\s+fun\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\((.*?)\)\s*:\s*([a-zA-Z0-9_<>\?\*]+)",
            re.DOTALL,
        )

        for match in operation_pattern.finditer(text):
            method = MAPPING_TO_METHOD[match.group(1)]
            annotation_args = match.group(2)
            path_match = re.search(r"\"([^\"]+)\"", annotation_args)
            if not path_match:
                continue
            op_path = _normalize_path(class_base + path_match.group(1))
            fn_name = match.group(3)
            signature_block = match.group(4)
            response_type = match.group(5)
            params = _extract_params(signature_block)
            body_type = next((p.data_type for p in params if p.source == "body"), None)
            resource_name = _guess_resource(op_path)
            supports_streaming = "TEXT_EVENT_STREAM_VALUE" in annotation_args or "Flow<" in response_type

            op = Operation(
                operation_id=_to_snake(fn_name),
                method=method,
                path=op_path,
                summary=f"{method} {op_path}",
                request_body_type=body_type,
                response_type=response_type,
                supports_streaming=supports_streaming,
                params=params,
            )
            if resource_name not in resources:
                resources[resource_name] = Resource(name=resource_name, operations=[])
            resources[resource_name].operations.append(op)

    return ApiSurface(
        product_name=product_name,
        base_url=base_url,
        auth=AuthConfig(
            supports_api_key=True,
            supports_oauth=True,
            api_key_env_var=api_key_env_var,
        ),
        resources=sorted(resources.values(), key=lambda r: r.name),
    )
