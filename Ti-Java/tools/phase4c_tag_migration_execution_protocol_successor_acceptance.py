#!/usr/bin/env python3
"""Gitless successor acceptance for the Phase 4C execution protocol."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
import importlib
import json
from pathlib import Path
import subprocess
from typing import Any, Callable, Iterator, Mapping, TypeVar

try:
    from tools import build_phase4c_tag_migration_execution_protocol_contract as builder
except ModuleNotFoundError as error:
    if error.name not in {
        "tools",
        "tools.build_phase4c_tag_migration_execution_protocol_contract",
    }:
        raise
    import build_phase4c_tag_migration_execution_protocol_contract as builder


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_RELATIVE = builder.OUTPUT_RELATIVE

# Mechanically derived from the final deterministic builder payload.  The main
# lane writes those exact bytes to CONTRACT_RELATIVE.
CONTRACT_SHA256: str | None = (
    "e236b3cde251026c3a189762b650eb4df80213dcdab667a5b8f50eb20a0e8e14"
)
CONTRACT_PAYLOAD_SHA256: str | None = (
    "42599261bc5632feed89fc41637ee1a98cff844dd9dc776f889d155a0567a7c4"
)
CONTRACT_BYTE_COUNT: int | None = 44_336
BUILD_CONTEXT_SCRIPT_RELATIVE = builder.BUILD_CONTEXT_SCRIPT_RELATIVE
TRANSACTION_WRITE_SUCCESSOR_MODULE = (
    "tools."
    "phase4c_learning_transaction_write_http_full_parity_successor_acceptance"
)
TRANSACTION_WRITE_SUCCESSOR_DIRECT_MODULE = (
    "phase4c_learning_transaction_write_http_full_parity_successor_acceptance"
)
_CachedValue = TypeVar("_CachedValue")
_VALIDATION_SESSION: ContextVar[dict[tuple[str, str], Any] | None] = (
    ContextVar("phase4c_acceptance_validation_session", default=None)
)


@dataclass(frozen=True)
class ProductionRuntimeSuccessor:
    view: str
    accepted_file_count: int
    accepted_manifest_sha256: str
    current_file_count: int
    current_manifest_sha256: str
    added_files: tuple[tuple[str, str], ...]
    changed_files: tuple[tuple[str, str], ...]
    deleted_files: tuple[str, ...]


@dataclass(frozen=True)
class WormSuccessor:
    accepted_report_sha256: str
    accepted_build_context_sha256: str
    accepted_chain_node_count: int
    current_report_sha256: str
    current_build_context_sha256: str
    current_chain_node_count: int


@contextmanager
def validation_session() -> Iterator[None]:
    """Share validation only within one fail-closed top-level acceptance call."""
    existing = _VALIDATION_SESSION.get()
    if existing is not None:
        yield
        return
    token = _VALIDATION_SESSION.set({})
    try:
        yield
    finally:
        _VALIDATION_SESSION.reset(token)


def validation_session_cached(
    namespace: str,
    root: Path,
    factory: Callable[[], _CachedValue],
) -> _CachedValue:
    """Cache a validated value only while ``validation_session`` is active."""
    cache = _VALIDATION_SESSION.get()
    if cache is None:
        return factory()
    key = (namespace, str(root.resolve(strict=True)))
    if key not in cache:
        cache[key] = factory()
    return cache[key]


def _require_contract_envelope() -> tuple[str, str, int]:
    if (
        CONTRACT_SHA256 is None
        or CONTRACT_PAYLOAD_SHA256 is None
        or CONTRACT_BYTE_COUNT is None
    ):
        raise AssertionError(
            "execution-protocol contract envelope requires final mechanical refresh"
        )
    return CONTRACT_SHA256, CONTRACT_PAYLOAD_SHA256, CONTRACT_BYTE_COUNT


def _load_transaction_write_successor() -> object:
    try:
        return importlib.import_module(TRANSACTION_WRITE_SUCCESSOR_MODULE)
    except ModuleNotFoundError as error:
        if error.name not in {"tools", TRANSACTION_WRITE_SUCCESSOR_MODULE}:
            raise
    try:
        return importlib.import_module(TRANSACTION_WRITE_SUCCESSOR_DIRECT_MODULE)
    except ModuleNotFoundError as error:
        if error.name != TRANSACTION_WRITE_SUCCESSOR_DIRECT_MODULE:
            raise
        raise AssertionError(
            "execution-protocol transaction-write successor is required"
        ) from error


def _load_contract_envelope(root: Path) -> dict[str, Any]:
    sha256, payload_sha256, byte_count = _require_contract_envelope()
    payload = builder.fixed_regular_file(root, CONTRACT_RELATIVE).read_bytes()
    if len(payload) != byte_count or builder.sha256_bytes(payload) != sha256:
        raise AssertionError("execution-protocol contract bytes drifted")
    try:
        document = json.loads(payload)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise AssertionError("execution-protocol contract is unreadable") from error
    if not isinstance(document, dict):
        raise AssertionError("execution-protocol contract is not an object")
    if (
        document.get("schema_version") != 1
        or document.get("contract_id") != builder.CONTRACT_ID
        or document.get("document_payload_sha256") != payload_sha256
        or builder.document_payload_sha256(document) != payload_sha256
    ):
        raise AssertionError("execution-protocol contract envelope drifted")
    return document


def _validate_authorization(document: Mapping[str, Any]) -> None:
    authorization = document.get("authorization", {})
    if authorization.get("newly_closed_gates") != list(
        builder.NEWLY_CLOSED_GATES
    ):
        raise AssertionError("execution-protocol newly closed gates drifted")
    required_true = (
        "migration_global_preflight_evidence_closed",
        "migration_durable_ledger_freeze_design_evidence_closed",
        "operator_core_evidence_closed",
        "bounded_40001_40P01_retry_implemented",
        "operator_migration_implementation",
        "migration_execution_protocol_implemented",
        "cryptographic_evidence_verifier_implemented",
        "local_test_backup_restore_execution_rehearsal_closed",
    )
    required_false = (
        "migration_design_closed",
        "production_durable_ledger_or_tombstone",
        "production_source_write_freeze_evidence_closed",
        "production_target_write_freeze_evidence_closed",
        "production_membership_write_freeze_or_digest_recheck_evidence_closed",
        "production_connection_drain_evidence_closed",
        "production_schema_or_index",
        "flyway_baseline_or_migration",
        "backup_and_rollback_evidence_closed",
        "real_data_migration_execution",
        "production_trust_roots_or_key_rotation_audit",
        "durable_evidence_nonce_journal",
        "operator_runtime_wiring",
        "legacy_runtime_permanently_disabled",
        "route_or_openapi_delta",
        "client_gateway_or_proxy_change",
        "production_cutover",
        "source_successor_external_git_anchor_complete",
        "semantic_successor_external_git_anchor_complete",
        "bootstrap_control_sources_external_git_anchor_complete",
        "current_node_control_sources_external_git_anchor_complete",
    )
    if (
        any(authorization.get(key) is not True for key in required_true)
        or any(authorization.get(key) is not False for key in required_false)
    ):
        raise AssertionError("execution-protocol authorization boundary drifted")


def validate(document: dict[str, Any], root: Path = ROOT) -> None:
    resolved_root = root.resolve(strict=True)
    if document != builder.build_contract(resolved_root):
        raise AssertionError("execution-protocol deterministic contract drifted")
    _validate_authorization(document)
    if document.get("route_state") != builder.ROUTE_STATE:
        raise AssertionError("execution-protocol route state drifted")
    predecessor = document.get("predecessor", {})
    if predecessor != {
        "source": builder.PREDECESSOR_RELATIVE,
        "contract_id": builder.PREDECESSOR_ID,
        "captured_at": builder.PREDECESSOR_CAPTURED_AT,
        "scope": builder.PREDECESSOR_SCOPE,
        "status": builder.PREDECESSOR_STATUS,
        "sha256": builder.PREDECESSOR_SHA256,
        "byte_count": builder.PREDECESSOR_BYTE_COUNT,
        "document_payload_sha256": builder.PREDECESSOR_PAYLOAD_SHA256,
        "fixed_commit_oid": builder.PREDECESSOR_COMMIT,
        "immutable": True,
    }:
        raise AssertionError("execution-protocol predecessor descriptor drifted")

    authority = document.get("source_authority", {})
    fixed_sources = authority.get("fixed_non_control_sources")
    if (
        authority.get("fixed_non_control_source_count")
        != builder.FIXED_NON_CONTROL_SOURCE_COUNT
        or authority.get("implementation_source_count")
        != builder.IMPLEMENTATION_SOURCE_COUNT
        or authority.get("transition_source_count")
        != builder.SOURCE_TRANSITION_COUNT
        or authority.get("control_source_count") != builder.CONTROL_SOURCE_COUNT
        or authority.get("control_sources") != list(builder.CONTROL_SOURCES)
        or authority.get("control_sources_excluded_from_self_authority") is not True
        or authority.get("current_control_sources_external_git_anchor_complete")
        is not False
        or authority.get("fixed_source_allowlist_exact") is not True
        or authority.get("dynamic_source_discovery") is not False
        or authority.get("ordinary_build_and_load_are_gitless") is not True
        or authority.get("live_head_main_or_origin_authority") is not False
        or authority.get("fixed_c2_commit_replay_is_explicit_only") is not True
        or not isinstance(fixed_sources, dict)
        or set(fixed_sources) != set(builder.SOURCE_FILES)
    ):
        raise AssertionError("execution-protocol source authority drifted")
    for relative, (digest, byte_count) in builder.SOURCE_FILES.items():
        if fixed_sources.get(relative) != {
            "source": relative,
            "sha256": digest,
            "byte_count": byte_count,
        }:
            raise AssertionError(
                f"execution-protocol source descriptor drifted: {relative}"
            )

    transitions = document.get("historical_source_successors", {})
    if (
        transitions.get("predecessor_checkpoint") != builder.PREDECESSOR_COMMIT
        or transitions.get("override_count") != builder.SOURCE_TRANSITION_COUNT
        or transitions.get("overrides") != builder.SOURCE_TRANSITIONS
        or transitions.get("accepted_bytes_replayable_only_by_explicit_fixed_commit")
        is not True
        or transitions.get("successor_external_git_anchor_complete") is not False
        or transitions.get("unknown_path") != "reject"
    ):
        raise AssertionError("execution-protocol source transitions drifted")

    runtime = document.get("production_runtime_successor", {})
    if (
        runtime.get("accepted_file_count")
        != builder.ACCEPTED_PRODUCTION_FILE_COUNT
        or runtime.get("accepted_manifest_sha256")
        != builder.ACCEPTED_PRODUCTION_MANIFEST_SHA256
        or runtime.get("current_file_count")
        != builder.CURRENT_PRODUCTION_FILE_COUNT
        or runtime.get("current_manifest_sha256")
        != builder.CURRENT_PRODUCTION_MANIFEST_SHA256
        or runtime.get("added_files")
        != dict(sorted(builder.PRODUCTION_RUNTIME_ADDITIONS.items()))
        or runtime.get("changed_files") != {}
        or runtime.get("deleted_files") != []
        or runtime.get("exact_delta") != "4A0M0D"
    ):
        raise AssertionError("execution-protocol runtime successor drifted")
    main = runtime.get("learning_personalbank_main", {})
    if (
        main.get("accepted_file_count")
        != builder.ACCEPTED_LEARNING_PERSONALBANK_MAIN_FILE_COUNT
        or main.get("accepted_manifest_sha256")
        != builder.ACCEPTED_LEARNING_PERSONALBANK_MAIN_MANIFEST_SHA256
        or main.get("current_file_count")
        != builder.CURRENT_LEARNING_PERSONALBANK_MAIN_FILE_COUNT
        or main.get("current_manifest_sha256")
        != builder.CURRENT_LEARNING_PERSONALBANK_MAIN_MANIFEST_SHA256
        or main.get("exact_delta") != "4A0M0D"
    ):
        raise AssertionError("execution-protocol learning runtime drifted")

    worm = document.get("worm_successor", {})
    if (
        worm.get("accepted_report", {}).get("source")
        != builder.WORM_PREDECESSOR_RELATIVE
        or worm.get("accepted_report", {}).get("sha256")
        != builder.WORM_PREDECESSOR_SHA256
        or worm.get("accepted_build_context_sha256")
        != builder.ACCEPTED_BUILD_CONTEXT_SHA256
        or worm.get("accepted_chain_node_count") != 8
        or worm.get("current_report", {}).get("source")
        != builder.WORM_RELATIVE
        or worm.get("current_report", {}).get("sha256") != builder.WORM_SHA256
        or worm.get("current_report", {}).get("byte_count")
        != builder.WORM_BYTE_COUNT
        or worm.get("current_build_context_sha256")
        != builder.CURRENT_BUILD_CONTEXT_SHA256
        or worm.get("dockerfile_sha256") != builder.DOCKERFILE_SHA256
        or worm.get("current_chain_node_count") != 9
        or worm.get("appended_node_count") != 1
        or worm.get("historical_nodes_rewritten") is not False
    ):
        raise AssertionError("execution-protocol WORM successor drifted")


def _load_uncached(root: Path) -> dict[str, Any]:
    resolved_root = root.resolve(strict=True)
    document = _load_contract_envelope(resolved_root)
    try:
        validate(document, resolved_root)
        return document
    except AssertionError as predecessor_error:
        successor = _load_transaction_write_successor()
        loader = getattr(successor, "load_node_d_predecessor", None)
        if not callable(loader):
            raise AssertionError(
                "execution-protocol transaction-write predecessor API is absent"
            ) from predecessor_error
        try:
            successor_document = loader(resolved_root)
        except AssertionError as successor_error:
            raise AssertionError(
                "execution-protocol current source bytes or successor authority drifted"
            ) from successor_error
        if successor_document != document:
            raise AssertionError(
                "execution-protocol successor returned a different predecessor"
            ) from predecessor_error
        return document


def load(root: Path = ROOT) -> dict[str, Any]:
    resolved_root = root.resolve(strict=True)
    return validation_session_cached(
        "phase4c-tag-migration-execution-protocol",
        resolved_root,
        lambda: _load_uncached(resolved_root),
    )


def source_transition_from_validated_document(
    root: Path,
    relative: str,
    document: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Resolve one transition from a document already returned by ``load``.

    This deliberately does not cache across top-level acceptance calls.  It
    only lets a predecessor validate Node D once and then check every fixed
    transition against that same validated document.
    """
    transition = builder.SOURCE_TRANSITIONS.get(relative)
    if transition is None:
        return None
    resolved_root = root.resolve(strict=True)
    actual = document["historical_source_successors"]["overrides"].get(relative)
    if actual != transition:
        raise AssertionError(
            f"execution-protocol transition contract drifted: {relative}"
        )
    payload = builder.fixed_regular_file(resolved_root, relative).read_bytes()
    if (
        len(payload) != transition["successor_byte_count"]
        or builder.sha256_bytes(payload) != transition["successor_sha256"]
    ):
        successor = _load_transaction_write_successor()
        transition_from_node_d = getattr(
            successor, "transition_from_node_d", None
        )
        if not callable(transition_from_node_d):
            raise AssertionError(
                "execution-protocol transaction-write transition API is absent"
            )
        try:
            current = transition_from_node_d(
                resolved_root,
                relative,
                str(transition["successor_sha256"]),
                int(transition["successor_byte_count"]),
            )
        except AssertionError as error:
            raise AssertionError(
                f"execution-protocol transition bytes drifted: {relative}"
            ) from error
        physical_sha256 = builder.sha256_bytes(payload)
        if current != {
            "source": relative,
            "accepted_sha256": transition["successor_sha256"],
            "accepted_byte_count": transition["successor_byte_count"],
            "successor_sha256": physical_sha256,
            "successor_byte_count": len(payload),
        }:
            raise AssertionError(
                f"execution-protocol transaction-write transition drifted: {relative}"
            )
        return {
            "source": relative,
            "accepted_sha256": transition["accepted_sha256"],
            "accepted_byte_count": transition["accepted_byte_count"],
            "successor_sha256": physical_sha256,
            "successor_byte_count": len(payload),
        }
    return dict(transition)


