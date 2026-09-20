#!/usr/bin/env python3
"""Fail-closed acceptance for the transaction-write source successor."""

from __future__ import annotations

from dataclasses import dataclass
import importlib
import json
from pathlib import Path
import subprocess
from typing import Any, Mapping

try:
    from tools import build_phase4c_learning_transaction_write_http_source_successor_contract as builder
except ModuleNotFoundError as error:
    if error.name not in {
        "tools",
        "tools.build_phase4c_learning_transaction_write_http_source_successor_contract",
    }:
        raise
    import build_phase4c_learning_transaction_write_http_source_successor_contract as builder


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_RELATIVE = builder.OUTPUT_RELATIVE
CONTRACT_SHA256 = "0c1a46eea25404167cd740f679029c87ec224e7643159eb757dff782c5fc2f5d"
CONTRACT_PAYLOAD_SHA256 = (
    "890f2b90c10fcf55f30f426e287b69016af766b17c3c4c9cc86a9f84660bb6af"
)
CONTRACT_BYTE_COUNT = 19_381
NODE_D_SUCCESSOR_MODULE = (
    "tools.phase4c_tag_migration_execution_protocol_successor_acceptance"
)
NODE_D_SUCCESSOR_DIRECT_MODULE = (
    "phase4c_tag_migration_execution_protocol_successor_acceptance"
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


def _read_contract(root: Path) -> dict[str, Any]:
    payload = builder.fixed_regular_file(root, CONTRACT_RELATIVE).read_bytes()
    if (
        CONTRACT_BYTE_COUNT < 0
        or len(payload) != CONTRACT_BYTE_COUNT
        or builder.sha256_bytes(payload) != CONTRACT_SHA256
    ):
        raise AssertionError(
            "transaction-write source successor physical bytes drifted"
        )
    try:
        document = json.loads(payload)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise AssertionError(
            "transaction-write source successor is unreadable"
        ) from error
    if not isinstance(document, dict):
        raise AssertionError(
            "transaction-write source successor is not an object"
        )
    if (
        document.get("schema_version") != 1
        or document.get("contract_id") != builder.CONTRACT_ID
        or document.get("document_payload_sha256") != CONTRACT_PAYLOAD_SHA256
        or builder.payload_sha256(document) != CONTRACT_PAYLOAD_SHA256
    ):
        raise AssertionError(
            "transaction-write source successor envelope drifted"
        )
    return document


def _validate_source_bridge(
    document: dict[str, Any], root: Path
) -> None:
    resolved_root = root.resolve(strict=True)
    if set(document) != {
        "schema_version",
        "contract_id",
        "captured_at",
        "scope",
        "status",
        "predecessor",
        "bootstrap_external_anchor",
        "source_successors",
        "semantic_successors",
        "authorization",
        "route_state",
        "source_authority",
        "document_payload_sha256",
    }:
        raise AssertionError(
            "transaction-write source successor shape drifted"
        )
    if (
        document.get("status") != builder.STATUS
        or document.get("predecessor")
        != {**builder.PREDECESSOR, "immutable": True}
    ):
        raise AssertionError(
            "transaction-write source successor predecessor drifted"
        )
    predecessor_payload = builder.fixed_regular_file(
        resolved_root, builder.PREDECESSOR["source"]
    ).read_bytes()
    if (
        len(predecessor_payload) != builder.PREDECESSOR["byte_count"]
        or builder.sha256_bytes(predecessor_payload)
        != builder.PREDECESSOR["sha256"]
    ):
        raise AssertionError(
            "transaction-write source fixed predecessor drifted"
        )
    predecessor_document = json.loads(predecessor_payload)
    if (
        predecessor_document.get("contract_id")
        != builder.PREDECESSOR["contract_id"]
        or predecessor_document.get("document_payload_sha256")
        != builder.PREDECESSOR["document_payload_sha256"]
        or builder.predecessor.payload_sha256(predecessor_document)
        != builder.PREDECESSOR["document_payload_sha256"]
    ):
        raise AssertionError(
            "transaction-write source predecessor payload drifted"
        )

    expected_anchor = {
        "fixed_checkpoint": builder.BOOTSTRAP_CHECKPOINT,
        "anchored_control_source_count": len(
            builder.BOOTSTRAP_CONTROL_SOURCES
        ),
        "anchored_control_sources": {
            relative: {"source": relative, **descriptor}
            for relative, descriptor
            in builder.BOOTSTRAP_CONTROL_SOURCES.items()
        },
        "predecessor_control_sources_external_git_anchor_complete": True,
        "live_ref_authority": False,
    }
    if document.get("bootstrap_external_anchor") != expected_anchor:
        raise AssertionError(
            "transaction-write source bootstrap anchor drifted"
        )

    expected_transitions = {
        relative: {"source": relative, **transition}
        for relative, transition
        in builder.predecessor.SOURCE_TRANSITIONS.items()
    }
    if document.get("source_successors") != {
        "accepted_checkpoint": builder.predecessor.BASE_CHECKPOINT[
            "commit_oid"
        ],
        "successor_checkpoint": builder.predecessor.IMPLEMENTATION_CHECKPOINT[
            "commit_oid"
        ],
        "transition_count": len(expected_transitions),
        "transitions": expected_transitions,
        "dynamic_source_discovery": False,
        "unknown_path": "reject",
    }:
        raise AssertionError(
            "transaction-write source transition authority drifted"
        )
    for relative, transition in (
        builder.predecessor.SOURCE_TRANSITIONS.items()
    ):
        payload = builder.fixed_regular_file(
            resolved_root, relative
        ).read_bytes()
        if (
            len(payload) != transition["successor_byte_count"]
            or builder.sha256_bytes(payload)
            != transition["successor_sha256"]
        ) and not builder.integration.accepts(resolved_root, relative, transition["successor_sha256"], transition["successor_byte_count"]):
            raise AssertionError(
                f"transaction-write source transition drifted: {relative}"
            )

    if document.get("semantic_successors") != {
        "full_runtime": builder.FULL_RUNTIME,
        "learning_personalbank_main": builder.LEARNING_PERSONALBANK_MAIN,
        "java_build_context_and_worm": builder.WORM,
    }:
        raise AssertionError(
            "transaction-write source semantic descriptor drifted"
        )
    if document.get("authorization") != {
        "predecessor_control_sources_external_git_anchor_complete": True,
        "current_bridge_control_sources_external_git_anchor_complete": False,
        "full_target_parity_closed": True,
        "route_migration_eligible": False,
        "nine_transaction_write_operations_migrated": False,
        "route_delta": False,
        "production_cutover": False,
        "production_schema_execution": False,
        "real_data_migration_execution": False,
        "next_gate": "post_push_external_anchor_of_current_bridge_controls",
    }:
        raise AssertionError(
            "transaction-write source authorization drifted"
        )
    if document.get("route_state") != {
        "total_operation_count": 611,
        "migrated_operation_count": 13,
        "pending_operation_count": 598,
        "production_cutover_operation_count": 0,
        "implemented_pending_operation_count": 9,
    }:
        raise AssertionError("transaction-write source route state drifted")
    if document.get("source_authority") != {
        "control_source_count": len(builder.CONTROL_SOURCES),
        "control_sources": list(builder.CONTROL_SOURCES),
        "control_sources_excluded_from_self_authority": True,
        "ordinary_build_is_gitless": True,
        "fixed_checkpoint_replay_is_explicit_only": True,
        "live_head_main_or_origin_authority": False,
        "historical_contracts_or_worm_overwritten": False,
    }:
        raise AssertionError(
            "transaction-write source authority drifted"
        )


def validate(document: dict[str, Any], root: Path = ROOT) -> None:
    resolved_root = root.resolve(strict=True)
    _validate_source_bridge(document, resolved_root)
    if document != builder.build_contract(resolved_root):
        raise AssertionError(
            "transaction-write source successor deterministic rebuild drifted"
        )
    if (
        document.get("status") != builder.STATUS
        or document.get("predecessor")
        != {**builder.PREDECESSOR, "immutable": True}
    ):
        raise AssertionError(
            "transaction-write source successor predecessor drifted"
        )
    anchor = document.get("bootstrap_external_anchor", {})
    if (
        anchor.get("fixed_checkpoint") != builder.BOOTSTRAP_CHECKPOINT
        or anchor.get("anchored_control_source_count")
        != len(builder.BOOTSTRAP_CONTROL_SOURCES)
        or anchor.get(
            "predecessor_control_sources_external_git_anchor_complete"
        )
        is not True
        or anchor.get("live_ref_authority") is not False
    ):
        raise AssertionError(
            "transaction-write source bootstrap anchor drifted"
        )
    sources = document.get("source_successors", {})
    if (
        sources.get("transition_count")
        != len(builder.predecessor.SOURCE_TRANSITIONS)
        or sources.get("dynamic_source_discovery") is not False
        or sources.get("unknown_path") != "reject"
    ):
        raise AssertionError(
            "transaction-write source transition authority drifted"
        )
    semantic = document.get("semantic_successors", {})
    if (
        semantic.get("full_runtime") != builder.FULL_RUNTIME
        or semantic.get("learning_personalbank_main")
        != builder.LEARNING_PERSONALBANK_MAIN
        or semantic.get("java_build_context_and_worm") != builder.WORM
    ):
        raise AssertionError(
            "transaction-write source semantic successor drifted"
        )
    authorization = document.get("authorization", {})
    if (
        authorization.get(
            "predecessor_control_sources_external_git_anchor_complete"
        )
        is not True
        or authorization.get(
            "current_bridge_control_sources_external_git_anchor_complete"
        )
        is not False
        or authorization.get("full_target_parity_closed") is not True
        or authorization.get("route_migration_eligible") is not False
        or authorization.get("nine_transaction_write_operations_migrated")
        is not False
        or authorization.get("route_delta") is not False
        or authorization.get("production_cutover") is not False
    ):
        raise AssertionError(
            "transaction-write source authorization drifted"
        )
    if document.get("route_state") != {
        "total_operation_count": 611,
        "migrated_operation_count": 13,
        "pending_operation_count": 598,
        "production_cutover_operation_count": 0,
        "implemented_pending_operation_count": 9,
    }:
        raise AssertionError("transaction-write source route state drifted")
    authority = document.get("source_authority", {})
    if (
        authority.get("control_source_count") != len(builder.CONTROL_SOURCES)
        or authority.get("control_sources") != list(builder.CONTROL_SOURCES)
        or authority.get("control_sources_excluded_from_self_authority")
        is not True
        or authority.get("ordinary_build_is_gitless") is not True
        or authority.get("live_head_main_or_origin_authority") is not False
        or authority.get("historical_contracts_or_worm_overwritten") is not False
    ):
        raise AssertionError(
            "transaction-write source authority drifted"
        )


def _load_uncached(root: Path) -> dict[str, Any]:
    resolved_root = root.resolve(strict=True)
    document = _read_contract(resolved_root)
    validate(document, resolved_root)
    return document


def _load_node_d_successor() -> object:
    try:
        return importlib.import_module(NODE_D_SUCCESSOR_MODULE)
    except ModuleNotFoundError as error:
        if error.name not in {"tools", NODE_D_SUCCESSOR_MODULE}:
            raise
    try:
        return importlib.import_module(NODE_D_SUCCESSOR_DIRECT_MODULE)
    except ModuleNotFoundError as error:
        if error.name != NODE_D_SUCCESSOR_DIRECT_MODULE:
            raise
        raise AssertionError(
            "transaction-write source Node D successor is required"
        ) from error


def load(root: Path = ROOT) -> dict[str, Any]:
    resolved_root = root.resolve(strict=True)
    node_d_successor = _load_node_d_successor()
    session_cached = getattr(
        node_d_successor, "validation_session_cached", None
    )
    if not callable(session_cached):
        return _load_uncached(resolved_root)
    return session_cached(
        "phase4c-learning-transaction-write-http-source-successor",
        resolved_root,
        lambda: _load_uncached(resolved_root),
    )


def load_source_bridge(root: Path = ROOT) -> dict[str, Any]:
    resolved_root = root.resolve(strict=True)
    node_d_successor = _load_node_d_successor()
    session_cached = getattr(
        node_d_successor, "validation_session_cached", None
    )

    def factory() -> dict[str, Any]:
        document = _read_contract(resolved_root)
        _validate_source_bridge(document, resolved_root)
        return document

    if not callable(session_cached):
        return factory()
    return session_cached(
        "phase4c-learning-transaction-write-http-source-bridge",
        resolved_root,
        factory,
    )


def load_node_d_predecessor(root: Path = ROOT) -> dict[str, Any]:
    resolved_root = root.resolve(strict=True)
    load(resolved_root)
    path = builder.fixed_regular_file(
        resolved_root, builder.node_d.OUTPUT_RELATIVE
    )
    payload = path.read_bytes()
    if (
        len(payload) != 44_336
        or builder.sha256_bytes(payload)
        != "e236b3cde251026c3a189762b650eb4df80213dcdab667a5b8f50eb20a0e8e14"
    ):
        raise AssertionError(
            "transaction-write source Node D predecessor drifted"
        )
    document = json.loads(payload)
    if document.get("contract_id") != builder.node_d.CONTRACT_ID:
        raise AssertionError(
            "transaction-write source Node D identity drifted"
        )
    return document


def source_transition(
    root: Path, relative: str
) -> dict[str, Any] | None:
    transition = builder.predecessor.SOURCE_TRANSITIONS.get(relative)
    if transition is None:
        return None
    document = load_source_bridge(root)
    expected = {"source": relative, **transition}
    if document["source_successors"]["transitions"].get(relative) != expected:
        raise AssertionError(
            f"transaction-write source transition drifted: {relative}"
        )
    payload = builder.fixed_regular_file(root, relative).read_bytes()
    if (
        len(payload) != transition["successor_byte_count"]
        or builder.sha256_bytes(payload) != transition["successor_sha256"]
    ):
        if not builder.integration.accepts(root, relative, transition["successor_sha256"], transition["successor_byte_count"]):
            raise AssertionError(
                f"transaction-write source transition bytes drifted: {relative}"
            )
        expected = {**expected, "successor_sha256": builder.sha256_bytes(payload), "successor_byte_count": len(payload)}
    return expected


def transition_from_node_d(
    root: Path,
    relative: str,
    accepted_sha256: str,
    accepted_byte_count: int,
) -> dict[str, Any] | None:
    """Compose one fixed Node D source into this bootstrap.

    Ordinary sources must resolve through the externally anchored full-parity
    predecessor.  Only the explicit current control-source allowlist may end
    at the physical bootstrap bytes; those bytes remain self-excluded and do
    not authorize route migration until a later Git anchor fixes them.
    """
    node_d_source = builder.node_d.SOURCE_FILES.get(relative)
    if node_d_source is None:
        return None
    if node_d_source != (accepted_sha256, accepted_byte_count):
        raise AssertionError(
            f"transaction-write source Node D origin drifted: {relative}"
        )

    resolved_root = root.resolve(strict=True)
    load_source_bridge(resolved_root)
    predecessor_transition = builder.predecessor.SOURCE_TRANSITIONS.get(
        relative
    )
    if predecessor_transition is not None:
        transition = source_transition(resolved_root, relative)
        if transition is None:
            raise AssertionError(
                f"transaction-write source predecessor transition absent: {relative}"
            )
        return transition

    payload = builder.fixed_regular_file(resolved_root, relative).read_bytes()
    physical_sha256 = builder.sha256_bytes(payload)
    if relative not in builder.CONTROL_SOURCES and (
        len(payload) != accepted_byte_count
        or physical_sha256 != accepted_sha256
    ):
        raise AssertionError(
            f"transaction-write source unreviewed Node D drift: {relative}"
        )
    return {
        "source": relative,
        "accepted_sha256": accepted_sha256,
        "accepted_byte_count": accepted_byte_count,
        "successor_sha256": physical_sha256,
        "successor_byte_count": len(payload),
    }


def accepted_sha256(relative: str) -> str | None:
    transition = builder.predecessor.SOURCE_TRANSITIONS.get(relative)
    return None if transition is None else str(transition["accepted_sha256"])


def anchored_bootstrap_sha256(relative: str) -> str | None:
    descriptor = builder.BOOTSTRAP_CONTROL_SOURCES.get(relative)
    return None if descriptor is None else str(descriptor["sha256"])


def is_current_control_source(relative: str) -> bool:
    return relative in builder.CONTROL_SOURCES


def successor_sha256(root: Path, relative: str) -> str | None:
    transition = source_transition(root, relative)
    return None if transition is None else str(transition["successor_sha256"])


def _expected_runtime(
    root: Path, view: str
) -> tuple[dict[str, str], dict[str, str], dict[str, Any]]:
    _, node_d_current = builder.node_d.production_runtime_manifests(root)
    actual = builder.production_runtime_manifest(root)
    if view == "full_runtime":
        return node_d_current, actual, builder.FULL_RUNTIME
    if view == "learning_personalbank_main":
        return (
            builder.learning_personalbank_main(node_d_current),
            builder.learning_personalbank_main(actual),
            builder.LEARNING_PERSONALBANK_MAIN,
        )
    raise AssertionError(
        f"transaction-write source unknown production view: {view}"
    )


def validate_production_runtime_successor(
    root: Path,
    accepted_files: Mapping[str, str],
    current_files: Mapping[str, str],
    *,
    view: str = "full_runtime",
) -> ProductionRuntimeSuccessor:
    resolved_root = root.resolve(strict=True)
    load(resolved_root)
    expected_accepted, expected_current, semantic = _expected_runtime(
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
        raise AssertionError(
            "transaction-write source rejected accepted production manifest"
        )
    if (
        current != expected_current
        or len(current) != semantic["current_file_count"]
        or builder.sha256_json(current) != semantic["current_manifest_sha256"]
    ):
        raise AssertionError(
            "transaction-write source rejected current production manifest"
        )
    added = {path: digest for path, digest in current.items() if path not in accepted}
    changed = {
        path: digest
        for path, digest in current.items()
        if path in accepted and accepted[path] != digest
    }
    deleted = tuple(sorted(set(accepted) - set(current)))
    if (
        len(added) != semantic["added_file_count"]
        or len(changed) != semantic["changed_file_count"]
        or len(deleted) != semantic["deleted_file_count"]
    ):
        raise AssertionError(
            "transaction-write source production delta drifted"
        )
    return ProductionRuntimeSuccessor(
        view=view,
        accepted_file_count=len(accepted),
        accepted_manifest_sha256=builder.sha256_json(accepted),
        current_file_count=len(current),
        current_manifest_sha256=builder.sha256_json(current),
        added_files=tuple(sorted(added.items())),
        changed_files=tuple(sorted(changed.items())),
        deleted_files=deleted,
    )


def _physical_build_context(root: Path) -> str:
    script = builder.fixed_regular_file(
        root, "infra/phase2/hash-java-build-context.sh"
    )
    completed = subprocess.run(
        ["/bin/sh", str(script)],
        cwd=root,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.returncode != 0:
        raise AssertionError(
            "transaction-write source build-context hasher failed"
        )
    return completed.stdout.strip()


def validate_current_build_context(
    root: Path, physical_build_context_sha256: str | None = None
) -> str:
    resolved_root = root.resolve(strict=True)
    load(resolved_root)
    physical = (
        _physical_build_context(resolved_root)
        if physical_build_context_sha256 is None
        else physical_build_context_sha256
    )
    if physical != builder.WORM["current_build_context_sha256"]:
        raise AssertionError(
            "transaction-write source current build context drifted"
        )
    return physical


def validate_worm_successor(
    root: Path,
    accepted_report_sha256: str,
    accepted_build_context_sha256: str,
) -> WormSuccessor:
    resolved_root = root.resolve(strict=True)
    load(resolved_root)
    if (
        accepted_report_sha256 != builder.WORM["accepted_report_sha256"]
        or accepted_build_context_sha256
        != builder.WORM["accepted_build_context_sha256"]
    ):
        raise AssertionError(
            "transaction-write source rejected WORM predecessor"
        )
    physical = validate_current_build_context(resolved_root)
    return WormSuccessor(
        accepted_report_sha256=accepted_report_sha256,
        accepted_build_context_sha256=accepted_build_context_sha256,
        accepted_chain_node_count=int(
            builder.WORM["accepted_chain_node_count"]
        ),
        current_report_sha256=str(builder.WORM["current_report_sha256"]),
        current_build_context_sha256=physical,
        current_chain_node_count=int(builder.WORM["current_chain_node_count"]),
    )


def minimal_fixture_paths() -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            (
                CONTRACT_RELATIVE,
                builder.PREDECESSOR["source"],
                builder.WORM["accepted_report_source"],
                builder.WORM["current_report_source"],
                "infra/phase2/hash-java-build-context.sh",
                *builder.predecessor.SOURCE_TRANSITIONS,
                *builder.production_runtime_manifest(ROOT),
            )
        )
    )


def main() -> None:
    document = load()
    print(
        json.dumps(
            {
                "accepted": True,
                "contract_id": document["contract_id"],
                "full_target_parity_closed": document["authorization"][
                    "full_target_parity_closed"
                ],
                "route_migration_eligible": document["authorization"][
                    "route_migration_eligible"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
