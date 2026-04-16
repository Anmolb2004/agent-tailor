from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Param(BaseModel):
    name: str
    source: Literal["path", "query", "header", "body"]
    required: bool = True
    data_type: str = "string"


class Operation(BaseModel):
    operation_id: str
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
    path: str
    summary: str
    request_body_type: str | None = None
    response_type: str | None = None
    supports_streaming: bool = False
    params: list[Param] = Field(default_factory=list)


class Resource(BaseModel):
    name: str
    operations: list[Operation] = Field(default_factory=list)


class AuthConfig(BaseModel):
    supports_api_key: bool = True
    supports_oauth: bool = True
    api_key_env_var: str = "API_KEY"


class ApiSurface(BaseModel):
    product_name: str
    base_url: str
    auth: AuthConfig
    resources: list[Resource] = Field(default_factory=list)