def source_transition(root: Path, relative: str) -> dict[str, Any] | None:
    if relative not in builder.SOURCE_TRANSITIONS:
        return None
    resolved_root = root.resolve(strict=True)
    document = load(resolved_root)
    return source_transition_from_validated_document(
        resolved_root,
        relative,
        document,
    )


def accepted_sha256(relative: str) -> str | None:
    transition = builder.SOURCE_TRANSITIONS.get(relative)
    return None if transition is None else str(transition["accepted_sha256"])


def successor_sha256(root: Path, relative: str) -> str | None:
    transition = source_transition(root, relative)
    return None if transition is None else str(transition["successor_sha256"])


def successor_paths() -> tuple[str, ...]:
    return tuple(builder.SOURCE_TRANSITION_PATHS)


def _runtime_view(
    root: Path,
    view: str,
) -> tuple[dict[str, str], dict[str, str], dict[str, Any]]:
    accepted, current = builder.production_runtime_manifests(root)
    document = load(root)
    runtime = document["production_runtime_successor"]
    if view == "full_runtime":
        return accepted, current, runtime
    if view == "learning_personalbank_main":
        return (
            builder._learning_personalbank_main(accepted),
            builder._learning_personalbank_main(current),
            runtime["learning_personalbank_main"],
        )
    raise AssertionError(f"execution-protocol unknown production view: {view}")


