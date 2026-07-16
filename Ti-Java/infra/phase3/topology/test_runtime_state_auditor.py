#!/usr/bin/env python3
"""Unit and black-box tests for the Phase 3 runtime-state auditor."""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
import uuid
from dataclasses import dataclass
from typing import Any


SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
PHASE3_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(PHASE3_DIR))

import prepare_run  # noqa: E402
import read_compare  # noqa: E402
import runtime_state_auditor as auditor  # noqa: E402
import topology_guard  # noqa: E402


LEGACY_IMAGE = "legacy@sha256:" + "a" * 64
JAVA_IMAGE = "java@sha256:" + "b" * 64
SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64
SHA_C = "sha256:" + "c" * 64


def prepare(prefix: str, port_offset: int) -> pathlib.Path:
    run_id = f"{prefix}-{uuid.uuid4().hex[:10]}"
    return prepare_run.prepare(argparse.Namespace(
        operation="PREPARE",
        environment="test",
        run_id=run_id,
        legacy_image=LEGACY_IMAGE,
        java_image=JAVA_IMAGE,
        legacy_api_port=28081 + port_offset,
        java_api_port=28080 + port_offset,
        legacy_postgres_port=45431 + port_offset,
        java_postgres_port=45432 + port_offset,
        legacy_redis_port=46378 + port_offset,
        java_redis_port=46379 + port_offset,
    ))


class PreparedPairTestCase(unittest.TestCase):
    legacy_env: pathlib.Path
    java_env: pathlib.Path

    def setUp(self) -> None:
        self.legacy_env = prepare("auditl", 0)
        self.java_env = prepare("auditj", 20)

    def tearDown(self) -> None:
        shutil.rmtree(self.legacy_env.parent, ignore_errors=True)
        shutil.rmtree(self.java_env.parent, ignore_errors=True)

    def audit_environment(self, side: str = "legacy", phase: str = "before") -> dict[str, str]:
        return {
            "TI_READ_COMPARE_ENVIRONMENT": "test",
            "TI_READ_COMPARE_SIDE": side,
            "TI_READ_COMPARE_PHASE": phase,
            "TI_PHASE3_AUDIT_LEGACY_ENV_FILE": str(self.legacy_env),
            "TI_PHASE3_AUDIT_JAVA_ENV_FILE": str(self.java_env),
        }


class ScopeTests(PreparedPairTestCase):
    def test_two_distinct_guarded_runs_select_the_requested_side(self) -> None:
        scope = auditor.resolve_scope(self.audit_environment("java", "after"))
        self.assertEqual("java", scope.side)
        self.assertEqual("after", scope.phase)
        self.assertEqual(self.java_env, scope.topology.env_file)
        self.assertEqual(self.legacy_env, scope.peer_topology.env_file)

    def test_same_guarded_run_is_rejected(self) -> None:
        environment = self.audit_environment()
        environment["TI_PHASE3_AUDIT_JAVA_ENV_FILE"] = str(self.legacy_env)
        with self.assertRaisesRegex(auditor.AuditError, "different guarded runs"):
            auditor.resolve_scope(environment)

    def test_scope_mismatch_is_rejected_before_docker(self) -> None:
        environment = self.audit_environment()
        environment["TI_READ_COMPARE_ENVIRONMENT"] = "local"
        with self.assertRaisesRegex(auditor.AuditError, "does not match"):
            auditor.resolve_scope(environment)


@dataclass
class FakeResult:
    stdout: bytes = b""
    returncode: int = 0


