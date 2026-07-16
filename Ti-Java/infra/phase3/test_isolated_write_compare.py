#!/usr/bin/env python3
"""Black-box tests for the Phase 3 isolated login write evidence comparator."""

import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from typing import Any, Dict, List, Tuple


SCRIPT = pathlib.Path(__file__).resolve().with_name("isolated_write_compare.py")
SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64
SHA_C = "sha256:" + "c" * 64
SHA_D = "sha256:" + "d" * 64
SHA_E = "sha256:" + "e" * 64
QUEUE_BOUNDARY_POLICY_SHA256 = (
    "sha256:72292cd44bf85870a7398c1cbcb10f5fcff7b4e17a75e7b981da08889399399e"
)
OBJECT_STORE_BOUNDARY_POLICY_SHA256 = (
    "sha256:bfdd689deb6a0c3f45aca1da5b1baf9e3d985197327e35a2a02e273ee3db839e"
)
EXTERNAL_SINK_BOUNDARY_POLICY_SHA256 = (
    "sha256:e1fc1f413780c4428da382a5d92cfa38c7a776c51537f0021879d8311b65d36c"
)


def configuration_only_boundary(policy_sha256: str) -> Dict[str, Any]:
    return {
        "runtime_observation_performed": False,
        "configured": False,
        "boundary_policy_sha256": policy_sha256,
    }


class IsolatedWriteCompareCliTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="ti-phase3-isolated-write-")
        self.directory = pathlib.Path(self.temporary.name)
        self.counter = 0
        self.fingerprints: Dict[str, pathlib.Path] = {}
        self.fingerprint_values: Dict[str, Dict[str, str]] = {}
        for side, suffix in (("legacy", "a"), ("java", "b")):
            values = {
                "database": f"{side}-write-db-{suffix}",
                "redis": f"{side}-write-redis-{suffix}",
                "volume": f"{side}-write-volume-{suffix}",
            }
            path = self.directory / f"{side}-fingerprint.json"
            self._write_json(
                path,
                {
                    "schema_version": "1",
                    "environment": "local",
                    "side": side,
                    **values,
                },
            )
            self.fingerprints[side] = path
            self.fingerprint_values[side] = values

        self.evidence: Dict[Tuple[str, str], pathlib.Path] = {}
        sequences = {
            ("legacy", "before"): 1,
            ("legacy", "after"): 2,
            ("java", "before"): 3,
            ("java", "after"): 4,
        }
        for side in ("legacy", "java"):
            for phase in ("before", "after"):
                path = self.directory / f"{side}-{phase}.json"
                self._write_evidence(path, side, phase, sequences[(side, phase)])
                self.evidence[(side, phase)] = path

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def _write_json(path: pathlib.Path, value: Any) -> None:
        path.write_text(
            json.dumps(value, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
        )

    @staticmethod
    def _resource_binding(values: Dict[str, str]) -> str:
        payload = b"ti-phase3-isolated-write-fingerprint-v1\0" + b"\0".join(
            values[field].encode("utf-8") for field in ("database", "redis", "volume")
        )
        return "sha256:" + hashlib.sha256(payload).hexdigest()

    def _write_evidence(self, path: pathlib.Path, side: str, phase: str, sequence: int) -> None:
        before = phase == "before"
        storage = "none" if before else (
            "signed-client-cookie" if side == "legacy" else "server-redis"
        )
        authority = "none" if before else (
            "signed-login-snapshot" if side == "legacy" else "postgresql-per-request"
        )
        response: Dict[str, Any]
        if before:
            response = {
                "observed": False,
                "status": 0,
                "content_type": "none",
                "normalized_body_sha256": "none",
                "authenticated_session_issued": False,
                "remember_applied": False,
            }
        else:
            response = {
                "observed": True,
                "status": 200,
                "content_type": (
                    "application/json; charset=utf-8"
                    if side == "legacy"
                    else "Application/JSON;charset=\"UTF-8\""
                ),
                "normalized_body_sha256": SHA_D,
                "authenticated_session_issued": True,
                "remember_applied": True,
            }
        self._write_json(
            path,
            {
                "schema_version": "1",
                "environment": "local",
                "run_id": "auth-login-write-001",
                "side": side,
                "phase": phase,
                "capture_sequence": sequence,
                "operation_id": "identity.auth.login",
                "fixture_id": "auth-login-success-001",
                "snapshot_id": "sanitized-auth-s0-001",
                "snapshot_digest": SHA_A,
                "resource_binding_sha256": self._resource_binding(
                    self.fingerprint_values[side]
                ),
                "auditor": "phase3-auth-state-auditor-v1",
                "request_count": 0 if before else 1,
                "response": response,
                "state": {
                    "database": {
                        "schema_sha256": SHA_B,
                        "normalized_business_state_sha256": SHA_C,
                        "users_row_count": 5,
                        "credential": {
                            "format_family": "werkzeug-scrypt",
                            "target_parameters": "32768:8:1",
                            "verifies_fixture_password": True,
                            "has_password_set": not before,
                            "session_version": 7,
                            "last_active_state": "null",
                        },
                        "constraint_violations": 0,
                        "unexpected_row_changes": 0,
                    },
                    "session": {
                        "authenticated": not before,
                        "principal_binding_hmac_sha256": "none" if before else SHA_E,
                        "session_version": "none" if before else 7,
                        "remember": not before,
                        "storage_profile": storage,
                        "authority_profile": authority,
                        "credential_material_count": 0,
                    },
                    "redis": {
                        "business_fact_keys": 0,
                        "server_session_records": (
                            0 if side == "legacy" else 1
                        ),
                        "rate_limit_attempt_recorded": (
                            not before or side == "java"
                        ),
                        "rebuildable_only": True,
                        "unexpected_keys": 0,
                    },
                    "external": {
                        "persistent_file_writes": 0,
                        "queue": configuration_only_boundary(
                            QUEUE_BOUNDARY_POLICY_SHA256
                        ),
                        "object_store": configuration_only_boundary(
                            OBJECT_STORE_BOUNDARY_POLICY_SHA256
                        ),
                        "external_sink": configuration_only_boundary(
                            EXTERNAL_SINK_BOUNDARY_POLICY_SHA256
                        ),
                    },
                },
            },
        )

    def _update_both_credentials(self, phase: str, **updates: Any) -> None:
        for side in ("legacy", "java"):
            path = self.evidence[(side, phase)]
            document = json.loads(path.read_text(encoding="utf-8"))
            document["state"]["database"]["credential"].update(updates)
            self._write_json(path, document)

    def _assert_invariant_failure_with_cross_side_equivalence(self) -> Dict[str, Any]:
        completed, report_path = self._run()
        self.assertEqual(1, completed.returncode, completed.stderr)
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual("fail", report["outcome"])
        self.assertTrue(report["checks"]["same_snapshot_initial_database"])
        self.assertTrue(report["checks"]["final_business_database_equivalent"])
        self.assertFalse(report["checks"]["per_side_invariants_satisfied"])
        self.assertTrue(any(
            difference["scope"] == "invariant" for difference in report["differences"]
        ))
        return report

    def _base_arguments(self) -> Tuple[List[str], pathlib.Path]:
        self.counter += 1
        report = self.directory / f"report-{self.counter}.json"
        return [
            sys.executable,
            str(SCRIPT),
            "ISOLATED_WRITE_COMPARE",
            "--environment",
            "local",
            "--operation-id",
            "identity.auth.login",
            "--run-id",
            "auth-login-write-001",
            "--fixture-id",
            "auth-login-success-001",
            "--snapshot-id",
            "sanitized-auth-s0-001",
            "--snapshot-digest",
            SHA_A,
            "--legacy-artifact-digest",
            "sha256:" + "1" * 64,
            "--java-artifact-digest",
            "sha256:" + "2" * 64,
            "--execution-order",
            "legacy-then-java",
            "--legacy-fingerprint",
            str(self.fingerprints["legacy"]),
            "--java-fingerprint",
            str(self.fingerprints["java"]),
            "--legacy-before-evidence",
            str(self.evidence[("legacy", "before")]),
            "--legacy-after-evidence",
            str(self.evidence[("legacy", "after")]),
            "--java-before-evidence",
            str(self.evidence[("java", "before")]),
            "--java-after-evidence",
            str(self.evidence[("java", "after")]),
            "--report",
            str(report),
        ], report

    @staticmethod
    def _replace(arguments: List[str], flag: str, value: str) -> None:
        arguments[arguments.index(flag) + 1] = value

    def _run(self, mutate_arguments=None) -> Tuple[subprocess.CompletedProcess, pathlib.Path]:
        arguments, report = self._base_arguments()
        if mutate_arguments:
            mutate_arguments(arguments, report)
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

    def test_equivalent_final_state_passes_without_network_or_raw_values(self) -> None:
        completed, report_path = self._run()

        self.assertEqual(0, completed.returncode, completed.stderr)
        report_text = report_path.read_text(encoding="utf-8")
        report = json.loads(report_text)
        self.assertEqual("pass", report["outcome"])
        self.assertEqual(0, report["request"]["writes_issued_by_comparator"])
        self.assertFalse(report["execution"]["network_capability_present"])
        self.assertTrue(report["execution"]["serial_evidence_validated"])
        self.assertTrue(report["checks"]["same_snapshot_initial_database"])
        self.assertTrue(report["checks"]["final_business_database_equivalent"])
        self.assertTrue(report["checks"]["session_semantics_equivalent"])
        self.assertTrue(report["checks"]["redis_semantics_equivalent"])
        self.assertTrue(
            report["checks"]["file_and_external_configuration_boundaries_equivalent"]
        )
        self.assertNotIn("external_effects_equivalent", report["checks"])
        self.assertTrue(report["checks"]["per_side_invariants_satisfied"])
        self.assertEqual(["P3-AUTH-002"], [
            item["id"] for item in report["approved_implementation_differences"]
        ])
        for raw_value in self.fingerprint_values["legacy"].values():
            self.assertNotIn(raw_value, report_text)
        self.assertNotIn("Application/JSON", report_text)
        self.assertNotIn("queue_messages", report_text)
        self.assertNotIn("object_writes", report_text)
        self.assertNotIn("external_writes", report_text)
        for policy_sha256 in (
            QUEUE_BOUNDARY_POLICY_SHA256,
            OBJECT_STORE_BOUNDARY_POLICY_SHA256,
            EXTERNAL_SINK_BOUNDARY_POLICY_SHA256,
        ):
            self.assertNotIn(policy_sha256, report_text)
        for summary_by_phase in report["state_summaries"].values():
            for summary in summary_by_phase.values():
                self.assertIn("external_boundary_sha256", summary)
                self.assertNotIn("external_sha256", summary)

        source = SCRIPT.read_text(encoding="utf-8")
        for forbidden_import in (
            "import socket",
            "import urllib",
            "import http.client",
            "import requests",
            "import subprocess",
        ):
            self.assertNotIn(forbidden_import, source)

    def test_before_has_password_set_must_be_false_even_when_both_sides_match(self) -> None:
        self._update_both_credentials("before", has_password_set=True)

        self._assert_invariant_failure_with_cross_side_equivalence()

    def test_after_has_password_set_must_be_true_even_when_both_sides_match(self) -> None:
        self._update_both_credentials("after", has_password_set=False)

        self._assert_invariant_failure_with_cross_side_equivalence()

    def test_hash_family_change_fails_even_when_both_sides_match(self) -> None:
        self._update_both_credentials("after", format_family="werkzeug-pbkdf2")

        self._assert_invariant_failure_with_cross_side_equivalence()

    def test_hash_parameter_change_fails_even_when_both_sides_match(self) -> None:
        self._update_both_credentials("after", target_parameters="not-target")

        self._assert_invariant_failure_with_cross_side_equivalence()

    def test_other_credential_field_change_fails_even_when_both_sides_match(self) -> None:
        self._update_both_credentials("after", session_version=8)
        for side in ("legacy", "java"):
            path = self.evidence[(side, "after")]
            document = json.loads(path.read_text(encoding="utf-8"))
            document["state"]["session"]["session_version"] = 8
            self._write_json(path, document)

        self._assert_invariant_failure_with_cross_side_equivalence()

    def test_database_response_session_and_redis_differences_fail_with_hashes_only(self) -> None:
        java_after_path = self.evidence[("java", "after")]
        document = json.loads(java_after_path.read_text(encoding="utf-8"))
        document["state"]["database"]["credential"]["session_version"] = 8
        document["state"]["session"]["principal_binding_hmac_sha256"] = (
            "sha256:" + "9" * 64
        )
        document["state"]["redis"]["business_fact_keys"] = 1
        document["response"]["normalized_body_sha256"] = "sha256:" + "8" * 64
        self._write_json(java_after_path, document)

        completed, report_path = self._run()

        self.assertEqual(1, completed.returncode, completed.stderr)
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual("fail", report["outcome"])
        scopes = {difference["scope"] for difference in report["differences"]}
        self.assertTrue({"final_database", "response", "session", "redis", "invariant"}.issubset(scopes))
        self.assertTrue(all("sha256" in side or side.get("type") == "null"
                            for item in report["differences"]
                            for side in (item["legacy"], item["java"])))

    def test_shared_resource_fingerprint_is_rejected_before_report(self) -> None:
        java = json.loads(self.fingerprints["java"].read_text(encoding="utf-8"))
        java["database"] = self.fingerprint_values["legacy"]["database"]
        self._write_json(self.fingerprints["java"], java)

        completed, report_path = self._run()

        self.assertEqual(2, completed.returncode)
        self.assertEqual("SHARED_ENVIRONMENT_FINGERPRINT", self._error_code(completed))
        self.assertFalse(report_path.exists())

    def test_evidence_must_bind_resource_and_full_serial_sequence(self) -> None:
        java_before_path = self.evidence[("java", "before")]
        document = json.loads(java_before_path.read_text(encoding="utf-8"))
        document["resource_binding_sha256"] = SHA_D
        self._write_json(java_before_path, document)

        completed, report_path = self._run()
        self.assertEqual(2, completed.returncode)
        self.assertEqual("EVIDENCE_RESOURCE_MISMATCH", self._error_code(completed))
        self.assertFalse(report_path.exists())

        document["resource_binding_sha256"] = self._resource_binding(
            self.fingerprint_values["java"]
        )
        document["capture_sequence"] = 2
        self._write_json(java_before_path, document)
        completed, report_path = self._run()
        self.assertEqual(2, completed.returncode)
        self.assertEqual("NON_SERIAL_EVIDENCE", self._error_code(completed))
        self.assertFalse(report_path.exists())

    def test_unknown_raw_password_hash_field_and_wrong_operation_are_rejected(self) -> None:
        legacy_after_path = self.evidence[("legacy", "after")]
        document = json.loads(legacy_after_path.read_text(encoding="utf-8"))
        document["state"]["database"]["credential"]["password_hash"] = "must-not-pass"
        self._write_json(legacy_after_path, document)

        completed, report_path = self._run()
        self.assertEqual(2, completed.returncode)
        self.assertEqual("UNKNOWN_INPUT_FIELD", self._error_code(completed))
        self.assertFalse(report_path.exists())

        def wrong_operation(arguments: List[str], report: pathlib.Path) -> None:
            self._replace(arguments, "--operation-id", "identity.other.write")

        completed, report_path = self._run(wrong_operation)
        self.assertEqual(2, completed.returncode)
        self.assertEqual("OPERATION_FORBIDDEN", self._error_code(completed))
        self.assertFalse(report_path.exists())

    def test_legacy_external_count_shape_and_unknown_boundary_fields_are_rejected(self) -> None:
        legacy_after_path = self.evidence[("legacy", "after")]
        document = json.loads(legacy_after_path.read_text(encoding="utf-8"))
        document["state"]["external"] = {
            "queue_messages": 0,
            "object_writes": 0,
            "persistent_file_writes": 0,
            "external_writes": 0,
        }
        self._write_json(legacy_after_path, document)

        completed, report_path = self._run()
        self.assertEqual(2, completed.returncode)
        self.assertEqual("UNKNOWN_INPUT_FIELD", self._error_code(completed))
        self.assertFalse(report_path.exists())

        self._write_evidence(legacy_after_path, "legacy", "after", 2)
        document = json.loads(legacy_after_path.read_text(encoding="utf-8"))
        document["state"]["external"]["queue"]["observed_messages"] = 0
        self._write_json(legacy_after_path, document)
        completed, report_path = self._run()
        self.assertEqual(2, completed.returncode)
        self.assertEqual("UNKNOWN_INPUT_FIELD", self._error_code(completed))
        self.assertFalse(report_path.exists())

    def test_configuration_only_boundary_rejects_observation_configuration_and_policy_drift(
            self) -> None:
        cases = (
            ("runtime_observation_performed", True),
            ("configured", True),
            ("boundary_policy_sha256", SHA_A),
        )
        for field, value in cases:
            with self.subTest(field=field):
                path = self.evidence[("java", "after")]
                self._write_evidence(path, "java", "after", 4)
                document = json.loads(path.read_text(encoding="utf-8"))
                document["state"]["external"]["external_sink"][field] = value
                self._write_json(path, document)
                completed, report_path = self._run()
                self.assertEqual(2, completed.returncode)
                self.assertEqual("INVALID_EVIDENCE_VALUE", self._error_code(completed))
                self.assertFalse(report_path.exists())

    def test_nonzero_observed_persistent_file_write_is_an_invariant_failure(self) -> None:
        for side in ("legacy", "java"):
            path = self.evidence[(side, "after")]
            document = json.loads(path.read_text(encoding="utf-8"))
            document["state"]["external"]["persistent_file_writes"] = 1
            self._write_json(path, document)

        report = self._assert_invariant_failure_with_cross_side_equivalence()
        self.assertTrue(any(
            difference["path"].endswith("/external/persistent_file_writes")
            for difference in report["differences"]
        ))

    def test_existing_report_is_never_overwritten(self) -> None:
        def create_report(arguments: List[str], report: pathlib.Path) -> None:
            report.write_text("user-owned-evidence", encoding="utf-8")

        completed, report_path = self._run(create_report)

        self.assertEqual(2, completed.returncode)
        self.assertEqual("REPORT_EXISTS", self._error_code(completed))
        self.assertEqual("user-owned-evidence", report_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
