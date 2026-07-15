#!/usr/bin/env python3
"""Validate Phase 1 module boundaries, ownership, invariants and cutover protocol.

The validator intentionally uses only the Python standard library so the
architecture contract can be checked before the Java build exists.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable


ROOT_PACKAGE = "io.saksk.ti"
BUSINESS_MODULES = (
    "identity",
    "catalog",
    "personalbank",
    "assessment",
    "learning",
    "community",
    "campus",
    "coding",
    "intelligence",
    "messaging",
    "operations",
)
ADAPTER_BOUNDARIES = ("web",)
ALL_OWNERS = frozenset((*BUSINESS_MODULES, *ADAPTER_BOUNDARIES))

EXPECTED_DEPENDENCIES = {
    "identity": ("sharedkernel",),
    "catalog": ("sharedkernel", "identity"),
    "personalbank": ("sharedkernel", "identity", "catalog"),
    "assessment": ("sharedkernel", "identity", "catalog", "personalbank"),
    "learning": (
        "sharedkernel",
        "identity",
        "catalog",
        "personalbank",
        "assessment",
    ),
    "community": ("sharedkernel", "identity", "catalog"),
    "campus": ("sharedkernel", "identity"),
    "coding": ("sharedkernel", "identity", "catalog"),
    "intelligence": (
        "sharedkernel",
        "identity",
        "catalog",
        "personalbank",
        "coding",
    ),
    "messaging": (
        "sharedkernel",
        "identity",
        "assessment",
        "learning",
        "community",
        "campus",
        "coding",
        "intelligence",
    ),
    "operations": ("sharedkernel",),
    "web": ("sharedkernel", *BUSINESS_MODULES),
}

MESSAGING_EVENT_PROVIDERS = (
    "assessment",
    "learning",
    "community",
    "campus",
    "coding",
    "intelligence",
)

EXPECTED_PUBLIC_EVENT_EDGES = frozenset(
    {("learning", "assessment"), *({("messaging", provider) for provider in MESSAGING_EVENT_PROVIDERS})}
)

REQUIRED_INVARIANTS = (
    "identity.account-lock-immediate-revocation",
    "personalbank.bank-access-matrix",
    "learning.answer-command-idempotency",
    "assessment.single-final-submission",
    "assessment.decimal-score-determinism",
    "campus.refresh-and-snapshot-deduplication",
)

REQUIRED_INVARIANT_TOKENS = {
    "identity.account-lock-immediate-revocation": (
        "session_version",
        "locked",
        "同一本地事务",
    ),
    "personalbank.bank-access-matrix": (
        "status=0",
        "公开题库只允许读取",
        "未知 permission",
    ),
    "learning.answer-command-idempotency": (
        "logicalAttemptId",
        "IDEMPOTENCY_CONFLICT",
        "统计",
    ),
    "assessment.single-final-submission": (
        "pending_review",
        "compare-and-set",
        "重新评分",
    ),
    "assessment.decimal-score-determinism": (
        "BigDecimal",
        "RoundingMode.UNNECESSARY",
        "scale=2",
        "unknown",
    ),
    "campus.refresh-and-snapshot-deduplication": (
        "Redis",
        "userId+refreshId+xnm+xqm",
        "最近成功",
    ),
}

REQUIRED_PROTOCOL_MARKERS = (
    "READ_COMPARE",
    "ISOLATED_WRITE_COMPARE",
    "SELECT_ONLY",
    "NO_DUAL_WRITE",
    "FREEZE",
    "CUTOVER",
    "ROLLBACK_PRE_WRITE",
    "ROLLBACK_POST_WRITE",
)

REQUIRED_OWNERSHIP_COLUMNS = (
    "resource_kind",
    "resource_name",
    "target_owner",
    "persistence_role",
    "constraints_or_pattern",
)

FORBIDDEN_CROSS_MODULE_IMPORTS = (
    "*.domain.*",
    "*.infrastructure.*",
    "*.persistence.*",
    "*.entity.*",
)

COMMON_INVARIANT_FIELDS = (
    "invariant_id",
    "owner_module",
    "title",
    "legacy_evidence",
    "legacy_gap",
    "command_scope",
    "idempotency_key",
    "transaction_boundary",
    "concurrency_rule",
    "rule",
    "success_observation",
    "failure_observation",
    "verification_scenarios",
)


class DuplicateJsonKey(ValueError):
    """Raised when a JSON object contains a repeated key."""


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateJsonKey(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle, object_pairs_hook=_strict_object)


def _error(errors: list[str], message: str) -> None:
    errors.append(message)


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _duplicates(values: Iterable[str]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates


def _walk_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for nested in value.values():
            yield from _walk_strings(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _walk_strings(nested)


def _load_ownership(path: Path, errors: list[str]) -> list[dict[str, str]]:
    try:
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            headers = reader.fieldnames or []
            missing_headers = [
                column for column in REQUIRED_OWNERSHIP_COLUMNS if column not in headers
            ]
            if missing_headers:
                _error(
                    errors,
                    "ownership CSV missing columns: " + ", ".join(missing_headers),
                )
                return []
            return [dict(row) for row in reader]
    except (OSError, csv.Error) as exc:
        _error(errors, f"cannot read ownership CSV {path}: {exc}")
        return []


def _validate_ownership_rows(
    rows: list[dict[str, str]], errors: list[str]
) -> tuple[dict[tuple[str, str], dict[str, str]], int]:
    matrix: dict[tuple[str, str], dict[str, str]] = {}
    table_owner: dict[str, str] = {}

    for number, row in enumerate(rows, start=2):
        kind = (row.get("resource_kind") or "").strip()
        name = (row.get("resource_name") or "").strip()
        owner = (row.get("target_owner") or "").strip()
        role = (row.get("persistence_role") or "").strip()
        if not kind or not name:
            _error(errors, f"ownership CSV row {number} has blank resource key")
            continue
        key = (kind, name)
        if key in matrix:
            _error(errors, f"ownership CSV resource appears more than once: {kind}:{name}")
            continue
        if owner not in ALL_OWNERS:
            _error(errors, f"ownership CSV has unknown owner {owner!r} for {kind}:{name}")
        if not role:
            _error(errors, f"ownership CSV has blank persistence_role for {kind}:{name}")
        matrix[key] = row
        if kind == "table":
            if name in table_owner:
                _error(errors, f"table appears more than once in ownership CSV: {name}")
            table_owner[name] = owner

    cross_owner_foreign_ids = 0
    for row in rows:
        if row.get("resource_kind") != "table":
            continue
        source = row.get("resource_name", "")
        source_owner = row.get("target_owner", "")
        constraints = row.get("constraints_or_pattern", "")
        match = re.search(r"(?:^|;\s*)fk=([^;]+)", constraints)
        if not match:
            continue
        for declaration in match.group(1).split("|"):
            if "->" not in declaration:
                _error(errors, f"cannot parse foreign ID declaration on table {source}: {declaration}")
                continue
            reference = declaration.split("->", 1)[1].strip()
            target_table = reference.split(".", 1)[0]
            if target_table not in table_owner:
                _error(
                    errors,
                    f"foreign ID from {source} references unowned table {target_table}",
                )
                continue
            if table_owner[target_table] != source_owner:
                cross_owner_foreign_ids += 1

    return matrix, cross_owner_foreign_ids


def _find_cycles(graph: dict[str, tuple[str, ...] | list[str]]) -> list[list[str]]:
    state: dict[str, int] = {node: 0 for node in graph}
    stack: list[str] = []
    positions: dict[str, int] = {}
    cycles: list[list[str]] = []

    def visit(node: str) -> None:
        state[node] = 1
        positions[node] = len(stack)
        stack.append(node)
        for dependency in graph.get(node, ()):
            if dependency == "sharedkernel" or dependency not in graph:
                continue
            if state[dependency] == 0:
                visit(dependency)
            elif state[dependency] == 1:
                start = positions[dependency]
                cycles.append([*stack[start:], dependency])
        stack.pop()
        positions.pop(node, None)
        state[node] = 2

    for node in graph:
        if state[node] == 0:
            visit(node)
    return cycles


def _validate_contract(
    contract: Any,
    ownership: dict[tuple[str, str], dict[str, str]],
    cross_owner_foreign_ids: int,
    errors: list[str],
) -> None:
    if not isinstance(contract, dict):
        _error(errors, "module contract root must be an object")
        return

    if contract.get("contract_id") != "ti.phase1.module-boundaries":
        _error(errors, "module contract has unexpected contract_id")
    if contract.get("java_root_package") != ROOT_PACKAGE:
        _error(errors, f"java_root_package must be {ROOT_PACKAGE}")
    if contract.get("declared_business_module_count") != len(BUSINESS_MODULES):
        _error(errors, "declared business module count must be 11")
    if contract.get("declared_adapter_boundary_count") != len(ADAPTER_BOUNDARIES):
        _error(errors, "declared adapter boundary count must be 1")

    old_roots = sorted({text for text in _walk_strings(contract) if "cn.ti" in text})
    if old_roots:
        _error(errors, "module contract contains stale cn.ti package names")

    shared_kernel = contract.get("shared_kernel")
    if not isinstance(shared_kernel, dict):
        _error(errors, "shared_kernel must be an object")
    else:
        if shared_kernel.get("module_id") != "sharedkernel":
            _error(errors, "shared kernel module_id must be sharedkernel")
        if shared_kernel.get("base_package") != f"{ROOT_PACKAGE}.sharedkernel":
            _error(errors, "shared kernel base package is inconsistent with ADR-0002")
        forbidden = shared_kernel.get("forbidden_contents")
        if not isinstance(forbidden, list) or not any(
            isinstance(item, str) and "JPA" in item for item in forbidden
        ):
            _error(errors, "shared kernel must explicitly forbid JPA entities")

    cross_rules = contract.get("cross_module_rules")
    if not isinstance(cross_rules, dict):
        _error(errors, "cross_module_rules must be an object")
    else:
        if cross_rules.get("physical_foreign_key_implies_java_dependency") is not False:
            _error(errors, "physical foreign keys must not imply Java dependencies")
        if cross_rules.get("shared_jpa_entities") != []:
            _error(errors, "shared_jpa_entities must be empty")
        if cross_rules.get("cross_owner_foreign_id_count_from_matrix") != cross_owner_foreign_ids:
            _error(
                errors,
                "cross-owner foreign ID count does not match ownership matrix "
                f"({cross_owner_foreign_ids})",
            )

    modulith_mapping = contract.get("spring_modulith_mapping")
    if not isinstance(modulith_mapping, dict):
        _error(errors, "spring_modulith_mapping must be an object")
    else:
        if "@ApplicationModule" not in str(modulith_mapping.get("module_declaration", "")):
            _error(errors, "Modulith modules must declare @ApplicationModule")
        named_interface = str(modulith_mapping.get("public_api_exposure", ""))
        if "@NamedInterface" not in named_interface or f"{ROOT_PACKAGE}.<module>.api" not in named_interface:
            _error(errors, "public application APIs must be an explicit Modulith named interface")
        if "ApplicationModules" not in str(modulith_mapping.get("verification", "")):
            _error(errors, "Modulith ApplicationModules verification is missing")

    modules = contract.get("modules")
    if not isinstance(modules, list):
        _error(errors, "modules must be an array")
        return
    if not all(isinstance(module, dict) for module in modules):
        _error(errors, "every module entry must be an object")
        return

    ids = [str(module.get("module_id", "")) for module in modules]
    for duplicate in sorted(_duplicates(ids)):
        _error(errors, f"module appears more than once: {duplicate}")
    expected_ids = set(ALL_OWNERS)
    actual_ids = set(ids)
    for missing in sorted(expected_ids - actual_ids):
        _error(errors, f"module contract is missing boundary: {missing}")
    for extra in sorted(actual_ids - expected_ids):
        _error(errors, f"module contract has unknown boundary: {extra}")

    modules_by_id = {str(module.get("module_id", "")): module for module in modules}
    graph: dict[str, list[str]] = {}
    contract_resources: dict[tuple[str, str], str] = {}
    contract_roles: dict[tuple[str, str], str] = {}

    for module_id, module in modules_by_id.items():
        if module_id not in expected_ids:
            continue
        expected_kind = (
            "business_module" if module_id in BUSINESS_MODULES else "adapter_boundary"
        )
        if module.get("boundary_kind") != expected_kind:
            _error(errors, f"{module_id}: boundary_kind must be {expected_kind}")
        base_package = module.get("base_package")
        expected_package = f"{ROOT_PACKAGE}.{module_id}"
        if base_package != expected_package:
            _error(errors, f"{module_id}: base_package must be {expected_package}")
        if not _is_nonempty_string(module.get("responsibility")):
            _error(errors, f"{module_id}: responsibility must be non-empty")
        if module.get("shared_entities") != []:
            _error(errors, f"{module_id}: shared_entities must be empty")
        forbidden_imports = module.get("cross_module_forbidden_imports")
        if not isinstance(forbidden_imports, list) or tuple(
            forbidden_imports
        ) != FORBIDDEN_CROSS_MODULE_IMPORTS:
            _error(errors, f"{module_id}: forbidden cross-module import patterns drifted")
        if not _is_nonempty_string(module.get("transaction_boundary")):
            _error(errors, f"{module_id}: transaction_boundary must be non-empty")

        dependencies = module.get("allowed_dependencies")
        if not isinstance(dependencies, list) or not all(
            isinstance(item, str) for item in dependencies
        ):
            _error(errors, f"{module_id}: allowed_dependencies must be a string array")
            dependencies = []
        for duplicate in sorted(_duplicates(dependencies)):
            _error(errors, f"{module_id}: duplicate allowed dependency {duplicate}")
        if module_id in dependencies:
            _error(errors, f"{module_id}: a module cannot depend on itself")
        for dependency in dependencies:
            if dependency not in expected_ids and dependency != "sharedkernel":
                _error(errors, f"{module_id}: unknown dependency {dependency}")
        expected_dependencies = EXPECTED_DEPENDENCIES[module_id]
        if tuple(dependencies) != expected_dependencies:
            _error(
                errors,
                f"{module_id}: allowed dependency contract drifted; expected "
                + ", ".join(expected_dependencies),
            )
        graph[module_id] = dependencies

        tables = module.get("owned_tables")
        if not isinstance(tables, list) or not all(isinstance(item, str) for item in tables):
            _error(errors, f"{module_id}: owned_tables must be a string array")
            tables = []
        for duplicate in sorted(_duplicates(tables)):
            _error(errors, f"{module_id}: duplicate owned table {duplicate}")
        for table in tables:
            key = ("table", table)
            if key in contract_resources:
                _error(
                    errors,
                    f"table is owned more than once: {table} by "
                    f"{contract_resources[key]} and {module_id}",
                )
            else:
                contract_resources[key] = module_id

        resources = module.get("owned_resources")
        if not isinstance(resources, list) or not all(
            isinstance(item, dict) for item in resources
        ):
            _error(errors, f"{module_id}: owned_resources must be an object array")
            resources = []
        for resource in resources:
            kind = resource.get("kind")
            name = resource.get("name")
            role = resource.get("persistence_role")
            if not all(_is_nonempty_string(item) for item in (kind, name, role)):
                _error(errors, f"{module_id}: owned resource has blank kind/name/role")
                continue
            if kind == "table":
                _error(errors, f"{module_id}: tables must be declared in owned_tables")
            key = (kind, name)
            if key in contract_resources:
                _error(
                    errors,
                    f"resource is owned more than once: {kind}:{name} by "
                    f"{contract_resources[key]} and {module_id}",
                )
            else:
                contract_resources[key] = module_id
                contract_roles[key] = role

        apis = module.get("public_application_apis")
        internal = module.get("internal_packages")
        if not isinstance(internal, list) or not all(
            isinstance(item, dict) for item in internal
        ):
            _error(errors, f"{module_id}: internal_packages must be an object array")
            internal = []
        internal_names = [item.get("package") for item in internal]
        if not all(_is_nonempty_string(item) for item in internal_names):
            _error(errors, f"{module_id}: every internal package must be named")
        if any(
            isinstance(item, str) and not item.startswith(f"{expected_package}.")
            for item in internal_names
        ):
            _error(errors, f"{module_id}: internal package escapes its module root")

        if module_id in BUSINESS_MODULES:
            if module.get("cross_module_reference_policy") != "id_only":
                _error(errors, f"{module_id}: cross-module references must be id_only")
            if not isinstance(apis, list) or not apis or not all(
                isinstance(api, dict) for api in apis
            ):
                _error(errors, f"{module_id}: at least one public application API is required")
                apis = []
            for api in apis:
                if api.get("package") != f"{expected_package}.api":
                    _error(errors, f"{module_id}: public API must be in {expected_package}.api")
                for field in ("type", "purpose", "payload_policy"):
                    if not _is_nonempty_string(api.get(field)):
                        _error(errors, f"{module_id}: public API {field} must be non-empty")
                if "never expose persistence entities" not in str(
                    api.get("payload_policy", "")
                ):
                    _error(errors, f"{module_id}: public API must forbid persistence entities")
                if not isinstance(api.get("inputs"), list) or not isinstance(
                    api.get("outputs"), list
                ):
                    _error(errors, f"{module_id}: public API inputs/outputs must be arrays")
            expected_internal = {
                f"{expected_package}.application",
                f"{expected_package}.domain",
                f"{expected_package}.infrastructure",
            }
            if not all(isinstance(item, str) for item in internal_names) or set(
                internal_names
            ) != expected_internal:
                _error(errors, f"{module_id}: internal package set is incomplete or expanded")
        else:
            if apis != []:
                _error(errors, "web adapter must not publish a business application API")
            if tables:
                _error(errors, "web adapter boundary must not own tables/JPA persistence")
            if module.get("cross_module_reference_policy") != "api_only":
                _error(errors, "web adapter cross-module references must be api_only")
            expected_web_internal = {
                f"{expected_package}.compat",
                f"{expected_package}.v1",
                f"{expected_package}.security",
                f"{expected_package}.contract",
            }
            if not all(isinstance(item, str) for item in internal_names) or set(
                internal_names
            ) != expected_web_internal:
                _error(errors, "web adapter internal packages must contain no persistence layer")
            adapter_contract = module.get("adapter_contract")
            if not isinstance(adapter_contract, dict):
                _error(errors, "web adapter_contract must be an object")
            else:
                if adapter_contract.get("database_access") != "forbidden":
                    _error(errors, "web adapter database access must be forbidden")
                if adapter_contract.get("legacy_runtime_fallback") != "forbidden after a route is cut over":
                    _error(errors, "web adapter legacy runtime fallback policy drifted")

    for cycle in _find_cycles(graph):
        _error(errors, "module dependency cycle: " + " -> ".join(cycle))

    missing_resources = set(ownership) - set(contract_resources)
    extra_resources = set(contract_resources) - set(ownership)
    for kind, name in sorted(missing_resources):
        _error(errors, f"module contract is missing owned resource: {kind}:{name}")
    for kind, name in sorted(extra_resources):
        _error(errors, f"module contract declares unknown resource: {kind}:{name}")
    for key in sorted(set(ownership) & set(contract_resources)):
        expected_owner = ownership[key].get("target_owner")
        actual_owner = contract_resources[key]
        if actual_owner != expected_owner:
            _error(
                errors,
                f"owner mismatch for {key[0]}:{key[1]}: matrix={expected_owner}, "
                f"contract={actual_owner}",
            )
        if key[0] != "table":
            expected_role = ownership[key].get("persistence_role")
            if contract_roles.get(key) != expected_role:
                _error(errors, f"persistence role mismatch for {key[0]}:{key[1]}")

    adjustments = contract.get("dependency_adjustments")
    if not isinstance(adjustments, list):
        _error(errors, "dependency_adjustments must document Phase 0 DAG changes")
    else:
        catalog_adjustments = [
            item
            for item in adjustments
            if isinstance(item, dict) and item.get("edge") == "catalog -> identity"
        ]
        if len(catalog_adjustments) != 1:
            _error(errors, "catalog -> identity must have exactly one documented adjustment")
        else:
            adjustment = catalog_adjustments[0]
            if adjustment.get("change_from_phase0_candidate") != "added":
                _error(errors, "catalog -> identity must be marked added from Phase 0")
            evidence = adjustment.get("evidence")
            if not isinstance(evidence, list) or not any(
                isinstance(item, str) and "subject_permissions.py" in item
                for item in evidence
            ):
                _error(errors, "catalog -> identity adjustment lacks legacy permission evidence")
            if not _is_nonempty_string(adjustment.get("rationale")):
                _error(errors, "catalog -> identity adjustment lacks rationale")

    event_constraints = contract.get("event_dependency_constraints")
    if not isinstance(event_constraints, dict):
        _error(errors, "messaging event dependency constraints are missing")
    else:
        if event_constraints.get("consumer") != "messaging":
            _error(errors, "event dependency consumer must be messaging")
        event_providers = event_constraints.get("event_providers")
        if not isinstance(event_providers, list) or tuple(
            event_providers
        ) != MESSAGING_EVENT_PROVIDERS:
            _error(errors, "messaging event provider contract drifted")
        if event_constraints.get("synchronous_reverse_calls") != "forbidden":
            _error(errors, "messaging synchronous reverse calls must be forbidden")

    messaging = modules_by_id.get("messaging", {})
    dependency_contracts = messaging.get("dependency_contracts")
    if not isinstance(dependency_contracts, list):
        _error(errors, "messaging dependency_contracts are missing")
    else:
        by_provider = {
            item.get("provider"): item
            for item in dependency_contracts
            if isinstance(item, dict)
        }
        for provider in MESSAGING_EVENT_PROVIDERS:
            detail = by_provider.get(provider)
            if not detail or detail.get("interaction") != "public_event_contract" or detail.get(
                "mode"
            ) != "asynchronous_consumption_only":
                _error(
                    errors,
                    f"messaging -> {provider} must be public-event asynchronous-only",
                )
        identity_detail = by_provider.get("identity")
        if not identity_detail or identity_detail.get("mode") != "narrow_synchronous_query":
            _error(errors, "messaging -> identity must be a narrow synchronous query only")

    public_event_edges = contract.get("public_event_edges")
    if not isinstance(public_event_edges, list) or not all(
        isinstance(item, dict) for item in public_event_edges
    ):
        _error(errors, "public_event_edges must be an object array")
    else:
        actual_event_edges: list[tuple[str, str]] = []
        for edge in public_event_edges:
            consumer = edge.get("consumer")
            provider = edge.get("provider")
            if not isinstance(consumer, str) or not isinstance(provider, str):
                _error(errors, "public event edge consumer/provider must be strings")
                continue
            actual_event_edges.append((consumer, provider))
            if edge.get("interaction") != "public_event_contract" or edge.get(
                "mode"
            ) != "asynchronous_consumption_only":
                _error(
                    errors,
                    f"{consumer} -> {provider} event edge must be asynchronous public-only",
                )
        if _duplicates(f"{consumer}->{provider}" for consumer, provider in actual_event_edges):
            _error(errors, "public_event_edges contain duplicate edges")
        if frozenset(actual_event_edges) != EXPECTED_PUBLIC_EVENT_EDGES:
            _error(errors, "public event edge set drifted from the Phase 0/1 DAG")


def _validate_invariants(document: Any, errors: list[str]) -> None:
    if not isinstance(document, dict):
        _error(errors, "business invariants root must be an object")
        return
    if document.get("contract_id") != "ti.phase1.business-invariants":
        _error(errors, "business invariants have unexpected contract_id")

    declared = document.get("required_invariant_ids")
    if not isinstance(declared, list) or not all(isinstance(item, str) for item in declared):
        _error(errors, "required_invariant_ids must be a string array")
        declared = []
    if tuple(declared) != REQUIRED_INVARIANTS:
        _error(errors, "required invariant declaration drifted")

    invariants = document.get("invariants")
    if not isinstance(invariants, list) or not all(
        isinstance(item, dict) for item in invariants
    ):
        _error(errors, "invariants must be an object array")
        return
    ids = [str(item.get("invariant_id", "")) for item in invariants]
    for duplicate in sorted(_duplicates(ids)):
        _error(errors, f"business invariant appears more than once: {duplicate}")
    by_id = {str(item.get("invariant_id", "")): item for item in invariants}
    for required in REQUIRED_INVARIANTS:
        if required not in by_id:
            _error(errors, f"required business invariant is missing: {required}")
        else:
            serialized = json.dumps(by_id[required], ensure_ascii=False, sort_keys=True)
            for token in REQUIRED_INVARIANT_TOKENS[required]:
                if token not in serialized:
                    _error(errors, f"{required}: required semantic token is missing: {token}")

    for invariant_id, invariant in by_id.items():
        for field in COMMON_INVARIANT_FIELDS:
            if field not in invariant:
                _error(errors, f"{invariant_id}: missing field {field}")
        owner = invariant.get("owner_module")
        if owner not in BUSINESS_MODULES:
            _error(errors, f"{invariant_id}: owner must be a business module")
        if isinstance(owner, str) and invariant_id and not invariant_id.startswith(f"{owner}."):
            _error(errors, f"{invariant_id}: ID prefix must match owner {owner}")
        for field in (
            "title",
            "legacy_gap",
            "command_scope",
            "idempotency_key",
            "transaction_boundary",
            "concurrency_rule",
            "rule",
            "success_observation",
            "failure_observation",
        ):
            if not _is_nonempty_string(invariant.get(field)):
                _error(errors, f"{invariant_id}: {field} must be non-empty")
        evidence = invariant.get("legacy_evidence")
        if not isinstance(evidence, list) or not evidence or not all(
            _is_nonempty_string(item) for item in evidence
        ):
            _error(errors, f"{invariant_id}: legacy_evidence must be non-empty")
        scenarios = invariant.get("verification_scenarios")
        if not isinstance(scenarios, list) or len(scenarios) < 3:
            _error(errors, f"{invariant_id}: at least three verification scenarios required")
        else:
            for index, scenario in enumerate(scenarios, start=1):
                if not isinstance(scenario, dict) or not all(
                    _is_nonempty_string(scenario.get(field))
                    for field in ("given", "when", "then")
                ):
                    _error(errors, f"{invariant_id}: scenario {index} is incomplete")

    idempotency = document.get("global_idempotency_contract")
    if not isinstance(idempotency, dict):
        _error(errors, "global_idempotency_contract must be an object")
    else:
        if "409" not in str(idempotency.get("same_key_different_digest", "")):
            _error(errors, "idempotency digest conflict must be HTTP 409")
        if "one local transaction" not in str(idempotency.get("atomicity", "")):
            _error(errors, "idempotency record and fact must share one local transaction")

    precision = document.get("score_precision_policy")
    if not isinstance(precision, dict):
        _error(errors, "score_precision_policy must be an object")
    else:
        if precision.get("scope") != "new_v1_target_rule":
            _error(errors, "scale=2 HALF_UP must be scoped to the new v1 target rule")
        if precision.get("internal_type") != "java.math.BigDecimal":
            _error(errors, "score calculations must use java.math.BigDecimal")
        item_total = precision.get("item_and_total", {})
        if not isinstance(item_total, dict) or item_total.get("rounding") != "UNNECESSARY":
            _error(errors, "item and total score must not use implicit rounding")
        derived = precision.get("derived_percentage_and_average", {})
        if not isinstance(derived, dict) or derived.get("scale") != 2 or derived.get(
            "rounding"
        ) != "HALF_UP":
            _error(errors, "new v1 derived scores must use scale=2 HALF_UP")
        if precision.get("legacy_compatibility_precision_status") != "unknown":
            _error(errors, "legacy compatibility precision must remain unknown until evidenced")
        compatibility = str(precision.get("legacy_wire_compatibility", ""))
        if "逐字段" not in compatibility or "不得" not in compatibility:
            _error(errors, "legacy score precision must be proven per field, not inferred from v1")
        if not _is_nonempty_string(precision.get("cutover_gate")):
            _error(errors, "score precision cutover gate is missing")

    score_rule = str(
        by_id.get("assessment.decimal-score-determinism", {}).get("rule", "")
    )
    for token in ("新 /api/v1", "unknown", "不得切换写流量"):
        if token not in score_rule:
            _error(errors, f"assessment score invariant must distinguish compatibility: {token}")


def _validate_protocol(protocol: str, errors: list[str]) -> None:
    for marker in REQUIRED_PROTOCOL_MARKERS:
        count = len(re.findall(rf"(?m)^{re.escape(marker)}$", protocol))
        if count != 1:
            _error(errors, f"protocol marker {marker} must appear once, found {count}")

    required_phrases = (
        "不授权执行生产切换",
        "legacy_read_db",
        "java_read_db",
        "legacy_write_db",
        "java_write_db",
        "数据库侧 writer 撤销",
        "一次性把完整入口整体指向 Java",
        "route split",
        "percentage split",
        "shadow write",
        "第三套隔离",
        "写前回滚",
        "写后恢复",
    )
    for phrase in required_phrases:
        if phrase not in protocol:
            _error(errors, f"cutover protocol is missing required phrase: {phrase}")

    forbidden_phrases = (
        "网关按批准步长开放流量",
        "默认恢复冻结快照",
        "默认恢复冻结快照 `SF`",
    )
    for phrase in forbidden_phrases:
        if phrase in protocol:
            _error(errors, f"cutover protocol contains forbidden strategy: {phrase}")

    decision_tokens = (
        "**前向修复（默认优先）**",
        "**反向迁移**",
        "**恢复冻结备份并丢弃窗口写入（最后手段）**",
    )
    positions = [protocol.find(token) for token in decision_tokens]
    if any(position < 0 for position in positions) or positions != sorted(positions):
        _error(
            errors,
            "post-write recovery order must be forward fix, reverse migration, then approved loss",
        )
    if "SI` 是前向修复或提取窗口增量做反向迁移的权威输入" not in protocol:
        _error(errors, "incident snapshot SI must drive forward/reverse recovery")
    if "旧 Flask 保持离线且无写权" not in protocol:
        _error(errors, "whole-deployment cutover must keep Flask offline and write-revoked")


def validate_all(
    contracts_path: Path,
    invariants_path: Path,
    ownership_path: Path,
    protocol_path: Path,
) -> list[str]:
    """Return every deterministic validation error; an empty list means success."""

    errors: list[str] = []
    ownership_rows = _load_ownership(ownership_path, errors)
    ownership, cross_owner_foreign_ids = _validate_ownership_rows(
        ownership_rows, errors
    )

    contract: Any = None
    try:
        contract = load_json(contracts_path)
    except (OSError, json.JSONDecodeError, DuplicateJsonKey, ValueError) as exc:
        _error(errors, f"cannot read module contract {contracts_path}: {exc}")

    invariants: Any = None
    try:
        invariants = load_json(invariants_path)
    except (OSError, json.JSONDecodeError, DuplicateJsonKey, ValueError) as exc:
        _error(errors, f"cannot read business invariants {invariants_path}: {exc}")

    try:
        protocol = protocol_path.read_text(encoding="utf-8")
    except OSError as exc:
        _error(errors, f"cannot read cutover protocol {protocol_path}: {exc}")
        protocol = ""

    if contract is not None:
        _validate_contract(contract, ownership, cross_owner_foreign_ids, errors)
    if invariants is not None:
        _validate_invariants(invariants, errors)
    _validate_protocol(protocol, errors)
    return errors


def _default_paths() -> dict[str, Path]:
    ti_java = Path(__file__).resolve().parents[1]
    phase1 = ti_java / "docs" / "refactor" / "phase1"
    return {
        "contracts": phase1 / "module-contracts.json",
        "invariants": phase1 / "business-invariants.json",
        "ownership": ti_java / "docs" / "refactor" / "03-data-ownership.csv",
        "protocol": phase1 / "comparison-cutover-protocol.md",
    }


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    defaults = _default_paths()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contracts", type=Path, default=defaults["contracts"])
    parser.add_argument("--invariants", type=Path, default=defaults["invariants"])
    parser.add_argument("--ownership", type=Path, default=defaults["ownership"])
    parser.add_argument("--protocol", type=Path, default=defaults["protocol"])
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    errors = validate_all(
        args.contracts.resolve(),
        args.invariants.resolve(),
        args.ownership.resolve(),
        args.protocol.resolve(),
    )
    if errors:
        print(f"phase1 boundary validation: FAILED ({len(errors)} errors)")
        for error in errors:
            print(f"- {error}")
        return 1

    print(
        "phase1 boundary validation: OK "
        "(11 business modules, 1 web adapter, 70 tables, 84 non-table resources, "
        "6 required invariants)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
