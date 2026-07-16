#!/usr/bin/env python3
"""Unit tests for the bounded Phase 3 login write evidence collector."""

from __future__ import annotations

import base64
import email.utils
import hashlib
import hmac
import json
import pathlib
import tempfile
import time
import unittest

import capture_login_write_evidence as capture


SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64
SHA_C = "sha256:" + "c" * 64
SHA_D = "sha256:" + "d" * 64
FLASK_SECRET = b"PublicPhase3FlaskSecretForUnitTests0001"
JAVA_SESSION_ID = "123e4567-e89b-42d3-a456-426614174000"
OTHER_JAVA_SESSION_ID = "f47ac10b-58cc-4372-a567-0e02b2c3d479"
QUEUE_BOUNDARY_POLICY_SHA256 = (
    "sha256:72292cd44bf85870a7398c1cbcb10f5fcff7b4e17a75e7b981da08889399399e"
)
OBJECT_STORE_BOUNDARY_POLICY_SHA256 = (
    "sha256:bfdd689deb6a0c3f45aca1da5b1baf9e3d985197327e35a2a02e273ee3db839e"
)
EXTERNAL_SINK_BOUNDARY_POLICY_SHA256 = (
    "sha256:e1fc1f413780c4428da382a5d92cfa38c7a776c51537f0021879d8311b65d36c"
)


def java_session_cookie(session_id: str = JAVA_SESSION_ID) -> str:
    return base64.b64encode(session_id.encode("ascii")).decode("ascii")


def java_success_headers(session_value: str | None = None) -> bytes:
    target = java_session_cookie() if session_value is None else session_value
    return (
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: application/json;charset=UTF-8\r\n"
        "X-Request-ID: phase3-login-write-001\r\n"
        f"Set-Cookie: ti_phase3_java_csrf={'A' * 43}; Path=/; SameSite=Lax\r\n"
        "Set-Cookie: ti_phase3_java_csrf=; Max-Age=0; "
        "Expires=Thu, 01 Jan 1970 00:00:00 GMT; Path=/; SameSite=Lax\r\n"
        "Set-Cookie: session=; Max-Age=0; Expires=Thu, 01 Jan 1970 00:00:00 GMT; "
        "HttpOnly; Path=/; SameSite=Lax\r\n"
        f"Set-Cookie: ti_phase3_java_session={target}; Max-Age=604800; "
        "Expires=Thu, 23 Jul 2026 00:00:00 GMT; HttpOnly; Path=/; SameSite=Lax\r\n\r\n"
    ).encode("ascii")