def validate_production_runtime_successor(
    root: Path,
    accepted_files: Mapping[str, str],
    current_files: Mapping[str, str],
    *,
    view: str = "full_runtime",
) -> ProductionRuntimeSuccessor:
    resolved_root = root.resolve(strict=True)
    expected_accepted, expected_current, semantic = _runtime_view(
        resolved_root, view
    )
    accepted = dict(sorted(accepted_files.items()))
    current = dict(sorted(current_files.items()))
    if (
        accepted != expected_accepted
        or len(accepted) != semantic["accepted_file_count"]
        or builder.sha256_json(accepted)
        != semantic["accepted_manifest_sha256"]
    ):
        raise AssertionError("execution-protocol rejected accepted runtime")
    if (
        current != expected_current
        or len(current) != semantic["current_file_count"]
        or builder.sha256_json(current) != semantic["current_manifest_sha256"]
    ):
        raise AssertionError("execution-protocol rejected current runtime")
    return ProductionRuntimeSuccessor(
        view=view,
        accepted_file_count=int(semantic["accepted_file_count"]),
        accepted_manifest_sha256=str(semantic["accepted_manifest_sha256"]),
        current_file_count=int(semantic["current_file_count"]),
        current_manifest_sha256=str(semantic["current_manifest_sha256"]),
        added_files=tuple(sorted(semantic["added_files"].items())),
        changed_files=tuple(sorted(semantic["changed_files"].items())),
        deleted_files=tuple(sorted(semantic["deleted_files"])),
    )


