from __future__ import annotations

import json
from pathlib import Path

import typer
from rich import print

from agent_tailor.generation.suit_generator import generate_agentsuit
from agent_tailor.models import ApiSurface


def generate_command(
    ir: Path = typer.Option(Path("build/ir.json"), "--ir", exists=True, readable=True, help="IR JSON path."),
    output: Path = typer.Option(Path("agentsuit-output"), "--output", help="Generated suit output directory."),
) -> None:
    data = json.loads(ir.read_text(encoding="utf-8"))
    surface = ApiSurface.model_validate(data)
    generate_agentsuit(surface, output_dir=output)
    print(f"[green]Generated AgentSuit[/green]: {output}")
