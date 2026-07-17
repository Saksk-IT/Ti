#!/usr/bin/env python3
"""Fail-closed checks for the Phase 4C HTTP-neutral user-counts read contract."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

try:
    from tools import build_phase4c_personal_bank_user_counts_read_contract as builder
    from tools.phase4c_read_successor_acceptance import (
        CONTRACT_ID,
        CONTRACT_STATUS,
        PREDECESSOR_SHA256,
        load_read_successor_contract,
        validate_read_successor_contract,
    )
except ModuleNotFoundError:  # Direct script execution from tools/.
    import build_phase4c_personal_bank_user_counts_read_contract as builder
    from phase4c_read_successor_acceptance import (
        CONTRACT_ID,
        CONTRACT_STATUS,
        PREDECESSOR_SHA256,
        load_read_successor_contract,
        validate_read_successor_contract,
    )


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = (
    ROOT / "docs/refactor/phase4c/personal-bank-user-counts-read-contract.json"
)
COMPOSITION_PATH = (
    ROOT / "docs/refactor/phase4c/"
    "personal-bank-user-counts-composition-contract.json"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def document_payload_sha256(document: dict) -> str:
    payload = {
        key: value for key, value in document.items()
        if key != "document_payload_sha256"
    }
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def junit_methods(path: Path) -> set[str]:
    return set(re.findall(
        r"@Test\s+(?:public\s+|private\s+|protected\s+)?void\s+"
        r"([A-Za-z0-9_]+)\s*\(",
        path.read_text(encoding="utf-8"),
    ))


class Phase4cPersonalBankUserCountsReadContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = load_read_successor_contract(ROOT)
        if cls.contract is None:
            raise AssertionError("Phase4C read contract is required")
        cls.composition = json.loads(COMPOSITION_PATH.read_text(encoding="utf-8"))
        cls.requirements = cls.composition["successor_handoff"][
            "future_read_contract_requirements"
        ]

    def test_01_identity_predecessor_payload_sources_and_determinism_close(self):
        contract = self.contract
        self.assertEqual(CONTRACT_ID, contract["contract_id"])
        self.assertEqual(CONTRACT_STATUS, contract["status"])
        self.assertEqual(1, contract["schema_version"])
        self.assertEqual(
            "phase4c-personal-bank-user-counts-http-neutral-read",
            contract["scope"],
        )
        self.assertEqual(PREDECESSOR_SHA256, sha256(COMPOSITION_PATH))
        self.assertEqual(PREDECESSOR_SHA256, contract["predecessor"]["sha256"])
        self.assertEqual(
            self.composition["contract_id"],
            contract["predecessor"]["contract_id"],
        )
        self.assertEqual(
            contract["document_payload_sha256"],
            document_payload_sha256(contract),
        )
        for name, reference in contract["source_contracts"].items():
            source = ROOT / reference["source"]
            self.assertTrue(source.is_file(), name)
            self.assertEqual(reference["sha256"], sha256(source), name)

        with tempfile.TemporaryDirectory(prefix="ti-phase4c-read-") as temporary:
            generated = Path(temporary) / "read-contract.json"
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/build_phase4c_personal_bank_user_counts_read_contract.py"),
                    "--output",
                    str(generated),
                ],
                cwd=ROOT,
                check=True,
            )
            self.assertEqual(CONTRACT_PATH.read_bytes(), generated.read_bytes())

    def test_02_exact_main_and_runtime_surface_delta_is_only_seventeen_plus_one(self):
        implementation = self.contract["implementation"]
        requirements = self.requirements
        self.assertTrue(implementation["http_neutral_java_implemented"])
        self.assertEqual(27, implementation["implemented_public_application_method_count"])
        self.assertEqual(["learning", "personalbank"], implementation["main_source_scope"])
        self.assertEqual(40, implementation["main_source_file_count"])
        self.assertEqual(
            set(requirements["expected_added_main_sources"]),
            set(implementation["added_main_sources"]),
        )
        self.assertEqual(
            set(requirements["expected_changed_main_sources"]),
            set(implementation["changed_main_sources"]),
        )
        self.assertEqual([], implementation["deleted_main_sources"])

        current_main = builder.main_source_manifest()
        self.assertEqual(
            current_main,
            implementation["learning_and_personalbank_main_source_manifest"],
        )
        self.assertEqual(
            builder.sha256_json(current_main),
            implementation["learning_and_personalbank_main_source_manifest_sha256"],
        )
        runtime = implementation["production_runtime_surface"]
        self.assertEqual(288, runtime["file_count"])
        self.assertEqual(builder.production_runtime_manifest(), runtime["files"])
        self.assertEqual(builder.sha256_json(runtime["files"]), runtime["manifest_sha256"])

    def test_03_exact_twenty_seven_method_shape_and_http_neutral_apis_close(self):
        methods = self.contract["implementation"]["public_application_methods"]
        self.assertEqual(27, len(methods))
        signatures = {
            (method["owner_api"], method["name"], tuple(method["parameter_types"]))
            for method in methods
        }
        self.assertEqual(27, len(signatures))
        self.assertIn((
            "io.saksk.ti.learning.api.LearningApplicationApi",
            "findPersonalBankUserCounts",
            (
                "io.saksk.ti.learning.api.AuthenticatedLearningViewer",
                "io.saksk.ti.learning.api.PersonalBankUserCountsQuery",
            ),
        ), signatures)
        self.assertIn((
            "io.saksk.ti.personalbank.api.PersonalBankQuestionFactsApi",
            "inspectQuestionMembership",
            ("int", "java.util.List"),
        ), signatures)
        self.assertEqual(4, sum(
            method["name"] in {
                "findPersonalBankUserCounts",
                "checkQuestionAccess",
                "summarizeQuestions",
                "inspectQuestionMembership",
            }
            for method in methods
        ))

        authorized = set(self.requirements["expected_added_main_sources"]) | set(
            self.requirements["expected_changed_main_sources"]
        )
        forbidden_tokens = (
            "@RestController",
            "@Controller",
            "SecurityFilterChain",
            "HttpSecurity",
            "@RequestMapping",
            "@GetMapping",
            "@PostMapping",
        )
        for relative in authorized:
            code = (ROOT / relative).read_text(encoding="utf-8")
            for token in forbidden_tokens:
                self.assertNotIn(token, code, relative)

    def test_04_required_named_verification_sources_and_behavior_are_fixed(self):
        implementation = self.contract["implementation"]
        self.assertEqual(
            self.requirements["required_verification_sources"],
            implementation["verification_source_files"],
        )
        self.assertEqual(
            set(implementation["verification_source_files"]),
            set(implementation["verification_source_sha256"]),
        )
        for name, relative in implementation["verification_source_files"].items():
            source = ROOT / relative
            self.assertEqual(
                sha256(source),
                implementation["verification_source_sha256"][name],
            )
            self.assertTrue(
                set(self.requirements["required_verification_test_methods"][name])
                .issubset(junit_methods(source)),
                name,
            )
        self.assertEqual(
            self.requirements["required_behavior_evidence"],
            self.contract["required_behavior_evidence"],
        )
        self.assertEqual(
            ["16.14", "18.4"],
            self.contract["required_behavior_evidence"]["postgresql_versions"],
        )

    def test_05_transaction_array_share_and_membership_safety_are_concrete(self):
        learning_service = (
            ROOT / "server/src/main/java/io/saksk/ti/learning/application/"
            "PersonalBankUserCountsService.java"
        ).read_text(encoding="utf-8")
        learning_adapter = (
            ROOT / "server/src/main/java/io/saksk/ti/learning/infrastructure/persistence/"
            "JdbcPersonalBankUserCountsQueryAdapter.java"
        ).read_text(encoding="utf-8")
        facts_service = (
            ROOT / "server/src/main/java/io/saksk/ti/personalbank/application/"
            "PersonalBankQuestionFactsService.java"
        ).read_text(encoding="utf-8")
        facts_adapter = (
            ROOT / "server/src/main/java/io/saksk/ti/personalbank/infrastructure/persistence/"
            "JdbcPersonalBankQuestionFactsQueryAdapter.java"
        ).read_text(encoding="utf-8")

        self.assertIn("Propagation.NOT_SUPPORTED", learning_service)
        self.assertIn("DataAccessException", learning_service)
        self.assertIn("TransactionException", learning_service)
        self.assertGreaterEqual(learning_adapter.count("Propagation.REQUIRES_NEW"), 3)
        self.assertIn('new SqlArrayValue("integer", candidates)', learning_adapter)
        self.assertNotIn(" IN (", learning_adapter.upper())
        self.assertGreaterEqual(facts_service.count("Propagation.REQUIRES_NEW"), 3)
        self.assertIn("ALLOWED_SHARE_PERMISSIONS", facts_service)
        self.assertIn("isAfter(now)", facts_service)
        self.assertIn("bsr.bank_id = requested_bank.id", facts_adapter)
        self.assertIn("bs.bank_id = requested_bank.id", facts_adapter)
        self.assertGreaterEqual(
            facts_adapter.count('new SqlArrayValue("integer", candidates)'),
            2,
        )

    def test_06_security_policy_authorization_routes_and_migration_stay_closed(self):
        self.assertEqual(
            self.composition["security_access_policy"],
            self.contract["security_access_policy"],
        )
        authorization = self.contract["authorization"]
        self.assertTrue(authorization["http_neutral_java_implementation"])
        for key in self.requirements["forbidden_authorizations"]:
            self.assertFalse(authorization[key], key)
        self.assertEqual(
            {
                "migrated_operation_count": 11,
                "pending_operation_count": 600,
                "production_cutover_operation_count": 0,
                "real_data_migration_executed": False,
                "operator_implemented": False,
            },
            self.contract["migration_status"],
        )
        route = self.contract["route_status"]
        self.assertEqual(self.composition["route_status"]["operations"], route["operations"])
        self.assertTrue(route["routes_remain_pending"])
        self.assertFalse(route["route_or_openapi_delta"])
        self.assertFalse(route["controller_added"])
        self.assertFalse(route["security_matcher_added"])
        self.assertFalse(route["production_cutover"])
        self.assertEqual(
            builder.ROUTE_SURFACE_MANIFEST_SHA256,
            self.contract["implementation"]["route_status_surface"]["manifest_sha256"],
        )

    def test_07_fourth_worm_tip_binds_current_build_and_keeps_history_immutable(self):
        evidence = self.contract["worm_successor_evidence"]
        self.assertEqual(
            "fourth_versioned_tip_verified_historical_reports_immutable",
            evidence["status"],
        )
        predecessor = ROOT / evidence["predecessor"]["source"]
        self.assertEqual(builder.WORM_PREDECESSOR_RELATIVE, evidence["predecessor"]["source"])
        self.assertEqual(builder.WORM_PREDECESSOR_SHA256, sha256(predecessor))
        self.assertEqual(
            builder.WORM_PREDECESSOR_SHA256,
            evidence["predecessor"]["sha256"],
        )
        tip = evidence["current_tip"]
        report = ROOT / tip["source"]
        self.assertEqual(sha256(report), tip["sha256"])
        self.assertEqual(
            self.contract["implementation"]["java_build_context_sha256"],
            tip["java_build_context_sha256"],
        )
        self.assertEqual("18.4", tip["postgresql_version"])
        self.assertEqual(70, tip["public_base_tables"])
        self.assertEqual(617, tip["public_columns"])
        self.assertTrue(tip["startup_passed"])
        self.assertTrue(tip["readiness_passed"])
        self.assertTrue(tip["read_only_acl_passed"])
        self.assertTrue(evidence["arbitrary_report_lookup_forbidden"])
        self.assertTrue(evidence["historical_report_overwrite_forbidden"])

    def test_08_historical_successor_bridge_is_exact_and_rejects_tampering(self):
        history = self.contract["historical_successor_acceptance"]
        self.assertEqual(
            set(builder.PYTHON_ACCEPTED_SHA256), set(history["python_sources"])
        )
        self.assertEqual(set(builder.JAVA_ACCEPTED_SHA256), set(history["java_sources"]))
        self.assertEqual(
            set(builder.AUXILIARY_ACCEPTED_SHA256),
            set(history["auxiliary_sources"]),
        )
        self.assertTrue(history["successor_allowlist_exact"])
        self.assertTrue(history["arbitrary_source_hash_lookup_forbidden"])
        for source_map in (
            history["python_sources"],
            history["java_sources"],
            history["auxiliary_sources"],
        ):
            for relative, reference in source_map.items():
                self.assertEqual(relative, reference["source"])
                self.assertEqual(sha256(ROOT / relative), reference["successor_sha256"])
                self.assertNotEqual(reference["accepted_sha256"], "")

        tampered = copy.deepcopy(self.contract)
        first = next(iter(tampered["historical_successor_acceptance"]["python_sources"]))
        tampered["historical_successor_acceptance"]["python_sources"][first][
            "successor_sha256"
        ] = "0" * 64
        with self.assertRaisesRegex(AssertionError, "successor hash is not fixed"):
            validate_read_successor_contract(tampered, ROOT)

        unexpected = copy.deepcopy(self.contract)
        unexpected["historical_successor_acceptance"]["python_sources"][
            "tools/unreviewed.py"
        ] = {
            "source": "tools/unreviewed.py",
            "accepted_sha256": "0" * 64,
            "successor_sha256": "0" * 64,
        }
        with self.assertRaisesRegex(AssertionError, "unexpected .* source set"):
            validate_read_successor_contract(unexpected, ROOT)

    def test_09_acceptance_is_read_only_and_next_gate_does_not_claim_http(self):
        acceptance = self.contract["acceptance"]
        self.assertTrue(acceptance["targeted_verification_passed"])
        self.assertTrue(acceptance["http_neutral_read_implemented"])
        self.assertTrue(acceptance["routes_remain_pending"])
        self.assertFalse(acceptance["production_cutover"])
        self.assertEqual(
            "close_http_entry_contract_without_authorizing_operator_or_cutover",
            acceptance["next_gate"],
        )


if __name__ == "__main__":
    unittest.main()