def validate_worm_successor(
    root: Path,
    accepted_report_sha256: str,
    accepted_build_context_sha256: str,
) -> WormSuccessor:
    resolved_root = root.resolve(strict=True)
    document = load(resolved_root)
    worm = document["worm_successor"]
    if (
        accepted_report_sha256 != builder.WORM_PREDECESSOR_SHA256
        or accepted_build_context_sha256
        != builder.ACCEPTED_BUILD_CONTEXT_SHA256
        or worm["accepted_chain_node_count"] != 8
    ):
        raise AssertionError("execution-protocol rejected WORM predecessor")
    script = builder.fixed_regular_file(
        resolved_root, BUILD_CONTEXT_SCRIPT_RELATIVE
    )
    completed = subprocess.run(
        ("/bin/sh", str(script)),
        cwd=resolved_root,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    physical = completed.stdout.strip()
    if (
        completed.returncode != 0
        or physical != builder.CURRENT_BUILD_CONTEXT_SHA256
        or physical != worm["current_build_context_sha256"]
    ):
        raise AssertionError(
            "execution-protocol physical build-context successor drifted"
        )
    return WormSuccessor(
        accepted_report_sha256=accepted_report_sha256,
        accepted_build_context_sha256=accepted_build_context_sha256,
        accepted_chain_node_count=int(worm["accepted_chain_node_count"]),
        current_report_sha256=str(worm["current_report"]["sha256"]),
        current_build_context_sha256=physical,
        current_chain_node_count=int(worm["current_chain_node_count"]),
    )


def minimal_fixture_paths() -> tuple[str, ...]:
    transaction_successor = _load_transaction_write_successor()
    successor_fixture_paths = getattr(
        transaction_successor, "minimal_fixture_paths", None
    )
    if not callable(successor_fixture_paths):
        raise AssertionError(
            "execution-protocol transaction-write fixture API is absent"
        )
    node_c_runtime_paths = (
        *builder.node_c.PRODUCTION_RUNTIME_ADDITIONS,
        *builder.node_c.PRODUCTION_RUNTIME_CHANGES,
    )
    return tuple(
        dict.fromkeys(
            (
                CONTRACT_RELATIVE,
                builder.PREDECESSOR_RELATIVE,
                builder.WORM_PREDECESSOR_RELATIVE,
                builder.node_c.GLOBAL_PREFLIGHT_CONTRACT_RELATIVE,
                builder.node_c.HISTORICAL_RUNTIME_CONTRACT_RELATIVE,
                BUILD_CONTEXT_SCRIPT_RELATIVE,
                *node_c_runtime_paths,
                *builder.SOURCE_FILES,
                *successor_fixture_paths(),
            )
        )
    )


def contract_envelope(root: Path = ROOT) -> dict[str, Any]:
    """Mechanically derive final constants after the main lane writes JSON."""
    payload = builder.fixed_regular_file(
        root.resolve(strict=True), CONTRACT_RELATIVE
    ).read_bytes()
    document = json.loads(payload)
    if document != builder.build_contract(root.resolve(strict=True)):
        raise AssertionError("execution-protocol final contract is not deterministic")
    return {
        "contract_sha256": builder.sha256_bytes(payload),
        "contract_payload_sha256": builder.document_payload_sha256(document),
        "contract_byte_count": len(payload),
    }


def main() -> None:
    accepted = load()
    print(
        json.dumps(
            {
                "accepted": True,
                "migration_execution_protocol_implemented": accepted[
                    "authorization"
                ]["migration_execution_protocol_implemented"],
                "production_cutover": accepted["authorization"][
                    "production_cutover"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
