#!/usr/bin/env python3
"""Build the append-only Phase 4C user-counts route-promotion successor."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EFFECTIVE_RELATIVE = "docs/refactor/phase4c/effective-route-parity-successor-status.json"
OUTPUT_RELATIVE = "docs/refactor/phase4c/personal-bank-user-counts-route-promotion-contract.json"
CONTRACT_ID = "ti.phase4c.personal-bank-user-counts-route-promotion-contract"
CAPTURED_AT = "2026-07-18T22:05:00+08:00"

SOURCES = {
    "baseline": {
        "source": "docs/refactor/02-route-parity-matrix.csv",
        "sha256": "fdbdfedf3dd70cd09778b2a7072711d103eee8461d0e7dd356d797006fc92c74",
        "byte_count": 416_225,
    },
    "predecessor_effective": {
        "source": "docs/refactor/phase4a/effective-route-parity-status.json",
        "sha256": "1c4645354be4d4a778ec7d68d2957130718e826648e420dd3d1fec7bea5339d4",
        "byte_count": 4_048,
    },
    "phase4c_pending_delta": {
        "source": "docs/refactor/phase4c/route-parity-delta.csv",
        "sha256": "40ead5f703f1a589989fd524107f1fc31994662fb7d3e3be54fe22705025b52b",
        "byte_count": 2_230,
    },
    "successor_delta": {
        "source": "docs/refactor/phase4c/route-parity-successor-delta.csv",
        "sha256": "eef46dc120be7aff600f7f767120673451d21fa42389a777f24e7b4e4f011d07",
        "byte_count": 836,
    },
    "eligibility_anchor": {
        "source": (
            "docs/refactor/phase4c/"
            "personal-bank-user-counts-http-full-parity-anchor-contract.json"
        ),
        "sha256": "77c15295db2addf223ac425dfbbde687c4be3685fd6c6a9b842db7a238b58836",
        "document_payload_sha256": (
            "eb76c6bf825b4efe0ad6d1ed0a1d2fa02eb1025226c9168c6fe42108dc4ff816"
        ),
        "byte_count": 14_885,
    },
}

EFFECTIVE_SHA256 = "c0e96472533d0bbe7d67ac1416a91f3e9a3bfcef8c27e1170b0e9939c46b358a"
EFFECTIVE_PAYLOAD_SHA256 = "3788d541c027ba7f9c397afee1d006ea92da300845557ca35bdd513b920a0637"
EFFECTIVE_BYTE_COUNT = 5_340

ROUTES = (
    {
        "route_id": "6858f6fa506f",
        "path": "/api/user/banks/api/<int:bank_id>/user-counts",
        "method": "GET",
        "target_module": "learning",
    },
    {
        "route_id": "006913d0d956",
        "path": "/user/banks/api/<int:bank_id>/user-counts",
        "method": "GET",
        "target_module": "learning",
    },
)

CONTROL_SOURCES = (
    OUTPUT_RELATIVE,
    "server/src/test/java/io/saksk/ti/architecture/Phase4cHttpRoutePromotionSuccessorAcceptance.java",
    "server/src/test/java/io/saksk/ti/architecture/Phase4cPersonalBankUserCountsRoutePromotionContractParityTest.java",
    "tools/build_phase4c_personal_bank_user_counts_route_promotion_contract.py",
    "tools/phase4c_http_route_promotion_successor_acceptance.py",
    "tools/test_phase4c_personal_bank_user_counts_route_promotion_contract.py",
)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def payload_sha256(document: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json({
        key: value for key, value in document.items()
        if key != "document_payload_sha256"
    }).encode("utf-8"))


def serialized(document: dict[str, Any]) -> bytes:
    return (json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def fixed_regular_file(root: Path, relative: str) -> Path:
    resolved_root = root.resolve(strict=True)
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise AssertionError(f"route promotion path escapes root: {relative}")
    cursor = resolved_root
    for part in candidate.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise AssertionError(f"route promotion path contains symlink: {relative}")
    resolved = (resolved_root / candidate).resolve(strict=True)
    resolved.relative_to(resolved_root)
    if not resolved.is_file():
        raise AssertionError(f"route promotion path is not a regular file: {relative}")
    return resolved


def _validated_bytes(root: Path, descriptor: dict[str, Any]) -> bytes:
    relative = descriptor["source"]
    payload = fixed_regular_file(root, relative).read_bytes()
    if (
        sha256_bytes(payload) != descriptor["sha256"]
        or len(payload) != descriptor["byte_count"]
    ):
        raise AssertionError(f"route promotion fixed bytes drifted: {relative}")
    return payload


def _csv_rows(root: Path, source_name: str) -> list[dict[str, str]]:
    payload = _validated_bytes(root, SOURCES[source_name])
    return list(csv.DictReader(io.StringIO(payload.decode("utf-8"))))


def _validate_route_sources(root: Path) -> tuple[dict[str, Any], list[dict[str, str]]]:
    baseline = _csv_rows(root, "baseline")
    baseline_by_key: dict[tuple[str, str, str], dict[str, str]] = {}
    expanded_count = 0
    for row in baseline:
        methods = [method.strip() for method in row["methods"].split(",") if method.strip()]
        expanded_count += len(methods)
        for method in methods:
            key = (row["route_id"], row["path"], method)
            if key in baseline_by_key:
                raise AssertionError(f"route promotion duplicate baseline key: {key}")
            baseline_by_key[key] = row
    if len(baseline) != 592 or expanded_count != 611:
        raise AssertionError("route promotion baseline counts drifted")

    predecessor = json.loads(_validated_bytes(root, SOURCES["predecessor_effective"]))
    if predecessor.get("effective", {}).get("migration_status") != {
        "pending": 600,
        "migrated": 11,
    }:
        raise AssertionError("route promotion predecessor status drifted")
    if predecessor.get("effective", {}).get("production_cutover_operation_count") != 0:
        raise AssertionError("route promotion predecessor cutover drifted")

    pending_rows = _csv_rows(root, "phase4c_pending_delta")
    successor_rows = _csv_rows(root, "successor_delta")
    if len(pending_rows) != 2 or len(successor_rows) != 2:
        raise AssertionError("route promotion delta row count drifted")
    expected_keys = {(route["route_id"], route["path"], route["method"]) for route in ROUTES}
    pending_keys = {(row["route_id"], row["path"], row["method"]) for row in pending_rows}
    successor_keys = {(row["route_id"], row["path"], row["method"]) for row in successor_rows}
    if pending_keys != expected_keys or successor_keys != expected_keys:
        raise AssertionError("route promotion delta key set drifted")
    if any(key not in baseline_by_key for key in expected_keys):
        raise AssertionError("route promotion delta contains unknown route")
    if any(row["phase4c_migration_status"] != "pending" for row in pending_rows):
        raise AssertionError("route promotion historical pending delta drifted")
    for row in successor_rows:
        if (
            row["previous_phase4c_migration_status"] != "pending"
            or row["successor_migration_status"] != "migrated"
            or row["production_cutover"] != "false"
            or row["target_module"] != "learning"
        ):
            raise AssertionError("route promotion successor row drifted")

    anchor = json.loads(_validated_bytes(root, SOURCES["eligibility_anchor"]))
    if (
        anchor.get("document_payload_sha256")
        != SOURCES["eligibility_anchor"]["document_payload_sha256"]
        or anchor.get("authorization", {}).get("route_migration_eligible") is not True
        or anchor.get("parity", {}).get("full_target_parity_closed") is not True
    ):
        raise AssertionError("route promotion eligibility anchor drifted")
    return predecessor, successor_rows


def build_effective_status(root: Path = ROOT) -> dict[str, Any]:
    predecessor, _ = _validate_route_sources(root)
    migrated = list(predecessor["effective"]["migrated_operations"])
    migrated.extend({
        **route,
        "introduced_in": "4C-user-counts-full-parity-route-successor",
    } for route in ROUTES)
    document: dict[str, Any] = {
        "schema_version": 1,
        "contract_id": "ti.phase4c.effective-route-parity-successor-status",
        "captured_at": CAPTURED_AT,
        "baseline": {
            "source": "../02-route-parity-matrix.csv",
            "sha256": SOURCES["baseline"]["sha256"],
            "rule_count": 592,
            "expanded_operation_count": 611,
            "migration_status": {"pending": 611, "migrated": 0},
        },
        "predecessor": {
            "source": "../phase4a/effective-route-parity-status.json",
            "sha256": SOURCES["predecessor_effective"]["sha256"],
            "migration_status": {"pending": 600, "migrated": 11},
        },
        "deltas": [
            {
                "source": "route-parity-delta.csv",
                "sha256": SOURCES["phase4c_pending_delta"]["sha256"],
                "operation_count": 2,
                "effect": "implemented_pending_no_status_change",
            },
            {
                "source": "route-parity-successor-delta.csv",
                "sha256": SOURCES["successor_delta"]["sha256"],
                "operation_count": 2,
                "effect": "pending_to_migrated",
            },
        ],
        "eligibility": {
            "source": "personal-bank-user-counts-http-full-parity-anchor-contract.json",
            "sha256": SOURCES["eligibility_anchor"]["sha256"],
            "document_payload_sha256": SOURCES["eligibility_anchor"]["document_payload_sha256"],
            "route_migration_eligible": True,
            "full_target_parity_closed": True,
        },
        "materialization_policy": {
            "key": ["route_id", "path", "method"],
            "precedence": (
                "phase4c_route_successor_delta_over_phase4c_pending_delta_"
                "over_phase4a_effective_predecessor"
            ),
            "unknown_delta_key": "reject",
            "duplicate_delta_key_within_layer": "reject",
            "historical_files": "immutable",
        },
        "effective": {
            "rule_count": 592,
            "expanded_operation_count": 611,
            "overridden_operation_count": 13,
            "migration_status": {"pending": 598, "migrated": 13},
            "production_cutover_operation_count": 0,
            "migrated_operations": migrated,
        },
        "scope_note": (
            "migrated records Java route parity only; production cutover remains zero, "
            "the legacy Flask runtime remains owner, and 598 operations remain pending"
        ),
    }
    document["document_payload_sha256"] = payload_sha256(document)
    return document


def build_contract(root: Path = ROOT) -> dict[str, Any]:
    effective = build_effective_status(root)
    effective_payload = fixed_regular_file(root, EFFECTIVE_RELATIVE).read_bytes()
    if (
        len(effective_payload) != EFFECTIVE_BYTE_COUNT
        or sha256_bytes(effective_payload) != EFFECTIVE_SHA256
        or json.loads(effective_payload) != effective
        or effective["document_payload_sha256"] != EFFECTIVE_PAYLOAD_SHA256
    ):
        raise AssertionError("route promotion effective status drifted")
    document: dict[str, Any] = {
        "schema_version": 1,
        "contract_id": CONTRACT_ID,
        "captured_at": CAPTURED_AT,
        "scope": "phase4c-personal-bank-user-counts-route-parity-promotion",
        "status": "two_user_counts_get_routes_migrated_production_cutover_false",
        "predecessor": {**SOURCES["eligibility_anchor"], "immutable": True},
        "route_authority": {
            "sources": SOURCES,
            "effective_status": {
                "source": EFFECTIVE_RELATIVE,
                "sha256": EFFECTIVE_SHA256,
                "document_payload_sha256": EFFECTIVE_PAYLOAD_SHA256,
                "byte_count": EFFECTIVE_BYTE_COUNT,
            },
            "promoted_routes": list(ROUTES),
            "historical_matrix_and_deltas_overwritten": False,
        },
        "parity": {
            "pg16_pg18_termination_fingerprints_complete": True,
            "real_tomcat_complete_response_header_matrix_complete": True,
            "same_service_redis_outage_and_recovery_complete": True,
            "full_target_parity_closed": True,
            "route_migration_eligible": True,
        },
        "authorization": {
            "two_legacy_get_routes_migrated": True,
            "derived_head_and_options_count_as_migrated": False,
            "production_cutover": False,
            "operator_migration_implementation": False,
            "production_schema_or_index": False,
            "real_data_migration_execution": False,
            "client_change": False,
            "gateway_or_proxy_change": False,
        },
        "route_state": {
            "total_operation_count": 611,
            "migrated_operation_count": 13,
            "pending_operation_count": 598,
            "production_cutover_operation_count": 0,
        },
        "source_authority": {
            "control_source_count": len(CONTROL_SOURCES),
            "control_sources": list(CONTROL_SOURCES),
            "excluded_from_self_authority": True,
            "historical_contracts_and_worm_overwritten": False,
        },
    }
    document["document_payload_sha256"] = payload_sha256(document)
    return document


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--effective", action="store_true")
    arguments = parser.parse_args()
    document = build_effective_status() if arguments.effective else build_contract()
    print(serialized(document).decode("utf-8"), end="")


if __name__ == "__main__":
    main()
