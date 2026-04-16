from __future__ import annotations

import json
import os
from pathlib import Path

import typer
from rich import print

from agent_tailor.generation.suit_generator import generate_agentsuit
from agent_tailor.models import ApiSurface
from agent_tailor.parsing.kotlin_parser import parse_kotlin_controllers
from agent_tailor.parsing.llm_enricher import enrich_surface_with_llm


def stitch_command(
    input: list[Path] = typer.Option(..., "--input", exists=True, readable=True, help="Kotlin controller file(s)."),
    name: str = typer.Option(..., "--name", help="Product name."),
    base_url: str = typer.Option(..., "--base-url", help="API base URL."),
    output: Path = typer.Option(Path("agentsuit-output"), "--output", help="Output directory."),
    api_key_env_var: str = typer.Option("API_KEY", "--api-key-env-var", help="API key env var name."),
    save_ir: bool = typer.Option(True, "--save-ir/--no-save-ir", help="Save parsed IR JSON in output/build."),
) -> None:
    surface = parse_kotlin_controllers(input, product_name=name, base_url=base_url, api_key_env_var=api_key_env_var)
    if os.getenv("AGENT_TAILOR_USE_LLM", "false").lower() == "true":
        try:
            surface = enrich_surface_with_llm(surface)
        except Exception as exc:
            print(f"[yellow]LLM enrichment failed, using deterministic parse only:[/yellow] {exc}")

    if save_ir:
        build_dir = output / "build"
        build_dir.mkdir(parents=True, exist_ok=True)
        (build_dir / "ir.json").write_text(json.dumps(surface.model_dump(), indent=2), encoding="utf-8")
    generate_agentsuit(surface, output_dir=output)

    validated = ApiSurface.model_validate(surface.model_dump())
    print(f"[green]Stitched AgentSuit[/green]: {output}")
    print(f"Resources: {[r.name for r in validated.resources]}")
