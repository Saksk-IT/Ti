#!/usr/bin/env python3
"""Fail-closed checks for the bounded Phase 4A catalog disposition audit."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import subprocess
import unittest
from collections import Counter
from pathlib import Path


TI_JAVA_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = TI_JAVA_ROOT.parent
PHASE4A_ROOT = TI_JAVA_ROOT / "docs" / "refactor" / "phase4a"
CONTRACT_PATH = PHASE4A_ROOT / "catalog-candidate-disposition.json"
FINAL_ACCEPTANCE_PATH = PHASE4A_ROOT / "phase4a-final-acceptance.json"
FINAL_ACCEPTANCE_REPOSITORY_PATH = (
    "Ti-Java/docs/refactor/phase4a/phase4a-final-acceptance.json"
)
HTTP_METHODS = {"get", "post", "put", "delete", "patch", "options", "head"}
CALLER_KIND_CLUES = {
    "dynamic_fetch_literal": ("fetch(",),
    "dynamic_navigation_literal": ("window.location", "href=", "href =", "var url"),
    "dynamic_window_open": ("window.open(",),
    "fetch_literal": ("fetch(",),
    "fetch_post": ("fetch(",),
    "form_action_literal": ("<form", "action="),
    "generated_detail_url": ("detail_url",),
    "navigation_literal": ("href=", "href ="),
    "request": ("request(",),
    "test_client_literal": ("client.get(",),
    "window_open_literal": ("window.open(",),
    "wx_downloadFile": ("wx.downloadFile(",),
}


def _load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_java(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    text = re.sub(r"//.*", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s*([(),;<>])\s*", r"\1", text)
    return text


def _git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=REPOSITORY_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise AssertionError(
            f"git {' '.join(args)} failed ({completed.returncode}): {completed.stderr.strip()}"
        )
    return completed.stdout


def _controlled_manifest_without_final_acceptance() -> tuple[int, int, str]:
    paths = sorted(
        {
            item
            for item in _git(
                "ls-files",
                "-co",
                "--exclude-standard",
                "-z",
                "--",
                "Ti-Java",
            ).split("\0")
            if item and (REPOSITORY_ROOT / item).is_file()
        }
    )
    if FINAL_ACCEPTANCE_REPOSITORY_PATH not in paths:
        raise AssertionError("final acceptance contract is absent from the controlled file set")
    records = []
    for relative in paths:
        path = REPOSITORY_ROOT / relative
        if path.is_symlink():
            raise AssertionError(f"controlled symlink is forbidden: {relative}")
        if relative == FINAL_ACCEPTANCE_REPOSITORY_PATH:
            continue
        records.append(
            {
                "path": relative.removeprefix("Ti-Java/"),
                "sha256": _sha256(path),
            }
        )
    payload = (
        json.dumps(
            records,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode()
    return len(paths), len(records), hashlib.sha256(payload).hexdigest()


def _resource_triples(resources):
    return {(item["kind"], item["name"], item["owner"]) for item in resources}


def _decode_operation_key(encoded: str) -> tuple[str, str, str]:
    return tuple(encoded.split("|", 2))


def _caller_route_clues(path: str) -> tuple[str, ...]:
    candidates = set()
    if "<" not in path:
        candidates.add(path)
    prefix = path.split("<", 1)[0]
    if prefix:
        candidates.add(prefix)
    for candidate in list(candidates):
        if candidate.startswith("/api/"):
            candidates.add(candidate[len("/api") :])
    return tuple(sorted((item for item in candidates if len(item) >= 4), key=len, reverse=True))


class Phase4aCatalogCandidateDispositionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = _load_json(CONTRACT_PATH)
        cls.source_contracts = cls.contract["source_contracts"]

        def resolve(reference: str) -> Path:
            return (PHASE4A_ROOT / reference).resolve()

        cls.resolve = staticmethod(resolve)
        cls.matrix_path = resolve(cls.source_contracts["frozen_route_matrix"]["source"])
        cls.openapi_path = resolve(cls.source_contracts["phase1_openapi"]["source"])
        cls.ownership_path = resolve(cls.source_contracts["frozen_data_ownership"]["source"])
        cls.effective_route_path = resolve(cls.source_contracts["effective_route_status"]["source"])
        cls.effective_ownership_path = resolve(cls.source_contracts["effective_data_ownership"]["source"])
        cls.api_shape_path = resolve(cls.source_contracts["application_api_shape"]["source"])
        cls.module_boundaries_path = resolve(cls.source_contracts["module_boundaries"]["source"])
        cls.question_export_plan_path = resolve(
            cls.source_contracts["question_export_query_plan_evidence"]["source"]
        )

        with cls.matrix_path.open("r", encoding="utf-8", newline="") as handle:
            cls.matrix_rows = list(csv.DictReader(handle))
        cls.expanded = []
        operation_ordinal = 0
        for rule_ordinal, row in enumerate(cls.matrix_rows, 1):
            methods = [method.strip() for method in row["methods"].split(",")]
            for method_ordinal, method in enumerate(methods, 1):
                operation_ordinal += 1
                cls.expanded.append(
                    {
                        "key": (row["route_id"], method, row["path"]),
                        "row": row,
                        "rule_ordinal": rule_ordinal,
                        "operation_ordinal": operation_ordinal,
                        "method_ordinal": method_ordinal,
                    }
                )
        cls.expanded_by_key = {item["key"]: item for item in cls.expanded}
        cls.expanded_by_route_id = {}
        for item in cls.expanded:
            cls.expanded_by_route_id.setdefault(item["key"][0], []).append(item)

        cls.openapi = _load_json(cls.openapi_path)
        cls.openapi_by_key = {}
        for target_path, path_item in cls.openapi["paths"].items():
            for method, operation in path_item.items():
                if method not in HTTP_METHODS or not isinstance(operation, dict):
                    continue
                legacy = operation.get("x-ti-legacy", {})
                route_id = legacy.get("routeId")
                legacy_method = legacy.get("method")
                flask_path = legacy.get("flaskPath")
                if route_id and legacy_method and flask_path:
                    cls.openapi_by_key[(route_id, legacy_method, flask_path)] = (
                        target_path,
                        operation,
                    )

        with cls.ownership_path.open("r", encoding="utf-8", newline="") as handle:
            cls.ownership_rows = list(csv.DictReader(handle))
        cls.ownership = {
            (row["resource_kind"], row["resource_name"]): row["target_owner"]
            for row in cls.ownership_rows
        }
        cls.effective_route = _load_json(cls.effective_route_path)
        cls.effective_ownership = _load_json(cls.effective_ownership_path)
        cls.api_shape = _load_json(cls.api_shape_path)
        cls.operations = cls.contract["operations"]
        cls.operation_keys = [
            (operation["route_id"], operation["method"], operation["path"])
            for operation in cls.operations
        ]
        cls.operations_by_key = {
            (operation["route_id"], operation["method"], operation["path"]): operation
            for operation in cls.operations
        }

    def assert_pinned_source(self, commit: str, source: str, expected_text: str | None = None):
        match = re.fullmatch(r"(?P<path>.+):(?P<start>\d+)(?:-(?P<end>\d+))?", source)
        self.assertIsNotNone(match, source)
        path = match.group("path")
        start = int(match.group("start"))
        end = int(match.group("end") or start)
        self.assertGreaterEqual(start, 1, source)
        self.assertGreaterEqual(end, start, source)
        object_name = f"{commit}:{path}"
        self.assertEqual("blob", _git("cat-file", "-t", object_name).strip(), source)
        lines = _git("show", object_name).splitlines()
        self.assertLessEqual(end, len(lines), source)
        selected = "\n".join(lines[start - 1 : end])
        self.assertTrue(selected.strip(), source)
        if expected_text is not None:
            self.assertIn(expected_text, selected, source)
        return selected

    def pinned_source_context(self, commit: str, source: str, radius: int = 5) -> str:
        match = re.fullmatch(r"(?P<path>.+):(?P<line>\d+)", source)
        self.assertIsNotNone(match, source)
        path = match.group("path")
        line = int(match.group("line"))
        lines = _git("show", f"{commit}:{path}").splitlines()
        self.assertLessEqual(line, len(lines), source)
        start = max(0, line - 1 - radius)
        end = min(len(lines), line + radius)
        return "\n".join(lines[start:end])

    def assert_source_assertions(self, commit: str, assertions):
        self.assertTrue(assertions)
        for assertion in assertions:
            self.assertEqual({"source", "contains"}, set(assertion))
            self.assertTrue(assertion["contains"], assertion["source"])
            for token in assertion["contains"]:
                self.assert_pinned_source(commit, assertion["source"], token)

    def assert_side_effect_evidence(self, operation, evidence):
        self.assertEqual({"operation_key", "side_effect_sources"}, set(evidence))
        self.assertEqual(
            (operation["route_id"], operation["method"], operation["path"]),
            _decode_operation_key(evidence["operation_key"]),
        )
        self.assert_effect_sources(operation, evidence["side_effect_sources"])

    def assert_effect_sources(self, operation, side_effect_sources):
        self.assertEqual(
            operation["side_effects"],
            [item["effect"] for item in side_effect_sources],
        )
        for item in side_effect_sources:
            self.assertEqual({"effect", "assertions"}, set(item))
            self.assert_source_assertions(self.contract["legacy_commit"], item["assertions"])

    def test_01_schema_and_required_per_operation_fields(self):
        self.assertEqual("ti.phase4a.catalog-candidate-disposition", self.contract["contract_id"])
        self.assertEqual(1, self.contract["schema_version"])
        self.assertEqual("disposition_audit_complete", self.contract["status"])
        self.assertIsNone(self.contract["integrity_policy"]["self_hash"])
        required = {
            "route_id",
            "method",
            "path",
            "source_order",
            "caller_evidence",
            "read_relations",
            "non_table_resources",
            "side_effects",
            "baseline_owner",
            "reviewed_target_owner",
            "disposition_phase",
            "disposition_class",
            "reason",
            "required_existing_catalog_apis",
            "single_owner_catalog_candidate",
            "migration_status",
            "production_cutover",
        }
        source_required = {
            "baseline_rule_ordinal",
            "expanded_operation_ordinal",
            "method_ordinal_within_rule",
            "endpoint",
            "source",
            "registration_source",
            "registration_kind",
        }
        self.assertEqual(24, len(self.operations))
        for operation in self.operations:
            self.assertTrue(required.issubset(operation), operation.get("route_id"))
            self.assertTrue(source_required.issubset(operation["source_order"]))
            self.assertTrue(operation["caller_evidence"])
            self.assertTrue(operation["side_effects"])
            self.assertTrue(operation["reason"])
            self.assertIn(operation["disposition_phase"], {"4C", "4H", "6"})

    def test_02_source_references_and_frozen_hashes(self):
        expected = {
            "frozen_route_matrix": (
                "../02-route-parity-matrix.csv",
                "fdbdfedf3dd70cd09778b2a7072711d103eee8461d0e7dd356d797006fc92c74",
            ),
            "phase1_openapi": (
                "../../../contracts/openapi.json",
                "41e0ad0e1eca3ba8731242dea7a638cd348069aad1331382f5f1bf6d4a08d64e",
            ),
            "frozen_data_ownership": (
                "../03-data-ownership.csv",
                "3f9cb0650c523593d7037dc24df902dbccdb3885f261f530e1725a9dc7a31748",
            ),
            "effective_route_status": (
                "effective-route-parity-status.json",
                "1c4645354be4d4a778ec7d68d2957130718e826648e420dd3d1fec7bea5339d4",
            ),
            "effective_data_ownership": (
                "effective-data-ownership-status.json",
                "455b45b6c838c2308b3018e690bd444b503d3493b6290fa3e5083c4f84e01127",
            ),
            "application_api_shape": (
                "application-api-shape-status.json",
                "74782a5a26b1f32f85869cafa931acf4a7c7e1398b3b2e9dab0d0ded93c448ca",
            ),
            "module_boundaries": (
                "../phase1/module-contracts.json",
                "3b0044b32876de9d467ae06040d7fffcd8d07ed1bea44a74cbbe43227f91c41a",
            ),
            "question_export_query_plan_evidence": (
                "question-export-query-plan-evidence.json",
                "96f04c1018f5c3a826c48972c2273096f8507e45900616ca6c842ee0318ae541",
            ),
        }
        self.assertEqual(set(expected), set(self.source_contracts))
        for name, reference in self.source_contracts.items():
            self.assertEqual({"source", "sha256"}, set(reference), name)
            self.assertRegex(reference["sha256"], r"^[0-9a-f]{64}$", name)
        for name, (source, sha256) in expected.items():
            reference = self.source_contracts[name]
            self.assertEqual(source, reference["source"], name)
            self.assertEqual(sha256, reference["sha256"], name)
            path = self.resolve(reference["source"])
            self.assertTrue(path.is_file(), f"missing source reference {name}: {path}")
            self.assertEqual(sha256, _sha256(path), name)

    def test_03_frozen_matrix_and_openapi_inventory_counts(self):
        self.assertEqual(592, len(self.matrix_rows))
        self.assertEqual(611, len(self.expanded))
        self.assertEqual(530, len(self.openapi["paths"]))
        rendered_operations = sum(
            1
            for path_item in self.openapi["paths"].values()
            for method in path_item
            if method in HTTP_METHODS
        )
        self.assertEqual(610, rendered_operations)

    def test_04_coverage_rule_is_exact_reproducible_union(self):
        migrated = {
            (item["route_id"], item["method"], item["path"])
            for item in self.effective_route["effective"]["migrated_operations"]
        }
        baseline_catalog_pending = {
            item["key"]
            for item in self.expanded
            if item["row"]["target_module"] == "catalog"
            and item["row"]["migration_status"] == "pending"
            and item["key"] not in migrated
        }
        self.assertEqual(8, len(baseline_catalog_pending))

        reviewed = set()
        groups = self.contract["reviewed_registry"][
            "internal_capability_complete_http_deferred_4h"
        ]
        for group in groups:
            for route_id in group["route_ids"]:
                matches = self.expanded_by_route_id.get(route_id, [])
                self.assertEqual(1, len(matches), route_id)
                reviewed.add(matches[0]["key"])
        for encoded in self.contract["reviewed_registry"]["additional_reviewed_operations"]:
            route_id, method, path = encoded.split("|", 2)
            reviewed.add((route_id, method, path))
        self.assertEqual(16, len(reviewed))
        expected = baseline_catalog_pending | reviewed
        self.assertEqual(24, len(expected))
        self.assertEqual(expected, set(self.operation_keys))
        self.assertEqual(len(self.operation_keys), len(set(self.operation_keys)))

    def test_05_every_operation_snapshot_matches_matrix_and_source_order(self):
        for operation in self.operations:
            key = (operation["route_id"], operation["method"], operation["path"])
            self.assertIn(key, self.expanded_by_key)
            item = self.expanded_by_key[key]
            row = item["row"]
            source = operation["source_order"]
            self.assertEqual("pending", row["migration_status"], key)
            self.assertEqual(row["target_module"], operation["baseline_owner"], key)
            self.assertEqual(row["endpoint"], source["endpoint"], key)
            self.assertEqual(row["source"], source["source"], key)
            self.assertEqual(row["registration_source"], source["registration_source"], key)
            self.assertEqual(row["registration_kind"], source["registration_kind"], key)
            self.assertEqual(item["rule_ordinal"], source["baseline_rule_ordinal"], key)
            self.assertEqual(item["operation_ordinal"], source["expanded_operation_ordinal"], key)
            self.assertEqual(item["method_ordinal"], source["method_ordinal_within_rule"], key)

    def test_06_effective_status_is_11_600_0_and_candidates_stay_pending(self):
        expected = self.contract["expected_effective_status"]
        effective = self.effective_route["effective"]
        self.assertEqual(expected["expanded_operation_count"], effective["expanded_operation_count"])
        self.assertEqual(expected["migrated"], effective["migration_status"]["migrated"])
        self.assertEqual(expected["pending"], effective["migration_status"]["pending"])
        self.assertEqual(
            expected["production_cutover"], effective["production_cutover_operation_count"]
        )
        migrated = {
            (item["route_id"], item["method"], item["path"])
            for item in effective["migrated_operations"]
        }
        self.assertTrue(set(self.operation_keys).isdisjoint(migrated))
        ownership_effective = self.effective_ownership["effective"]
        self.assertEqual(expected["effective_resource_count"], ownership_effective["resource_count"])
        self.assertEqual(
            expected["resources_with_exactly_one_owner"],
            ownership_effective["resources_with_exactly_one_owner"],
        )

    def test_07_every_operation_remains_pending_in_phase1_openapi(self):
        for operation in self.operations:
            key = (operation["route_id"], operation["method"], operation["path"])
            self.assertIn(key, self.openapi_by_key, key)
            _target_path, rendered = self.openapi_by_key[key]
            legacy = rendered["x-ti-legacy"]
            migration = rendered["x-ti-migration"]
            self.assertEqual(operation["route_id"], legacy["routeId"])
            self.assertEqual(operation["method"], legacy["method"])
            self.assertEqual(operation["path"], legacy["flaskPath"])
            self.assertEqual("pending", migration["status"])
            self.assertEqual(operation["baseline_owner"], migration["targetModule"])

    def test_08_all_relation_and_non_table_owners_match_frozen_ownership(self):
        resources = []
        for operation in self.operations:
            for field in ("read_relations", "non_table_resources"):
                declared = operation[field]
                self.assertEqual(len(declared), len(_resource_triples(declared)), (operation["route_id"], field))
                for resource in declared:
                    self.assertEqual({"kind", "name", "owner"}, set(resource), (operation["route_id"], field))
                resources.extend(declared)
        resources.extend(self.contract["recommended_next_slice"]["single_owner_basis"])
        for resource in resources:
            key = (resource["kind"], resource["name"])
            self.assertIn(key, self.ownership, key)
            self.assertEqual(self.ownership[key], resource["owner"], key)
        self.assertEqual(len(self.ownership_rows), len(self.ownership))

    def test_09_internal_4h_registry_matches_phase4a_read_contracts(self):
        groups = self.contract["reviewed_registry"][
            "internal_capability_complete_http_deferred_4h"
        ]
        expected_hashes = {
            "question-type-read-contract.json": "e947e7ce7755d594f79e56f35f334765893d11724bc27e7a52982d9077f8517a",
            "question-detail-read-contract.json": "cc0151548085786ffacfe3c9aa8834799954244dcfea3b07c18da13c76236266",
            "question-list-read-contract.json": "3eac95e1a2e247262280ab7b15a9a04b3c0c40f600ca26016862565ae5088935",
            "subject-inventory-read-contract.json": "f2deb8ae1a8a5dffba7f321897e2e01a366bdc6e649d8d415dc79c93786c08da",
            "subject-context-read-contract.json": "ff98d6542c89d9bb6d53dce310c9319c7d8a5d155fee282ec84ac12e47c646eb",
            "question-export-read-contract.json": "4bb990dad2235ec15f865e643b90a7654a52ddda6f26046c0f471169ce56fe6c",
        }
        self.assertEqual(expected_hashes, {group["contract"]: group["sha256"] for group in groups})
        route_ids = []
        for group in groups:
            self.assertEqual({"contract", "sha256", "route_ids", "java_api", "method"}, set(group))
            path = PHASE4A_ROOT / group["contract"]
            self.assertTrue(path.is_file())
            self.assertEqual(group["sha256"], _sha256(path), group["contract"])
            evidence = _load_json(path)
            boundary = evidence["module_boundary"]
            self.assertEqual("4H", boundary["deferred_phase"])
            self.assertFalse(evidence["acceptance"]["production_cutover"])
            status = evidence["route_status"]
            raw_operations = status.get("operations") or [status["operation"]]
            evidence_ids = {item["route_id"] for item in raw_operations}
            self.assertEqual(set(group["route_ids"]), evidence_ids, group["contract"])
            for item in raw_operations:
                self.assertEqual("pending", item["migration_status"])
                self.assertFalse(item["production_cutover"])
            self.assertEqual(
                group["java_api"] + "#" + re.search(r"\b(\w+)\s*\(", group["method"]).group(1),
                boundary["internal_application_api"],
            )
            route_ids.extend(group["route_ids"])
        self.assertEqual(11, len(route_ids))
        self.assertEqual(11, len(set(route_ids)))

    def test_10_application_api_shape_has_exact_deferred_ids_and_methods(self):
        self.assertEqual(11, self.api_shape["migrated_route_count"])
        self.assertEqual(11, self.api_shape["implemented_route_backed_operation_count"])
        self.assertEqual(19, self.api_shape["implemented_public_application_method_count"])
        catalog = next(module for module in self.api_shape["modules"] if module["module_id"] == "catalog")
        apis = {item["java_api"]: item for item in catalog["additional_public_apis"]}
        question = apis["io.saksk.ti.catalog.api.QuestionMetadataApplicationApi"]
        subject = apis["io.saksk.ti.catalog.api.SubjectMetadataApplicationApi"]
        deferred_4h = set(question["deferred_http_route_ids"])
        deferred_4h.update(question["deferred_question_detail_http_route_ids"])
        deferred_4h.update(question["deferred_question_list_http_route_ids"])
        deferred_4h.update(question["deferred_question_export_http_route_ids"])
        deferred_4h.update(subject["deferred_http_route_ids"])
        deferred_4h.update(subject["deferred_subject_context_http_route_ids"])
        expected_4h = {
            route_id
            for group in self.contract["reviewed_registry"][
                "internal_capability_complete_http_deferred_4h"
            ]
            for route_id in group["route_ids"]
        }
        self.assertEqual(expected_4h, deferred_4h)
        self.assertEqual({"c618fb5f9f97", "bb21e7730d04"}, set(question["deferred_learning_http_route_ids"]))
        self.assertEqual(
            {"questionTypes", "countQuestions", "findQuestionById", "listQuestionSummaries", "listQuestionExportRecords"},
            {method["name"] for method in question["methods"]},
        )
        self.assertEqual(
            {"listSubjectInventorySummaries", "findSubjectById"},
            {method["name"] for method in subject["methods"]},
        )

    def test_11_every_required_catalog_api_signature_exists_exactly(self):
        api_sources = {
            "io.saksk.ti.catalog.api.QuestionMetadataApplicationApi": TI_JAVA_ROOT
            / "server/src/main/java/io/saksk/ti/catalog/api/QuestionMetadataApplicationApi.java",
            "io.saksk.ti.catalog.api.SubjectMetadataApplicationApi": TI_JAVA_ROOT
            / "server/src/main/java/io/saksk/ti/catalog/api/SubjectMetadataApplicationApi.java",
            "io.saksk.ti.catalog.api.PublicBankCatalogApi": TI_JAVA_ROOT
            / "server/src/main/java/io/saksk/ti/catalog/api/PublicBankCatalogApi.java",
        }
        required = {
            (item["java_api"], item["method"])
            for operation in self.operations
            for item in operation["required_existing_catalog_apis"]
        }
        required.update(
            (group["java_api"], group["method"])
            for group in self.contract["reviewed_registry"][
                "internal_capability_complete_http_deferred_4h"
            ]
        )
        self.assertIn(
            (
                "io.saksk.ti.catalog.api.QuestionMetadataApplicationApi",
                "List<QuestionExportRecordView> listQuestionExportRecords(QuestionExportQuery query)",
            ),
            required,
        )
        for java_api, signature in required:
            self.assertIn(java_api, api_sources)
            source = api_sources[java_api]
            self.assertTrue(source.is_file(), source)
            body = _canonical_java(source.read_text(encoding="utf-8"))
            self.assertIn(_canonical_java(signature), body, f"{java_api}#{signature}")

    def test_12_no_reviewed_candidate_is_implement_now_migrated_or_cut_over(self):
        summary = self.contract["disposition_summary"]
        self.assertEqual(0, summary["implement_now_operations"])
        self.assertEqual(0, summary["additional_safe_catalog_only_reads_found"])
        self.assertEqual(0, summary["production_cutover_true_operations"])
        self.assertEqual(24, summary["reviewed_operation_count"])
        phases = Counter(operation["disposition_phase"] for operation in self.operations)
        self.assertEqual({"4H": 16, "4C": 4, "6": 4}, dict(phases))
        for operation in self.operations:
            self.assertFalse(operation["single_owner_catalog_candidate"])
            self.assertNotIn("implement_now", operation["disposition_class"])
            self.assertEqual("pending", operation["migration_status"])
            self.assertFalse(operation["production_cutover"])

    def test_13_true_caller_evidence_is_pinned_and_not_a_false_static_caller(self):
        commit = self.contract["legacy_commit"]
        self.assertRegex(commit, r"^[0-9a-f]{40}$")
        self.assertEqual("commit", _git("cat-file", "-t", commit).strip())
        self.assertEqual(commit, _git("rev-parse", f"{commit}^{{commit}}").strip())
        source_pattern = re.compile(r"^.+:\d+$")
        for operation in self.operations:
            for evidence in operation["caller_evidence"]:
                self.assertEqual(commit, evidence["pinned_commit"])
                self.assertRegex(evidence["source"], source_pattern)
                self.assertNotEqual("not_found_static_scan", evidence["source"])
                self.assertTrue(evidence["surface"])
                self.assertTrue(evidence["kind"])
                self.assert_pinned_source(commit, evidence["source"])
                self.assertIn(evidence["kind"], CALLER_KIND_CLUES)
                context = self.pinned_source_context(commit, evidence["source"])
                self.assertTrue(
                    any(clue in context for clue in CALLER_KIND_CLUES[evidence["kind"]]),
                    (operation["path"], evidence["source"], evidence["kind"]),
                )
                route_clues = _caller_route_clues(operation["path"])
                self.assertTrue(route_clues, operation["path"])
                self.assertTrue(
                    any(clue in context for clue in route_clues),
                    (operation["path"], evidence["source"], route_clues),
                )

    def test_14_quality_summary_and_stop_conditions_are_explicit(self):
        expected_dimensions = {
            "filter",
            "sort",
            "pagination",
            "visibility",
            "permissions",
            "cache",
            "n_plus_one",
            "count",
            "query_plans",
        }
        quality = self.contract["quality_coverage"]
        self.assertEqual(expected_dimensions, set(quality))
        for dimension, item in quality.items():
            self.assertTrue(item["status"], dimension)
            self.assertTrue(item["evidence"], dimension)
        self.assertIn("finding", quality["query_plans"])
        self.assertNotIn("gap", quality["query_plans"])
        stops = self.contract["stop_conditions"]
        self.assertGreaterEqual(len(stops), 9)
        joined = "\n".join(stops)
        for required in ["11 migrated, 600 pending", "24 unique operation", "listQuestionExportRecords", "Phase 4B", "WORM"]:
            self.assertIn(required, joined)

    def test_15_disposition_is_static_and_separate_final_acceptance_authorizes_only_phase4b_categories(self):
        self.assertNotIn("phase4a_closure_gate", self.contract)
        self.assertNotIn("next_action", self.contract)
        handoff = self.contract["phase4a_handoff_requirements"]
        self.assertTrue(handoff["disposition_audit_complete"])
        self.assertTrue(handoff["no_additional_implement_now_catalog_candidate"])
        self.assertFalse(handoff["closure_owned_by_this_contract"])
        self.assertEqual(7, len(handoff["required_external_acceptance_dimensions"]))

        recommended = self.contract["recommended_next_slice"]
        self.assertNotIn("authorized_now", recommended)
        self.assertNotIn("authorization_predicate", recommended)
        self.assertEqual("4B", recommended["phase"])
        self.assertEqual("personalbank", recommended["module"])
        expected_keys = {
            "19b37a262989|GET|/api/user/banks/api/categories",
            "e32aec766730|GET|/user/banks/api/categories",
        }
        self.assertEqual(expected_keys, set(recommended["only_operation_keys"]))
        self.assertEqual(2, len(recommended["operations"]))
        for operation in recommended["operations"]:
            key = (operation["route_id"], operation["method"], operation["path"])
            item = self.expanded_by_key[key]
            self.assertEqual(operation["baseline_rule_ordinal"], item["rule_ordinal"])
            self.assertEqual(operation["expanded_operation_ordinal"], item["operation_ordinal"])
            self.assertEqual(operation["registration_source"], item["row"]["registration_source"])
            self.assertEqual(operation["registration_kind"], item["row"]["registration_kind"])
            self.assertEqual(operation["source"], item["row"]["source"])
            self.assertEqual("personalbank", item["row"]["target_module"])
            self.assertEqual("pending", item["row"]["migration_status"])
            self.assertFalse(operation["production_cutover"])
        self.assertEqual(
            {"personalbank"},
            {resource["owner"] for resource in recommended["single_owner_basis"]},
        )

        final = _load_json(FINAL_ACCEPTANCE_PATH)
        if os.environ.get("TI_PHASE4A_PREFINAL_ACCEPTANCE") == "1":
            lock_token = os.environ.get("TI_PHASE4A_PREFINAL_LOCK_TOKEN", "")
            self.assertRegex(lock_token, r"^[0-9a-f]{64}$")
            acceptance_lock = (
                TI_JAVA_ROOT
                / "server"
                / "target"
                / "phase4a-independent-acceptance.lock"
            )
            self.assertTrue(acceptance_lock.is_dir())
            self.assertFalse(acceptance_lock.is_symlink())
            lock_owner = acceptance_lock / "owner-token"
            self.assertTrue(lock_owner.is_file())
            self.assertFalse(lock_owner.is_symlink())
            self.assertEqual(lock_token, lock_owner.read_text(encoding="utf-8").strip())
            self.assertEqual("pending", final["status"])
            self.assertFalse(final["phase4a_closure"]["phase4a_closed"])
            self.assertFalse(final["phase4a_closure"]["final_control_plane_passed"])
            return
        self.assertEqual("ti.phase4a.final-acceptance", final["contract_id"])
        self.assertEqual(1, final["schema_version"])
        self.assertEqual("passed", final["status"])
        integrity = final["integrity_policy"]
        self.assertEqual("sha256", integrity["algorithm"])
        self.assertIsNone(integrity["self_hash"])
        self.assertEqual(
            ["docs/refactor/phase4a/phase4a-final-acceptance.json"],
            integrity["controlled_manifest_excluded_paths"],
        )

        for name, reference in final["source_contracts"].items():
            self.assertEqual({"source", "sha256"}, set(reference), name)
            source = (PHASE4A_ROOT / reference["source"]).resolve()
            self.assertTrue(source.is_file(), (name, source))
            self.assertEqual(reference["sha256"], _sha256(source), name)
        candidate_reference = final["source_contracts"]["catalog_candidate_disposition"]
        self.assertEqual("catalog-candidate-disposition.json", candidate_reference["source"])
        self.assertEqual(_sha256(CONTRACT_PATH), candidate_reference["sha256"])

        question_export = final["question_export_acceptance"]
        self.assertEqual(44, question_export["golden_case_count"])
        self.assertEqual(2, question_export["runtime_query_count"])
        self.assertEqual(9, question_export["query_plan_observation_count"])
        self.assertEqual(53, question_export["focused_java_and_contract_tests"])
        self.assertEqual(2, question_export["postgres_compatibility_tests"])

        raw = final["independent_full_acceptance"]
        self.assertRegex(raw["raw_report_sha256"], r"^[0-9a-f]{64}$")
        local_raw_path = TI_JAVA_ROOT / raw["ignored_local_raw_report"]
        if local_raw_path.is_file():
            self.assertEqual(raw["raw_report_sha256"], _sha256(local_raw_path))
        self.assertEqual(1220, raw["controlled_file_count"])
        self.assertEqual(raw["source_manifest_sha256"], raw["copy_manifest_sha256"])
        self.assertTrue(raw["source_equals_copy"])
        self.assertEqual(0, raw["symlink_count"])
        self.assertEqual(0, raw["forbidden_artifact_count"])
        self.assertEqual(215, raw["source_tool_tests"])
        self.assertEqual(36, raw["miniprogram_node_tests"])
        self.assertEqual(
            {"surefire": 406, "failsafe": 58, "failures": 0, "errors": 0, "skipped": 0},
            raw["maven"],
        )
        self.assertEqual(3, raw["compose"]["healthy_services"])
        self.assertEqual(3, raw["compose"]["exact_runtime_policy_services"])
        self.assertEqual(3, raw["compose"]["restarted_services"])
        self.assertEqual(8, raw["compose"]["read_only_bind_count"])
        self.assertEqual(0, raw["compose"]["source_worktree_bind_count"])
        self.assertTrue(all(raw["checks"].values()))
        self.assertTrue(all(value == 0 for value in raw["cleanup"].values()))

        controlled_count, included_count, manifest_sha256 = (
            _controlled_manifest_without_final_acceptance()
        )
        control = final["final_control_plane"]
        self.assertEqual(controlled_count, control["controlled_file_count"])
        self.assertEqual(included_count, control["manifest_included_file_count"])
        self.assertEqual(1, control["manifest_excluded_file_count"])
        self.assertEqual(manifest_sha256, control["source_manifest_sha256"])
        self.assertEqual(manifest_sha256, control["copy_manifest_sha256"])
        self.assertTrue(control["source_equals_copy"])
        self.assertTrue(all(control["static_checks"].values()))
        self.assertTrue(control["java_build_context_matches_full_acceptance"])

        closure = final["phase4a_closure"]
        required_closure_evidence = {
            "catalog_candidate_disposition_audit_complete",
            "question_export_acceptance_passed",
            "worm_acceptance_passed",
            "independent_full_acceptance_passed",
            "final_control_plane_passed",
        }
        self.assertTrue(all(closure[name] for name in required_closure_evidence))
        self.assertTrue(closure["phase4a_closed"])
        self.assertFalse(closure["production_cutover"])
        self.assertEqual("4B", closure["next_phase"])

        authorized = final["authorized_next_slice"]
        self.assertEqual(expected_keys, set(authorized["only_operation_keys"]))
        self.assertEqual(recommended["only_operation_keys"], authorized["only_operation_keys"])
        self.assertEqual("implementation_and_parity_evidence_only", authorized["scope"])
        self.assertFalse(authorized["route_openapi_delta_authorized"])
        self.assertFalse(authorized["production_cutover_authorized"])

    def test_16_targeted_resources_and_side_effects_are_fail_closed(self):
        truth = self.contract["legacy_truth_evidence"]
        self.assertEqual({"count_routes", "search_route", "public_bank_page_routes"}, set(truth))
        count_relations = {
            ("table", "questions", "catalog"),
            ("table", "subjects", "catalog"),
            ("table", "favorites", "learning"),
            ("table", "mistakes", "learning"),
            ("table", "user_progress", "learning"),
            ("table", "user_question_tag_items", "learning"),
            ("table", "users", "identity"),
            ("table", "user_subjects", "identity"),
        }
        count_resources = {
            ("redis_key", "cache:quiz:questions_count:<sha256(params)>", "catalog"),
            ("redis_key", "LIMITS:*", "operations"),
            ("db_kv_namespace", "question_tags_v1", "learning"),
            ("redis_key", "cache:ver:quiz:questions", "catalog"),
            ("redis_key", "cache:ver:quiz:subjects", "catalog"),
            ("redis_key", "cache:ver:quiz:u:<user_id>", "learning"),
        }
        count_effects = [
            "writes or refreshes the shared count response cache",
            "writes endpoint limiter counters",
            "tag reads can issue CREATE TABLE/INDEX and lazily copy legacy tags into user_question_tag_items",
            "Session identity synchronization may update users.last_active",
            "GET may write missing cache version defaults because get_questions_version, get_subjects_version, and get_user_quiz_version delegate to redis_set_text(..., nx=True)",
        ]
        count_keys = {
            ("c618fb5f9f97", "GET", "/api/questions/count"),
            ("bb21e7730d04", "GET", "/api/quiz/questions/count"),
        }
        for key in count_keys:
            operation = self.operations_by_key[key]
            self.assertEqual(count_relations, _resource_triples(operation["read_relations"]), key)
            self.assertEqual(len(count_relations), len(operation["read_relations"]), key)
            self.assertEqual(count_resources, _resource_triples(operation["non_table_resources"]), key)
            self.assertEqual(len(count_resources), len(operation["non_table_resources"]), key)
            self.assertEqual(count_effects, operation["side_effects"], key)

        count_truth = truth["count_routes"]
        self.assertEqual({"operation_keys", "resource_sources", "side_effect_sources"}, set(count_truth))
        self.assertEqual(count_keys, {_decode_operation_key(item) for item in count_truth["operation_keys"]})
        resource_sources = {
            (item["resource"]["kind"], item["resource"]["name"], item["resource"]["owner"]): item
            for item in count_truth["resource_sources"]
        }
        self.assertEqual(count_resources, set(resource_sources))
        self.assertEqual(len(count_resources), len(count_truth["resource_sources"]))
        for triple, item in resource_sources.items():
            self.assertEqual({"resource", "assertions"}, set(item), triple)
            self.assertEqual({"kind", "name", "owner"}, set(item["resource"]), triple)
            self.assertEqual(self.ownership[triple[:2]], triple[2], triple)
            self.assert_source_assertions(self.contract["legacy_commit"], item["assertions"])
        for key in count_keys:
            self.assert_effect_sources(
                self.operations_by_key[key], count_truth["side_effect_sources"]
            )

        search_key = ("4289bc27d0bb", "GET", "/search")
        search = self.operations_by_key[search_key]
        search_relations = {
            ("table", "questions", "catalog"),
            ("table", "subjects", "catalog"),
            ("table", "favorites", "learning"),
            ("table", "mistakes", "learning"),
            ("table", "users", "identity"),
            ("table", "user_subjects", "identity"),
            ("table", "public_bank_plaza_metrics", "catalog"),
            ("table", "plaza_boards", "catalog"),
            ("table", "user_question_banks", "personalbank"),
            ("table", "public_bank_users", "personalbank"),
            ("table", "bank_share_records", "personalbank"),
            ("table", "bank_shares", "personalbank"),
            ("table", "user_bank_answers", "learning"),
            ("table", "user_answers", "learning"),
            ("table", "public_subject_users", "catalog"),
            ("table", "forum_posts", "community"),
            ("table", "forum_boards", "community"),
            ("table", "forum_likes", "community"),
            ("table", "forum_favorites", "community"),
        }
        self.assertEqual(search_relations, _resource_triples(search["read_relations"]), search_key)
        self.assertEqual(len(search_relations), len(search["read_relations"]), search_key)
        self.assertEqual(
            {("redis_key", "plaza:metrics:refresh:lock", "catalog")},
            _resource_triples(search["non_table_resources"]),
        )
        self.assertEqual(
            [
                "public-bank search can synchronously refresh public_bank_plaza_metrics with DELETE/INSERT/commit when stale",
                "refresh acquires and releases the Redis metrics lock",
                "the page composes independently paginated question, bank and forum results",
                "a Session request may update users.last_active",
            ],
            search["side_effects"],
        )
        relation_evidence = {
            item["resource"]: item for item in search["read_relation_evidence"]
        }
        self.assertEqual({"bank_shares", "user_answers"}, set(relation_evidence))
        self.assertEqual(2, len(search["read_relation_evidence"]))
        expected_relation_sources = {
            "bank_shares": "app/modules/user_bank/services/plaza_query_service.py:812-826",
            "user_answers": "app/modules/user_bank/services/plaza_metrics_service.py:189-195",
        }
        for resource, source in expected_relation_sources.items():
            evidence = relation_evidence[resource]
            self.assertEqual(self.contract["legacy_commit"], evidence["pinned_commit"])
            self.assertEqual(source, evidence["source"])
            self.assert_pinned_source(evidence["pinned_commit"], source, resource)
            relation = next(item for item in search["read_relations"] if item["name"] == resource)
            self.assertEqual(self.ownership[(relation["kind"], resource)], relation["owner"])

        self.assert_side_effect_evidence(search, truth["search_route"])

        expected_shell_effects = {
            ("6a8ad5f06651", "GET", "/public/banks"): [
                "route body only renders a template with Session-derived page context",
                "client JavaScript performs the catalog API reads",
                "Session request may update users.last_active",
            ],
            (
                "cda75caa95a8",
                "GET",
                "/public/banks/card/<source_type>/<int:bank_id>",
            ): [
                "route body normalizes source_type and renders a template with Session-derived context",
                "client JavaScript calls the route-backed public-bank detail API",
                "Session request may update users.last_active",
            ],
        }
        for key, effects in expected_shell_effects.items():
            operation = self.operations_by_key[key]
            self.assertEqual([], operation["read_relations"], key)
            self.assertEqual([], operation["non_table_resources"], key)
            self.assertEqual(effects, operation["side_effects"], key)
        shell_evidence = {
            _decode_operation_key(item["operation_key"]): item
            for item in truth["public_bank_page_routes"]
        }
        self.assertEqual(set(expected_shell_effects), set(shell_evidence))
        self.assertEqual(len(expected_shell_effects), len(truth["public_bank_page_routes"]))
        for key, evidence in shell_evidence.items():
            self.assert_side_effect_evidence(self.operations_by_key[key], evidence)

    def test_17_question_export_plan_is_exact_and_included(self):
        expected_name = "question-export-query-plan-evidence.json"
        expected_hash = "96f04c1018f5c3a826c48972c2273096f8507e45900616ca6c842ee0318ae541"
        reference = self.source_contracts["question_export_query_plan_evidence"]
        self.assertEqual(expected_name, reference["source"])
        self.assertEqual(expected_hash, reference["sha256"])
        self.assertEqual(PHASE4A_ROOT / expected_name, self.question_export_plan_path)
        self.assertTrue(self.question_export_plan_path.is_file())
        self.assertEqual(expected_hash, _sha256(self.question_export_plan_path))
        for dimension in ("n_plus_one", "query_plans"):
            evidence = self.contract["quality_coverage"][dimension]["evidence"]
            self.assertIn(expected_name, evidence, dimension)
            self.assertEqual(1, evidence.count(expected_name), dimension)


if __name__ == "__main__":
    unittest.main()
