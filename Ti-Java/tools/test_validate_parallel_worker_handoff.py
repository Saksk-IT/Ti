#!/usr/bin/env python3
"""Hostile tests for the parallel-control-plane v2 worker validator."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import validate_parallel_worker_handoff as validator


TI_JAVA_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_SOURCE = (
    TI_JAVA_ROOT / "docs/refactor/parallel/coordination-contract-v2.md"
)
VALIDATOR_SOURCE = TI_JAVA_ROOT / "tools/validate_parallel_worker_handoff.py"
LANE = "assessment-records-read"
BRANCH = f"codex/parallel-{LANE}"
OWNED_PREFIX = (
    "Ti-Java/server/src/main/java/io/saksk/ti/assessment/application"
)
HANDOFF_PATH = f"Ti-Java/docs/refactor/parallel/handoffs/{LANE}.json"


def _authorization() -> dict[str, bool]:
    return {key: False for key in validator.AUTHORIZATION_KEYS}


def _git(root: Path, *arguments: str) -> str:
    process = subprocess.run(
        ("git", *arguments), cwd=root, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        env={**os.environ, "LC_ALL": "C", "GIT_NO_REPLACE_OBJECTS": "1",
             "GIT_OPTIONAL_LOCKS": "0"},
    )
    if process.returncode != 0:
        raise AssertionError(
            f"git {' '.join(arguments)} failed: {process.stderr}"
        )
    return process.stdout.strip()


def _write(root: Path, relative: str, payload: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")
    return path


class GitFixture:
    def __init__(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="ti-parallel-validator-"
        )
        self.container = Path(self.temporary.name)
        self.root = self.container / "repository"
        self.root.mkdir()
        _git(self.root, "init", "-b", "main")
        _git(self.root, "config", "user.name", "Parallel Validator Test")
        _git(self.root, "config", "user.email", "parallel@example.invalid")
        contract = self.root / (
            "Ti-Java/docs/refactor/parallel/coordination-contract-v2.md"
        )
        contract.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(CONTRACT_SOURCE, contract)
        source = self.root / "Ti-Java/tools/validate_parallel_worker_handoff.py"
        source.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(VALIDATOR_SOURCE, source)
        _write(self.root, "Ti-Java/legacy-source.java", "final class Legacy {}\n")
        _git(self.root, "add", "Ti-Java")
        _git(self.root, "commit", "-m", "base")
        self.base_sha = _git(self.root, "rev-parse", "HEAD")
        self.assignment = self._assignment()
        self.assignment_path = self.container / "assignment.json"
        self.write_assignment()
        _git(self.root, "switch", "-c", BRANCH)

    def close(self) -> None:
        self.temporary.cleanup()

    def _assignment(self) -> dict:
        return {
            "schema_version": 2,
            "wave_id": "wave-test-01",
            "created_at": "2026-07-19T12:00:00+08:00",
            "base_sha": self.base_sha,
            "base_tree": _git(self.root, "rev-parse", f"{self.base_sha}^{{tree}}"),
            "coordination_contract": {
                "path": "Ti-Java/docs/refactor/parallel/coordination-contract-v2.md",
                "sha256": hashlib.sha256(CONTRACT_SOURCE.read_bytes()).hexdigest(),
            },
            "validator": {
                "path": "Ti-Java/tools/validate_parallel_worker_handoff.py",
                "sha256": hashlib.sha256(VALIDATOR_SOURCE.read_bytes()).hexdigest(),
            },
            "route_state": dict(validator.ROUTE_STATE),
            "central_denylist_exact": sorted(
                set(validator.MINIMUM_DENYLIST_EXACT)
                | {
                    "Ti-Java/server/src/main/java/io/saksk/ti/assessment/package-info.java",
                }
            ),
            "central_denylist_prefixes": sorted(
                set(validator.MINIMUM_DENYLIST_PREFIXES)
                | {
                    "Ti-Java/server/src/main/java/io/saksk/ti/assessment/api",
                }
            ),
            "authorization": _authorization(),
            "lanes": [{
                "lane": LANE,
                "branch": BRANCH,
                "handoff_path": HANDOFF_PATH,
                "lane_kind": "backend-http-neutral",
                "http_neutral": True,
                "ownership_targets": [{
                    "kind": "prefix",
                    "path": OWNED_PREFIX,
                }],
                "candidate_route": {
                    "fingerprint": "ee831203df4d",
                    "method": "GET",
                    "path": "/api/exams/records",
                    "status": "pending-analysis-only",
                },
                "authorization": _authorization(),
            }],
        }

    def write_assignment(self) -> None:
        self.assignment_path.chmod(0o644) if self.assignment_path.exists() else None
        self.assignment_path.write_bytes(validator.canonical_json(self.assignment))
        self.assignment_path.chmod(0o444)

    def commit_implementation(self, relative: str = OWNED_PREFIX + "/ReadUseCase.java",
                              payload: str = "package example; final class ReadUseCase {}\n",
                              executable: bool = False) -> str:
        path = _write(self.root, relative, payload)
        if executable:
            path.chmod(0o755)
        _git(self.root, "add", "--", relative)
        _git(self.root, "commit", "-m", "implement lane")
        return _git(self.root, "rev-parse", "HEAD")

    def handoff_document(self, implementation_sha: str) -> dict:
        return {
            "schema_version": 2,
            "wave_id": self.assignment["wave_id"],
            "assignment_sha256": hashlib.sha256(
                self.assignment_path.read_bytes()).hexdigest(),
            "lane": LANE,
            "branch": BRANCH,
            "base_sha": self.base_sha,
            "implementation_sha": implementation_sha,
            "route_state": dict(validator.ROUTE_STATE),
            "ownership_targets": deepcopy(
                self.assignment["lanes"][0]["ownership_targets"]),
            "diff_entries": validator.implementation_diff_entries(
                self.root, self.base_sha, implementation_sha),
            "validation_records": [{
                "command": f"git diff --check {self.base_sha} {implementation_sha}",
                "result": "passed",
                "detail": "no whitespace errors",
            }],
            "lock_records": [{
                "lock": "heavy-verify.lock",
                "status": "not_acquired",
                "owner": None,
                "acquired_at": None,
                "released_at": None,
                "commands": [],
            }],
            "known_risks": ["HTTP parity remains central"],
            "central_requests": ["INT wires the HTTP entry later"],
            "authorization": _authorization(),
            "declarations": {
                key: True for key in validator.DECLARATION_KEYS
            },
        }

    def commit_handoff(self, implementation_sha: str, *, document: dict = None,
                       extra_path: str = None) -> str:
        if document is None:
            document = self.handoff_document(implementation_sha)
        path = self.root / HANDOFF_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(validator.canonical_json(document))
        _git(self.root, "add", "--", HANDOFF_PATH)
        if extra_path is not None:
            _write(self.root, extra_path, "extra\n")
            _git(self.root, "add", "--", extra_path)
        _git(self.root, "commit", "-m", "handoff lane")
        return _git(self.root, "rev-parse", "HEAD")


class ParallelAssignmentSchemaTest(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = GitFixture()

    def tearDown(self) -> None:
        self.fixture.close()

    def test_valid_assignment_is_external_readonly_and_git_bound(self) -> None:
        assignment, payload = validator.validate_assignment_file(
            self.fixture.assignment_path, self.fixture.root)
        self.assertEqual(self.fixture.base_sha, assignment["base_sha"])
        self.assertEqual(validator.canonical_json(assignment), payload)

    def test_unknown_duplicate_and_bool_integer_fields_fail_closed(self) -> None:
        unknown = deepcopy(self.fixture.assignment)
        unknown["unexpected"] = True
        with self.assertRaisesRegex(validator.ValidationError, "keys mismatch"):
            validator.validate_assignment_document(unknown)
        invalid = deepcopy(self.fixture.assignment)
        invalid["schema_version"] = True
        with self.assertRaisesRegex(validator.ValidationError, "integer"):
            validator.validate_assignment_document(invalid)
        duplicate = b'{"schema_version":2,"schema_version":2}\n'
        with self.assertRaisesRegex(validator.ValidationError, "duplicate JSON key"):
            validator._parse_canonical_json(duplicate, "assignment")

    def test_path_escape_case_collision_and_near_sibling(self) -> None:
        for path in ("/Ti-Java/x", "Ti-Java/../x", "Ti-Java\\x",
                     "Ti-Java//x", "Ti-Java/\u4e2d"):
            changed = deepcopy(self.fixture.assignment)
            changed["lanes"][0]["ownership_targets"][0]["path"] = path
            with self.subTest(path=path), self.assertRaises(validator.ValidationError):
                validator.validate_assignment_document(changed)
        self.assertFalse(validator._paths_overlap("Ti-Java/foo/bar",
                                                  "Ti-Java/foo/barista"))
        self.assertTrue(validator._paths_overlap("Ti-Java/Foo",
                                                 "Ti-Java/foo/child"))

    def test_intra_lane_cross_lane_and_denylist_overlap_fail(self) -> None:
        intra = deepcopy(self.fixture.assignment)
        intra["lanes"][0]["ownership_targets"].append({
            "kind": "prefix", "path": OWNED_PREFIX + "/nested",
        })
        with self.assertRaisesRegex(validator.ValidationError, "overlap"):
            validator.validate_assignment_document(intra)

        cross = deepcopy(self.fixture.assignment)
        second = deepcopy(cross["lanes"][0])
        second["lane"] = "assessment-second"
        second["branch"] = "codex/parallel-assessment-second"
        second["handoff_path"] = (
            "Ti-Java/docs/refactor/parallel/handoffs/assessment-second.json"
        )
        second["ownership_targets"] = [{
            "kind": "exact", "path": OWNED_PREFIX + "/Other.java",
        }]
        cross["lanes"].append(second)
        with self.assertRaisesRegex(validator.ValidationError,
                                    "ownership overlap"):
            validator.validate_assignment_document(cross)

        denied = deepcopy(self.fixture.assignment)
        denied["lanes"][0]["ownership_targets"] = [{
            "kind": "prefix", "path": "Ti-Java/tools/generated",
        }]
        with self.assertRaisesRegex(validator.ValidationError,
                                    "conflicts with denylist"):
            validator.validate_assignment_document(denied)

    def test_route_state_and_authorization_cannot_advance(self) -> None:
        for key, value in (("migrated", 14), ("pending", 597),
                           ("production_cutover", 1)):
            changed = deepcopy(self.fixture.assignment)
            changed["route_state"][key] = value
            with self.subTest(key=key), self.assertRaises(validator.ValidationError):
                validator.validate_assignment_document(changed)
        changed = deepcopy(self.fixture.assignment)
        changed["authorization"]["route_migration"] = True
        with self.assertRaisesRegex(validator.ValidationError,
                                    "must remain false"):
            validator.validate_assignment_document(changed)


class ParallelWorkerGitTest(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = GitFixture()

    def tearDown(self) -> None:
        self.fixture.close()

    def _accept(self, handoff_sha: str, integration_head: str = None,
                post_integration_head: str = None,
                assignment_sha256: str = None) -> dict:
        if assignment_sha256 is None:
            assignment_sha256 = hashlib.sha256(
                self.fixture.assignment_path.read_bytes()).hexdigest()
        return validator.validate_worker_handoff(
            self.fixture.root, self.fixture.assignment_path, LANE,
            handoff_sha, assignment_sha256, integration_head,
            post_integration_head,
        )

    def test_exact_two_commit_handoff_is_accepted(self) -> None:
        implementation = self.fixture.commit_implementation()
        handoff = self.fixture.commit_handoff(implementation)
        result = self._accept(handoff, self.fixture.base_sha,
                              implementation)
        self.assertEqual("accepted-boundary-only", result["status"])
        self.assertEqual(implementation, result["implementation_sha"])
        self.assertEqual(validator.ROUTE_STATE, result["route_state"])

    def test_unauthorized_path_and_unicode_http_token_are_rejected(self) -> None:
        implementation = self.fixture.commit_implementation(
            "Ti-Java/server/src/main/java/io/saksk/ti/community/domain/X.java")
        handoff = self.fixture.commit_handoff(implementation)
        with self.assertRaisesRegex(validator.ValidationError,
                                    "outside ownership"):
            self._accept(handoff)

        self.fixture.close()
        self.fixture = GitFixture()
        implementation = self.fixture.commit_implementation(
            payload=r"package example; \u0040RestController final class X {}" + "\n"
        )
        handoff = self.fixture.commit_handoff(implementation)
        with self.assertRaisesRegex(validator.ValidationError,
                                    "HTTP-neutral token"):
            self._accept(handoff)

    def test_symlink_and_executable_modes_are_rejected(self) -> None:
        relative = OWNED_PREFIX + "/Link.java"
        target = self.fixture.root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.symlink_to("ReadUseCase.java")
        _git(self.fixture.root, "add", "--", relative)
        _git(self.fixture.root, "commit", "-m", "symlink")
        implementation = _git(self.fixture.root, "rev-parse", "HEAD")
        handoff = self.fixture.commit_handoff(implementation)
        with self.assertRaisesRegex(validator.ValidationError,
                                    "forbidden Git mode"):
            self._accept(handoff)

        self.fixture.close()
        self.fixture = GitFixture()
        implementation = self.fixture.commit_implementation(executable=True)
        handoff = self.fixture.commit_handoff(implementation)
        with self.assertRaisesRegex(validator.ValidationError,
                                    "forbidden Git mode"):
            self._accept(handoff)

    def test_extra_implementation_commit_and_extra_handoff_file_are_rejected(self) -> None:
        first = self.fixture.commit_implementation()
        _write(self.fixture.root, OWNED_PREFIX + "/Second.java",
               "package example; final class Second {}\n")
        _git(self.fixture.root, "add", "--", OWNED_PREFIX + "/Second.java")
        _git(self.fixture.root, "commit", "-m", "second implementation")
        second = _git(self.fixture.root, "rev-parse", "HEAD")
        self.assertNotEqual(first, second)
        handoff = self.fixture.commit_handoff(second)
        with self.assertRaisesRegex(validator.ValidationError,
                                    "direct single-parent child of BASE_SHA"):
            self._accept(handoff)

        self.fixture.close()
        self.fixture = GitFixture()
        implementation = self.fixture.commit_implementation()
        handoff = self.fixture.commit_handoff(
            implementation, extra_path="Ti-Java/extra.txt")
        with self.assertRaisesRegex(validator.ValidationError,
                                    "must only add"):
            self._accept(handoff)

    def test_rename_from_unowned_source_checks_both_endpoints(self) -> None:
        destination = OWNED_PREFIX + "/Legacy.java"
        (self.fixture.root / destination).parent.mkdir(parents=True, exist_ok=True)
        _git(self.fixture.root, "mv", "Ti-Java/legacy-source.java", destination)
        _git(self.fixture.root, "commit", "-m", "rename unowned source")
        implementation = _git(self.fixture.root, "rev-parse", "HEAD")
        entries = validator.implementation_diff_entries(
            self.fixture.root, self.fixture.base_sha, implementation)
        self.assertTrue(entries[0]["status"].startswith("R"))
        handoff = self.fixture.commit_handoff(implementation)
        with self.assertRaisesRegex(validator.ValidationError,
                                    "outside ownership"):
            self._accept(handoff)

    def test_branch_tip_digest_and_handoff_diff_are_fixed(self) -> None:
        implementation = self.fixture.commit_implementation()
        document = self.fixture.handoff_document(implementation)
        document["assignment_sha256"] = "0" * 64
        handoff = self.fixture.commit_handoff(implementation, document=document)
        with self.assertRaisesRegex(validator.ValidationError,
                                    "does not match assignment"):
            self._accept(handoff)

        with self.assertRaisesRegex(validator.ValidationError,
                                    "fixed CLI digest"):
            self._accept(handoff, assignment_sha256="f" * 64)

        self.fixture.close()
        self.fixture = GitFixture()
        implementation = self.fixture.commit_implementation()
        handoff = self.fixture.commit_handoff(implementation)
        _write(self.fixture.root, OWNED_PREFIX + "/After.java",
               "package example; final class After {}\n")
        _git(self.fixture.root, "add", "--", OWNED_PREFIX + "/After.java")
        _git(self.fixture.root, "commit", "-m", "advance branch")
        with self.assertRaisesRegex(validator.ValidationError,
                                    "branch ref does not point"):
            self._accept(handoff)

    def test_integration_head_must_preserve_owned_paths_from_base(self) -> None:
        implementation = self.fixture.commit_implementation()
        handoff = self.fixture.commit_handoff(implementation)
        _git(self.fixture.root, "switch", "-c", "integration", self.fixture.base_sha)
        _write(self.fixture.root, OWNED_PREFIX + "/Other.java",
               "package example; final class Other {}\n")
        _git(self.fixture.root, "add", "--", OWNED_PREFIX + "/Other.java")
        _git(self.fixture.root, "commit", "-m", "conflicting integration head")
        integration = _git(self.fixture.root, "rev-parse", "HEAD")
        with self.assertRaisesRegex(validator.ValidationError,
                                    "changed this lane's ownership"):
            self._accept(handoff, integration)

    def test_post_integration_head_must_reproduce_implementation_tree(self) -> None:
        implementation = self.fixture.commit_implementation()
        handoff = self.fixture.commit_handoff(implementation)
        _git(self.fixture.root, "switch", "-c", "post-integration",
             self.fixture.base_sha)
        _write(self.fixture.root, OWNED_PREFIX + "/ReadUseCase.java",
               "package example; final class Different {}\n")
        _git(self.fixture.root, "add", "--", OWNED_PREFIX + "/ReadUseCase.java")
        _git(self.fixture.root, "commit", "-m", "different integration bytes")
        post_integration = _git(self.fixture.root, "rev-parse", "HEAD")
        with self.assertRaisesRegex(validator.ValidationError,
                                    "does not reproduce implementation bytes"):
            self._accept(handoff, post_integration_head=post_integration)


if __name__ == "__main__":
    unittest.main()
