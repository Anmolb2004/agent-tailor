from __future__ import annotations

import json
import os
from pathlib import Path

import typer
from rich import print

from agent_tailor.parsing.kotlin_parser import parse_kotlin_controllers
from agent_tailor.parsing.llm_enricher import enrich_surface_with_llm


def parse_kotlin_command(
    input: list[Path] = typer.Option(..., "--input", exists=True, readable=True, help="Kotlin controller file(s)."),
    name: str = typer.Option(..., "--name", help="Product name."),
    base_url: str = typer.Option(..., "--base-url", help="API base URL."),
    api_key_env_var: str = typer.Option("API_KEY", "--api-key-env-var", help="API key env var name."),
    out: Path = typer.Option(Path("build/ir.json"), "--out", help="Where to write normalized IR JSON."),
) -> None:
    surface = parse_kotlin_controllers(input, product_name=name, base_url=base_url, api_key_env_var=api_key_env_var)
    if os.getenv("AGENT_TAILOR_USE_LLM", "false").lower() == "true":
        try:
            surface = enrich_surface_with_llm(surface)
        except Exception as exc:
            print(f"[yellow]LLM enrichment failed, using deterministic parse only:[/yellow] {exc}")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(surface.model_dump(), indent=2), encoding="utf-8")
    print(f"[green]Wrote IR[/green]: {out}")
