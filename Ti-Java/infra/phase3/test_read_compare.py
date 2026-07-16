#!/usr/bin/env python3
"""Black-box tests for the Phase 3 local/test READ_COMPARE CLI."""

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional, Tuple


SCRIPT = pathlib.Path(__file__).resolve().with_name("read_compare.py")


class StubHandler(BaseHTTPRequestHandler):
    server_version = "Phase3Stub/1"

    def log_message(self, format: str, *args: Any) -> None:
        return

    def do_GET(self) -> None:
        self._respond(include_body=True)

    def do_HEAD(self) -> None:
        self._respond(include_body=False)

    def do_POST(self) -> None:
        self.server.scenario["hits"].append(("POST", self.path))
        self.send_response(405)
        self.end_headers()

    def _respond(self, include_body: bool) -> None:
        scenario = self.server.scenario
        scenario["hits"].append((self.command, self.path))
        response = scenario["response"]
        body = response.get("raw_body")
        if body is None:
            body = json.dumps(
                response.get("body"), ensure_ascii=False, separators=(",", ":")
            ).encode("utf-8")
        self.send_response(response.get("status", 200))
        self.send_header("Content-Type", response.get("content_type", "application/json"))
        for name, value in response.get("headers", {}).items():
            self.send_header(name, value)
        self.end_headers()
        if include_body and body:
            self.wfile.write(body)


class ReadCompareCliTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.legacy_server = ThreadingHTTPServer(("127.0.0.1", 0), StubHandler)
        cls.java_server = ThreadingHTTPServer(("127.0.0.1", 0), StubHandler)
        cls.legacy_thread = threading.Thread(target=cls.legacy_server.serve_forever, daemon=True)
        cls.java_thread = threading.Thread(target=cls.java_server.serve_forever, daemon=True)
        cls.legacy_thread.start()
        cls.java_thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.legacy_server.shutdown()
        cls.java_server.shutdown()
        cls.legacy_server.server_close()
        cls.java_server.server_close()
        cls.legacy_thread.join(timeout=2)
        cls.java_thread.join(timeout=2)

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="ti-phase3-read-compare-")
        self.directory = pathlib.Path(self.temporary.name)
        self.counter = 0
        self._set_response(self.legacy_server, {"ok": True})
        self._set_response(self.java_server, {"ok": True})

        self.rules = self.directory / "rules.json"
        self._write_json(
            self.rules,
            {
                "schema_version": "1",
                "ruleset_version": "phase3-tests-v1",
                "operations": {
                    "dynamic.read": {
                        "ignore_json_pointers": ["/meta/request_id"],
                        "unordered_array_json_pointers": [],
                        "ignore_response_headers": ["x-request-id"],
                    },
                    "ordered.read": {
                        "ignore_json_pointers": [],
                        "unordered_array_json_pointers": [],
                        "ignore_response_headers": [],
                    },
                    "unordered.read": {
                        "ignore_json_pointers": [],
                        "unordered_array_json_pointers": ["/items"],
                        "ignore_response_headers": [],
                    },
                },
            },
        )
        self.legacy_fingerprint = self.directory / "legacy-fingerprint.json"
        self.java_fingerprint = self.directory / "java-fingerprint.json"
        self._write_fingerprint(
            self.legacy_fingerprint,
            "legacy",
            "legacy-db-identity-a",
            "legacy-redis-identity-a",
            "legacy-volume-identity-a",
        )
        self._write_fingerprint(
            self.java_fingerprint,
            "java",
            "java-db-identity-b",
            "java-redis-identity-b",
            "java-volume-identity-b",
        )
        self.evidence: Dict[Tuple[str, str], pathlib.Path] = {}
        for side in ("legacy", "java"):
            for phase in ("before", "after"):
                path = self.directory / f"{side}-{phase}.json"
                self._write_evidence(path, side, phase)
                self.evidence[(side, phase)] = path
        self.headers = self.directory / "headers.json"
        self._write_json(
            self.headers,
            {"Authorization": "Bearer local-test-only-request-value-123456789"},
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def _write_json(path: pathlib.Path, value: Any) -> None:
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")

    def _write_fingerprint(
        self,
        path: pathlib.Path,
        side: str,
        database: str,
        redis: str,
        volume: str,
    ) -> None:
        self._write_json(
            path,
            {
                "schema_version": "1",
                "environment": "local",
                "side": side,
                "database": database,
                "redis": redis,
                "volume": volume,
            },
        )

    def _write_evidence(
        self,
        path: pathlib.Path,
        side: str,
        phase: str,
        state_override: Optional[Dict[str, Any]] = None,
    ) -> None:
        state: Dict[str, Any] = {
            "database": "stable-database-state",
            "redis": "stable-redis-state",
            "volume": "stable-volume-state",
            "queue": "stable-queue-state",
            "object_store": "stable-object-state",
            "external_writes": 0,
        }
        if state_override:
            state.update(state_override)
        self._write_json(
            path,
            {
                "schema_version": "1",
                "environment": "local",
                "side": side,
                "phase": phase,
                "auditor": "phase3-stub-auditor-v1",
                "state": state,
            },
        )

    @staticmethod
    def _set_response(
        server: ThreadingHTTPServer,
        body: Any,
        status: int = 200,
        headers: Optional[Dict[str, str]] = None,
        content_type: str = "application/json; charset=utf-8",
        raw_body: Optional[bytes] = None,
    ) -> None:
        server.scenario = {
            "hits": [],
            "response": {
                "body": body,
                "status": status,
                "headers": headers or {"ETag": '"fixture-v1"'},
                "content_type": content_type,
                "raw_body": raw_body,
            },
        }

    def _base_arguments(
        self, operation_id: str = "ordered.read", file_evidence: bool = True
    ) -> Tuple[List[str], pathlib.Path]:
        self.counter += 1
        report = self.directory / f"report-{self.counter}.json"
        arguments = [
            sys.executable,
            str(SCRIPT),
            "READ_COMPARE",
            "--environment",
            "local",
            "--operation-id",
            operation_id,
            "--fixture-id",
            "fixture-read-001",
            "--snapshot-id",
            "sanitized-snapshot-001",
            "--legacy-artifact-digest",
            "sha256:" + "a" * 64,
            "--java-artifact-digest",
            "sha256:" + "b" * 64,
            "--legacy-origin",
            f"http://127.0.0.1:{self.legacy_server.server_port}",
            "--java-origin",
            f"http://127.0.0.1:{self.java_server.server_port}",
            "--path",
            "/fixture?case=read",
            "--request-headers-file",
            str(self.headers),
            "--legacy-fingerprint",
            str(self.legacy_fingerprint),
            "--java-fingerprint",
            str(self.java_fingerprint),
            "--normalization-rules",
            str(self.rules),
            "--report",
            str(report),
        ]
        if file_evidence:
            arguments.extend(
                [
                    "--legacy-before-evidence",
                    str(self.evidence[("legacy", "before")]),
                    "--legacy-after-evidence",
                    str(self.evidence[("legacy", "after")]),
                    "--java-before-evidence",
                    str(self.evidence[("java", "before")]),
                    "--java-after-evidence",
                    str(self.evidence[("java", "after")]),
                ]
            )
        return arguments, report

    def _run(
        self,
        operation_id: str = "ordered.read",
        extra: Optional[List[str]] = None,
        file_evidence: bool = True,
    ) -> Tuple[subprocess.CompletedProcess, pathlib.Path]:
        arguments, report = self._base_arguments(operation_id, file_evidence=file_evidence)
        if extra:
            arguments.extend(extra)
        completed = subprocess.run(
            arguments,
            cwd=self.directory,
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
        return completed, report

    @staticmethod
    def _error_code(completed: subprocess.CompletedProcess) -> str:
        return json.loads(completed.stderr)["error"]["code"]

    def test_dynamic_field_allowlist_passes_without_persisting_sensitive_inputs(self) -> None:
        shared_openid = "openid-value-that-must-never-be-persisted"
        self._set_response(
            self.legacy_server,
            {
                "items": [1, 2],
                "nullable": None,
                "meta": {"request_id": "legacy-dynamic-value"},
                "openid": shared_openid,
            },
            headers={"ETag": '"fixture-v1"', "X-Request-ID": "legacy-request-id"},
        )
        self._set_response(
            self.java_server,
            {
                "items": [1, 2],
                "nullable": None,
                "meta": {"request_id": "java-dynamic-value"},
                "openid": shared_openid,
            },
            headers={"ETag": '"fixture-v1"', "X-Request-ID": "java-request-id"},
        )

        completed, report_path = self._run("dynamic.read")

        self.assertEqual(0, completed.returncode, completed.stderr)
        report_text = report_path.read_text(encoding="utf-8")
        report = json.loads(report_text)
        self.assertEqual("pass", report["outcome"])
        self.assertFalse(report["raw_comparison"]["body_sha256_equal"])
        self.assertFalse(report["raw_comparison"]["selected_headers_equal"])
        self.assertEqual(
            report["responses"]["legacy"]["normalized_body_sha256"],
            report["responses"]["java"]["normalized_body_sha256"],
        )
        self.assertEqual(1, report["normalization"]["legacy"]["ignored_applied"])
        self.assertEqual(1, report["normalization"]["legacy"]["headers_ignored_applied"])
        self.assertNotIn(shared_openid, report_text)
        self.assertNotIn("local-test-only-request-value", report_text)
        self.assertFalse(report["request"]["request_headers_persisted"])

    def test_structural_diff_distinguishes_order_missing_null_and_type(self) -> None:
        self._set_response(
            self.legacy_server,
            {"items": ["a", "b"], "missing_or_null": None, "typed": 1},
        )
        self._set_response(
            self.java_server,
            {"items": ["b", "a"], "typed": "1"},
        )

        completed, report_path = self._run("ordered.read")

        self.assertEqual(1, completed.returncode, completed.stderr)
        report = json.loads(report_path.read_text(encoding="utf-8"))
        kinds = {item["kind"] for item in report["differences"]}
        self.assertTrue({"array_order", "missing", "type"}.issubset(kinds))
        missing = next(item for item in report["differences"] if item["kind"] == "missing")
        self.assertEqual("null", missing["legacy"]["type"])
        self.assertEqual("missing", missing["java"]["type"])

    def test_explicit_unordered_array_rule_is_operation_scoped(self) -> None:
        self._set_response(self.legacy_server, {"items": [1, 2, 2]})
        self._set_response(self.java_server, {"items": [2, 1, 2]})

        completed, report_path = self._run("unordered.read")

        self.assertEqual(0, completed.returncode, completed.stderr)
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(1, report["normalization"]["legacy"]["unordered_applied"])
        self.assertEqual([], report["differences"])

    def test_dynamic_normalization_never_hides_field_or_header_presence(self) -> None:
        self._set_response(
            self.legacy_server,
            {"meta": {"request_id": "legacy-value"}},
            headers={"ETag": '"fixture-v1"', "X-Request-ID": "legacy-request-id"},
        )
        self._set_response(
            self.java_server,
            {"meta": {}},
            headers={"ETag": '"fixture-v1"'},
        )

        completed, report_path = self._run("dynamic.read")

        self.assertEqual(1, completed.returncode, completed.stderr)
        report = json.loads(report_path.read_text(encoding="utf-8"))
        missing_scopes = {
            item["scope"] for item in report["differences"] if item["kind"] == "missing"
        }
        self.assertEqual({"body", "header"}, missing_scopes)

    def test_committed_login_methods_rule_requires_exact_fixed_request_id_echo(self) -> None:
        committed_rules_path = SCRIPT.with_name("normalization-rules.v1.json")
        committed_rules = json.loads(committed_rules_path.read_text(encoding="utf-8"))

        self.assertEqual(
            {
                "ignore_json_pointers": [],
                "unordered_array_json_pointers": [],
                "ignore_response_headers": [],
            },
            committed_rules["operations"]["88d7dc05cdbb"],
        )

        fixed_request_id = "phase3-login-methods-read-001"
        self._write_json(self.headers, {"X-Request-ID": fixed_request_id})
        response_body = {"status": "success", "request_id": fixed_request_id, "message": ""}
        response_headers = {"X-Request-ID": fixed_request_id, "X-Frame-Options": "SAMEORIGIN"}
        self._set_response(
            self.legacy_server,
            response_body,
            headers=response_headers,
            content_type="Application/JSON; Charset=UTF-8",
        )
        self._set_response(
            self.java_server,
            response_body,
            headers=response_headers,
            content_type="application/json;charset=utf-8",
        )
        temporary_rules = self.rules
        self.rules = committed_rules_path
        try:
            completed, report_path = self._run("88d7dc05cdbb")
        finally:
            self.rules = temporary_rules

        self.assertEqual(0, completed.returncode, completed.stderr)
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertFalse(report["raw_comparison"]["content_type_equal"])
        self.assertTrue(report["raw_comparison"]["content_type_canonical_equal"])
        self.assertEqual(
            "application/json;charset=utf-8",
            report["responses"]["legacy"]["canonical_content_type"],
        )
        self.assertEqual(
            report["responses"]["legacy"]["canonical_content_type"],
            report["responses"]["java"]["canonical_content_type"],
        )
        self.assertEqual([], report["differences"])

    def test_content_type_parameter_contract_is_never_normalized_away(self) -> None:
        cases = [
            ("application/json;charset=utf-8", "application/json", "missing charset"),
            ("application/json;charset=utf-8", "application/json;charset=gbk", "different charset"),
            (
                "application/json;charset=utf-8",
                "application/json;charset=utf-8;profile=public",
                "extra parameter",
            ),
        ]
        for legacy_content_type, java_content_type, label in cases:
            with self.subTest(label=label):
                self._set_response(
                    self.legacy_server,
                    {"ok": True},
                    content_type=legacy_content_type,
                )
                self._set_response(
                    self.java_server,
                    {"ok": True},
                    content_type=java_content_type,
                )

                completed, report_path = self._run("ordered.read")

                self.assertEqual(1, completed.returncode, completed.stderr)
                report = json.loads(report_path.read_text(encoding="utf-8"))
                self.assertFalse(report["raw_comparison"]["content_type_canonical_equal"])
                self.assertIn(
                    "content_type",
                    {difference["scope"] for difference in report["differences"]},
                )

    def test_content_type_rejects_ows_outside_semicolon_boundaries(self) -> None:
        invalid_values = [
            "application /json;charset=utf-8",
            "application/ json;charset=utf-8",
            "application/json;charset =utf-8",
            "application/json;charset= utf-8",
        ]
        for invalid_value in invalid_values:
            with self.subTest(content_type=invalid_value):
                self._set_response(
                    self.legacy_server,
                    {"ok": True},
                    content_type=invalid_value,
                )
                self._set_response(
                    self.java_server,
                    {"ok": True},
                    content_type="application/json;charset=utf-8",
                )

                completed, report_path = self._run("ordered.read")

                self.assertEqual(2, completed.returncode)
                self.assertEqual("INVALID_CONTENT_TYPE", self._error_code(completed))
                self.assertFalse(report_path.exists())

    def test_any_side_effect_evidence_change_fails_report(self) -> None:
        self._write_evidence(
            self.evidence[("java", "after")],
            "java",
            "after",
            {"database": "changed-database-state"},
        )

        completed, report_path = self._run()

        self.assertEqual(1, completed.returncode, completed.stderr)
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertTrue(report["side_effects"]["java"]["changed"])
        self.assertTrue(any(item["scope"] == "side_effect" for item in report["differences"]))

    def test_redirect_is_rejected_and_not_followed(self) -> None:
        self._set_response(
            self.legacy_server,
            None,
            status=302,
            headers={"Location": "/redirect-target"},
            raw_body=b"",
        )

        completed, report_path = self._run()

        self.assertEqual(2, completed.returncode)
        self.assertEqual("REDIRECT_FORBIDDEN", self._error_code(completed))
        self.assertFalse(report_path.exists())
        self.assertEqual([("GET", "/fixture?case=read")], self.legacy_server.scenario["hits"])

    def test_non_get_empty_or_shared_fingerprint_are_rejected_before_http(self) -> None:
        completed, report_path = self._run(extra=["--method", "POST"])
        self.assertEqual(2, completed.returncode)
        self.assertEqual("METHOD_FORBIDDEN", self._error_code(completed))
        self.assertFalse(report_path.exists())
        self.assertEqual([], self.legacy_server.scenario["hits"])

        self._write_fingerprint(
            self.java_fingerprint,
            "java",
            "",
            "java-redis-identity-b",
            "java-volume-identity-b",
        )
        completed, report_path = self._run()
        self.assertEqual(2, completed.returncode)
        self.assertEqual("EMPTY_FINGERPRINT", self._error_code(completed))
        self.assertFalse(report_path.exists())

        self._write_fingerprint(
            self.java_fingerprint,
            "java",
            "legacy-db-identity-a",
            "java-redis-identity-b",
            "java-volume-identity-b",
        )
        completed, report_path = self._run()
        self.assertEqual(2, completed.returncode)
        self.assertEqual("SHARED_ENVIRONMENT_FINGERPRINT", self._error_code(completed))
        self.assertFalse(report_path.exists())
        self.assertEqual([], self.legacy_server.scenario["hits"])

    def test_existing_report_is_rejected_before_http(self) -> None:
        arguments, report_path = self._base_arguments()
        report_path.write_text("user-owned-evidence", encoding="utf-8")

        completed = subprocess.run(
            arguments,
            cwd=self.directory,
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )

        self.assertEqual(2, completed.returncode)
        self.assertEqual("REPORT_EXISTS", self._error_code(completed))
        self.assertEqual("user-owned-evidence", report_path.read_text(encoding="utf-8"))
        self.assertEqual([], self.legacy_server.scenario["hits"])

    def test_production_non_loopback_and_same_origin_are_rejected(self) -> None:
        cases = [
            (["--fixture-id", "fixture-prod"], "PRODUCTION_FORBIDDEN"),
            (["--legacy-origin", "http://192.0.2.10:18081"], "NON_LOOPBACK_ORIGIN"),
            (
                ["--legacy-origin", f"http://user@127.0.0.1:{self.legacy_server.server_port}"],
                "INVALID_ORIGIN",
            ),
            (
                ["--java-origin", f"http://localhost:{self.legacy_server.server_port}"],
                "SAME_ORIGIN_FORBIDDEN",
            ),
            (["--path", "/fixture?access_token=not-a-real-value"], "SENSITIVE_QUERY_FORBIDDEN"),
        ]
        for extra, expected_code in cases:
            with self.subTest(expected_code=expected_code):
                completed, report_path = self._run(extra=extra)
                self.assertEqual(2, completed.returncode)
                self.assertEqual(expected_code, self._error_code(completed))
                self.assertFalse(report_path.exists())
        self.assertEqual([], self.legacy_server.scenario["hits"])
        self.assertEqual([], self.java_server.scenario["hits"])

        completed, report_path = self._run(extra=["--environment", "production"])
        self.assertEqual(2, completed.returncode)
        self.assertEqual("CLI_ARGUMENT_INVALID", self._error_code(completed))
        self.assertNotIn("production", completed.stderr)
        self.assertFalse(report_path.exists())

    def test_sensitive_body_values_are_hashed_and_unsafe_safe_header_is_blocked(self) -> None:
        legacy_openid = "wx-openid-legacy-raw-value"
        java_openid = "wx-openid-java-raw-value"
        self._set_response(self.legacy_server, {"user_openid": legacy_openid})
        self._set_response(self.java_server, {"user_openid": java_openid})

        completed, report_path = self._run()

        self.assertEqual(1, completed.returncode, completed.stderr)
        report_text = report_path.read_text(encoding="utf-8")
        self.assertNotIn(legacy_openid, report_text)
        self.assertNotIn(java_openid, report_text)
        self.assertNotIn("user_openid", report_text)
        report = json.loads(report_text)
        self.assertTrue(report["differences"][0]["path"].startswith("/$sensitive-"))

        self._set_response(
            self.legacy_server,
            {"ok": True},
            headers={"ETag": "Bearer local-test-output-value-123456789"},
        )
        self._set_response(self.java_server, {"ok": True})
        completed, report_path = self._run()
        self.assertEqual(2, completed.returncode)
        self.assertEqual("SENSITIVE_OUTPUT_BLOCKED", self._error_code(completed))
        self.assertFalse(report_path.exists())

    def test_duplicate_json_keys_are_invalid_and_top_level_null_is_preserved(self) -> None:
        self._set_response(
            self.legacy_server,
            None,
            raw_body=b'{"value":1,"value":2}',
        )
        self._set_response(self.java_server, {"value": 2})

        completed, report_path = self._run()

        self.assertEqual(1, completed.returncode, completed.stderr)
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertTrue(any(item["kind"] == "invalid_json" for item in report["differences"]))
        self.assertFalse(report["responses"]["legacy"]["valid_json"])

        self._set_response(self.legacy_server, None)
        self._set_response(self.java_server, None)
        completed, report_path = self._run()
        self.assertEqual(0, completed.returncode, completed.stderr)
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertTrue(report["responses"]["legacy"]["valid_json"])
        self.assertIn("normalized_body_sha256", report["responses"]["legacy"])

    def test_head_is_supported_and_command_auditor_wraps_each_request(self) -> None:
        auditor = self.directory / "auditor.py"
        auditor.write_text(
            """#!/usr/bin/env python3
import json
import os
side = os.environ["TI_READ_COMPARE_SIDE"]
phase = os.environ["TI_READ_COMPARE_PHASE"]
print(json.dumps({
    "schema_version": "1",
    "environment": os.environ["TI_READ_COMPARE_ENVIRONMENT"],
    "side": side,
    "phase": phase,
    "auditor": "phase3-command-auditor-v1",
    "state": {
        "database": "stable-database-state",
        "redis": "stable-redis-state",
        "volume": "stable-volume-state",
        "queue": "stable-queue-state",
        "object_store": "stable-object-state",
        "external_writes": 0
    }
}))
""",
            encoding="utf-8",
        )
        os.chmod(auditor, 0o700)

        completed, report_path = self._run(
            extra=[
                "--method",
                "HEAD",
                "--legacy-auditor-command",
                str(auditor),
                "--java-auditor-command",
                str(auditor),
            ],
            file_evidence=False,
        )

        self.assertEqual(0, completed.returncode, completed.stderr)
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual("command", report["side_effects"]["legacy"]["source_kind"])
        self.assertEqual(0, report["responses"]["legacy"]["body_size"])
        self.assertEqual([("HEAD", "/fixture?case=read")], self.legacy_server.scenario["hits"])
        self.assertEqual([("HEAD", "/fixture?case=read")], self.java_server.scenario["hits"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