def urlsafe(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def signed_flask_cookie() -> str:
    payload = json.dumps({
        "_permanent": True,
        "user_id": 1,
        "username": "phase3-fixture",
        "is_admin": False,
        "is_subject_admin": False,
        "is_notification_admin": False,
        "session_version": 7,
        "remember": True,
    }, separators=(",", ":"), sort_keys=True).encode("utf-8")
    issued_at = int(time.time()).to_bytes(8, "big").lstrip(b"\x00")
    signed_value = urlsafe(payload) + "." + urlsafe(issued_at)
    derived = hmac.new(FLASK_SECRET, b"cookie-session", hashlib.sha1).digest()
    signature = hmac.new(derived, signed_value.encode("ascii"), hashlib.sha1).digest()
    return signed_value + "." + urlsafe(signature)


def success_body() -> bytes:
    return json.dumps({
        "status": "success", "redirect": "/practice", "remember": True,
        "needs_password_set": False, "message": "", "request_id": "phase3-login-write-001",
        "data": {"redirect": "/practice", "remember": True, "needs_password_set": False},
    }).encode("utf-8")


def response_date() -> str:
    return email.utils.formatdate(time.time(), usegmt=True)


def scope(phase: str, sequence: int, side: str = "legacy") -> capture.CaptureScope:
    class FakeTopology:
        environment = "test"
        run_id = "guarded-legacy"
        project = "ti-phase3-test-guarded-legacy"

    return capture.CaptureScope(
        environment="test",
        side=side,
        phase=phase,
        logical_run_id="auth-login-write-001",
        fixture_id="auth-login-success-001",
        snapshot_id="sanitized-auth-s0-001",
        snapshot_digest=SHA_A,
        capture_sequence=sequence,
        topology=FakeTopology(),  # type: ignore[arg-type]
        peer_topology=FakeTopology(),  # type: ignore[arg-type]
        fingerprint={"database": "db-a", "redis": "redis-a", "volume": "volume-a"},
        resource_binding_sha256=SHA_B,
    )


def database(password_set: bool) -> dict[str, object]:
    return {
        "schema_sha256": SHA_A,
        "normalized_business_state_sha256": SHA_B,
        "transition_guard_sha256": SHA_C,
        "users_row_count": 2,
        "credential_material_sha256": capture.FIXTURE_PASSWORD_MATERIAL_SHA256,
        "format_family": "werkzeug-scrypt",
        "target_parameters": "32768:8:1",
        "verifies_fixture_password": True,
        "has_password_set": password_set,
        "session_version": 7,
        "last_active_state": "null",
        "constraint_violations": 0,
    }


def volume() -> dict[str, object]:
    return {
        "normalized_manifest_sha256": SHA_A,
        "exclusion_policy_sha256": SHA_B,
        "excluded_rotated_file_count": 0,
        "included_entry_count": 1,
    }


class ResponseSanitizerTests(unittest.TestCase):
    def test_legacy_response_is_reduced_without_cookie_or_body_values(self) -> None:
        cookie = signed_flask_cookie()
        headers = (
            "HTTP/1.1 200 OK\r\n"
            f"Date: {response_date()}\r\n"
            "Content-Type: application/json; charset=utf-8\r\n"
            "X-Request-ID: phase3-login-write-001\r\n"
            f"Set-Cookie: session={cookie}; Expires=Fri, 23 Jul 2026 00:00:00 GMT; "
            "HttpOnly; Path=/\r\n\r\n"
        ).encode("ascii")
        result = capture.sanitize_response(
            "legacy", headers, success_body(), FLASK_SECRET, SHA_A
        )
        serialized = json.dumps(result, sort_keys=True)
        self.assertEqual(200, result["status"])
        self.assertTrue(result["authenticated_session_issued"])
        self.assertTrue(result["legacy_signed_snapshot_verified"])
        self.assertNotIn(cookie, serialized)
        self.assertNotIn("request_id", serialized)

    def test_java_envelope_is_projected_to_same_stable_body(self) -> None:
        encoded_session = java_session_cookie()
        headers = java_success_headers(encoded_session)
        java = capture.sanitize_response("java", headers, success_body())
        legacy_headers = (
            f"HTTP/1.1 200 OK\r\nDate: {response_date()}\r\n"
            "Content-Type: application/json; charset=utf-8\r\n"
            "X-Request-ID: phase3-login-write-001\r\n"
            f"Set-Cookie: session={signed_flask_cookie()}; "
            "Expires=Fri, 23 Jul 2026 00:00:00 GMT; "
            "HttpOnly; Path=/\r\n\r\n"
        ).encode("ascii")
        legacy = capture.sanitize_response(
            "legacy", legacy_headers, success_body(), FLASK_SECRET, SHA_A
        )
        self.assertEqual(legacy["normalized_body_sha256"], java["normalized_body_sha256"])
        self.assertEqual(capture._target_session_binding(JAVA_SESSION_ID),
                         java["target_session_binding_sha256"])
        self.assertNotIn(encoded_session, json.dumps(java))
        self.assertNotIn(JAVA_SESSION_ID, json.dumps(java))

    def test_redirect_chain_and_unexpected_cookie_are_rejected(self) -> None:
        headers = (
            "HTTP/1.1 302 Found\r\nLocation: /login\r\n\r\n"
            "HTTP/1.1 200 OK\r\nContent-Type: application/json;charset=utf-8\r\n\r\n"
        ).encode("ascii")
        with self.assertRaisesRegex(capture.EvidenceError, "exactly one"):
            capture.sanitize_response("legacy", headers, b"{}")

    def test_tampered_legacy_signed_session_and_wrong_fixed_fields_are_rejected(self) -> None:
        cookie = signed_flask_cookie()
        signed_value, encoded_signature = cookie.rsplit(".", 1)
        signature = bytearray(base64.urlsafe_b64decode(
            encoded_signature + "=" * (-len(encoded_signature) % 4)
        ))
        signature[0] ^= 1
        tampered = signed_value + "." + urlsafe(bytes(signature))
        with self.assertRaisesRegex(capture.EvidenceError, "signature mismatch"):
            capture.verify_flask_session_cookie(tampered, FLASK_SECRET)
        headers = (
            "HTTP/1.1 200 OK\r\nContent-Type: application/json;charset=utf-8\r\n"
            "X-Request-ID: phase3-login-write-001\r\n"
            f"Set-Cookie: ti_phase3_java_session={java_session_cookie()}; Max-Age=604800; "
            "HttpOnly; Path=/; SameSite=Lax\r\n\r\n"
        ).encode("ascii")
        wrong = json.loads(success_body())
        wrong["redirect"] = "/"
        wrong["data"]["redirect"] = "/"
        with self.assertRaisesRegex(capture.EvidenceError, "semantics"):
            capture.sanitize_response("java", headers, json.dumps(wrong).encode())

    def test_java_cookie_requires_canonical_base64_uuidv4(self) -> None:
        for value in (JAVA_SESSION_ID, "=" + java_session_cookie(),
                      base64.b64encode(b"not-a-uuid").decode("ascii")):
            headers = java_success_headers(value)
            with self.subTest(value=value), self.assertRaises(capture.EvidenceError):
                capture.sanitize_response("java", headers, success_body())
        wrong = json.loads(success_body())
        wrong["request_id"] = "another-request"
        with self.assertRaisesRegex(capture.EvidenceError, "request id"):
            capture.sanitize_response("java", headers, json.dumps(wrong).encode())

    def test_java_allows_only_the_exact_ordered_csrf_issue_then_clear_pair(self) -> None:
        capture.sanitize_response("java", java_success_headers(), success_body())
        duplicate_session = java_success_headers().replace(
            b"\r\n\r\n",
            (f"\r\nSet-Cookie: ti_phase3_java_session={java_session_cookie()}; "
             "Max-Age=604800; HttpOnly; Path=/; SameSite=Lax\r\n\r\n").encode("ascii"),
        )
        with self.assertRaisesRegex(capture.EvidenceError, "duplicate"):
            capture.sanitize_response("java", duplicate_session, success_body())
        issued_then_cleared = (
            f"Set-Cookie: ti_phase3_java_csrf={'A' * 43}; Path=/; SameSite=Lax\r\n"
            "Set-Cookie: ti_phase3_java_csrf=; Max-Age=0; "
            "Expires=Thu, 01 Jan 1970 00:00:00 GMT; Path=/; SameSite=Lax\r\n"
        ).encode("ascii")
        cleared_then_issued = (
            "Set-Cookie: ti_phase3_java_csrf=; Max-Age=0; "
            "Expires=Thu, 01 Jan 1970 00:00:00 GMT; Path=/; SameSite=Lax\r\n"
            f"Set-Cookie: ti_phase3_java_csrf={'A' * 43}; Path=/; SameSite=Lax\r\n"
        ).encode("ascii")
        reversed_csrf = java_success_headers().replace(
            issued_then_cleared,
            cleared_then_issued,
        )
        with self.assertRaisesRegex(capture.EvidenceError, "issued before"):
            capture.sanitize_response("java", reversed_csrf, success_body())


class ProofTests(unittest.TestCase):
    def test_fixture_password_material_digest_is_a_canonical_sha256(self) -> None:
        self.assertRegex(capture.FIXTURE_PASSWORD_MATERIAL_SHA256, r"^sha256:[0-9a-f]{64}$")

    def test_private_proof_allows_only_false_to_true(self) -> None:
        before_scope = scope("before", 1)
        after_scope = scope("after", 2)
        proof = capture.build_before_proof(before_scope, database(False), volume())
        capture.validate_after_against_proof(
            after_scope, proof, database(True), volume()
        )
        serialized = json.dumps(proof)
        self.assertNotIn("scrypt:32768", serialized)
        self.assertNotIn("PublicSalt", serialized)
        self.assertFalse(proof["raw_password_hash_persisted"])

    def test_non_projected_change_is_rejected_even_if_has_password_transitions(self) -> None:
        proof = capture.build_before_proof(scope("before", 1), database(False), volume())
        changed = database(True)
        changed["transition_guard_sha256"] = SHA_D
        with self.assertRaisesRegex(capture.EvidenceError, "outside the sole"):
            capture.validate_after_against_proof(
                scope("after", 2), proof, changed, volume()
            )

    def test_password_material_session_version_and_last_active_are_fixed(self) -> None:
        proof = capture.build_before_proof(scope("before", 1), database(False), volume())
        for field, value in (
            ("credential_material_sha256", SHA_D),
            ("session_version", 8),
            ("last_active_state", "present"),
        ):
            changed = database(True)
            changed[field] = value
            with self.subTest(field=field), self.assertRaises(capture.EvidenceError):
                capture.validate_after_against_proof(
                    scope("after", 2), proof, changed, volume()
                )

    def test_sequence_must_be_adjacent(self) -> None:
        proof = capture.build_before_proof(scope("before", 1), database(False), volume())
        with self.assertRaisesRegex(capture.EvidenceError, "immediately follow"):
            capture.validate_after_against_proof(
                scope("after", 3), proof, database(True), volume()
            )

    def test_application_volume_change_is_rejected_before_zero_file_writes_are_claimed(self) -> None:
        proof = capture.build_before_proof(scope("before", 1), database(False), volume())
        changed_volume = volume()
        changed_volume["normalized_manifest_sha256"] = SHA_D
        with self.assertRaisesRegex(capture.EvidenceError, "application volume changed"):
            capture.validate_after_against_proof(
                scope("after", 2), proof, database(True), changed_volume
            )


class RedisAndStaticBoundaryTests(unittest.TestCase):
    def test_bounded_redis_summary_is_semantic_only(self) -> None:
        value = capture.parse_redis_summary(
            ("phase3-login-redis-v1\n11\n1\n0\n3\n0\n0\n"
             + JAVA_SESSION_ID + "\n").encode("ascii")
        )
        self.assertEqual(1, value["server_session_records"])
        self.assertTrue(value["rate_limit_attempt_recorded"])
        self.assertEqual(0, value["unexpected_keys"])
        self.assertEqual(capture._target_session_binding(JAVA_SESSION_ID),
                         value["target_session_binding_sha256"])

    def test_unknown_or_oversized_redis_state_is_rejected(self) -> None:
        with self.assertRaises(capture.EvidenceError):
            capture.parse_redis_summary(
                b"phase3-login-redis-v1\n65\n0\n1\n0\n0\n0\nnone\n"
            )
        self.assertIn("UNKNOWN_REDIS_KEY_OR_TYPE", capture.REDIS_CAPTURE_LUA)
        self.assertIn("INVALID_SERVER_SESSION_SEMANTICS", capture.REDIS_CAPTURE_LUA)

    def test_redis_policy_distinguishes_anonymous_before_and_authenticated_after(self) -> None:
        source = capture.REDIS_CAPTURE_LUA
        for marker in (
            "sessionAttr:anonymous_expires_at", "sessionAttr:csrf_token",
            "INVALID_ANONYMOUS_SESSION_SEMANTICS", "anonymous_records ~= 1",
            "session_records == 1", "anonymous_records == 0",
            "TARGET_SESSION_REGISTRY_BINDING_INVALID", "first_attempt_counter",
            "login_rate == 3", "csrf_rate == 2", "#keys == 11", "ZRANGE",
            "global:owners",
        ):
            self.assertIn(marker, source)
        for indexed_repository_marker in (
            "session_prefix .. 'expires:'", "expiration_prefix", "expirations:",
            "SESSION_EXPIRY_MISSING", "SESSION_EXPIRATION_MEMBER_MISSING",
        ):
            self.assertNotIn(indexed_repository_marker, source)
        self.assertIn('EVAL "$1" 0 "$2" "$3" "$4"', capture.REDIS_CAPTURE_SHELL)

    def test_cookie_binding_must_equal_current_redis_session_and_is_not_emitted(self) -> None:
        headers = java_success_headers()
        observation = capture.sanitize_response("java", headers, success_body())
        redis = capture.parse_redis_summary(
            ("phase3-login-redis-v1\n11\n1\n0\n3\n0\n0\n"
             + JAVA_SESSION_ID + "\n").encode("ascii")
        )
        evidence = capture.build_evidence(scope("after", 4, "java"), database(True),
                                          redis, observation, True)
        self.assertNotIn("target_session_binding_sha256", evidence["state"]["redis"])
        external = evidence["state"]["external"]
        self.assertEqual(
            {"persistent_file_writes", "queue", "object_store", "external_sink"},
            set(external),
        )
        self.assertEqual(0, external["persistent_file_writes"])
        expected_policies = {
            "queue": QUEUE_BOUNDARY_POLICY_SHA256,
            "object_store": OBJECT_STORE_BOUNDARY_POLICY_SHA256,
            "external_sink": EXTERNAL_SINK_BOUNDARY_POLICY_SHA256,
        }
        for boundary, policy_sha256 in expected_policies.items():
            self.assertEqual({
                "runtime_observation_performed": False,
                "configured": False,
                "boundary_policy_sha256": policy_sha256,
            }, external[boundary])
        serialized = json.dumps(external, sort_keys=True)
        for misleading_count in ("queue_messages", "object_writes", "external_writes"):
            self.assertNotIn(misleading_count, serialized)
        wrong_redis = dict(redis)
        wrong_redis["target_session_binding_sha256"] = capture._target_session_binding(
            OTHER_JAVA_SESSION_ID
        )
        with self.assertRaisesRegex(capture.EvidenceError, "does not bind"):
            capture.build_evidence(scope("after", 4, "java"), database(True),
                                   wrong_redis, observation, True)

    def test_collector_source_has_no_http_dispatch_capability(self) -> None:
        source = pathlib.Path(capture.__file__).read_text(encoding="utf-8")
        for forbidden in (
            "import urllib", "import requests", "import socket", "http.client",
            "urlopen(", "requests.post", "shell=True",
        ):
            self.assertNotIn(forbidden, source)
        self.assertIn('"writes_issued_by_collector": 0', source)
        self.assertIn('"raw_cookie_or_session_id_persisted": False', source)

    def test_legacy_login_limiter_suffix_is_exact_and_representable(self) -> None:
        source = capture.REDIS_CAPTURE_LUA
        self.assertIn(
            "auth%.auth_api%.(api_[a-z_]+)/5/1/minute$",
            source,
        )
        self.assertNotIn("(api_[a-z_]+)/([^/]+)$", source)
        self.assertNotIn("limit ~= '5/1/minute'", source)

    def test_business_digest_sql_quotes_literals_and_projects_only_declared_fields(self) -> None:
        transition = capture._business_state_sql(
            [("users", "r"), ("users_id_seq", "S")], "transition"
        )
        projected = capture._business_state_sql([("users", "r")], "projected")
        self.assertIn("'public.users\t#relation'", transition)
        self.assertIn('FROM ONLY "public"."users" AS t', transition)
        self.assertIn("__phase3_projected_has_password_set__", transition)
        self.assertNotIn("__phase3_projected_password_hash__", transition)
        self.assertIn("__phase3_projected_password_hash__", projected)
        self.assertIn("__phase3_projected_session_version__", projected)
        self.assertIn("__phase3_projected_last_active__", projected)


class FileBoundaryTests(unittest.TestCase):
    def test_atomic_output_is_owner_only_and_never_overwrites(self) -> None:
        with tempfile.TemporaryDirectory() as directory_text:
            directory = pathlib.Path(directory_text)
            directory.chmod(0o700)
            output = directory / "observation.json"
            capture.write_json_atomic(output, {"safe": True})
            self.assertEqual(0o600, output.stat().st_mode & 0o777)
            with self.assertRaises(capture.EvidenceError):
                capture.write_json_atomic(output, {"safe": False})


if __name__ == "__main__":
    unittest.main(verbosity=2)
