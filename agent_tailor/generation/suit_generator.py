from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from agent_tailor.models import ApiSurface


def _method_to_action(method: str) -> str:
    return {
        "GET": "list",
        "POST": "create",
        "PUT": "update",
        "PATCH": "patch",
        "DELETE": "delete",
    }.get(method, method.lower())


def _operation_command_name(path: str, method: str, operation_id: str) -> str:
    method = method.upper()
    last_segment = path.rstrip("/").split("/")[-1]
    has_path_var = "{" in path and "}" in path
    if method == "GET":
        if last_segment.startswith("{"):
            return "get"
        if has_path_var:
            return operation_id.replace("_", "-")
        return "list"
    if method == "POST":
        if last_segment == "ask":
            return "ask"
        if last_segment == "chat":
            return "chat"
        if last_segment not in {"agents", "responses"}:
            return operation_id.replace("_", "-")
        return "create"
    if method in {"PUT", "PATCH", "DELETE"}:
        return _method_to_action(method)
    return operation_id.replace("_", "-")


def generate_agentsuit(surface: ApiSurface, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    package_dir = output_dir / "agentsuit"
    package_dir.mkdir(parents=True, exist_ok=True)
    (package_dir / "__init__.py").write_text("", encoding="utf-8")

    template_dir = Path(__file__).parent / "templates"
    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(disabled_extensions=("j2",)),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    context = {
        "surface": surface.model_dump(),
        "command_name_for": _operation_command_name,
    }

    for template_name, out_name in [
        ("cli.py.j2", "cli.py"),
        ("auth.py.j2", "auth.py"),
        ("http_client.py.j2", "http_client.py"),
        ("skills.md.j2", "SKILLS.md"),
    ]:
        rendered = env.get_template(template_name).render(**context)
        target = package_dir / out_name if out_name.endswith(".py") else output_dir / out_name
        target.write_text(rendered, encoding="utf-8")

    pyproject = f"""
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "{surface.product_name.lower().replace(' ', '-')}-agentsuit"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = ["typer>=0.12.3", "httpx>=0.27.0", "python-dotenv>=1.0.1", "rich>=13.7.1"]

[project.scripts]
{surface.product_name.lower().replace(' ', '-')}-suit = "agentsuit.cli:app"

[tool.setuptools.packages.find]
where = ["."]
include = ["agentsuit*"]
""".strip() + "\n"
    (output_dir / "pyproject.toml").write_text(pyproject, encoding="utf-8")
