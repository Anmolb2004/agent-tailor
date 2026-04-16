from __future__ import annotations

import typer

from agent_tailor.commands.generate import generate_command
from agent_tailor.commands.parse_kotlin import parse_kotlin_command
from agent_tailor.commands.stitch import stitch_command

app = typer.Typer(help="AgentTailor: stitch AgentSuits from product APIs.")
app.command("parse-kotlin")(parse_kotlin_command)
app.command("generate")(generate_command)
app.command("stitch")(stitch_command)


if __name__ == "__main__":
    app()
