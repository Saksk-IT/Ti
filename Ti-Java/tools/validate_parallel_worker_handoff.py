#!/usr/bin/env python3
"""Fail-closed validator for Ti-Java parallel-control-plane v2 handoffs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
from typing import Any, Iterable, Optional, Sequence


SCHEMA_VERSION = 2
ROUTE_STATE = {
    "migrated": 13,
    "pending": 598,
    "production_cutover": 0,
}
AUTHORIZATION_KEYS = (
    "authority_write",
    "contract_successor",
    "data_migration",
    "gateway_change",
    "http_entry",
    "main_write",
    "openapi",
    "operator",
    "production_cutover",
    "route_delta",
    "route_migration",
    "schema_or_index",
)
DECLARATION_KEYS = (
    "central_authority_untouched",
    "historical_evidence_untouched",
    "implementation_worktree_clean",
    "root_assets_untouched",
)
LANE_KINDS = (
    "backend-http-neutral",
    "web-migrated-consumer",
)
MINIMUM_DENYLIST_EXACT = (
    "AGENTS.md",
    "CLAUDE.md",
    "miniprogram-1/.gitignore",
    "Ti-Java/.env.example",
    "Ti-Java/AGENTS.md",
    "Ti-Java/README.md",
    "Ti-Java/server/build-versions.properties",
    "Ti-Java/server/pom.xml",
    "Ti-Java/server/src/main/java/io/saksk/ti/TiApplication.java",
)
MINIMUM_DENYLIST_PREFIXES = (
    ".playwright-cli",
    "output",
    "Ti-Java/contracts",
    "Ti-Java/docs/refactor",
    "Ti-Java/infra",
    "Ti-Java/openapi",
    "Ti-Java/server/src/main/java/io/saksk/ti/sharedkernel",
    "Ti-Java/server/src/main/java/io/saksk/ti/web",
    "Ti-Java/server/src/main/resources",
    "Ti-Java/server/src/test/java/io/saksk/ti/actuator",
    "Ti-Java/server/src/test/java/io/saksk/ti/architecture",
    "Ti-Java/server/src/test/java/io/saksk/ti/integration",
    "Ti-Java/server/src/test/java/io/saksk/ti/support",
    "Ti-Java/server/src/test/java/io/saksk/ti/web",
    "Ti-Java/server/src/test/resources",
    "Ti-Java/tools",
)
HTTP_NEUTRAL_FORBIDDEN_TOKENS = (
    "/api/",
    "/coding/api/",
    "@controller",
    "@deletemapping",
    "@getmapping",
    "@patchmapping",
    "@postmapping",
    "@putmapping",
    "@requestmapping",
    "@restcontroller",
    "httpservlet",
    "jakarta.servlet",
    "javax.servlet",
    "openapi",
    "org.springframework.http",
    "org.springframework.web",
    "routerfunction",
    "route-parity",
    "route_parity",
    "securityfilterchain",
    "serverrequest",
    "serverresponse",
    "swagger",
)
HEX40 = re.compile(r"[0-9a-f]{40}\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
LANE_NAME = re.compile(r"[a-z0-9][a-z0-9-]*\Z")
ROUTE_FINGERPRINT = re.compile(r"[0-9a-f]{12}\Z")
ROUTE_METHODS = {"DELETE", "GET", "PATCH", "POST", "PUT"}
ROUTE_STATUSES = {"migrated-consumer-only", "pending-analysis-only"}
TARGET_KINDS = {"exact", "prefix"}
DIFF_STATUSES = re.compile(r"(?:A|D|M|R[0-9]{1,3}|C[0-9]{1,3})\Z")
JAVA_UNICODE_ESCAPE = re.compile(r"\\u+([0-9a-fA-F]{4})")


class ValidationError(ValueError):
    """Raised when a control-plane document or Git handoff fails closed."""


def canonical_json(document: Any) -> bytes:
    return (json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2)
            + "\n").encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _fail(message: str) -> None:
    raise ValidationError(message)


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail(f"{label} must be an object")
    return value


def _array(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        _fail(f"{label} must be an array")
    return value


def _strict_keys(value: dict[str, Any], expected: Iterable[str],
                 label: str) -> None:
    expected_set = set(expected)
    actual_set = set(value)
    if actual_set != expected_set:
        missing = sorted(expected_set - actual_set)
        unknown = sorted(actual_set - expected_set)
        _fail(f"{label} keys mismatch; missing={missing}, unknown={unknown}")


def _string(value: Any, label: str, *, nonempty: bool = True) -> str:
    if not isinstance(value, str):
        _fail(f"{label} must be a string")
    if nonempty and not value:
        _fail(f"{label} must not be empty")
    return value


def _boolean(value: Any, label: str) -> bool:
    if type(value) is not bool:
        _fail(f"{label} must be a boolean")
    return value


def _integer(value: Any, label: str) -> int:
    if type(value) is not int:
        _fail(f"{label} must be an integer")
    return value


def _hex(value: Any, regex: re.Pattern[str], label: str) -> str:
    result = _string(value, label)
    if not regex.fullmatch(result):
        _fail(f"{label} has invalid hexadecimal shape")
    return result


def _repo_path(value: Any, label: str, *, ti_java_only: bool = False) -> str:
    path = _string(value, label)
    if not path.isascii():
        _fail(f"{label} must use ASCII path bytes")
    if path.startswith("/") or path.endswith("/"):
        _fail(f"{label} must be a normalized repository-relative path")
    if "\\" in path or ":" in path or "\x00" in path:
        _fail(f"{label} contains a forbidden path character")
    if any(ord(character) < 32 or ord(character) == 127
           for character in path):
        _fail(f"{label} contains a control character")
    parts = path.split("/")
    if any(part in ("", ".", "..") for part in parts):
        _fail(f"{label} is not normalized")
    if ".git" in parts:
        _fail(f"{label} enters the Git metadata namespace")
    if ti_java_only and not (path == "Ti-Java" or path.startswith("Ti-Java/")):
        _fail(f"{label} is outside Ti-Java")
    return path


def _paths_overlap(left: str, right: str) -> bool:
    folded_left = left.casefold()
    folded_right = right.casefold()
    return (folded_left == folded_right
            or folded_left.startswith(folded_right + "/")
            or folded_right.startswith(folded_left + "/"))


def _target_contains(target: dict[str, str], path: str) -> bool:
    if target["kind"] == "exact":
        return target["path"] == path
    return path == target["path"] or path.startswith(target["path"] + "/")


def _validate_authorization(value: Any, label: str) -> None:
    document = _object(value, label)
    _strict_keys(document, AUTHORIZATION_KEYS, label)
    for key in AUTHORIZATION_KEYS:
        if _boolean(document[key], f"{label}.{key}"):
            _fail(f"{label}.{key} must remain false")


def _validate_string_array(value: Any, label: str) -> list[str]:
    result = []
    for index, item in enumerate(_array(value, label)):
        result.append(_string(item, f"{label}[{index}]"))
    return result


def _validate_target(value: Any, label: str) -> dict[str, str]:
    target = _object(value, label)
    _strict_keys(target, ("kind", "path"), label)
    kind = _string(target["kind"], f"{label}.kind")
    if kind not in TARGET_KINDS:
        _fail(f"{label}.kind is unsupported")
    path = _repo_path(target["path"], f"{label}.path", ti_java_only=True)
    return {"kind": kind, "path": path}


def _target_sort_key(target: dict[str, str]) -> tuple[str, str]:
    return target["path"], target["kind"]


def _target_conflicts_denylist(target: dict[str, str], exact: Sequence[str],
                               prefixes: Sequence[str]) -> Optional[str]:
    target_path = target["path"]
    for path in exact:
        if target_path == path or (target["kind"] == "prefix"
                                   and path.startswith(target_path + "/")):
            return path
    for path in prefixes:
        if _paths_overlap(target_path, path):
            return path
    return None


def _validate_route_candidate(value: Any, label: str,
                              lane_kind: str) -> None:
    candidate = _object(value, label)
    _strict_keys(candidate, ("fingerprint", "method", "path", "status"), label)
    _hex(candidate["fingerprint"], ROUTE_FINGERPRINT, f"{label}.fingerprint")
    method = _string(candidate["method"], f"{label}.method")
    if method not in ROUTE_METHODS:
        _fail(f"{label}.method is unsupported")
    route_path = _string(candidate["path"], f"{label}.path")
    if not re.fullmatch(r"/[!-~]*", route_path):
        _fail(f"{label}.path must use printable ASCII without spaces")
    status = _string(candidate["status"], f"{label}.status")
    if status not in ROUTE_STATUSES:
        _fail(f"{label}.status is unsupported")
    expected = ("pending-analysis-only" if lane_kind == "backend-http-neutral"
                else "migrated-consumer-only")
    if status != expected:
        _fail(f"{label}.status must be {expected} for {lane_kind}")


def validate_assignment_document(document: Any) -> dict[str, Any]:
    assignment = _object(document, "assignment")
    _strict_keys(assignment, (
        "authorization", "base_sha", "base_tree", "central_denylist_exact",
        "central_denylist_prefixes", "coordination_contract", "created_at",
        "lanes", "route_state", "schema_version", "validator", "wave_id",
    ), "assignment")
    if _integer(assignment["schema_version"], "assignment.schema_version") != SCHEMA_VERSION:
        _fail("assignment.schema_version is unsupported")
    wave_id = _string(assignment["wave_id"], "assignment.wave_id")
    if not LANE_NAME.fullmatch(wave_id):
        _fail("assignment.wave_id has invalid shape")
    created_at = _string(assignment["created_at"], "assignment.created_at")
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}[+-][0-9]{2}:[0-9]{2}", created_at):
        _fail("assignment.created_at must be an offset timestamp without fractions")
    _hex(assignment["base_sha"], HEX40, "assignment.base_sha")
    _hex(assignment["base_tree"], HEX40, "assignment.base_tree")

    for key, expected_path in (
        ("coordination_contract",
         "Ti-Java/docs/refactor/parallel/coordination-contract-v2.md"),
        ("validator", "Ti-Java/tools/validate_parallel_worker_handoff.py"),
    ):
        descriptor = _object(assignment[key], f"assignment.{key}")
        _strict_keys(descriptor, ("path", "sha256"), f"assignment.{key}")
        path = _repo_path(descriptor["path"], f"assignment.{key}.path",
                          ti_java_only=True)
        if path != expected_path:
            _fail(f"assignment.{key}.path is not the fixed v2 path")
        _hex(descriptor["sha256"], HEX64, f"assignment.{key}.sha256")

    route_state = _object(assignment["route_state"], "assignment.route_state")
    _strict_keys(route_state, ROUTE_STATE, "assignment.route_state")
    for key, expected in ROUTE_STATE.items():
        if _integer(route_state[key], f"assignment.route_state.{key}") != expected:
            _fail(f"assignment.route_state.{key} must remain {expected}")
    _validate_authorization(assignment["authorization"],
                            "assignment.authorization")

    exact = [_repo_path(item, f"assignment.central_denylist_exact[{index}]")
             for index, item in enumerate(_array(
                 assignment["central_denylist_exact"],
                 "assignment.central_denylist_exact"))]
    prefixes = [_repo_path(item,
                           f"assignment.central_denylist_prefixes[{index}]")
                for index, item in enumerate(_array(
                    assignment["central_denylist_prefixes"],
                    "assignment.central_denylist_prefixes"))]
    if exact != sorted(set(exact)):
        _fail("assignment.central_denylist_exact must be sorted and unique")
    if prefixes != sorted(set(prefixes)):
        _fail("assignment.central_denylist_prefixes must be sorted and unique")
    if not set(MINIMUM_DENYLIST_EXACT).issubset(exact):
        _fail("assignment.central_denylist_exact weakens the v2 minimum")
    if not set(MINIMUM_DENYLIST_PREFIXES).issubset(prefixes):
        _fail("assignment.central_denylist_prefixes weakens the v2 minimum")

    lanes = _array(assignment["lanes"], "assignment.lanes")
    if not 1 <= len(lanes) <= 8:
        _fail("assignment.lanes must contain between one and eight lanes")
    seen_lanes: set[str] = set()
    seen_branches: set[str] = set()
    seen_handoffs: set[str] = set()
    all_targets: list[tuple[str, dict[str, str]]] = []
    for lane_index, lane_value in enumerate(lanes):
        label = f"assignment.lanes[{lane_index}]"
        lane = _object(lane_value, label)
        _strict_keys(lane, (
            "authorization", "branch", "candidate_route", "handoff_path",
            "http_neutral", "lane", "lane_kind", "ownership_targets",
        ), label)
        name = _string(lane["lane"], f"{label}.lane")
        if not LANE_NAME.fullmatch(name) or name in seen_lanes:
            _fail(f"{label}.lane is invalid or duplicated")
        seen_lanes.add(name)
        branch = _string(lane["branch"], f"{label}.branch")
        if branch != f"codex/parallel-{name}" or branch in seen_branches:
            _fail(f"{label}.branch is invalid or duplicated")
        seen_branches.add(branch)
        handoff = _repo_path(lane["handoff_path"], f"{label}.handoff_path",
                             ti_java_only=True)
        expected_handoff = (
            f"Ti-Java/docs/refactor/parallel/handoffs/{name}.json"
        )
        if handoff != expected_handoff or handoff in seen_handoffs:
            _fail(f"{label}.handoff_path is invalid or duplicated")
        seen_handoffs.add(handoff)
        lane_kind = _string(lane["lane_kind"], f"{label}.lane_kind")
        if lane_kind not in LANE_KINDS:
            _fail(f"{label}.lane_kind is unsupported")
        http_neutral = _boolean(lane["http_neutral"],
                                f"{label}.http_neutral")
        if http_neutral != (lane_kind == "backend-http-neutral"):
            _fail(f"{label}.http_neutral conflicts with lane_kind")
        _validate_route_candidate(lane["candidate_route"],
                                  f"{label}.candidate_route", lane_kind)
        _validate_authorization(lane["authorization"],
                                f"{label}.authorization")
        targets = [_validate_target(target, f"{label}.ownership_targets[{index}]")
                   for index, target in enumerate(_array(
                       lane["ownership_targets"], f"{label}.ownership_targets"))]
        if not targets:
            _fail(f"{label}.ownership_targets must not be empty")
        if targets != sorted(targets, key=_target_sort_key):
            _fail(f"{label}.ownership_targets must be sorted")
        if len({(item["kind"], item["path"]) for item in targets}) != len(targets):
            _fail(f"{label}.ownership_targets contains duplicates")
        for left_index, left in enumerate(targets):
            conflict = _target_conflicts_denylist(left, exact, prefixes)
            if conflict is not None:
                _fail(f"{label} target {left['path']} conflicts with denylist {conflict}")
            for right in targets[left_index + 1:]:
                if _paths_overlap(left["path"], right["path"]):
                    _fail(f"{label} ownership targets overlap")
            for other_lane, other in all_targets:
                if _paths_overlap(left["path"], other["path"]):
                    _fail(f"ownership overlap between {name} and {other_lane}")
            all_targets.append((name, left))
    return assignment


def _regular_file_bytes(path: Path, label: str, *, readonly: bool = False) -> bytes:
    if path.is_symlink():
        _fail(f"{label} must not be a symlink")
    try:
        metadata = path.stat()
    except FileNotFoundError:
        _fail(f"{label} does not exist")
    if not stat.S_ISREG(metadata.st_mode):
        _fail(f"{label} must be a regular file")
    if readonly and metadata.st_mode & 0o222:
        _fail(f"{label} must have all write permission bits removed")
    return path.read_bytes()


def _parse_canonical_json(payload: bytes, label: str) -> dict[str, Any]:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                _fail(f"{label} contains duplicate JSON key {key!r}")
            result[key] = value
        return result

    try:
        document = json.loads(payload.decode("utf-8"),
                              object_pairs_hook=reject_duplicates)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        _fail(f"{label} is not valid UTF-8 JSON: {error}")
    if canonical_json(document) != payload:
        _fail(f"{label} is not canonical JSON")
    return _object(document, label)


def _git(repository_root: Path, *arguments: str, check: bool = True) -> str:
    process = subprocess.run(
        ("git", *arguments), cwd=repository_root, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env={**os.environ, "GIT_NO_REPLACE_OBJECTS": "1",
             "GIT_OPTIONAL_LOCKS": "0", "GIT_PAGER": "cat", "LC_ALL": "C"},
        check=False,
    )
    if check and process.returncode != 0:
        _fail(f"git {' '.join(arguments)} failed: {process.stderr.strip()}")
    return process.stdout.strip()


def _git_bytes(repository_root: Path, *arguments: str,
               check: bool = True) -> bytes:
    process = subprocess.run(
        ("git", *arguments), cwd=repository_root,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env={**os.environ, "GIT_NO_REPLACE_OBJECTS": "1",
             "GIT_OPTIONAL_LOCKS": "0", "GIT_PAGER": "cat", "LC_ALL": "C"},
        check=False,
    )
    if check and process.returncode != 0:
        message = process.stderr.decode("utf-8", errors="replace").strip()
        _fail(f"git {' '.join(arguments)} failed: {message}")
    return process.stdout


def _resolve_repository_root(repository_root: Path) -> Path:
    root = repository_root.resolve()
    discovered = Path(_git(root, "rev-parse", "--show-toplevel")).resolve()
    if discovered != root:
        _fail("--repository-root must be the exact Git worktree root")
    return root


def _git_blob(repository_root: Path, commit: str, path: str) -> bytes:
    return _git_bytes(repository_root, "show", f"{commit}:{path}")


def _git_mode(repository_root: Path, commit: str, path: str) -> Optional[str]:
    payload = _git_bytes(repository_root, "ls-tree", "-z", commit, "--", path)
    if not payload:
        return None
    records = [record for record in payload.split(b"\0") if record]
    if len(records) != 1 or b"\t" not in records[0]:
        _fail(f"unable to resolve exact Git mode for {commit}:{path}")
    metadata, returned_path = records[0].split(b"\t", 1)
    if returned_path.decode("utf-8") != path:
        _fail(f"Git path mismatch for {commit}:{path}")
    fields = metadata.split()
    if len(fields) != 3:
        _fail(f"Git tree metadata malformed for {commit}:{path}")
    return fields[0].decode("ascii")


def _require_regular_git_blob(repository_root: Path, commit: str,
                              path: str) -> None:
    mode = _git_mode(repository_root, commit, path)
    if mode != "100644":
        _fail(f"{commit}:{path} uses forbidden Git mode {mode}")


def _parse_diff_entries(payload: bytes) -> list[dict[str, Optional[str]]]:
    fields = payload.split(b"\0")
    if fields and fields[-1] == b"":
        fields.pop()
    entries: list[dict[str, Optional[str]]] = []
    index = 0
    while index < len(fields):
        try:
            status_value = fields[index].decode("ascii")
        except UnicodeDecodeError:
            _fail("Git diff status is not ASCII")
        index += 1
        if not DIFF_STATUSES.fullmatch(status_value):
            _fail(f"unsupported Git diff status {status_value}")
        if status_value.startswith(("R", "C")):
            if index + 1 >= len(fields):
                _fail("truncated rename/copy Git diff entry")
            old_path = fields[index].decode("utf-8")
            new_path = fields[index + 1].decode("utf-8")
            index += 2
            score = int(status_value[1:])
            if not 0 <= score <= 100 or old_path == new_path:
                _fail("invalid rename/copy Git diff entry")
        else:
            if index >= len(fields):
                _fail("truncated Git diff entry")
            path = fields[index].decode("utf-8")
            index += 1
            if status_value == "A":
                old_path, new_path = None, path
            elif status_value == "D":
                old_path, new_path = path, None
            else:
                old_path, new_path = path, path
        if old_path is not None:
            old_path = _repo_path(old_path, "Git diff old_path")
        if new_path is not None:
            new_path = _repo_path(new_path, "Git diff new_path")
        entries.append({
            "status": status_value,
            "old_path": old_path,
            "new_path": new_path,
        })
    return entries


def implementation_diff_entries(repository_root: Path, base_sha: str,
                                implementation_sha: str
                                ) -> list[dict[str, Optional[str]]]:
    payload = _git_bytes(
        repository_root, "diff", "--no-ext-diff", "--no-textconv",
        "--name-status", "-z", "-M", "-C", "--find-copies-harder",
        base_sha, implementation_sha, "--",
    )
    return _parse_diff_entries(payload)


def _validate_diff_entry_document(value: Any, label: str
                                  ) -> dict[str, Optional[str]]:
    entry = _object(value, label)
    _strict_keys(entry, ("new_path", "old_path", "status"), label)
    status_value = _string(entry["status"], f"{label}.status")
    if not DIFF_STATUSES.fullmatch(status_value):
        _fail(f"{label}.status is unsupported")
    old_path = entry["old_path"]
    new_path = entry["new_path"]
    if old_path is not None:
        old_path = _repo_path(old_path, f"{label}.old_path")
    if new_path is not None:
        new_path = _repo_path(new_path, f"{label}.new_path")
    if status_value == "A" and (old_path is not None or new_path is None):
        _fail(f"{label} has invalid A endpoints")
    elif status_value == "D" and (old_path is None or new_path is not None):
        _fail(f"{label} has invalid D endpoints")
    elif status_value == "M" and (old_path is None or old_path != new_path):
        _fail(f"{label} has invalid M endpoints")
    elif status_value.startswith(("R", "C")) and (
            old_path is None or new_path is None or old_path == new_path):
        _fail(f"{label} has invalid rename/copy endpoints")
    return {"status": status_value, "old_path": old_path,
            "new_path": new_path}


def validate_handoff_document(document: Any, assignment: dict[str, Any],
                              lane: dict[str, Any], assignment_sha256: str
                              ) -> dict[str, Any]:
    handoff = _object(document, "handoff")
    _strict_keys(handoff, (
        "assignment_sha256", "authorization", "base_sha", "branch",
        "central_requests", "declarations", "diff_entries",
        "implementation_sha", "known_risks", "lane", "lock_records",
        "ownership_targets", "route_state", "schema_version", "validation_records",
        "wave_id",
    ), "handoff")
    if _integer(handoff["schema_version"], "handoff.schema_version") != SCHEMA_VERSION:
        _fail("handoff.schema_version is unsupported")
    fixed_pairs = (
        ("wave_id", assignment["wave_id"]),
        ("assignment_sha256", assignment_sha256),
        ("lane", lane["lane"]),
        ("branch", lane["branch"]),
        ("base_sha", assignment["base_sha"]),
    )
    for key, expected in fixed_pairs:
        if _string(handoff[key], f"handoff.{key}") != expected:
            _fail(f"handoff.{key} does not match assignment")
    _hex(handoff["assignment_sha256"], HEX64, "handoff.assignment_sha256")
    _hex(handoff["implementation_sha"], HEX40,
         "handoff.implementation_sha")
    route_state = _object(handoff["route_state"], "handoff.route_state")
    _strict_keys(route_state, ROUTE_STATE, "handoff.route_state")
    for key, expected in ROUTE_STATE.items():
        if _integer(route_state[key], f"handoff.route_state.{key}") != expected:
            _fail(f"handoff.route_state.{key} must remain {expected}")
    targets = [_validate_target(value, f"handoff.ownership_targets[{index}]")
               for index, value in enumerate(_array(
                   handoff["ownership_targets"], "handoff.ownership_targets"))]
    if targets != lane["ownership_targets"]:
        _fail("handoff.ownership_targets does not exactly match assignment")
    entries = [_validate_diff_entry_document(
        value, f"handoff.diff_entries[{index}]")
        for index, value in enumerate(_array(
            handoff["diff_entries"], "handoff.diff_entries"))]
    if not entries:
        _fail("handoff.diff_entries must not be empty")

    validation_records = _array(handoff["validation_records"],
                                "handoff.validation_records")
    if not validation_records:
        _fail("handoff.validation_records must not be empty")
    diff_check_passed = False
    for index, value in enumerate(validation_records):
        label = f"handoff.validation_records[{index}]"
        record = _object(value, label)
        _strict_keys(record, ("command", "detail", "result"), label)
        command = _string(record["command"], f"{label}.command")
        result = _string(record["result"], f"{label}.result")
        _string(record["detail"], f"{label}.detail", nonempty=False)
        if result not in ("not_run", "passed"):
            _fail(f"{label}.result is unsupported")
        if "git diff --check" in command and result == "passed":
            diff_check_passed = True
    if not diff_check_passed:
        _fail("handoff must record a passing git diff --check")

    lock_records = _array(handoff["lock_records"], "handoff.lock_records")
    if len(lock_records) != 1:
        _fail("handoff.lock_records must contain exactly heavy-verify.lock")
    lock = _object(lock_records[0], "handoff.lock_records[0]")
    _strict_keys(lock, (
        "acquired_at", "commands", "lock", "owner", "released_at", "status",
    ), "handoff.lock_records[0]")
    if lock["lock"] != "heavy-verify.lock":
        _fail("handoff lock record must describe heavy-verify.lock")
    status_value = _string(lock["status"], "handoff.lock_records[0].status")
    commands = _validate_string_array(lock["commands"],
                                      "handoff.lock_records[0].commands")
    if status_value == "not_acquired":
        if any(lock[key] is not None for key in
               ("acquired_at", "owner", "released_at")) or commands:
            _fail("not_acquired lock record must use null timestamps/owner and no commands")
    elif status_value == "acquired_and_released":
        for key in ("acquired_at", "owner", "released_at"):
            _string(lock[key], f"handoff.lock_records[0].{key}")
        if not commands:
            _fail("acquired_and_released lock record must list commands")
    else:
        _fail("handoff lock status is unsupported")

    _validate_string_array(handoff["known_risks"], "handoff.known_risks")
    _validate_string_array(handoff["central_requests"],
                           "handoff.central_requests")
    _validate_authorization(handoff["authorization"], "handoff.authorization")
    declarations = _object(handoff["declarations"], "handoff.declarations")
    _strict_keys(declarations, DECLARATION_KEYS, "handoff.declarations")
    for key in DECLARATION_KEYS:
        if not _boolean(declarations[key], f"handoff.declarations.{key}"):
            _fail(f"handoff.declarations.{key} must be true")
    return handoff


def _lane_by_name(assignment: dict[str, Any], name: str) -> dict[str, Any]:
    for lane in assignment["lanes"]:
        if lane["lane"] == name:
            return lane
    _fail(f"lane {name} is not present in assignment")


def _path_authorized(path: str, targets: Sequence[dict[str, str]]) -> bool:
    return any(_target_contains(target, path) for target in targets)


def _java_unicode_decode(value: str) -> str:
    result = value
    for _ in range(8):
        changed = JAVA_UNICODE_ESCAPE.sub(
            lambda match: chr(int(match.group(1), 16)), result)
        if changed == result:
            return result
        result = changed
    return result


def _scan_http_neutral_blob(repository_root: Path, commit: str,
                            path: str) -> None:
    text = _read_utf8_blob(repository_root, commit, path)
    searchable = _java_unicode_decode(path + "\n" + text).lower()
    for token in HTTP_NEUTRAL_FORBIDDEN_TOKENS:
        if token in searchable:
            _fail(f"HTTP-neutral token {token!r} found in {commit}:{path}")


def _read_utf8_blob(repository_root: Path, commit: str, path: str) -> str:
    payload = _git_blob(repository_root, commit, path)
    if len(payload) > 2_000_000:
        _fail(f"worker blob exceeds 2 MB: {commit}:{path}")
    if b"\x00" in payload:
        _fail(f"worker blob contains NUL/binary content: {commit}:{path}")
    try:
        return payload.decode("utf-8")
    except UnicodeDecodeError:
        _fail(f"worker blob is not UTF-8 text: {commit}:{path}")


def _commit_parents(repository_root: Path, commit: str) -> list[str]:
    line = _git(repository_root, "rev-list", "--parents", "-n", "1", commit)
    fields = line.split()
    if not fields or fields[0] != commit:
        _fail(f"unable to resolve commit graph for {commit}")
    return fields[1:]


def _require_commit(repository_root: Path, commit: str, label: str) -> None:
    _hex(commit, HEX40, label)
    resolved = _git(repository_root, "rev-parse", f"{commit}^{{commit}}")
    if resolved != commit:
        _fail(f"{label} does not resolve to the fixed commit")


def validate_assignment_file(assignment_path: Path, repository_root: Path
                             ) -> tuple[dict[str, Any], bytes]:
    root = _resolve_repository_root(repository_root)
    assignment_resolved = assignment_path.resolve()
    try:
        assignment_resolved.relative_to(root)
    except ValueError:
        pass
    else:
        _fail("assignment must be repository-external")
    payload = _regular_file_bytes(assignment_path, "assignment", readonly=True)
    assignment = validate_assignment_document(
        _parse_canonical_json(payload, "assignment"))
    base_sha = assignment["base_sha"]
    if _git(root, "rev-parse", "--show-object-format") != "sha1":
        _fail("parallel control plane v2 requires the fixed sha1 object format")
    _require_commit(root, base_sha, "assignment.base_sha")
    base_tree = _git(root, "rev-parse", f"{base_sha}^{{tree}}")
    if base_tree != assignment["base_tree"]:
        _fail("assignment.base_tree does not match assignment.base_sha")
    for key in ("coordination_contract", "validator"):
        descriptor = assignment[key]
        blob = _git_blob(root, base_sha, descriptor["path"])
        if sha256_bytes(blob) != descriptor["sha256"]:
            _fail(f"assignment.{key}.sha256 does not match BASE_SHA blob")
        _require_regular_git_blob(root, base_sha, descriptor["path"])
    return assignment, payload


def _validate_branch_ref(repository_root: Path, branch: str,
                         handoff_sha: str) -> None:
    candidates = (
        f"refs/heads/{branch}",
        f"refs/remotes/origin/{branch}",
    )
    resolved = []
    for reference in candidates:
        value = _git(repository_root, "show-ref", "--verify", "--hash",
                     reference, check=False)
        if value:
            resolved.append(value)
    if not resolved:
        _fail(f"no fixed local or origin ref exists for {branch}")
    if handoff_sha not in resolved:
        _fail(f"branch ref does not point to handoff SHA {handoff_sha}")


def _validate_integration_head(repository_root: Path, base_sha: str,
                               integration_head: str,
                               targets: Sequence[dict[str, str]]) -> None:
    resolved = _git(repository_root, "rev-parse",
                    f"{integration_head}^{{commit}}")
    if not HEX40.fullmatch(resolved):
        _fail("integration head does not resolve to a full commit")
    if _git(repository_root, "merge-base", base_sha, resolved) != base_sha:
        _fail("assignment BASE_SHA is not an ancestor of integration head")
    paths = [target["path"] for target in targets]
    process = subprocess.run(
        ("git", "diff", "--quiet", base_sha, resolved, "--", *paths),
        cwd=repository_root, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env={**os.environ, "GIT_NO_REPLACE_OBJECTS": "1",
             "GIT_OPTIONAL_LOCKS": "0", "GIT_PAGER": "cat", "LC_ALL": "C"},
        check=False,
    )
    if process.returncode == 1:
        _fail("integration head changed this lane's ownership since BASE_SHA")
    if process.returncode not in (0, 1):
        _fail("unable to compare integration head against BASE_SHA")


def _validate_post_integration_head(repository_root: Path,
                                    implementation_sha: str,
                                    post_integration_head: str,
                                    targets: Sequence[dict[str, str]]) -> None:
    resolved = _git(repository_root, "rev-parse",
                    f"{post_integration_head}^{{commit}}")
    if not HEX40.fullmatch(resolved):
        _fail("post-integration head does not resolve to a full commit")
    paths = [target["path"] for target in targets]
    process = subprocess.run(
        ("git", "diff", "--quiet", implementation_sha, resolved, "--", *paths),
        cwd=repository_root, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env={**os.environ, "GIT_NO_REPLACE_OBJECTS": "1",
             "GIT_OPTIONAL_LOCKS": "0", "GIT_PAGER": "cat", "LC_ALL": "C"},
        check=False,
    )
    if process.returncode == 1:
        _fail("post-integration head does not reproduce implementation bytes")
    if process.returncode not in (0, 1):
        _fail("unable to compare post-integration head with implementation")


def validate_worker_handoff(repository_root: Path, assignment_path: Path,
                            lane_name: str, handoff_sha: str,
                            expected_assignment_sha256: str,
                            integration_head: Optional[str] = None,
                            post_integration_head: Optional[str] = None,
                            ) -> dict[str, Any]:
    root = _resolve_repository_root(repository_root)
    assignment, assignment_payload = validate_assignment_file(
        assignment_path, root)
    _hex(expected_assignment_sha256, HEX64, "expected_assignment_sha256")
    actual_assignment_sha256 = sha256_bytes(assignment_payload)
    if actual_assignment_sha256 != expected_assignment_sha256:
        _fail("assignment raw SHA-256 does not match the fixed CLI digest")
    lane = _lane_by_name(assignment, lane_name)
    _require_commit(root, handoff_sha, "handoff_sha")
    _validate_branch_ref(root, lane["branch"], handoff_sha)
    handoff_blob = _git_blob(root, handoff_sha, lane["handoff_path"])
    handoff_document = _parse_canonical_json(handoff_blob, "handoff")
    handoff = validate_handoff_document(
        handoff_document, assignment, lane, sha256_bytes(assignment_payload))
    implementation_sha = handoff["implementation_sha"]
    _require_commit(root, implementation_sha, "handoff.implementation_sha")
    if _commit_parents(root, implementation_sha) != [assignment["base_sha"]]:
        _fail("implementation commit must be the direct single-parent child of BASE_SHA")
    if _commit_parents(root, handoff_sha) != [implementation_sha]:
        _fail("handoff commit must be the direct single-parent child of implementation")

    handoff_diff = _parse_diff_entries(_git_bytes(
        root, "diff", "--no-ext-diff", "--no-textconv", "--name-status",
        "-z", "--no-renames",
        implementation_sha, handoff_sha, "--",
    ))
    expected_handoff_diff = [{
        "status": "A", "old_path": None, "new_path": lane["handoff_path"],
    }]
    if handoff_diff != expected_handoff_diff:
        _fail("handoff commit must only add the fixed handoff JSON")
    if _git_mode(root, handoff_sha, lane["handoff_path"]) != "100644":
        _fail("handoff JSON must use Git mode 100644")

    diff_entries = implementation_diff_entries(
        root, assignment["base_sha"], implementation_sha)
    if diff_entries != handoff["diff_entries"]:
        _fail("handoff.diff_entries does not match the Git implementation diff")
    exact = assignment["central_denylist_exact"]
    prefixes = assignment["central_denylist_prefixes"]
    targets = lane["ownership_targets"]
    for entry in diff_entries:
        endpoints = []
        if entry["old_path"] is not None:
            endpoints.append((assignment["base_sha"], entry["old_path"]))
        if entry["new_path"] is not None:
            endpoints.append((implementation_sha, entry["new_path"]))
        for commit, path in endpoints:
            if path == lane["handoff_path"] or not _path_authorized(path, targets):
                _fail(f"implementation path is outside ownership: {path}")
            if path in exact or any(path == prefix or path.startswith(prefix + "/")
                                    for prefix in prefixes):
                _fail(f"implementation path enters central denylist: {path}")
            _require_regular_git_blob(root, commit, path)
            _read_utf8_blob(root, commit, path)
            if lane["http_neutral"]:
                _scan_http_neutral_blob(root, commit, path)
    if integration_head is not None:
        _validate_integration_head(root, assignment["base_sha"],
                                   integration_head, targets)
    if post_integration_head is not None:
        _validate_post_integration_head(root, implementation_sha,
                                        post_integration_head, targets)
    return {
        "assignment_sha256": sha256_bytes(assignment_payload),
        "base_sha": assignment["base_sha"],
        "diff_entry_count": len(diff_entries),
        "handoff_sha": handoff_sha,
        "implementation_sha": implementation_sha,
        "lane": lane_name,
        "route_state": ROUTE_STATE,
        "status": "accepted-boundary-only",
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", required=True, type=Path)
    parser.add_argument("--assignment", required=True, type=Path)
    parser.add_argument("--lane", required=True)
    parser.add_argument("--handoff-sha", required=True)
    parser.add_argument("--assignment-sha256", required=True)
    parser.add_argument("--integration-head")
    parser.add_argument("--post-integration-head")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        result = validate_worker_handoff(
            arguments.repository_root, arguments.assignment, arguments.lane,
            arguments.handoff_sha, arguments.assignment_sha256,
            arguments.integration_head, arguments.post_integration_head,
        )
    except ValidationError as error:
        print(f"parallel handoff rejected: {error}", file=sys.stderr)
        return 2
    print(canonical_json(result).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
