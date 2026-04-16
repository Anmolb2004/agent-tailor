from __future__ import annotations

import builtins
import importlib
import io
import json
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from contextlib import redirect_stdout

from agent_tailor.generation.suit_generator import generate_agentsuit
from agent_tailor.parsing.kotlin_parser import parse_kotlin_controllers


KOTLIN_SAMPLE = """
package ai.test

import kotlinx.coroutines.flow.Flow
import org.springframework.http.MediaType
import org.springframework.http.ResponseEntity
import org.springframework.web.bind.annotation.*

@RestController
@RequestMapping("/v1")
class SampleController {
  @GetMapping("/items/{itemId}", produces = [MediaType.APPLICATION_JSON_VALUE])
  suspend fun getItem(
    @PathVariable("itemId") itemId: String,
    @RequestParam(required = false) after: String?,
    @RequestParam(defaultValue = "20") limit: Int,
  ): ResponseEntity<String> = ResponseEntity.ok("ok")

  @PostMapping("/stream", produces = [MediaType.TEXT_EVENT_STREAM_VALUE])
  suspend fun streamItems(
    @RequestBody request: StreamRequest
  ): ResponseEntity<Flow<String>> = ResponseEntity.ok(kotlinx.coroutines.flow.emptyFlow())
}
"""


