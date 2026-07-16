#!/usr/bin/env python3
"""Black-box and state-machine tests for the Phase 3 switch infrastructure."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest
import uuid
from dataclasses import dataclass
from unittest import mock


SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import prepare_run  # noqa: E402
import rehearse_switch  # noqa: E402
import snapshot_bundle  # noqa: E402
import topology_guard  # noqa: E402


LEGACY_IMAGE = "legacy@sha256:" + "a" * 64
JAVA_IMAGE = "java@sha256:" + "b" * 64
POSTGRES_IMAGE = (
    "postgres:18.4-alpine@sha256:"
    "9a8afca54e7861fd90fab5fdf4c42477a6b1cb7d293595148e674e0a3181de15"
)
REDIS_IMAGE = (
    "redis:7.4.7-alpine@sha256:"
    "02f2cc4882f8bf87c79a220ac958f58c700bdec0dfb9b9ea61b62fb0e8f1bfcf"
)
ALL_SERVICES = (
    "legacy-api", "legacy-postgres", "legacy-redis",
    "java-api", "java-postgres", "java-redis",
)


class DockerClientBoundaryTests(unittest.TestCase):
    @staticmethod
    def runner(environment: dict[str, str], inspected_endpoint: str):
        runner = object.__new__(rehearse_switch.DockerRunner)
        runner.environment = dict(environment)
        result = subprocess.CompletedProcess(
            args=["docker", "context", "inspect"],
            returncode=0,
            stdout=(inspected_endpoint + "\n").encode(),
            stderr=b"",
        )
        runner.docker = mock.Mock(return_value=result)
        runner.compose = mock.Mock(return_value=result)
        return runner

    def test_local_socket_host_is_the_only_accepted_docker_override(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ti-phase3-docker-boundary-") as raw:
            root = pathlib.Path(raw)
            socket_path = root / "docker.sock"
            regular_path = root / "not-a-socket"
            regular_path.write_text("not a socket\n", encoding="utf-8")
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as local_socket:
                local_socket.bind(str(socket_path))
                endpoint = f"unix://{socket_path}"

                for environment in ({}, {"DOCKER_HOST": endpoint}):
                    with self.subTest(accepted_environment=environment):
                        runner = self.runner(environment, endpoint)
                        runner.preflight_local_context()
                        self.assertEqual(endpoint, runner.environment["DOCKER_HOST"])
                        runner.docker.assert_called_once()
                        runner.compose.assert_called_once_with(["config", "--quiet"])

                frozen = self.runner({"DOCKER_HOST": endpoint}, endpoint)
                with mock.patch.dict(os.environ, {"DOCKER_HOST": "tcp://remote:2376"}):
                    frozen.preflight_local_context()

                rejected = (
                    ({"DOCKER_HOST": ""}, endpoint, "DOCKER_HOST"),
                    ({"DOCKER_HOST": "tcp://remote:2376"}, endpoint, "DOCKER_HOST"),
                    ({"DOCKER_HOST": "unix://relative.sock"}, endpoint, "DOCKER_HOST"),
                    ({"DOCKER_HOST": f"unix://{root / 'missing.sock'}"}, endpoint, "DOCKER_HOST"),
                    ({"DOCKER_HOST": f"unix://{regular_path}"}, endpoint, "DOCKER_HOST"),
                    ({"DOCKER_CONTEXT": ""}, endpoint, "DOCKER_CONTEXT"),
                    ({"DOCKER_TLS": ""}, endpoint, "DOCKER_TLS"),
                    ({"DOCKER_TLS_VERIFY": ""}, endpoint, "DOCKER_TLS_VERIFY"),
                    ({"DOCKER_CERT_PATH": ""}, endpoint, "DOCKER_CERT_PATH"),
                    ({"DOCKER_HOST": endpoint}, "unix:///different.sock", "endpoint mismatch"),
                    ({}, "tcp://remote:2376", "non-local endpoint"),
                    ({}, "ssh://remote", "non-local endpoint"),
                    ({}, "unix://relative.sock", "non-local endpoint"),
                    ({}, f"unix://{root / 'missing.sock'}", "non-local endpoint"),
                    ({}, f"unix://{regular_path}", "non-local endpoint"),
                )
                for environment, inspected, message in rejected:
                    with self.subTest(rejected_environment=environment, inspected=inspected):
                        runner = self.runner(environment, inspected)
                        with self.assertRaisesRegex(rehearse_switch.RehearsalError, message):
                            runner.preflight_local_context()


def unique_run_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def prepare(run_id: str) -> pathlib.Path:
    return prepare_run.prepare(argparse.Namespace(
        operation="PREPARE",
        environment="test",
        run_id=run_id,
        legacy_image=LEGACY_IMAGE,
        java_image=JAVA_IMAGE,
        legacy_api_port=28081,
        java_api_port=28080,
        legacy_postgres_port=45431,
        java_postgres_port=45432,
        legacy_redis_port=46378,
        java_redis_port=46379,
    ))


class PreparedRunTestCase(unittest.TestCase):
    env_file: pathlib.Path

    def setUp(self) -> None:
        self.env_file = prepare(unique_run_id("gate"))

    def tearDown(self) -> None:
        shutil.rmtree(self.env_file.parent, ignore_errors=True)


class GuardBlackBoxTests(PreparedRunTestCase):
    def invoke_guard(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "topology_guard.py"), "VALIDATE",
             "--env-file", str(self.env_file)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            cwd="/tmp",
        )

    def replace_env(self, key: str, value: str) -> None:
        lines = self.env_file.read_text(encoding="utf-8").splitlines()
        updated = [f"{key}={value}" if line.startswith(key + "=") else line for line in lines]
        self.env_file.write_text("\n".join(updated) + "\n", encoding="utf-8")
        os.chmod(self.env_file, 0o600)

    def test_independent_working_directory_and_redacted_report(self) -> None:
        result = self.invoke_guard()
        self.assertEqual(0, result.returncode, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual("test", report["environment"])
        self.assertTrue(report["ports_are_distinct"])
        self.assertNotIn("password", result.stdout.lower())
        self.assertNotIn(str(self.env_file.parent), result.stdout)

    def test_shared_volume_is_rejected(self) -> None:
        values = topology_guard.load_env_file(self.env_file)
        self.replace_env("TI_PHASE3_JAVA_PG_VOLUME", values["TI_PHASE3_LEGACY_PG_VOLUME"])
        result = self.invoke_guard()
        self.assertEqual(2, result.returncode)
        self.assertIn("SHARED_VOLUME_FORBIDDEN", result.stderr)

    def test_production_environment_is_rejected(self) -> None:
        self.replace_env("TI_PHASE3_ENVIRONMENT", "production")
        result = self.invoke_guard()
        self.assertEqual(2, result.returncode)
        self.assertIn("PRODUCTION_FORBIDDEN", result.stderr)

    def test_permissive_secret_mode_is_rejected(self) -> None:
        topology = topology_guard.guard_env_file(self.env_file)
        secret_path = pathlib.Path(topology.values["TI_PHASE3_JAVA_REDIS_SECRET_FILE"])
        os.chmod(secret_path, 0o644)
        result = self.invoke_guard()
        self.assertEqual(2, result.returncode)
        self.assertIn("permissions are forbidden", result.stderr)

    def test_same_artifact_digest_under_different_names_is_rejected(self) -> None:
        self.replace_env("TI_PHASE3_JAVA_IMAGE", "different-name@sha256:" + "a" * 64)
        result = self.invoke_guard()
        self.assertEqual(2, result.returncode)
        self.assertIn("image digests must differ", result.stderr)


class SnapshotBlackBoxTests(PreparedRunTestCase):
    def create_snapshot(self) -> tuple[topology_guard.GuardedTopology, pathlib.Path]:
        topology = topology_guard.guard_env_file(self.env_file)
        source_dump = self.env_file.parent / ".fixture.dump"
        descriptor = os.open(source_dump, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(b"PGDMPphase3-fixture")
        stopped = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace(
            "+00:00", "Z")
        bundle = snapshot_bundle.create_bundle(
            topology,
            snapshot_id=f"{topology.run_id}-fixture",
            source_side="legacy",
            target_side="java",
            observed_stopped_at=stopped,
            verified_stopped_after_dump_at=stopped,
            server_version_num="180004",
            source_dump=source_dump,
            archive_list_sha256="sha256:" + "c" * 64,
            canonical_sql_sha256="sha256:" + "d" * 64,
        )
        source_dump.unlink()
        return topology, bundle

    def invoke_validate(self, bundle: pathlib.Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "snapshot_bundle.py"), "VALIDATE",
             "--env-file", str(self.env_file), "--bundle", str(bundle),
             "--expected-source", "legacy", "--expected-target", "java"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            cwd="/tmp",
        )

    def test_bundle_validates_from_unrelated_working_directory(self) -> None:
        _, bundle = self.create_snapshot()
        result = self.invoke_validate(bundle)
        self.assertEqual(0, result.returncode, result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["valid"])
        self.assertNotIn("PGDMP", result.stdout)

    def test_payload_tamper_is_rejected(self) -> None:
        _, bundle = self.create_snapshot()
        with (bundle / "database.dump").open("ab") as handle:
            handle.write(b"tamper")
        result = self.invoke_validate(bundle)
        self.assertEqual(2, result.returncode)
        self.assertIn("checksum mismatch", result.stderr)

    def test_extra_file_is_rejected(self) -> None:
        _, bundle = self.create_snapshot()
        extra = bundle / "unexpected"
        descriptor = os.open(extra, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.close(descriptor)
        result = self.invoke_validate(bundle)
        self.assertEqual(2, result.returncode)
        self.assertIn("missing or extra", result.stderr)

    def test_bundle_directory_must_match_snapshot_id(self) -> None:
        _, bundle = self.create_snapshot()
        renamed = bundle.with_name(bundle.name + "-renamed")
        os.rename(bundle, renamed)
        result = self.invoke_validate(renamed)
        self.assertEqual(2, result.returncode)
        self.assertIn("directory/id mismatch", result.stderr)


@dataclass
class FakeResult:
    returncode: int = 0
    stdout: bytes = b""


class FakeRunner:
    def __init__(self, topology: topology_guard.GuardedTopology,
                 direction: rehearse_switch.Direction, *, fail_restore: bool = False,
                 fail_retire_source: bool = False) -> None:
        self.topology = topology
        self.direction = direction
        overrides = rehearse_switch.rollback_overrides(topology, direction.generation) \
            if direction.operation == "ROLLBACK" else {}
        self.environment = {**topology.values, **overrides}
        self.fail_restore = fail_restore
        self.fail_retire_source = fail_retire_source
        self.source_services = {
            direction.source_api, direction.source_postgres, direction.source_redis,
        }
        self.containers = set(self.source_services)
        self.running = set(self.source_services)
        self.volumes = {
            rehearse_switch.side_value(topology, direction.source, suffix)
            for suffix in ("PG_VOLUME", "REDIS_VOLUME", "APP_VOLUME")
        }
        self.container_ids = {
            service: f"{index:064x}" for index, service in enumerate(ALL_SERVICES, 1)
        }
        self.service_by_id = {
            container_id: service for service, container_id in self.container_ids.items()
        }
        self.runtime = {
            service: self._runtime(service) for service in ALL_SERVICES
        }

    @staticmethod
    def _kind(service: str) -> str:
        return service.split("-", 1)[1]

    @staticmethod
    def _side(service: str) -> str:
        return service.split("-", 1)[0]

    def _value(self, side: str, suffix: str) -> str:
        prefix = "TI_PHASE3_LEGACY" if side == "legacy" else "TI_PHASE3_JAVA"
        return self.environment[f"{prefix}_{suffix}"]

    def _image_reference(self, service: str) -> str:
        kind = self._kind(service)
        if kind == "postgres":
            return POSTGRES_IMAGE
        if kind == "redis":
            return REDIS_IMAGE
        return self._value(self._side(service), "IMAGE")

    def _mounts(self, service: str) -> list[dict[str, object]]:
        side = self._side(service)
        kind = self._kind(service)
        if kind == "postgres":
            data = (self._value(side, "PG_VOLUME"), "/var/lib/postgresql")
            binds = (
                (str(SCRIPT_DIR / "postgres/010-bootstrap-roles.sh"),
                 "/docker-entrypoint-initdb.d/010-bootstrap-roles.sh"),
                (str(SCRIPT_DIR / "postgres/grant-after-restore.sql"),
                 "/usr/local/share/grant-after-restore.sql"),
                (self._value(side, "DB_OWNER_SECRET_FILE"),
                 "/run/secrets/db.owner.password"),
                (self._value(side, "DB_APP_SECRET_FILE"),
                 "/run/secrets/db.app.password"),
                (self._value(side, "DB_AUDIT_SECRET_FILE"),
                 "/run/secrets/db.audit.password"),
            )
            tmpfs = ("/tmp", "/var/run/postgresql")
        elif kind == "redis":
            data = (self._value(side, "REDIS_VOLUME"), "/data")
            binds = (
                (str(SCRIPT_DIR / "runtime/redis-entrypoint.sh"),
                 "/phase3/redis-entrypoint.sh"),
                (self._value(side, "REDIS_SECRET_FILE"), "/run/secrets/redis.password"),
            )
            tmpfs = ("/tmp",)
        elif side == "legacy":
            data = (self._value(side, "APP_VOLUME"), "/data")
            binds = (
                (str(SCRIPT_DIR / "runtime/legacy-entrypoint.sh"),
                 "/phase3/legacy-entrypoint.sh"),
                (self._value(side, "DB_APP_SECRET_FILE"), "/run/secrets/db.app.password"),
                (self._value(side, "REDIS_SECRET_FILE"), "/run/secrets/redis.password"),
                (self._value(side, "FLASK_SECRET_FILE"), "/run/secrets/flask.secret"),
            )
            tmpfs = ("/tmp",)
        else:
            data = (self._value(side, "APP_VOLUME"), "/app/data")
            binds = (
                (str(SCRIPT_DIR / "runtime/java-entrypoint.sh"),
                 "/phase3/java-entrypoint.sh"),
                (self._value(side, "DB_APP_SECRET_FILE"), "/run/secrets/ti.db.password"),
                (self._value(side, "REDIS_SECRET_FILE"), "/run/secrets/ti.redis.password"),
            )
            tmpfs = ("/tmp",)
        mounts: list[dict[str, object]] = [{
            "Type": "volume", "Name": data[0], "Source": data[0],
            "Destination": data[1], "RW": True,
        }]
        mounts.extend({
            "Type": "bind",
            "Source": "/host_mnt" + source if source.startswith(str(SCRIPT_DIR)) else source,
            "Destination": destination, "RW": False,
        } for source, destination in binds)
        mounts.extend({
            "Type": "tmpfs", "Source": "", "Destination": destination, "RW": True,
        } for destination in tmpfs)
        return mounts

    def _runtime(self, service: str) -> dict[str, object]:
        side = self._side(service)
        kind = self._kind(service)
        container_port = {
            "api": "8000/tcp" if side == "legacy" else "8080/tcp",
            "postgres": "5432/tcp",
            "redis": "6379/tcp",
        }[kind]
        host_port = self._value(side, {
            "api": "API_PORT", "postgres": "POSTGRES_PORT", "redis": "REDIS_PORT",
        }[kind])
        ports: dict[str, object] = {
            container_port: [{"HostIp": "127.0.0.1", "HostPort": host_port}],
        }
        if service == "java-api":
            ports["9090/tcp"] = None
        return {
            "Image": self.image_id(self._image_reference(service)),
            "Labels": {
                "com.docker.compose.project": self.topology.project,
                "com.docker.compose.service": service,
                "com.docker.compose.oneoff": "False",
                "com.docker.compose.project.config_files": str(rehearse_switch.COMPOSE_FILE),
                "com.docker.compose.project.working_dir": str(rehearse_switch.SCRIPT_DIR),
                "com.docker.compose.config-hash": "c" * 64,
            },
            "State": {"Running": True, "Status": "running", "Health": {"Status": "healthy"}},
            "Mounts": self._mounts(service),
            "Tmpfs": {
                mount["Destination"]: "rw,noexec,nosuid"
                for mount in self._mounts(service) if mount["Type"] == "tmpfs"
            },
            "Networks": {
                f"{self.topology.project}-{side}-backend": {"NetworkID": "d" * 64},
                f"{self.topology.project}-{side}-host-access": {"NetworkID": "e" * 64},
            },
            "Ports": ports,
        }

    def preflight_local_context(self) -> None:
        return None

    def compose_ids(self, service: str, *, running_only: bool) -> list[str]:
        present = service in (self.running if running_only else self.containers)
        return [self.container_ids[service]] if present else []

    def volume_exists(self, name: str) -> bool:
        return name in self.volumes

    def docker(self, arguments, *, capture=False, check=True):
        if arguments[:2] == ["volume", "rm"]:
            self.volumes.discard(arguments[2])
        return FakeResult()

    def image_id(self, reference):
        return "sha256:" + reference.rsplit("sha256:", 1)[1]

    def container_image_id(self, container_id):
        return self.runtime[self.service_by_id[container_id]]["Image"]

    def container_json(self, container_id: str, template: str, label: str):
        service = self.service_by_id[container_id]
        field = {
            "{{json .Config.Labels}}": "Labels",
            "{{json .State}}": "State",
            "{{json .Mounts}}": "Mounts",
            "{{json .HostConfig.Tmpfs}}": "Tmpfs",
            "{{json .NetworkSettings.Networks}}": "Networks",
            "{{json .NetworkSettings.Ports}}": "Ports",
        }[template]
        return json.loads(json.dumps(self.runtime[service][field]))

    @staticmethod
    def network_internal(name: str) -> bool:
        return name.endswith("-backend")

    def compose(self, arguments, *, stdin_path=None, stdout_path=None,
                capture=False, check=True):
        arguments = list(arguments)
        if arguments[0] == "stop":
            services = arguments[3:]
            if self.fail_retire_source and len(services) > 1 \
                    and self.direction.source_api in services:
                raise rehearse_switch.CommandError("injected source retirement failure")
            for service in services:
                self.running.discard(service)
            return FakeResult()
        if arguments[0] == "rm":
            services = arguments[3:]
            for service in services:
                self.running.discard(service)
                self.containers.discard(service)
            return FakeResult()
        if arguments[0] == "up":
            services = [value for value in arguments if value in {
                "legacy-api", "legacy-postgres", "legacy-redis",
                "java-api", "java-postgres", "java-redis",
            }]
            for service in services:
                self.containers.add(service)
                self.running.add(service)
                if service.endswith("postgres"):
                    key = rehearse_switch.target_volume_keys(service.removesuffix("-postgres"))[0]
                    self.volumes.add(self.environment[key])
                elif service.endswith("redis"):
                    key = rehearse_switch.target_volume_keys(service.removesuffix("-redis"))[1]
                    self.volumes.add(self.environment[key])
                elif service.endswith("api"):
                    key = rehearse_switch.target_volume_keys(service.removesuffix("-api"))[2]
                    self.volumes.add(self.environment[key])
            return FakeResult()
        if stdout_path is not None and "pg_dump" in arguments:
            descriptor = os.open(stdout_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(b"PGDMPstable-semantic-fixture")
            return FakeResult()
        if "pg_restore" in arguments and "--exit-on-error" in arguments:
            if self.fail_restore:
                raise rehearse_switch.CommandError("injected restore failure")
            return FakeResult()
        command_text = " ".join(arguments)
        if "SHOW server_version_num" in command_text:
            return FakeResult(stdout=b"180004\n")
        if rehearse_switch.POSTGRES_RELATION_COUNT_SQL in arguments:
            return FakeResult(stdout=b"0\n")
        if "redis-cli --no-auth-warning dbsize" in command_text:
            return FakeResult(stdout=b"0\n")
        if "SHOW default_transaction_read_only" in command_text:
            return FakeResult(stdout=b"on\n" if "phase3-audit-probe" in arguments else b"off\n")
        return FakeResult()

    def stream_sha256(self, arguments, *, stdin_path=None, normalize_pg_restore_sql=False):
        if "--list" in arguments:
            return "sha256:" + "c" * 64
        return "sha256:" + "d" * 64


class RehearsalStateMachineTests(PreparedRunTestCase):
    @staticmethod
    def canonical_fingerprint(*lines: bytes, token: bytes = b"a" * 64) -> str:
        hasher = rehearse_switch.PgRestoreCanonicalHasher()
        hasher.update(b"-- PostgreSQL database dump\n\n\\restrict " + token + b"\n")
        for line in lines:
            hasher.update(line)
        hasher.update(b"\\unrestrict " + token + b"\n")
        return hasher.finish()

    def test_canonical_sql_only_normalizes_matching_guard_tokens(self) -> None:
        def fingerprint(token: bytes) -> str:
            return self.canonical_fingerprint(
                b"CREATE TABLE example(id bigint);\n", token=token)

        self.assertEqual(fingerprint(b"a" * 64), fingerprint(b"B" * 64))
        hasher = rehearse_switch.PgRestoreCanonicalHasher()
        hasher.update(b"-- dump\n\\restrict " + b"a" * 64 + b"\n")
        with self.assertRaises(rehearse_switch.RehearsalError):
            hasher.update(b"\\unrestrict " + b"b" * 64 + b"\n")

    def test_canonical_sql_folds_only_the_proven_postgres_check_array_rewrite(self) -> None:
        source = (
            b"    CONSTRAINT ck_backup_jobs_status CHECK (((status)::text = ANY "
            b"((ARRAY['queued'::character varying, 'running'::character varying, "
            b"'completed'::character varying, 'failed'::character varying, "
            b"'deleting'::character varying])::text[]))),\n"
            b"    CONSTRAINT ck_backup_jobs_trigger CHECK (((trigger)::text = ANY "
            b"((ARRAY['manual'::character varying, "
            b"'scheduled'::character varying])::text[])))\n"
            b"    CONSTRAINT ck_edu_grade_overview_source CHECK (((source)::text = ANY "
            b"((ARRAY['official'::character varying, 'calculated'::character varying, "
            b"'unavailable'::character varying])::text[]))),\n"
        )
        roundtrip = (
            b"    CONSTRAINT ck_backup_jobs_status CHECK (((status)::text = ANY "
            b"(ARRAY[('queued'::character varying)::text, "
            b"('running'::character varying)::text, ('completed'::character varying)::text, "
            b"('failed'::character varying)::text, "
            b"('deleting'::character varying)::text]))),\n"
            b"    CONSTRAINT ck_backup_jobs_trigger CHECK (((trigger)::text = ANY "
            b"(ARRAY[('manual'::character varying)::text, "
            b"('scheduled'::character varying)::text])))\n"
            b"    CONSTRAINT ck_edu_grade_overview_source CHECK (((source)::text = ANY "
            b"(ARRAY[('official'::character varying)::text, "
            b"('calculated'::character varying)::text, "
            b"('unavailable'::character varying)::text]))),\n"
        )
        self.assertEqual(
            self.canonical_fingerprint(source),
            self.canonical_fingerprint(roundtrip, token=b"B" * 64),
        )

    def test_canonical_sql_preserves_array_value_order_cast_and_expression_changes(self) -> None:
        source = (
            b"    CONSTRAINT ck_example_status CHECK (((status)::text = ANY "
            b"((ARRAY['queued'::character varying, "
            b"'running'::character varying])::text[]))),\n"
        )
        non_equivalent_roundtrips = {
            "value": (
                b"    CONSTRAINT ck_example_status CHECK (((status)::text = ANY "
                b"(ARRAY[('queued'::character varying)::text, "
                b"('failed'::character varying)::text]))),\n"
            ),
            "order": (
                b"    CONSTRAINT ck_example_status CHECK (((status)::text = ANY "
                b"(ARRAY[('running'::character varying)::text, "
                b"('queued'::character varying)::text]))),\n"
            ),
            "cast": (
                b"    CONSTRAINT ck_example_status CHECK (((status)::text = ANY "
                b"(ARRAY[('queued'::character varying)::varchar, "
                b"('running'::character varying)::text]))),\n"
            ),
            "expression": (
                b"    CONSTRAINT ck_example_status CHECK (((status)::text = ANY "
                b"(ARRAY[lower(('queued'::character varying)::text), "
                b"('running'::character varying)::text]))),\n"
            ),
            "non_ascii": (
                "    CONSTRAINT ck_example_status CHECK (((status)::text = ANY "
                "(ARRAY[('排队'::character varying)::text, "
                "('running'::character varying)::text]))),\n".encode("utf-8")
            ),
            "whitespace": (
                b"    CONSTRAINT ck_example_status CHECK (((status)::text = ANY "
                b"(ARRAY[('queued'::character varying)::text,  "
                b"('running'::character varying)::text]))),\n"
            ),
        }
        source_fingerprint = self.canonical_fingerprint(source)
        for label, candidate in non_equivalent_roundtrips.items():
            with self.subTest(label=label):
                self.assertNotEqual(source_fingerprint, self.canonical_fingerprint(candidate))

    def test_snapshot_manifest_pins_the_canonicalization_contract(self) -> None:
        self.assertEqual(
            "pg-restore-sql-v2-restrict-token-static-ascii-varchar-text-array",
            snapshot_bundle.PG_RESTORE_CANONICALIZATION,
        )
        self.assertEqual(
            snapshot_bundle.PG_RESTORE_CANONICALIZATION,
            rehearse_switch.PgRestoreCanonicalHasher.canonicalization,
        )

    def make_rehearsal(self, direction: rehearse_switch.Direction, *, fail_restore=False,
                       fail_retire_source=False):
        topology = topology_guard.guard_env_file(self.env_file)
        runner = FakeRunner(
            topology, direction,
            fail_restore=fail_restore,
            fail_retire_source=fail_retire_source,
        )
        if direction.operation == "CUTOVER":
            confirmation = f"STOP_LEGACY_CAPTURE_RESTORE_JAVA:{topology.run_id}"
        else:
            confirmation = (
                f"STOP_JAVA_CAPTURE_RESTORE_LEGACY:{topology.run_id}:{direction.generation}"
            )
        return topology, runner, rehearse_switch.SwitchRehearsal(
            topology, direction, runner, confirmation)

    def test_cutover_stops_source_before_snapshot_and_never_dual_runs(self) -> None:
        direction = rehearse_switch.Direction("CUTOVER", "legacy", "java", "initial")
        _, runner, rehearsal = self.make_rehearsal(direction)
        report_path = rehearsal.run()
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual("passed", report["status"])
        self.assertEqual(
            snapshot_bundle.PG_RESTORE_CANONICALIZATION,
            report["snapshot"]["canonicalization"],
        )
        self.assertNotIn("legacy-api", runner.running)
        self.assertIn("java-api", runner.running)
        self.assertFalse(report["safety"]["dual_write_observed"])
        self.assertEqual([
            "guarded_inputs_and_fresh_target_verified",
            "source_api_stopped_and_observed",
            "controlled_snapshot_created_and_validated",
            "fresh_target_data_plane_started_and_empty",
            "snapshot_restored_transactionally_and_semantically_verified",
            "source_containers_retired_without_deleting_source_volumes",
            "target_api_healthy_with_source_retired",
        ], report["sequence"])

    def test_preflight_rejects_wrong_data_volume_for_every_source_service(self) -> None:
        directions = (
            rehearse_switch.Direction("CUTOVER", "legacy", "java", "initial"),
            rehearse_switch.Direction("ROLLBACK", "java", "legacy", "rb001"),
        )
        for direction in directions:
            for service in (
                direction.source_api, direction.source_postgres, direction.source_redis,
            ):
                with self.subTest(operation=direction.operation, service=service):
                    _, runner, rehearsal = self.make_rehearsal(direction)
                    data_mount = next(
                        mount for mount in runner.runtime[service]["Mounts"]
                        if mount["Type"] == "volume"
                    )
                    data_mount["Name"] = f"{runner.topology.project}-drift-volume"
                    with self.assertRaisesRegex(
                            rehearse_switch.RehearsalError, "volume|mount"):
                        rehearsal.preflight()

    def test_preflight_rejects_source_runtime_drift(self) -> None:
        direction = rehearse_switch.Direction("CUTOVER", "legacy", "java", "initial")

        def wrong_image(runner: FakeRunner) -> None:
            runner.runtime[direction.source_postgres]["Image"] = "sha256:" + "f" * 64

        def wrong_label(runner: FakeRunner) -> None:
            runner.runtime[direction.source_api]["Labels"][
                "com.docker.compose.project"
            ] = "foreign-project"

        def unhealthy(runner: FakeRunner) -> None:
            runner.runtime[direction.source_redis]["State"]["Health"]["Status"] = "unhealthy"

        def extra_mount(runner: FakeRunner) -> None:
            runner.runtime[direction.source_api]["Mounts"].append({
                "Type": "bind", "Source": "/tmp/drift", "Destination": "/drift", "RW": True,
            })

        def wrong_bind_source(runner: FakeRunner) -> None:
            bind_mount = next(
                mount for mount in runner.runtime[direction.source_api]["Mounts"]
                if mount["Type"] == "bind"
            )
            bind_mount["Source"] = "/host_mnt/forged" + str(SCRIPT_DIR)

        def extra_network(runner: FakeRunner) -> None:
            runner.runtime[direction.source_postgres]["Networks"]["shared-drift"] = {
                "NetworkID": "f" * 64,
            }

        def public_port(runner: FakeRunner) -> None:
            bindings = runner.runtime[direction.source_redis]["Ports"]["6379/tcp"]
            bindings[0]["HostIp"] = "0.0.0.0"

        cases = (
            ("image", wrong_image),
            ("labels", wrong_label),
            ("health", unhealthy),
            ("mounts", extra_mount),
            ("bind-source", wrong_bind_source),
            ("networks", extra_network),
            ("ports", public_port),
        )
        for label, mutate in cases:
            with self.subTest(drift=label):
                _, runner, rehearsal = self.make_rehearsal(direction)
                mutate(runner)
                with self.assertRaises(rehearse_switch.RehearsalError):
                    rehearsal.preflight()

    def test_preflight_accepts_only_exact_or_strict_host_mnt_bind_source_equivalence(
            self) -> None:
        direction = rehearse_switch.Direction("CUTOVER", "legacy", "java", "initial")
        _, _, desktop_rehearsal = self.make_rehearsal(direction)
        desktop_rehearsal.preflight()

        _, exact_runner, exact_rehearsal = self.make_rehearsal(direction)
        for service in exact_runner.source_services:
            for mount in exact_runner.runtime[service]["Mounts"]:
                source = mount.get("Source")
                if mount["Type"] == "bind" and source.startswith("/host_mnt"):
                    mount["Source"] = source.removeprefix("/host_mnt")
        exact_rehearsal.preflight()

        _, forged_runner, forged_rehearsal = self.make_rehearsal(direction)
        bind_mount = next(
            mount for mount in forged_runner.runtime[direction.source_postgres]["Mounts"]
            if mount["Type"] == "bind"
        )
        bind_mount["Source"] = "/host_mnt/Users/forged/source"
        with self.assertRaisesRegex(rehearse_switch.RehearsalError, "bind mount source"):
            forged_rehearsal.preflight()

    def test_snapshot_rechecks_actual_source_postgres_volume_after_api_stop(self) -> None:
        direction = rehearse_switch.Direction("CUTOVER", "legacy", "java", "initial")
        _, runner, rehearsal = self.make_rehearsal(direction)
        rehearsal.preflight()
        observed_stopped_at = rehearsal.stop_source()
        data_mount = next(
            mount for mount in runner.runtime[direction.source_postgres]["Mounts"]
            if mount["Type"] == "volume"
        )
        data_mount["Name"] = f"{runner.topology.project}-post-stop-drift"
        with self.assertRaisesRegex(rehearse_switch.RehearsalError, "volume|mount"):
            rehearsal.capture_snapshot(observed_stopped_at)

    def test_target_data_plane_drift_fails_before_api_exposure_and_restores_source(self) -> None:
        direction = rehearse_switch.Direction("CUTOVER", "legacy", "java", "initial")
        _, runner, rehearsal = self.make_rehearsal(direction)
        runner.runtime[direction.target_postgres]["Networks"]["shared-drift"] = {
            "NetworkID": "f" * 64,
        }
        with self.assertRaises(rehearse_switch.RehearsalError):
            rehearsal.run()
        self.assertTrue(runner.source_services.issubset(runner.running))
        self.assertNotIn(direction.target_api, runner.running)
        self.assertFalse(any(volume in runner.volumes for volume in rehearsal.target_volumes()))

    def test_restore_failure_cleans_target_and_restarts_only_source(self) -> None:
        direction = rehearse_switch.Direction("CUTOVER", "legacy", "java", "initial")
        _, runner, rehearsal = self.make_rehearsal(direction, fail_restore=True)
        with self.assertRaises(rehearse_switch.CommandError):
            rehearsal.run()
        self.assertIn("legacy-api", runner.running)
        self.assertNotIn("java-api", runner.running)
        self.assertFalse(any(volume in runner.volumes for volume in rehearsal.target_volumes()))
        report = json.loads(rehearsal.report_path.read_text(encoding="utf-8"))
        self.assertEqual("failed", report["status"])
        self.assertTrue(report["failure"]["target_cleanup_and_source_restart_succeeded"])

    def test_reverse_rollback_uses_fresh_generation_volumes(self) -> None:
        direction = rehearse_switch.Direction("ROLLBACK", "java", "legacy", "rb001")
        _, runner, rehearsal = self.make_rehearsal(direction)
        report_path = rehearsal.run()
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual("rollback", report["direction"])
        self.assertNotIn("java-api", runner.running)
        self.assertIn("legacy-api", runner.running)
        self.assertTrue(all("rollback-rb001" in volume for volume in rehearsal.target_volumes()))
        self.assertTrue(report["isolation"]["volumes_all_distinct"])

    def test_retirement_failure_before_target_exposure_restores_only_source(self) -> None:
        direction = rehearse_switch.Direction("CUTOVER", "legacy", "java", "initial")
        _, runner, rehearsal = self.make_rehearsal(
            direction, fail_retire_source=True)
        with self.assertRaises(rehearse_switch.CommandError):
            rehearsal.run()
        self.assertIn("legacy-api", runner.running)
        self.assertNotIn("java-api", runner.running)
        self.assertFalse(any(volume in runner.volumes for volume in rehearsal.target_volumes()))
        report = json.loads(rehearsal.report_path.read_text(encoding="utf-8"))
        self.assertTrue(report["failure"]["target_cleanup_and_source_restart_succeeded"])

    def test_target_api_runtime_drift_after_exposure_preserves_target_for_manual_recovery(self) -> None:
        direction = rehearse_switch.Direction("CUTOVER", "legacy", "java", "initial")
        _, runner, rehearsal = self.make_rehearsal(direction)
        bindings = runner.runtime[direction.target_api]["Ports"]["8080/tcp"]
        bindings[0]["HostIp"] = "0.0.0.0"
        with self.assertRaises(rehearse_switch.RehearsalError):
            rehearsal.run()
        self.assertTrue({
            direction.target_api, direction.target_postgres, direction.target_redis,
        }.issubset(runner.running))
        self.assertTrue(runner.source_services.isdisjoint(runner.running))
        self.assertTrue(all(volume in runner.volumes for volume in rehearsal.target_volumes()))
        report = json.loads(rehearsal.report_path.read_text(encoding="utf-8"))
        self.assertFalse(report["failure"]["target_cleanup_attempted"])
        self.assertFalse(report["failure"]["source_restart_attempted"])
        self.assertTrue(report["failure"]["target_data_plane_preserved"])
        self.assertTrue(report["failure"]["manual_intervention_required"])

    def test_report_write_failure_after_target_health_preserves_target_and_source_stays_retired(
            self) -> None:
        direction = rehearse_switch.Direction("CUTOVER", "legacy", "java", "initial")
        _, runner, rehearsal = self.make_rehearsal(direction)
        with mock.patch.object(
                rehearse_switch, "private_atomic_json",
                side_effect=OSError("injected report write failure")):
            with self.assertRaises(OSError):
                rehearsal.run()
        self.assertTrue({
            direction.target_api, direction.target_postgres, direction.target_redis,
        }.issubset(runner.running))
        self.assertTrue(runner.source_services.isdisjoint(runner.running))
        self.assertTrue(all(volume in runner.volumes for volume in rehearsal.target_volumes()))
        self.assertTrue(all(volume in runner.volumes for volume in rehearsal.source_volumes()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
