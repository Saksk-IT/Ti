#!/usr/bin/env python3
"""Fail-closed closure checks for the Phase 4B personal-bank category slice."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import pathlib
import re
import subprocess
import unittest


TI_JAVA_ROOT = pathlib.Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = TI_JAVA_ROOT.parent
PHASE4B_ROOT = TI_JAVA_ROOT / "docs" / "refactor" / "phase4b"
ACCEPTANCE_PATH = PHASE4B_ROOT / "personal-bank-category-acceptance.json"
SHARE_ENTRY_PATH = PHASE4B_ROOT / "personal-bank-share-list-entry-contract.json"
SHARE_READ_PATH = PHASE4B_ROOT / "personal-bank-share-list-read-contract.json"
ALL_SHARES_READ_PATH = PHASE4B_ROOT / "personal-bank-all-shares-read-contract.json"
ACCEPTANCE_RELATIVE = "docs/refactor/phase4b/personal-bank-category-acceptance.json"
PHASE4A_FINAL_SHA256 = (
    "9eeec781af91c0994c750ea2641653183f36eb4492d4ff9bd6809679c723620f"
)
SHAPE_SHA256 = "6efda6464411c6a355ea29ab51f0afa63804ea5110a862b9269c4e30e5f8adb6"
GOLDEN_SHA256 = "c81ad22b70e1e9e25eed96e2f06a475ba590eb7ae00b7a106c6bcedac3818515"
PLAN_SHA256 = "0b23e9af5cdbaec543fb798a45dd3c6fcd5c8a11cd9f7d27aeb92550cc80cffc"
READ_CONTRACT_SHA256 = (
    "8ef4b9a1eafeff9813f009a406d6863ac25b92ff438415ed674c758a5a2ff2c7"
)
ROUTE_KEYS = {
    "19b37a262989|GET|/api/user/banks/api/categories",
    "e32aec766730|GET|/user/banks/api/categories",
}
SHARE_ROUTE_KEYS = {
    "e817f8083d74|GET|/api/user/banks/api/<int:bank_id>/shares",
    "c50102968322|GET|/user/banks/api/<int:bank_id>/shares",
}
SHARE_ENTRY_PREREQUISITES = {
    "complete_caller_attestation",
    "capture_first_and_second_query_failure_boundaries",
    "verify_postgresql_16_14_and_18_4_jdbc_and_query_plans",
    "freeze_null_ordering_and_dialect_behavior",
}
RAW_CHECK_KEYS = {
    "docker_client_isolation",
    "maven_container_socket_binding",
    "phase3_docker_host_pinning",
    "phase1",
    "phase2_static",
    "phase3_static",
    "phase3_topology_static",
    "miniprogram",
    "data_plane",
    "empty_maven_cache",
    "maven",
    "unique_image_built_and_removed",
    "compose_http_and_database",
    "exact_runtime_policy",
    "restart_recovery",
    "baseline_resources_preserved",
}
RAW_CLEANUP_KEYS = {
    "container_residue",
    "network_residue",
    "volume_residue",
    "new_container_residue",
    "new_network_residue",
    "new_volume_residue",
    "deleted_baseline_container_count",
    "deleted_baseline_network_count",
    "deleted_baseline_volume_count",
    "image_residue",
    "cache_volume_residue",
    "port_residue",
}


def load_json(path: pathlib.Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_control_manifest() -> tuple[int, int, str]:
    completed = subprocess.run(
        [
            "git",
            "-C",
            str(REPOSITORY_ROOT),
            "ls-files",
            "-co",
            "--exclude-standard",
            "-z",
            "--",
            "Ti-Java",
        ],
        check=True,
        capture_output=True,
    )
    controlled = sorted({
        os.fsdecode(item)
        for item in completed.stdout.split(b"\0")
        if item
    })
    excluded = f"Ti-Java/{ACCEPTANCE_RELATIVE}"
    if controlled.count(excluded) != 1:
        raise AssertionError("acceptance contract must be the sole explicit exclusion")
    included = []
    for relative in controlled:
        path = REPOSITORY_ROOT / relative
        if path.is_symlink() or not path.is_file():
            raise AssertionError(f"invalid controlled path: {relative}")
        if relative == excluded:
            continue
        included.append({
            "path": relative.removeprefix("Ti-Java/"),
            "sha256": sha256(path),
        })
    payload = (json.dumps(
        included,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ) + "\n").encode()
    return len(controlled), len(included), hashlib.sha256(payload).hexdigest()


class Phase4bPersonalBankCategoryAcceptanceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.acceptance = load_json(ACCEPTANCE_PATH)
        cls.shape = load_json(PHASE4B_ROOT / "application-api-shape-status.json")
        cls.golden = load_json(PHASE4B_ROOT / "golden-personal-bank-category-reads.json")
        cls.plan = load_json(
            PHASE4B_ROOT / "personal-bank-category-query-plan-evidence.json"
        )
        cls.read_contract = load_json(
            PHASE4B_ROOT / "personal-bank-category-read-contract.json"
        )
        cls.share_read_contract = load_json(SHARE_READ_PATH)
        cls.all_shares_read_contract = load_json(ALL_SHARES_READ_PATH)

    def test_01_schema_predecessor_and_source_contracts(self):
        contract = self.acceptance
        self.assertEqual("ti.phase4b.personal-bank-category-acceptance", contract["contract_id"])
        self.assertEqual(1, contract["schema_version"])
        self.assertEqual(
            "personalbank-category-internal-read-closure-and-next-slice-handoff",
            contract["scope"],
        )
        self.assertEqual("700006dfdfa063deb4387be572911e782bcea0d9", contract["legacy_commit"])
        self.assertEqual("sha256", contract["integrity_policy"]["algorithm"])
        self.assertIsNone(contract["integrity_policy"]["self_hash"])
        self.assertEqual(
            [ACCEPTANCE_RELATIVE],
            contract["integrity_policy"]["controlled_manifest_excluded_paths"],
        )
        expected = {
            "phase4a_final_acceptance": PHASE4A_FINAL_SHA256,
            "application_api_shape": SHAPE_SHA256,
            "golden": GOLDEN_SHA256,
            "query_plan": PLAN_SHA256,
            "read_contract": READ_CONTRACT_SHA256,
        }
        for name, expected_hash in expected.items():
            reference = contract["source_contracts"][name]
            path = (PHASE4B_ROOT / reference["source"]).resolve()
            self.assertTrue(path.is_file(), name)
            self.assertEqual(expected_hash, reference["sha256"], name)
            self.assertEqual(expected_hash, sha256(path), name)

    def test_02_category_evidence_and_runtime_sql_are_closed(self):
        category = self.acceptance["category_acceptance"]
        self.assertEqual(22, category["golden_case_count"])
        self.assertEqual(GOLDEN_SHA256, category["golden_file_sha256"])
        self.assertEqual(22, self.golden["case_count"])
        self.assertEqual(22, len(self.golden["cases"]))
        self.assertEqual(
            category["golden_case_payload_sha256"],
            self.golden["case_payload_sha256"],
        )
        self.assertEqual(READ_CONTRACT_SHA256, category["read_contract_sha256"])
        self.assertEqual(PLAN_SHA256, category["query_plan_file_sha256"])
        self.assertEqual(1, category["runtime_query_count"])
        self.assertEqual(1, category["query_plan_observation_count"])
        self.assertEqual(2, category["postgres_compatibility_tests"])
        self.assertEqual(
            category["runtime_sql_sha256"],
            self.plan["measurement"]["observation"]["sql_sha256"],
        )
        self.assertEqual(
            category["runtime_sql_manifest_sha256"],
            self.plan["inputs"]["runtime_sql_manifest_sha256"],
        )
        self.assertEqual(
            PLAN_SHA256,
            self.read_contract["evidence"]["query_plan"]["file_sha256"],
        )

    def test_03_shape_routes_and_cutover_remain_unchanged(self):
        self.assertEqual(11, self.shape["migrated_route_count"])
        self.assertEqual(11, self.shape["implemented_route_backed_operation_count"])
        self.assertEqual(20, self.shape["implemented_public_application_method_count"])
        personalbank = next(
            module for module in self.shape["modules"]
            if module["module_id"] == "personalbank"
        )
        self.assertEqual([], personalbank["implemented_route_ids"])
        self.assertFalse(personalbank["direct_http_operation"])
        self.assertEqual({key.split("|", 1)[0] for key in ROUTE_KEYS},
                         set(personalbank["deferred_http_route_ids"]))
        operations = self.read_contract["route_status"]["operations"]
        self.assertEqual(ROUTE_KEYS, {
            f'{item["route_id"]}|{item["method"]}|{item["path"]}'
            for item in operations
        })
        self.assertTrue(all(item["migration_status"] == "pending" for item in operations))
        self.assertTrue(all(not item["production_cutover"] for item in operations))
        guard = self.read_contract["cutover_guard"]
        for field in (
            "controller_added",
            "security_matcher_added",
            "openapi_delta_added",
            "route_parity_delta_added",
            "production_cutover",
            "legacy_writer_changed",
            "phase4a_acceptance_changed",
        ):
            self.assertFalse(guard[field], field)

    def test_04_implementation_and_plan_inputs_match_current_files(self):
        implementation = self.read_contract["evidence"]["implementation"]
        self.assertEqual(set(implementation["source_files"]), set(implementation["source_sha256"]))
        for name, relative in implementation["source_files"].items():
            current_hash = sha256(TI_JAVA_ROOT / relative)
            if name in {"application_api", "application_service"}:
                successor = self.all_shares_read_contract["implementation"]
                self.assertEqual(relative, successor["main_source_files"][name])
                self.assertEqual(successor["main_source_sha256"][name], current_hash, name)
                self.assertNotEqual(implementation["source_sha256"][name], current_hash)
            else:
                self.assertEqual(implementation["source_sha256"][name], current_hash, name)
        inputs = self.plan["inputs"]
        for key in (
            "adapter",
            "runtime_sql_exporter",
            "postgres_compatibility_test",
            "postgres_schema",
            "postgres_fixture",
            "capture_tool",
            "capture_tool_test",
        ):
            self.assertEqual(inputs[f"{key}_sha256"], sha256(TI_JAVA_ROOT / inputs[key]), key)
        verification = implementation["postgres_compatibility"]["verification_record"]
        self.assertEqual("passed", verification["status"])
        self.assertEqual(0, verification["exit_code"])
        self.assertEqual(4, verification["runner_totals"]["surefire"]["tests"])
        self.assertEqual(2, verification["runner_totals"]["failsafe"]["tests"])

    def test_05_final_runtime_acceptance_control_plane_and_handoff(self):
        contract = self.acceptance
        if os.environ.get("TI_PHASE4B_CATEGORY_PREFINAL_ACCEPTANCE") == "1":
            token = os.environ.get("TI_PHASE4B_CATEGORY_PREFINAL_LOCK_TOKEN", "")
            self.assertRegex(token, r"^[0-9a-f]{64}$")
            lock = TI_JAVA_ROOT / "server" / "target" / (
                "phase4b-category-independent-acceptance.lock"
            )
            self.assertTrue(lock.is_dir())
            self.assertFalse(lock.is_symlink())
            owner = lock / "owner-token"
            self.assertTrue(owner.is_file())
            self.assertFalse(owner.is_symlink())
            self.assertEqual(token, owner.read_text(encoding="utf-8").strip())
            self.assertEqual("pending", contract["status"])
            self.assertFalse(contract["category_closure"]["category_internal_read_closed"])
            self.assertFalse(contract["final_control_plane"]["passed"])
            return

        self.assertEqual("passed", contract["status"])
        self.assertRegex(contract["captured_at"], r"^2026-07-\d\dT\d\d:\d\d:\d\dZ$")
        category = contract["category_acceptance"]
        self.assertTrue(category["passed"])
        self.assertFalse(category["http_aliases_migrated"])
        self.assertFalse(category["production_cutover"])
        self.assertEqual(
            {"surefire": 424, "failsafe": 60, "failures": 0, "errors": 0, "skipped": 0},
            category["maven"],
        )

        for name in ("contract_parity_test", "worm", "independent_acceptance_runner"):
            reference = contract["source_contracts"][name]
            source = (PHASE4B_ROOT / reference["source"]).resolve()
            self.assertTrue(source.is_file(), name)
            self.assertRegex(reference["sha256"], r"^[0-9a-f]{64}$")
            if name in {"contract_parity_test", "independent_acceptance_runner"}:
                if name == "contract_parity_test":
                    successor = self.all_shares_read_contract["implementation"]
                    successor_name = "category_contract_forward_handoff_test"
                else:
                    successor = self.share_read_contract["implementation"]
                    successor_name = "independent_acceptance_runner"
                self.assertEqual(
                    source.relative_to(TI_JAVA_ROOT).as_posix(),
                    successor["verification_source_files"][successor_name],
                )
                self.assertEqual(
                    successor["verification_source_sha256"][successor_name],
                    sha256(source),
                    name,
                )
                self.assertNotEqual(reference["sha256"], sha256(source), name)
            else:
                self.assertEqual(reference["sha256"], sha256(source), name)

        worm = contract["worm_acceptance"]
        worm_reference = contract["source_contracts"]["worm"]
        worm_document = load_json((PHASE4B_ROOT / worm_reference["source"]).resolve())
        self.assertTrue(worm["passed"])
        self.assertEqual("18.4", worm["postgresql"])
        self.assertEqual(70, worm["public_base_tables"])
        self.assertEqual(617, worm["public_columns"])
        self.assertTrue(worm["read_only_acl_passed"])
        self.assertTrue(worm["hibernate_validate_passed"])
        self.assertTrue(worm["startup_passed"])
        self.assertTrue(worm["readiness_passed"])
        self.assertEqual(worm["captured_at"], worm_document["capturedAt"])
        self.assertEqual(worm["postgresql"], worm_document["restore"]["serverVersion"])
        self.assertEqual(
            worm["public_base_tables"], worm_document["restore"]["publicBaseTables"]
        )
        self.assertEqual(worm["public_columns"], worm_document["restore"]["publicColumns"])
        self.assertTrue(all((
            worm_document["readRole"]["selectPassed"],
            worm_document["readRole"]["defaultTransactionReadOnly"],
            worm_document["readRole"]["aclVerifiedWithReadOnlyDefaultDisabled"],
            worm_document["readRole"]["insertRejected"],
            worm_document["readRole"]["updateRejected"],
            worm_document["readRole"]["deleteRejected"],
            worm_document["readRole"]["ddlRejected"],
            worm_document["readRole"]["temporaryDdlRejected"],
        )))
        self.assertFalse(worm_document["readRole"]["temporaryPrivilege"])
        self.assertEqual("validate", worm_document["java"]["hibernateDdlAuto"])
        self.assertEqual(worm["startup_passed"], worm_document["java"]["startupPassed"])
        self.assertEqual(worm["readiness_passed"], worm_document["java"]["readinessPassed"])
        self.assertEqual(
            worm["build_context_sha256"], worm_document["java"]["buildContextSha256"]
        )
        self.assertEqual(worm_reference["sha256"], worm["report_sha256"])
        self.assertEqual(
            worm["production_database_version"],
            worm_document["productionDatabaseVersion"],
        )
        self.assertEqual(
            worm["flyway_baseline_created"], worm_document["flywayBaselineCreated"]
        )

        raw = contract["independent_full_acceptance"]
        self.assertTrue(raw["passed"])
        self.assertEqual("phase4b-category-prefinal-independent-copy", raw["scope"])
        self.assertEqual(raw["source_manifest_sha256"], raw["copy_manifest_sha256"])
        self.assertTrue(raw["source_equals_copy"])
        self.assertEqual(0, raw["symlink_count"])
        self.assertEqual(0, raw["forbidden_artifact_count"])
        self.assertEqual(0, raw["forbidden_jar_count"])
        self.assertEqual(category["source_tool_tests"], raw["source_tool_tests"])
        self.assertEqual(1, raw["deferred_final_contract_assertion_groups"])
        self.assertTrue(raw["final_contract_closure_deferred"])
        self.assertEqual(36, raw["miniprogram_node_tests"])
        self.assertGreaterEqual(raw["maven_attempts"], 1)
        self.assertLessEqual(raw["maven_attempts"], raw["maven_max_attempts"])
        self.assertEqual(3, raw["maven_max_attempts"])
        self.assertEqual(category["maven"], raw["maven"])
        self.assertEqual(RAW_CHECK_KEYS, set(raw["checks"]))
        self.assertTrue(all(raw["checks"].values()))
        self.assertEqual(RAW_CLEANUP_KEYS, set(raw["cleanup"]))
        self.assertTrue(all(value == 0 for value in raw["cleanup"].values()))
        self.assertFalse(raw["raw_report_tracked"])
        self.assertFalse(raw["production_cutover"])
        self.assertRegex(raw["raw_report_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(
            [ACCEPTANCE_RELATIVE], raw["non_recursive_manifest_excluded_paths"]
        )
        self.assertEqual(1, raw["non_recursive_manifest_excluded_file_count"])
        self.assertTrue(raw["source_non_recursive_equals_copy"])
        local_report = (TI_JAVA_ROOT / raw["ignored_local_raw_report"]).resolve()
        self.assertEqual((TI_JAVA_ROOT / "server" / "target").resolve(), local_report.parent)
        if local_report.is_file():
            self.assertEqual(raw["raw_report_sha256"], sha256(local_report))
            raw_document = load_json(local_report)
            independent = raw_document["independentCopy"]
            source_tools = raw_document["sourceTools"]
            self.assertEqual("passed", raw_document["status"])
            self.assertEqual(raw["scope"], raw_document["scope"])
            self.assertEqual(raw["captured_at"], raw_document["capturedAt"])
            self.assertFalse(raw_document["productionCutover"])
            self.assertEqual(raw["controlled_file_count"], independent["controlledFileCount"])
            self.assertEqual(
                raw["source_manifest_sha256"], independent["sourceManifestSha256"]
            )
            self.assertEqual(
                raw["copy_manifest_sha256"], independent["copyManifestSha256"]
            )
            self.assertEqual(
                raw["source_non_recursive_manifest_sha256"],
                independent["sourceNonRecursiveManifestSha256"],
            )
            self.assertEqual(
                raw["copy_non_recursive_manifest_sha256"],
                independent["copyNonRecursiveManifestSha256"],
            )
            self.assertEqual(raw["source_tool_tests"], source_tools["tests"])
            self.assertEqual(
                raw["deferred_final_contract_assertion_groups"],
                source_tools["deferredFinalContractAssertionGroups"],
            )
            self.assertEqual(
                raw["final_contract_closure_deferred"],
                source_tools["finalContractClosureDeferred"],
            )
            self.assertEqual(raw["build_context_sha256"], independent["buildContextSha256"])
            self.assertEqual(raw["maven_attempts"], independent["mavenAttempts"])
            self.assertEqual(raw["maven_max_attempts"], independent["mavenMaxAttempts"])

        total, included, manifest = canonical_control_manifest()
        control = contract["final_control_plane"]
        self.assertTrue(control["passed"])
        self.assertEqual(1, control["manifest_excluded_file_count"])
        self.assertTrue(control["source_equals_copy"])
        if SHARE_ENTRY_PATH.is_file():
            downstream = load_json(SHARE_ENTRY_PATH)
            self.assertEqual(
                sha256(ACCEPTANCE_PATH), downstream["predecessor"]["sha256"]
            )
            self.assertEqual(
                "docs/refactor/phase4b/personal-bank-category-acceptance.json",
                downstream["predecessor"]["source"],
            )
            self.assertTrue(downstream["entry_gate"]["passed"])
            self.assertEqual(SHARE_ROUTE_KEYS, set(
                downstream["authorized_slice"]["only_operation_keys"]
            ))
            self.assertGreater(total, control["controlled_file_count"])
            self.assertGreater(included, control["manifest_included_file_count"])
            self.assertNotEqual(manifest, control["source_manifest_sha256"])
        else:
            self.assertEqual(total, control["controlled_file_count"])
            self.assertEqual(included, control["manifest_included_file_count"])
            self.assertEqual(manifest, control["source_manifest_sha256"])
            self.assertEqual(manifest, control["copy_manifest_sha256"])
            self.assertEqual(total, raw["controlled_file_count"])
            self.assertEqual(
                included, raw["non_recursive_manifest_included_file_count"]
            )
            self.assertEqual(
                manifest, raw["source_non_recursive_manifest_sha256"]
            )
            self.assertEqual(
                manifest, raw["copy_non_recursive_manifest_sha256"]
            )
        self.assertEqual(worm["build_context_sha256"], raw["build_context_sha256"])
        self.assertEqual(worm["build_context_sha256"], control["java_build_context_sha256"])

        status = contract["effective_status"]
        self.assertEqual(
            {
                "expanded_operation_count": 611,
                "migrated": 11,
                "pending": 600,
                "production_cutover": 0,
                "effective_resource_count": 159,
                "resources_with_exactly_one_owner": 159,
            },
            status,
        )
        closure = contract["category_closure"]
        self.assertTrue(closure["contract_and_implementation_passed"])
        self.assertTrue(closure["worm_acceptance_passed"])
        self.assertTrue(closure["independent_full_acceptance_passed"])
        self.assertTrue(closure["final_control_plane_passed"])
        self.assertTrue(closure["category_internal_read_closed"])
        self.assertFalse(closure["http_aliases_migrated"])
        self.assertFalse(closure["production_cutover"])

        handoff = contract["authorized_next_slice"]
        self.assertEqual("4B", handoff["phase"])
        self.assertEqual("personalbank", handoff["module"])
        self.assertEqual("personal bank share list aliases", handoff["capability"])
        self.assertEqual("implementation_and_parity_evidence_only", handoff["scope"])
        self.assertEqual(SHARE_ROUTE_KEYS, set(handoff["only_operation_keys"]))
        self.assertEqual(
            SHARE_ENTRY_PREREQUISITES,
            set(handoff["required_before_implementation"]),
        )
        self.assertEqual(
            "owner_status_probe_then_share_list",
            handoff["legacy_query_shape_to_preserve"],
        )
        self.assertFalse(handoff["route_openapi_delta_authorized"])
        self.assertFalse(handoff["production_cutover_authorized"])

        with (TI_JAVA_ROOT / "docs" / "refactor" / "02-route-parity-matrix.csv").open(
            "r", encoding="utf-8", newline=""
        ) as handle:
            rows = {
                row["route_id"]: row
                for row in csv.DictReader(handle)
                if row["route_id"] in {key.split("|", 1)[0] for key in SHARE_ROUTE_KEYS}
            }
        self.assertEqual(
            {key.split("|", 1)[0] for key in SHARE_ROUTE_KEYS},
            set(rows),
        )
        for row in rows.values():
            self.assertEqual("GET", row["methods"])
            self.assertEqual("personalbank", row["target_module"])
            self.assertEqual("pending", row["migration_status"])


if __name__ == "__main__":
    unittest.main()