class TestMark1Pipeline(unittest.TestCase):
    def test_reference_controllers_mark1_flow(self) -> None:
        repo_root = Path(__file__).resolve().parent.parent
        agents_controller = repo_root / "examples" / "AgentsController.kt"
        responses_controller = repo_root / "examples" / "ResponseController.kt"

        self.assertTrue(agents_controller.exists())
        self.assertTrue(responses_controller.exists())

        with TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "masaic-suit"
            surface = parse_kotlin_controllers(
                [agents_controller, responses_controller],
                product_name="masaic",
                base_url="http://localhost:8080",
                api_key_env_var="MASAIC_API_KEY",
            )
            generate_agentsuit(surface, output_dir)

            resources = {resource.name for resource in surface.resources}
            self.assertIn("agents", resources)
            self.assertIn("responses", resources)

            cli_contents = (output_dir / "agentsuit" / "cli.py").read_text(encoding="utf-8")
            self.assertIn("agents operations", cli_contents)
            self.assertIn("responses operations", cli_contents)
            self.assertIn("Authentication commands", cli_contents)
            self.assertNotIn("--queryParams", cli_contents)

    def test_auth_login_outputs_structured_envelope(self) -> None:
        with TemporaryDirectory() as tmp:
            file_path = Path(tmp) / "SampleController.kt"
            output_dir = Path(tmp) / "out"
            file_path.write_text(KOTLIN_SAMPLE, encoding="utf-8")

            surface = parse_kotlin_controllers(
                [file_path],
                product_name="demo",
                base_url="http://localhost:8080",
                api_key_env_var="DEMO_API_KEY",
            )
            generate_agentsuit(surface, output_dir)

            sys.path.insert(0, str(output_dir))
            try:
                # Ensure we import the newly generated package, not any preexisting module.
                for mod_name in ["agentsuit.cli", "agentsuit.auth", "agentsuit.http_client", "agentsuit"]:
                    sys.modules.pop(mod_name, None)
                cli_mod = importlib.import_module("agentsuit.cli")

                # Stub the OAuth callback and credential reader so we don't need a browser/server.
                cli_mod.oauth_login_via_local_callback = lambda start_url=None, open_browser=True, timeout_seconds=300: None
                cli_mod.read_oauth_credentials = lambda: {"access_token": "stub"}

                # Avoid rich-print formatting; we want raw JSON in stdout.
                cli_mod.print = builtins.print
                os.environ["DEMO_API_KEY"] = "demo-key"

                buf = io.StringIO()
                with redirect_stdout(buf):
                    cli_mod.auth_login(start_url="http://example.com", token=None, no_browser=False)
                payload = json.loads(buf.getvalue())

                self.assertTrue(payload["ok"])
                self.assertIn("data", payload)
                self.assertIn("meta", payload)
                self.assertTrue(payload["data"]["oauth_logged_in"])
                self.assertEqual(payload["data"]["api_key_env_var"], "DEMO_API_KEY")
                self.assertEqual(payload["meta"]["command"], "auth.login")
            finally:
                sys.path.pop(0)

    def test_auth_login_token_flag_skips_oauth_callback(self) -> None:
        with TemporaryDirectory() as tmp:
            file_path = Path(tmp) / "SampleController.kt"
            output_dir = Path(tmp) / "out"
            file_path.write_text(KOTLIN_SAMPLE, encoding="utf-8")

            surface = parse_kotlin_controllers(
                [file_path],
                product_name="demo",
                base_url="http://localhost:8080",
                api_key_env_var="DEMO_API_KEY",
            )
            generate_agentsuit(surface, output_dir)

            sys.path.insert(0, str(output_dir))
            try:
                for mod_name in ["agentsuit.cli", "agentsuit.auth", "agentsuit.http_client", "agentsuit"]:
                    sys.modules.pop(mod_name, None)
                cli_mod = importlib.import_module("agentsuit.cli")

                # Token-based login should not attempt the local callback flow.
                cli_mod.oauth_login_via_local_callback = lambda *args, **kwargs: (_ for _ in ()).throw(
                    AssertionError("oauth_login_via_local_callback should not be called when --token is provided")
                )
                cli_mod.save_oauth_credentials = lambda access_token, source, start_url=None: None
                cli_mod.read_oauth_credentials = lambda: {
                    "access_token": "stub",
                    "source": "cli_token",
                    "start_url": "http://example.com",
                }

                # Avoid rich-print formatting; we want raw JSON in stdout.
                cli_mod.print = builtins.print
                os.environ["DEMO_API_KEY"] = "demo-key"

                buf = io.StringIO()
                with redirect_stdout(buf):
                    cli_mod.auth_login(start_url="http://example.com", token="manual-token")
                payload = json.loads(buf.getvalue())

                self.assertTrue(payload["ok"])
                self.assertTrue(payload["data"]["oauth_logged_in"])
                self.assertEqual(payload["data"]["oauth_source"], "cli_token")
                self.assertEqual(payload["data"]["api_key_env_var"], "DEMO_API_KEY")
                self.assertEqual(payload["meta"]["command"], "auth.login")
            finally:
                sys.path.pop(0)

    def test_parser_handles_nullable_and_default_params(self) -> None:
        with TemporaryDirectory() as tmp:
            file_path = Path(tmp) / "SampleController.kt"
            file_path.write_text(KOTLIN_SAMPLE, encoding="utf-8")
            surface = parse_kotlin_controllers(
                [file_path],
                product_name="demo",
                base_url="http://localhost:8080",
                api_key_env_var="DEMO_API_KEY",
            )

        resources = {r.name: r for r in surface.resources}
        self.assertIn("items", resources)
        get_item = next(op for op in resources["items"].operations if op.operation_id == "get_item")
        params = {p.name: p for p in get_item.params}
        self.assertTrue(params["itemId"].required)
        self.assertFalse(params["after"].required)
        self.assertFalse(params["limit"].required)

    def test_parser_detects_streaming(self) -> None:
        with TemporaryDirectory() as tmp:
            file_path = Path(tmp) / "SampleController.kt"
            file_path.write_text(KOTLIN_SAMPLE, encoding="utf-8")
            surface = parse_kotlin_controllers(
                [file_path],
                product_name="demo",
                base_url="http://localhost:8080",
                api_key_env_var="DEMO_API_KEY",
            )
        stream_op = None
        for resource in surface.resources:
            for op in resource.operations:
                if op.operation_id == "stream_items":
                    stream_op = op
                    break
        self.assertIsNotNone(stream_op)
        assert stream_op is not None
        self.assertTrue(stream_op.supports_streaming)

    def test_generator_emits_stream_flag(self) -> None:
        with TemporaryDirectory() as tmp:
            source_file = Path(tmp) / "SampleController.kt"
            output_dir = Path(tmp) / "out"
            source_file.write_text(KOTLIN_SAMPLE, encoding="utf-8")
            surface = parse_kotlin_controllers(
                [source_file],
                product_name="demo",
                base_url="http://localhost:8080",
                api_key_env_var="DEMO_API_KEY",
            )
            generate_agentsuit(surface, output_dir)
            cli_contents = (output_dir / "agentsuit" / "cli.py").read_text(encoding="utf-8")
            http_contents = (output_dir / "agentsuit" / "http_client.py").read_text(encoding="utf-8")
            skills_contents = (output_dir / "SKILLS.md").read_text(encoding="utf-8")

        self.assertIn("--stream", cli_contents)
        self.assertIn("request_stream(", cli_contents)
        self.assertIn('{"ok": True, "data": {"oauth_logged_out": removed}}', cli_contents)
        self.assertIn('"ok": True', http_contents)
        self.assertIn('"ok": False', http_contents)
        self.assertIn("error.status_code", skills_contents)


if __name__ == "__main__":
    unittest.main()
