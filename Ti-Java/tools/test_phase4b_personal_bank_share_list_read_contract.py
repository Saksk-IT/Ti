#!/usr/bin/env python3
"""Fail-closed parity for the implemented Phase 4B personal-bank share list."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import pathlib
import re
import subprocess
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = ROOT.parent
PHASE4B = ROOT / "docs" / "refactor" / "phase4b"
CONTRACT_PATH = PHASE4B / "personal-bank-share-list-read-contract.json"
CONTRACT_RELATIVE = "docs/refactor/phase4b/personal-bank-share-list-read-contract.json"
ALL_SHARES_ENTRY_PATH = PHASE4B / "personal-bank-all-shares-entry-contract.json"
ALL_SHARES_ENTRY_RELATIVE = (
    "docs/refactor/phase4b/personal-bank-all-shares-entry-contract.json"
)
ALL_SHARES_READ_PATH = PHASE4B / "personal-bank-all-shares-read-contract.json"
ALL_SHARES_ROUTE_KEYS = {
    "a6fda3638fc3|GET|/api/user/banks/api/shares/all",
    "0fdd3026f636|GET|/user/banks/api/shares/all",
}
USAGE_STATS_ENTRY_PATH = PHASE4B / "personal-bank-usage-stats-entry-contract.json"
USAGE_STATS_ENTRY_RELATIVE = (
    "docs/refactor/phase4b/personal-bank-usage-stats-entry-contract.json"
)
USAGE_STATS_ROUTE_KEYS = {
    "d67a16965b08|GET|/api/user/banks/api/<int:bank_id>/usage-stats",
    "22aecd49a3c2|GET|/user/banks/api/<int:bank_id>/usage-stats",
}
USAGE_STATS_FORWARD_ADDITIONS = {
    f"Ti-Java/{USAGE_STATS_ENTRY_RELATIVE}",
    "Ti-Java/docs/refactor/phase4b/golden-personal-bank-usage-stats-reads.json",
    "Ti-Java/docs/refactor/phase4b/personal-bank-usage-stats-callers.json",
    (
        "Ti-Java/docs/refactor/phase4b/"
        "personal-bank-usage-stats-query-plan-evidence.json"
    ),
    (
        "Ti-Java/server/src/test/java/io/saksk/ti/integration/"
        "Phase4bPersonalBankUsageStatsEvidenceJdbcCompatibilityIT.java"
    ),
    (
        "Ti-Java/server/src/test/java/io/saksk/ti/personalbank/infrastructure/"
        "persistence/PersonalBankUsageStatsEvidenceSql.java"
    ),
    (
        "Ti-Java/server/src/test/java/io/saksk/ti/personalbank/infrastructure/"
        "persistence/PersonalBankUsageStatsEvidenceSqlContractTest.java"
    ),
    (
        "Ti-Java/server/src/test/java/io/saksk/ti/personalbank/infrastructure/"
        "persistence/PersonalBankUsageStatsEvidenceSqlManifestTest.java"
    ),
    "Ti-Java/server/src/test/resources/db/phase4b/065-personal-bank-usage-stats-schema.sql",
    "Ti-Java/server/src/test/resources/db/phase4b/066-personal-bank-usage-stats-seed.sql",
    "Ti-Java/tools/capture_phase4b_personal_bank_usage_stats_callers.py",
    "Ti-Java/tools/capture_phase4b_personal_bank_usage_stats_goldens.py",
    "Ti-Java/tools/capture_phase4b_personal_bank_usage_stats_query_plans.py",
    "Ti-Java/tools/test_capture_phase4b_personal_bank_usage_stats_callers.py",
    "Ti-Java/tools/test_capture_phase4b_personal_bank_usage_stats_goldens.py",
    "Ti-Java/tools/test_capture_phase4b_personal_bank_usage_stats_query_plans.py",
    "Ti-Java/tools/test_phase4b_personal_bank_usage_stats_entry_contract.py",
}
ALL_SHARES_FORWARD_ADDITIONS = {
    f"Ti-Java/{ALL_SHARES_ENTRY_RELATIVE}",
    "Ti-Java/docs/refactor/phase4b/golden-personal-bank-all-shares-reads.json",
    "Ti-Java/docs/refactor/phase4b/personal-bank-all-shares-callers.json",
    "Ti-Java/docs/refactor/phase4b/personal-bank-all-shares-query-plan-evidence.json",
    (
        "Ti-Java/server/src/test/java/io/saksk/ti/integration/"
        "Phase4bPersonalBankAllSharesEvidenceJdbcCompatibilityIT.java"
    ),
    (
        "Ti-Java/server/src/test/java/io/saksk/ti/personalbank/infrastructure/"
        "persistence/PersonalBankAllSharesEvidenceSql.java"
    ),
    (
        "Ti-Java/server/src/test/java/io/saksk/ti/personalbank/infrastructure/"
        "persistence/PersonalBankAllSharesEvidenceSqlContractTest.java"
    ),
    (
        "Ti-Java/server/src/test/java/io/saksk/ti/personalbank/infrastructure/"
        "persistence/PersonalBankAllSharesEvidenceSqlManifestTest.java"
    ),
    "Ti-Java/server/src/test/resources/db/phase4b/064-personal-bank-all-shares-seed.sql",
    "Ti-Java/tools/capture_phase4b_personal_bank_all_shares_callers.py",
    "Ti-Java/tools/capture_phase4b_personal_bank_all_shares_goldens.py",
    "Ti-Java/tools/capture_phase4b_personal_bank_all_shares_query_plans.py",
    "Ti-Java/tools/test_capture_phase4b_personal_bank_all_shares_callers.py",
    "Ti-Java/tools/test_capture_phase4b_personal_bank_all_shares_goldens.py",
    "Ti-Java/tools/test_capture_phase4b_personal_bank_all_shares_query_plans.py",
    "Ti-Java/tools/test_phase4b_personal_bank_all_shares_entry_contract.py",
}
SHARE_READ_FORWARD_TEST_RELATIVE = (
    "tools/test_phase4b_personal_bank_share_list_read_contract.py"
)
SHARE_READ_JAVA_PARITY_RELATIVE = (
    "server/src/test/java/io/saksk/ti/architecture/"
    "PersonalBankShareListContractParityTest.java"
)
SHARE_READ_JAVA_PARITY_HISTORICAL_SHA256 = (
    "b37147f2f1fc0bd4dbe7582d5457026e46d0e5ee323eb8b1480325eca8658fdb"
)
PHASE3_AUTH_TIME_TEST_RELATIVE = (
    "server/src/test/java/io/saksk/ti/integration/Phase3AuthenticationIT.java"
)
PHASE3_AUTH_TIME_TEST_HISTORICAL_SHA256 = (
    "059abbf9fdf6d07acf4aebef55a6da1705f66142e4daea77ac093553441d0c76"
)
PROGRESS_FORWARD_HANDOFF_RELATIVE = "docs/refactor/05-progress.md"
PROGRESS_HISTORICAL_SHA256 = (
    "89fa432fba5b793b002cc034dda4c7a92a666e0b871c1ef744ed0d90a55b7e63"
)
ROUTE_KEYS = {
    "e817f8083d74|GET|/api/user/banks/api/<int:bank_id>/shares",
    "c50102968322|GET|/user/banks/api/<int:bank_id>/shares",
}
EXPECTED_COMPONENTS = [
    ("id", "int", False),
    ("bankId", "int", False),
    ("ownerId", "long", False),
    ("shareCode", "java.lang.String", True),
    ("shareToken", "java.lang.String", True),
    ("permission", "java.lang.String", True),
    ("expiresAt", "java.time.LocalDateTime", True),
    ("maxUses", "java.lang.Integer", True),
    ("currentUses", "java.lang.Integer", True),
    ("isActive", "java.lang.Boolean", True),
    ("createdAt", "java.time.LocalDateTime", True),
]


def load_json(path: pathlib.Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_control_manifest(
        forward_additions: set[str] | None = None,
        historical_hash_overrides: dict[str, str] | None = None,
) -> tuple[int, int, str]:
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
    forward_additions = forward_additions or set()
    historical_hash_overrides = historical_hash_overrides or {}
    self_path = f"Ti-Java/{CONTRACT_RELATIVE}"
    missing = forward_additions - set(controlled)
    if missing:
        raise AssertionError(f"missing forward-controlled paths: {sorted(missing)}")
    historical_controlled = [
        relative for relative in controlled if relative not in forward_additions
    ]
    excluded = self_path
    if historical_controlled.count(excluded) != 1:
        raise AssertionError("read contract must be the sole explicit exclusion")
    included = []
    for relative in historical_controlled:
        path = REPOSITORY_ROOT / relative
        if path.is_symlink() or not path.is_file():
            raise AssertionError(f"invalid controlled path: {relative}")
        if relative == excluded:
            continue
        included.append({
            "path": relative.removeprefix("Ti-Java/"),
            "sha256": historical_hash_overrides.get(
                relative.removeprefix("Ti-Java/"), sha256(path)
            ),
        })
    payload = (json.dumps(
        included,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ) + "\n").encode()
    return (
        len(historical_controlled),
        len(included),
        hashlib.sha256(payload).hexdigest(),
    )


class Phase4bPersonalBankShareListReadContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = load_json(CONTRACT_PATH)
        cls.entry = load_json(PHASE4B / "personal-bank-share-list-entry-contract.json")
        cls.shape = load_json(
            PHASE4B / "personal-bank-share-list-application-api-shape.json"
        )
        cls.golden = load_json(
            PHASE4B / "golden-personal-bank-share-list-reads.json"
        )
        cls.plan = load_json(
            PHASE4B / "personal-bank-share-list-query-plan-evidence.json"
        )
        cls.openapi = load_json(ROOT / "contracts" / "openapi.json")
        cls.terminal = load_json(ALL_SHARES_READ_PATH)
        cls.usage_stats_entry = load_json(USAGE_STATS_ENTRY_PATH)

    def test_01_predecessor_shape_golden_and_plan_are_transitively_bound(self):
        contract = self.contract
        self.assertEqual(
            "ti.phase4b.personal-bank-share-list-read-contract",
            contract["contract_id"],
        )
        self.assertEqual(1, contract["schema_version"])
        self.assertEqual(
            "implemented_and_targeted_verified_http_aliases_deferred",
            contract["status"],
        )
        self.assertEqual(
            sha256(PHASE4B / contract["predecessor"]["source"]),
            contract["predecessor"]["sha256"],
        )
        self.assertTrue(self.entry["entry_gate"]["passed"])
        self.assertFalse(self.entry["implementation_state"]["implementation_started"])

        evidence = contract["evidence"]
        for key in ("application_api_shape", "golden", "query_plan"):
            reference = evidence[key]
            self.assertEqual(
                reference["sha256"], sha256(PHASE4B / reference["source"]), key
            )
        self.assertEqual(40, self.golden["case_count"])
        self.assertEqual(
            4,
            sum(len(engine["observations"]) for engine in self.plan["engines"]),
        )
        self.assertEqual(["16.14", "18.4"], [
            engine["server_version"] for engine in self.plan["engines"]
        ])

        worm = contract["worm_verification"]
        worm_path = PHASE4B / worm["source"]
        self.assertEqual(worm["sha256"], sha256(worm_path))
        worm_document = load_json(worm_path)
        self.assertEqual(worm["captured_at"], worm_document["capturedAt"])
        self.assertEqual(worm["postgresql"], worm_document["restore"]["serverVersion"])
        self.assertEqual(
            worm["public_base_tables"], worm_document["restore"]["publicBaseTables"]
        )
        self.assertEqual(
            worm["public_columns"], worm_document["restore"]["publicColumns"]
        )
        self.assertEqual(
            worm["build_context_sha256"],
            worm_document["java"]["buildContextSha256"],
        )
        self.assertTrue(worm["passed"])
        self.assertFalse(worm["schema_dump_persisted"])

    def test_02_cumulative_shape_adds_only_the_internal_share_method(self):
        shape = self.shape
        self.assertEqual(11, shape["migrated_route_count"])
        self.assertEqual(11, shape["implemented_route_backed_operation_count"])
        self.assertEqual(21, shape["implemented_public_application_method_count"])
        self.assertEqual(600, shape["pending_route_count"])
        self.assertEqual(0, shape["production_cutover_count"])
        personalbank = shape["personalbank"]
        self.assertEqual(["listCategories", "findShares"], [
            method["name"] for method in personalbank["methods"]
        ])
        self.assertEqual([], personalbank["implemented_route_ids"])
        self.assertFalse(personalbank["direct_http_operation"])
        self.assertEqual(
            {"e817f8083d74", "c50102968322"},
            set(personalbank["deferred_share_list_http_route_ids"]),
        )

    def test_03_all_implementation_and_verification_source_hashes_match(self):
        implementation = self.contract["implementation"]
        for files_key, hashes_key in (
            ("main_source_files", "main_source_sha256"),
            ("verification_source_files", "verification_source_sha256"),
        ):
            files = implementation[files_key]
            hashes = implementation[hashes_key]
            self.assertEqual(set(files), set(hashes))
            for name, relative in files.items():
                path = ROOT / relative
                self.assertTrue(path.is_file(), name)
                current_hash = sha256(path)
                terminal_name = None
                if files_key == "main_source_files" and name in {
                        "application_api", "application_service"
                }:
                    terminal_name = name
                elif files_key == "verification_source_files" and name in {
                        "service_test",
                        "entry_forward_handoff_test",
                        "category_acceptance_forward_handoff_test",
                        "category_golden_forward_handoff_test",
                        "category_contract_forward_handoff_test",
                        "share_read_contract_test",
                }:
                    terminal_name = {
                        "entry_forward_handoff_test":
                            "share_list_entry_forward_handoff_test",
                    }.get(name, name)
                if terminal_name is not None:
                    terminal_files = self.terminal["implementation"][files_key]
                    terminal_hashes = self.terminal["implementation"][hashes_key]
                    self.assertEqual(relative, terminal_files[terminal_name])
                    if name == "share_read_contract_test":
                        usage_handoff = self.usage_stats_entry["source_contracts"][
                            "share_list_read_transitive_forward_handoff_test"
                        ]
                        self.assertEqual(relative, usage_handoff["source"])
                        self.assertEqual(current_hash, usage_handoff["sha256"])
                        self.assertNotEqual(
                            current_hash, terminal_hashes[terminal_name]
                        )
                    else:
                        self.assertEqual(current_hash, terminal_hashes[terminal_name])
                    self.assertNotEqual(hashes[name], current_hash)
                    if name == "share_read_contract_test":
                        handoff = load_json(ALL_SHARES_ENTRY_PATH)["source_contracts"][
                            "share_list_read_forward_handoff_test"
                        ]
                        self.assertEqual(relative, handoff["source"])
                        self.assertNotEqual(current_hash, handoff["sha256"])
                        self.assertNotEqual(hashes[name], handoff["sha256"])
                else:
                    self.assertEqual(hashes[name], current_hash, name)

    def test_04_api_dto_optional_and_immutability_shapes_are_exact(self):
        application = self.contract["application_contract"]
        self.assertEqual(
            "Optional<PersonalBankShareListView> findShares("
            "AuthenticatedPersonalBankViewer viewer, int bankId)",
            application["method"],
        )
        self.assertEqual("Optional.empty", application["unavailable"])
        self.assertIn("immutable empty shares", application["available_empty"])
        self.assertFalse(application["bank_id_positive_validation"])
        self.assertEqual("long", application["viewer_identity_type"])
        self.assertEqual("List.copyOf", application["share_list_collection"])
        self.assertEqual(EXPECTED_COMPONENTS, [
            (item["name"], item["java_type"], item["nullable"])
            for item in self.contract["share_record_components"]
        ])

    def test_05_two_exact_queries_keep_short_circuit_binds_and_raw_order(self):
        persistence = self.contract["persistence_contract"]
        self.assertEqual(
            "SELECT id\nFROM user_question_banks\nWHERE id = :bank_id\n"
            "  AND user_id = :viewer_id\n  AND status = 1\n",
            persistence["owner_probe_sql"],
        )
        self.assertEqual(
            "SELECT id,\n       bank_id,\n       owner_id,\n       share_code,\n"
            "       share_token,\n       permission,\n       expires_at,\n"
            "       max_uses,\n       current_uses,\n       is_active,\n"
            "       created_at\nFROM bank_shares\nWHERE bank_id = :bank_id\n"
            "ORDER BY created_at DESC NULLS FIRST\n",
            persistence["share_list_sql"],
        )
        self.assertEqual(
            {"bank_id": "integer", "viewer_id": "bigint"},
            persistence["bind_types"],
        )
        self.assertTrue(persistence["sequential_execution"])
        self.assertFalse(persistence["second_query_on_probe_miss"])
        for key in (
            "exceptions_translated",
            "join_or_parallelization",
            "java_secondary_sorting",
            "extra_filters",
            "pagination",
            "schema_or_index_delta",
        ):
            self.assertFalse(persistence[key], key)

    def test_06_routes_and_openapi_remain_pending_inferred_and_opaque(self):
        route_state = self.contract["route_state"]
        self.assertEqual(11, route_state["migrated_route_count"])
        self.assertEqual(600, route_state["pending_route_count"])
        self.assertEqual(0, route_state["production_cutover_count"])
        actual_keys = {
            f'{item["route_id"]}|{item["method"]}|{item["path"]}'
            for item in route_state["operations"]
        }
        self.assertEqual(ROUTE_KEYS, actual_keys)

        with (ROOT / "docs/refactor/02-route-parity-matrix.csv").open(
            newline="", encoding="utf-8"
        ) as handle:
            rows = list(csv.DictReader(handle))
        selected = {
            row["route_id"]: row for row in rows
            if row["route_id"] in {key.split("|", 1)[0] for key in ROUTE_KEYS}
        }
        self.assertEqual(2, len(selected))
        self.assertTrue(all(row["migration_status"] == "pending" for row in selected.values()))
        self.assertTrue(all(row["target_module"] == "personalbank" for row in selected.values()))

        for item in route_state["operations"]:
            path = item["path"].replace("<int:bank_id>", "{bank_id}")
            operation = self.openapi["paths"][path]["get"]
            self.assertEqual("pending", operation["x-ti-migration"]["status"])
            self.assertEqual("personalbank", operation["x-ti-migration"]["targetModule"])
            self.assertEqual("inferred", operation["x-ti-contract-maturity"])
            self.assertEqual(
                "#/components/schemas/LegacyOpaquePayload",
                operation["responses"]["default"]["content"]["*/*"]
                ["schema"]["$ref"],
            )

    def test_07_no_forbidden_scope_was_smuggled_into_the_internal_slice(self):
        self.assertTrue(self.contract["targeted_verification"]["passed"])
        self.assertTrue(all(
            value is False for value in self.contract["forbidden_scope"].values()
        ))
        source_root = ROOT / "server/src/main/java/io/saksk/ti/personalbank"
        combined = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted(source_root.rglob("*.java"))
        )
        for forbidden in (
            "@RestController",
            "@Controller",
            "@GetMapping",
            "@RequestMapping",
            "ResponseEntity",
            "SecurityFilterChain",
            "shareLink",
            "Comparator",
            ".sorted(",
            "CREATE INDEX",
        ):
            self.assertNotIn(forbidden, combined)
        self._assert_final_acceptance()

    def _assert_final_acceptance(self):
        final = self.contract["final_acceptance"]
        integrity = final["integrity_policy"]
        self.assertEqual("sha256", integrity["algorithm"])
        self.assertIsNone(integrity["self_hash"])
        self.assertEqual(
            [CONTRACT_RELATIVE],
            integrity["controlled_manifest_excluded_paths"],
        )
        self.assertEqual(284, final["source_tool_tests"])
        self.assertEqual(
            {
                "surefire": 446,
                "failsafe": 64,
                "failures": 0,
                "errors": 0,
                "skipped": 0,
            },
            final["maven"],
        )

        if os.environ.get("TI_PHASE4B_SHARE_LIST_PREFINAL_ACCEPTANCE") == "1":
            token = os.environ.get(
                "TI_PHASE4B_SHARE_LIST_PREFINAL_LOCK_TOKEN", ""
            )
            self.assertRegex(token, r"^[0-9a-f]{64}$")
            lock = ROOT / "server" / "target" / (
                "phase4b-share-list-independent-acceptance.lock"
            )
            self.assertTrue(lock.is_dir())
            self.assertFalse(lock.is_symlink())
            owner = lock / "owner-token"
            self.assertTrue(owner.is_file())
            self.assertFalse(owner.is_symlink())
            self.assertEqual(token, owner.read_text(encoding="utf-8").strip())
            self.assertEqual("pending", final["status"])
            self.assertFalse(final["passed"])
            self.assertTrue(self.contract["next_gate"]["independent_extraction_required"])
            return

        self.assertEqual("passed", final["status"])
        self.assertTrue(final["passed"])
        self.assertRegex(final["captured_at"], r"^2026-07-\d\dT\d\d:\d\d:\d\dZ$")
        self.assertFalse(self.contract["next_gate"]["independent_extraction_required"])

        independent = final["independent_copy"]
        self.assertTrue(independent["passed"])
        self.assertEqual(
            "phase4b-share-list-prefinal-independent-copy",
            independent["scope"],
        )
        self.assertEqual(
            independent["source_manifest_sha256"],
            independent["copy_manifest_sha256"],
        )
        self.assertTrue(independent["source_equals_copy"])
        self.assertEqual(
            [CONTRACT_RELATIVE],
            independent["non_recursive_manifest_excluded_paths"],
        )
        self.assertEqual(1, independent["non_recursive_manifest_excluded_file_count"])
        self.assertTrue(independent["source_non_recursive_equals_copy"])
        self.assertEqual(284, independent["source_tool_tests"])
        self.assertEqual(final["maven"], independent["maven"])
        self.assertEqual(
            self.contract["worm_verification"]["build_context_sha256"],
            independent["build_context_sha256"],
        )
        self.assertEqual(36, independent["miniprogram_node_tests"])
        self.assertEqual(0, independent["symlink_count"])
        self.assertEqual(0, independent["forbidden_artifact_count"])
        self.assertEqual(0, independent["forbidden_jar_count"])
        self.assertTrue(all(independent["checks"].values()))
        self.assertTrue(all(value == 0 for value in independent["cleanup"].values()))
        self.assertFalse(independent["raw_report_tracked"])
        self.assertFalse(independent["production_cutover"])
        self.assertRegex(independent["raw_report_sha256"], r"^[0-9a-f]{64}$")

        local_report = (ROOT / independent["ignored_local_raw_report"]).resolve()
        self.assertEqual((ROOT / "server" / "target").resolve(), local_report.parent)
        if local_report.is_file():
            self.assertEqual(independent["raw_report_sha256"], sha256(local_report))
            raw = load_json(local_report)
            self.assertEqual("passed", raw["status"])
            self.assertEqual(independent["scope"], raw["scope"])
            self.assertEqual(independent["captured_at"], raw["capturedAt"])
            self.assertFalse(raw["productionCutover"])
            raw_copy = raw["independentCopy"]
            self.assertEqual(
                independent["controlled_file_count"],
                raw_copy["controlledFileCount"],
            )
            self.assertEqual(
                independent["source_manifest_sha256"],
                raw_copy["sourceManifestSha256"],
            )
            self.assertEqual(
                independent["source_non_recursive_manifest_sha256"],
                raw_copy["sourceNonRecursiveManifestSha256"],
            )
            self.assertEqual(
                independent["build_context_sha256"],
                raw_copy["buildContextSha256"],
            )
            self.assertEqual(284, raw["sourceTools"]["tests"])
            self.assertEqual(446, raw_copy["maven"]["surefire"]["tests"])
            self.assertEqual(64, raw_copy["maven"]["failsafe"]["tests"])

        forward_additions: set[str] = set()
        historical_hash_overrides: dict[str, str] = {}
        if ALL_SHARES_ENTRY_PATH.is_file():
            successor = load_json(ALL_SHARES_ENTRY_PATH)
            terminal = self.terminal
            self.assertEqual(
                "ti.phase4b.personal-bank-all-shares-entry-contract",
                successor["contract_id"],
            )
            self.assertEqual("entry_gate_passed_implementation_not_started", successor["status"])
            self.assertEqual(
                CONTRACT_RELATIVE, successor["predecessor"]["source"]
            )
            self.assertEqual(
                sha256(CONTRACT_PATH), successor["predecessor"]["sha256"]
            )
            self.assertEqual(
                ALL_SHARES_ROUTE_KEYS,
                set(successor["authorized_slice"]["only_operation_keys"]),
            )
            self.assertTrue(successor["entry_gate"]["implementation_authorized"])
            self.assertFalse(successor["entry_gate"]["http_migration_authorized"])
            self.assertEqual(
                "ti.phase4b.personal-bank-all-shares-read-contract",
                terminal["contract_id"],
            )
            self.assertEqual(
                ALL_SHARES_ENTRY_RELATIVE,
                terminal["predecessor"]["source"],
            )
            self.assertEqual(
                sha256(ALL_SHARES_ENTRY_PATH),
                terminal["predecessor"]["sha256"],
            )
            successor_sources = {
                f"Ti-Java/{reference['source']}"
                for reference in successor["source_contracts"].values()
            }
            self.assertEqual(
                ALL_SHARES_FORWARD_ADDITIONS - {
                    f"Ti-Java/{ALL_SHARES_ENTRY_RELATIVE}"
                },
                ALL_SHARES_FORWARD_ADDITIONS.intersection(successor_sources),
            )
            java_handoff = successor["source_contracts"][
                "share_list_java_forward_handoff_test"
            ]
            self.assertEqual(SHARE_READ_JAVA_PARITY_RELATIVE, java_handoff["source"])
            self.assertNotEqual(
                sha256(ROOT / SHARE_READ_JAVA_PARITY_RELATIVE), java_handoff["sha256"]
            )
            current_java_hash = sha256(ROOT / SHARE_READ_JAVA_PARITY_RELATIVE)
            terminal_java_hash = terminal["implementation"][
                "verification_source_sha256"
            ]["share_list_contract_parity_test"]
            if USAGE_STATS_ENTRY_PATH.is_file():
                transitive_java_handoff = self.usage_stats_entry[
                    "source_contracts"
                ]["share_list_java_transitive_forward_handoff_test"]
                self.assertEqual(
                    SHARE_READ_JAVA_PARITY_RELATIVE,
                    transitive_java_handoff["source"],
                )
                self.assertEqual(
                    current_java_hash, transitive_java_handoff["sha256"]
                )
                self.assertNotEqual(current_java_hash, terminal_java_hash)
            else:
                self.assertEqual(current_java_hash, terminal_java_hash)
            phase3_handoff = successor["source_contracts"][
                "phase3_auth_time_forward_handoff_test"
            ]
            self.assertEqual(PHASE3_AUTH_TIME_TEST_RELATIVE, phase3_handoff["source"])
            self.assertEqual(
                sha256(ROOT / PHASE3_AUTH_TIME_TEST_RELATIVE),
                phase3_handoff["sha256"],
            )
            progress_handoff = successor["source_contracts"][
                "progress_forward_handoff"
            ]
            self.assertEqual(
                PROGRESS_FORWARD_HANDOFF_RELATIVE,
                progress_handoff["source"],
            )
            current_progress_hash = sha256(
                ROOT / PROGRESS_FORWARD_HANDOFF_RELATIVE
            )
            terminal_progress_hash = terminal["implementation"][
                "verification_source_sha256"
            ]["progress_forward_handoff"]
            if USAGE_STATS_ENTRY_PATH.is_file():
                self.assertNotEqual(current_progress_hash, terminal_progress_hash)
            else:
                self.assertEqual(current_progress_hash, terminal_progress_hash)
            forward_additions = set(terminal["forward_handoff"]["forward_additions"])
            historical_hash_overrides = terminal["forward_handoff"][
                "historical_hash_overrides"
            ]

        if USAGE_STATS_ENTRY_PATH.is_file():
            successor = self.usage_stats_entry
            self.assertEqual(
                "ti.phase4b.personal-bank-usage-stats-entry-contract",
                successor["contract_id"],
            )
            self.assertEqual(
                "entry_gate_passed_implementation_not_started",
                successor["status"],
            )
            self.assertEqual(
                "docs/refactor/phase4b/personal-bank-all-shares-read-contract.json",
                successor["predecessor"]["source"],
            )
            self.assertEqual(
                sha256(ALL_SHARES_READ_PATH), successor["predecessor"]["sha256"]
            )
            self.assertEqual(
                USAGE_STATS_ROUTE_KEYS,
                set(successor["authorized_slice"]["only_operation_keys"]),
            )
            self.assertTrue(successor["entry_gate"]["implementation_authorized"])
            self.assertFalse(successor["entry_gate"]["http_migration_authorized"])
            self.assertFalse(
                successor["entry_gate"]["production_cutover_authorized"]
            )
            successor_sources = {
                f"Ti-Java/{reference['source']}"
                for reference in successor["source_contracts"].values()
            }
            self.assertEqual(
                USAGE_STATS_FORWARD_ADDITIONS - {
                    f"Ti-Java/{USAGE_STATS_ENTRY_RELATIVE}"
                },
                USAGE_STATS_FORWARD_ADDITIONS.intersection(successor_sources),
            )
            share_list_handoff = successor["source_contracts"][
                "share_list_read_transitive_forward_handoff_test"
            ]
            self.assertEqual(
                SHARE_READ_FORWARD_TEST_RELATIVE,
                share_list_handoff["source"],
            )
            self.assertEqual(
                sha256(ROOT / SHARE_READ_FORWARD_TEST_RELATIVE),
                share_list_handoff["sha256"],
            )
            share_list_java_handoff = successor["source_contracts"][
                "share_list_java_transitive_forward_handoff_test"
            ]
            self.assertEqual(
                SHARE_READ_JAVA_PARITY_RELATIVE,
                share_list_java_handoff["source"],
            )
            self.assertEqual(
                sha256(ROOT / SHARE_READ_JAVA_PARITY_RELATIVE),
                share_list_java_handoff["sha256"],
            )
            progress_handoff = successor["source_contracts"][
                "progress_forward_handoff"
            ]
            self.assertEqual(
                PROGRESS_FORWARD_HANDOFF_RELATIVE,
                progress_handoff["source"],
            )
            self.assertEqual(
                sha256(ROOT / PROGRESS_FORWARD_HANDOFF_RELATIVE),
                progress_handoff["sha256"],
            )
            forward_additions |= USAGE_STATS_FORWARD_ADDITIONS

        total, included, manifest = canonical_control_manifest(
            forward_additions,
            historical_hash_overrides,
        )
        control = final["final_control_plane"]
        self.assertTrue(control["passed"])
        self.assertEqual(total, control["controlled_file_count"])
        self.assertEqual(total - 1, included)
        self.assertEqual(1, control["manifest_excluded_file_count"])
        self.assertEqual(included, control["manifest_included_file_count"])
        self.assertEqual(manifest, control["source_manifest_sha256"])
        self.assertEqual(manifest, control["copy_manifest_sha256"])
        self.assertTrue(control["source_equals_copy"])
        self.assertEqual(
            independent["source_non_recursive_manifest_sha256"], manifest
        )
        self.assertEqual(
            independent["build_context_sha256"],
            control["java_build_context_sha256"],
        )
        self.assertTrue(control["java_build_context_matches_full_acceptance"])


if __name__ == "__main__":
    unittest.main()