class FakeRunner:
    def __init__(self, scope: auditor.AuditScope) -> None:
        self.scope = scope
        self.preflight_called = False
        self.service_by_id: dict[str, str] = {}
        for index, service in enumerate(
            (f"{scope.side}-api", f"{scope.side}-postgres", f"{scope.side}-redis"), 1
        ):
            self.service_by_id[str(index) * 64] = service
        side = scope.side
        topology = scope.topology
        self.image_environments = {
            auditor.side_value(topology, side, "IMAGE"): ["PATH=/usr/bin", "LANG=C.UTF-8"],
            auditor.POSTGRES_IMAGE: ["PATH=/usr/local/bin", "LANG=en_US.utf8"],
            auditor.REDIS_IMAGE: ["PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"],
        }
        self.environments: dict[str, list[str]] = {}
        self.mounts: dict[str, list[dict[str, Any]]] = {}
        self.tmpfs: dict[str, dict[str, str]] = {}
        self.ports: dict[str, dict[str, Any]] = {}
        self.network_details: dict[str, dict[str, Any]] = {}
        expected_networks = auditor._expected_networks(topology, side)
        for index, (name, (logical_name, internal)) in enumerate(expected_networks.items(), 10):
            identity = f"{index:x}" * 64
            self.network_details[name] = {
                "Id": identity,
                "Name": name,
                "Internal": internal,
                "Labels": {
                    "com.docker.compose.project": topology.project,
                    "com.docker.compose.network": logical_name,
                },
                "Containers": {
                    identity: {"Name": service}
                    for identity, service in self.service_by_id.items()
                },
            }
        self.networks: dict[str, dict[str, dict[str, str]]] = {
            service: {
                name: {"NetworkID": str(document["Id"])}
                for name, document in self.network_details.items()
            }
            for service in self.service_by_id.values()
        }
        for service in self.service_by_id.values():
            kind = service.rsplit("-", 1)[1]
            image = self._image(kind)
            environment = auditor._environment_map(
                self.image_environments[image], f"{service} fake image environment"
            )
            environment.update(auditor._expected_compose_environment(topology, side, kind))
            self.environments[service] = [
                f"{name}={value}" for name, value in reversed(environment.items())
            ]
            self.mounts[service] = [
                self._mount_document(item)
                for item in reversed(auditor._expected_mounts(topology, side, kind))
            ]
            self.tmpfs[service] = {
                destination: "rw,noexec,nosuid,size=67108864"
                for destination in auditor._expected_tmpfs(kind)
            }
            container_port, host_port = auditor._expected_published_port(
                topology, side, kind
            )
            self.ports[service] = {
                container_port: [{"HostIp": "127.0.0.1", "HostPort": host_port}]
            }
            if side == "java" and kind == "api":
                self.ports[service]["9090/tcp"] = None

    def _image(self, kind: str) -> str:
        if kind == "postgres":
            return auditor.POSTGRES_IMAGE
        if kind == "redis":
            return auditor.REDIS_IMAGE
        return auditor.side_value(self.scope.topology, self.scope.side, "IMAGE")

    @staticmethod
    def _mount_document(item: tuple[str, str, str, bool]) -> dict[str, Any]:
        kind, identity, destination, writable = item
        document: dict[str, Any] = {
            "Type": kind,
            "Destination": destination,
            "RW": writable,
        }
        document["Source" if kind == "bind" else "Name"] = identity
        return document

    def preflight_local_context(self) -> None:
        self.preflight_called = True

    def compose_ids(self, service: str, *, running_only: bool) -> list[str]:
        return [next(identity for identity, value in self.service_by_id.items() if value == service)]

    def image_id(self, reference: str) -> str:
        if "postgres" in reference:
            return "sha256:" + "3" * 64
        if "redis" in reference:
            return "sha256:" + "4" * 64
        return "sha256:" + reference.rsplit("sha256:", 1)[1]

    def container_image_id(self, container_id: str) -> str:
        service = self.service_by_id[container_id]
        if service.endswith("postgres"):
            return "sha256:" + "3" * 64
        if service.endswith("redis"):
            return "sha256:" + "4" * 64
        return self.image_id(auditor.side_value(self.scope.topology, self.scope.side, "IMAGE"))

    def docker(self, arguments: list[str], *, capture: bool = False, check: bool = True) -> FakeResult:
        if arguments[:2] == ["image", "inspect"]:
            return FakeResult(json.dumps(
                self.image_environments[arguments[4]], separators=(",", ":")
            ).encode("utf-8"))
        if arguments[:2] == ["network", "inspect"]:
            return FakeResult(json.dumps(
                self.network_details[arguments[4]], separators=(",", ":")
            ).encode("utf-8"))
        if arguments[:2] == ["container", "inspect"]:
            template = arguments[3]
            container_id = arguments[4]
            service = self.service_by_id[container_id]
            if template == "{{json .Config.Labels}}":
                value: Any = {
                    "com.docker.compose.project": self.scope.topology.project,
                    "com.docker.compose.service": service,
                    "com.docker.compose.oneoff": "False",
                }
            elif template == "{{json .State}}":
                value = {"Running": True, "Status": "running", "Health": {"Status": "healthy"}}
            elif template == "{{json .Mounts}}":
                value = self.mounts[service]
            elif template == "{{json .HostConfig.Tmpfs}}":
                value = self.tmpfs[service]
            elif template == "{{json .NetworkSettings.Networks}}":
                value = self.networks[service]
            elif template == "{{json .NetworkSettings.Ports}}":
                value = self.ports[service]
            elif template == "{{json .Config.Env}}":
                value = self.environments[service]
            else:
                raise AssertionError(f"unexpected fake inspect template: {template}")
            return FakeResult(json.dumps(value, separators=(",", ":")).encode("utf-8"))
        if arguments and arguments[0] == "run":
            value = {
                "schema_version": "1",
                "content_sha256": SHA_C,
                "entry_count": 7,
                "excluded_rotated_file_count": 0,
            }
            return FakeResult(json.dumps(value, separators=(",", ":")).encode("utf-8"))
        raise AssertionError(f"unexpected fake Docker command: {arguments}")

    def compose(
        self,
        arguments: list[str],
        *,
        stdin_path: pathlib.Path | None = None,
        stdout_path: pathlib.Path | None = None,
        capture: bool = False,
        check: bool = True,
    ) -> FakeResult:
        if "phase3-audit-role-check" in arguments:
            return FakeResult(b"on|t\n")
        if "phase3-redis-audit" in arguments:
            assert stdout_path is not None
            stdout_path.write_bytes(
                b"phase3-redis-audit-v1\n"
                b"excluded_runtime_key_count=0\n"
                b"included_key_count=1\n"
                + b"1" * 40 + b"|string|-1|" + b"2" * 40 + b"\n"
            )
            return FakeResult()
        raise AssertionError(f"unexpected fake Compose command: {arguments}")

    def stream_sha256(
        self,
        arguments: list[str],
        *,
        stdin_path: pathlib.Path | None = None,
        normalize_pg_restore_sql: bool = False,
    ) -> str:
        self.last_stream_arguments = arguments
        self.last_stream_normalized = normalize_pg_restore_sql
        return SHA_B


class CollectionTests(PreparedPairTestCase):
    def test_state_is_read_compare_schema_compatible_and_redacted(self) -> None:
        scope = auditor.resolve_scope(self.audit_environment())
        runner = FakeRunner(scope)
        document = auditor.build_document(scope, auditor.collect_state(scope, runner))
        validated = read_compare.validate_audit_document(document, "test", "legacy", "before")
        self.assertTrue(runner.preflight_called)
        self.assertEqual(auditor.AUDITOR_ID, validated["auditor"])
        self.assertEqual(SHA_B, validated["state"]["database"]["normalized_data_sha256"])
        self.assertEqual(1, validated["state"]["redis"]["included_key_count"])
        external = validated["state"]["external_writes"]
        self.assertIsInstance(external, dict)
        self.assertFalse(external["runtime_observation_performed"])
        self.assertFalse(external["configured_sink"])
        self.assertNotEqual(0, external)
        serialized = json.dumps(document, sort_keys=True)
        for forbidden in ("PublicSalt", "LIMITER/", "password_hash", "phase3-fixture"):
            self.assertNotIn(forbidden, serialized)
        for key in topology_guard.SECRET_KEYS:
            secret = pathlib.Path(scope.topology.values[key]).read_text(encoding="ascii").strip()
            self.assertNotIn(secret, serialized)

    def test_container_image_mismatch_is_rejected(self) -> None:
        scope = auditor.resolve_scope(self.audit_environment())
        runner = FakeRunner(scope)
        original = runner.container_image_id

        def mismatched(container_id: str) -> str:
            service = runner.service_by_id[container_id]
            return "sha256:" + "f" * 64 if service.endswith("-api") else original(container_id)

        runner.container_image_id = mismatched  # type: ignore[method-assign]
        with self.assertRaisesRegex(auditor.AuditError, "image identity mismatch"):
            auditor.validate_runtime(scope, runner)

    def test_legacy_and_java_runtime_bindings_are_accepted(self) -> None:
        for side in ("legacy", "java"):
            with self.subTest(side=side):
                scope = auditor.resolve_scope(self.audit_environment(side))
                result = auditor.validate_runtime(scope, FakeRunner(scope))
                self.assertTrue(result["all_instances_healthy"])
                self.assertRegex(result["identity_sha256"], r"^sha256:[0-9a-f]{64}$")

    def test_extra_bind_or_tmpfs_mount_is_rejected(self) -> None:
        scope = auditor.resolve_scope(self.audit_environment())
        runner = FakeRunner(scope)
        runner.mounts["legacy-api"].append({
            "Type": "bind",
            "Source": "/tmp/unapproved",
            "Destination": "/unapproved",
            "RW": False,
        })
        with self.assertRaisesRegex(auditor.AuditError, "mount allowlist mismatch"):
            auditor.validate_runtime(scope, runner)

        runner = FakeRunner(scope)
        runner.tmpfs["legacy-api"]["/unapproved"] = "rw,noexec,nosuid,size=4096"
        with self.assertRaisesRegex(auditor.AuditError, "tmpfs mount set mismatch"):
            auditor.validate_runtime(scope, runner)

    def test_docker_desktop_host_mnt_bind_mapping_is_exact(self) -> None:
        scope = auditor.resolve_scope(self.audit_environment())
        runner = FakeRunner(scope)
        entrypoint = next(
            mount for mount in runner.mounts["legacy-api"]
            if mount["Destination"] == "/phase3/legacy-entrypoint.sh"
        )
        expected_source = entrypoint["Source"]
        entrypoint["Source"] = "/host_mnt" + expected_source
        self.assertTrue(auditor.validate_runtime(scope, runner)["all_instances_healthy"])

        runner = FakeRunner(scope)
        entrypoint = next(
            mount for mount in runner.mounts["legacy-api"]
            if mount["Destination"] == "/phase3/legacy-entrypoint.sh"
        )
        entrypoint["Source"] = "/host_mnt_evil" + entrypoint["Source"]
        with self.assertRaisesRegex(auditor.AuditError, "mount allowlist mismatch"):
            auditor.validate_runtime(scope, runner)

    def test_network_set_identity_and_internal_policy_are_fail_closed(self) -> None:
        scope = auditor.resolve_scope(self.audit_environment())
        runner = FakeRunner(scope)
        runner.networks["legacy-api"]["unexpected-network"] = {"NetworkID": "f" * 64}
        with self.assertRaisesRegex(auditor.AuditError, "network set mismatch"):
            auditor.validate_runtime(scope, runner)

        runner = FakeRunner(scope)
        backend = f"{scope.topology.project}-legacy-backend"
        runner.network_details[backend]["Internal"] = False
        with self.assertRaisesRegex(auditor.AuditError, "Internal policy mismatch"):
            auditor.validate_runtime(scope, runner)

        runner = FakeRunner(scope)
        runner.network_details[backend]["Containers"]["f" * 64] = {"Name": "undeclared"}
        with self.assertRaisesRegex(auditor.AuditError, "network member set mismatch"):
            auditor.validate_runtime(scope, runner)

    def test_every_service_requires_its_exact_loopback_published_port(self) -> None:
        for side in ("legacy", "java"):
            scope = auditor.resolve_scope(self.audit_environment(side))
            for service in (f"{side}-api", f"{side}-postgres", f"{side}-redis"):
                with self.subTest(service=service):
                    runner = FakeRunner(scope)
                    binding = next(value for value in runner.ports[service].values() if value)
                    binding[0]["HostIp"] = "0.0.0.0"
                    with self.assertRaisesRegex(
                        auditor.AuditError, "loopback published port mismatch"
                    ):
                        auditor.validate_runtime(scope, runner)

    def test_effective_environment_drift_is_rejected_without_echoing_values(self) -> None:
        scope = auditor.resolve_scope(self.audit_environment("java"))
        runner = FakeRunner(scope)
        secret_value = "must-not-appear-in-audit-output"
        runner.environments["java-api"].append(f"TI_DB_PASSWORD={secret_value}")
        with self.assertRaises(auditor.AuditError) as raised:
            auditor.validate_runtime(scope, runner)
        self.assertIn("effective environment mismatch", str(raised.exception))
        self.assertNotIn(secret_value, str(raised.exception))


class RedisEvidenceTests(unittest.TestCase):
    def test_lua_policy_uses_the_observed_limits_storage_key_shape(self) -> None:
        self.assertIn("local limit_prefix = 'LIMITS:LIMITER/ip:'", auditor.REDIS_AUDIT_LUA)
        self.assertIn("/auth.auth_api.api_auth_login_methods/", auditor.REDIS_AUDIT_LUA)
        self.assertNotIn("string.sub(key, 1, 8) ~= 'LIMITER/'", auditor.REDIS_AUDIT_LUA)

    def test_canonical_rows_are_hashed_without_raw_values(self) -> None:
        raw = (
            b"phase3-redis-audit-v1\n"
            b"excluded_runtime_key_count=2\n"
            b"included_key_count=2\n"
            + b"1" * 40 + b"|hash|-1|" + b"2" * 40 + b"\n"
            + b"3" * 40 + b"|string|1999999999999|" + b"4" * 40 + b"\n"
        )
        content, excluded, included = auditor.parse_redis_audit(raw)
        self.assertRegex(content, r"^sha256:[0-9a-f]{64}$")
        self.assertEqual((2, 2), (excluded, included))

    def test_unknown_type_or_unsorted_rows_are_rejected(self) -> None:
        raw = (
            b"phase3-redis-audit-v1\nexcluded_runtime_key_count=0\n"
            b"included_key_count=1\n" + b"1" * 40 + b"|module|-1|" + b"2" * 40 + b"\n"
        )
        with self.assertRaisesRegex(auditor.AuditError, "canonical rows"):
            auditor.parse_redis_audit(raw)


class CliBlackBoxTests(unittest.TestCase):
    def test_invalid_phase_fails_before_env_file_or_docker_access(self) -> None:
        environment = {
            **os.environ,
            "TI_READ_COMPARE_ENVIRONMENT": "test",
            "TI_READ_COMPARE_SIDE": "legacy",
            "TI_READ_COMPARE_PHASE": "during",
            "TI_PHASE3_AUDIT_LEGACY_ENV_FILE": "/does/not/exist",
            "TI_PHASE3_AUDIT_JAVA_ENV_FILE": "/also/does/not/exist",
        }
        completed = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "runtime_state_auditor.py")],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=environment,
            cwd=tempfile.gettempdir(),
            check=False,
        )
        self.assertEqual(2, completed.returncode)
        self.assertEqual("", completed.stdout)
        self.assertIn("before/after phase is required", completed.stderr)
        self.assertNotIn("Traceback", completed.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
