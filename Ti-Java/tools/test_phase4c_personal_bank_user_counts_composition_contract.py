#!/usr/bin/env python3
"""Fail-closed checks for the Phase 4C user-counts composition gate."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

try:
    from tools.phase4c_http_entry_successor_acceptance import (
        accepted_sha256 as http_entry_accepted_sha256,
        successor_sha256 as http_entry_successor_sha256,
    )
    from tools.phase4c_successor_acceptance import validate_successor_contract
    from tools.phase4c_http_implementation_successor_acceptance import (
        accepted_sha256 as implementation_accepted_sha256,
        fixed_source_sha256 as implementation_fixed_source_sha256,
        load_http_implementation_successor_contract,
        runtime_successor_sha256 as implementation_runtime_successor_sha256,
        successor_sha256 as implementation_successor_sha256,
    )
    from tools.phase4c_read_successor_acceptance import (
        load_read_successor_contract,
        validate_read_successor_contract,
    )
except ModuleNotFoundError:  # Direct script execution from tools/.
    from phase4c_http_entry_successor_acceptance import (
        accepted_sha256 as http_entry_accepted_sha256,
        successor_sha256 as http_entry_successor_sha256,
    )
    from phase4c_successor_acceptance import validate_successor_contract
    from phase4c_http_implementation_successor_acceptance import (
        accepted_sha256 as implementation_accepted_sha256,
        fixed_source_sha256 as implementation_fixed_source_sha256,
        load_http_implementation_successor_contract,
        runtime_successor_sha256 as implementation_runtime_successor_sha256,
        successor_sha256 as implementation_successor_sha256,
    )
    from phase4c_read_successor_acceptance import (
        load_read_successor_contract,
        validate_read_successor_contract,
    )


ROOT = Path(__file__).resolve().parents[1]
PHASE4C = ROOT / "docs/refactor/phase4c"
CONTRACT_PATH = PHASE4C / "personal-bank-user-counts-composition-contract.json"
DELTA_PATH = PHASE4C / "data-ownership-delta.csv"
EFFECTIVE_PATH = PHASE4C / "effective-data-ownership-status.json"
PREDECESSOR_PATH = (
    ROOT / "docs/refactor/phase4b/personal-bank-user-counts-entry-contract.json"
)
APPROVED_PATH = PHASE4C / "approved-differences.md"
BUILDER_PATH = (
    ROOT / "tools/build_phase4c_personal_bank_user_counts_composition_contract.py"
)
ACCEPTED_COMMIT = "2ca3e16d9585de55313fd2de9b1429a6351d9683"
ACCEPTED_PREDECESSOR_SHA256 = (
    "1ec41fde1e17dd1f09a9aa737aadd9ada1f64c41f4e44f1df87dbf0613c30ee6"
)
ACCEPTED_JAVA_BUILD_CONTEXT_SHA256 = (
    "c59ee688646b7c23f0f883b4c1377d2a33b507e7dd08b978e98cf3ebdc11825c"
)
ACCEPTED_PRODUCTION_SURFACE_SHA256 = (
    "7d6113701aac8268f22e8b58b3c52d7d8ea388ddaa06aa2d3d7bd334edd17ebd"
)
ACCEPTED_ROUTE_SURFACE_SHA256 = (
    "6f9cfdd6ba849233c51a27ed281856681d8a6ec3a0bda628da9184ec284e4b86"
)
ACCEPTED_PHASE4B_WORM_SHA256 = (
    "779154127fc700e213fbb3d5f83c112c090d3481236dcd361dbd72b74a0bd1ad"
)
ACCEPTED_PHASE4C_WORM_SHA256 = (
    "cfb262319ded0840218fd9bfb4deff1e7bc9c66b5849e3ff05f49a459e686884"
)


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


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


def file_manifest(root: Path) -> dict[str, str]:
    if not root.exists():
        return {}
    paths = [root] if root.is_file() else [path for path in root.rglob("*") if path.is_file()]
    return {
        path.relative_to(ROOT).as_posix(): sha256(path)
        for path in sorted(paths)
    }


def production_runtime_manifest() -> dict[str, str]:
    manifest = file_manifest(ROOT / "server/src/main")
    for relative in (
        "server/pom.xml",
        "server/Dockerfile",
        "server/.dockerignore",
        "server/.mvn",
        "server/mvnw",
        "server/mvnw.cmd",
        "server/build-versions.properties",
        "compose.dev.yml",
        ".env.example",
    ):
        manifest.update(file_manifest(ROOT / relative))
    manifest.update(file_manifest(ROOT / "contracts"))
    manifest.update(file_manifest(ROOT / "openapi"))
    return dict(sorted(manifest.items()))


def route_status_manifest() -> dict[str, str]:
    return {
        relative: sha256(ROOT / relative)
        for relative in (
            "docs/refactor/02-route-parity-matrix.csv",
            "docs/refactor/phase3/route-parity-delta.csv",
            "docs/refactor/phase3/effective-route-parity-status.json",
            "docs/refactor/phase4a/route-parity-delta.csv",
            "docs/refactor/phase4a/effective-route-parity-status.json",
        )
    }


def manifest_sha256(manifest: dict[str, str]) -> str:
    return hashlib.sha256(canonical_json(manifest).encode("utf-8")).hexdigest()


def canonical_effective_owners() -> list[dict]:
    rows = list(csv.DictReader(
        (ROOT / "docs/refactor/03-data-ownership.csv")
        .read_text(encoding="utf-8")
        .splitlines()
    ))
    owners = {}
    for row in rows:
        key = (row["resource_kind"], row["resource_name"])
        if key in owners or not row["target_owner"].strip():
            raise AssertionError(f"invalid base owner: {key}")
        owners[key] = row["target_owner"].strip()
    phase4a = load_json(
        ROOT / "docs/refactor/phase4a/effective-data-ownership-status.json"
    )
    for resource in phase4a["effective"]["new_resources"]:
        key = (resource["resource_kind"], resource["resource_name"])
        if key in owners or not resource["owner"].strip():
            raise AssertionError(f"invalid Phase4A owner: {key}")
        owners[key] = resource["owner"].strip()
    owners[("db_kv_namespace", "bank_<bank_id>_tags")] = "learning"
    return [
        {"resource_kind": key[0], "resource_name": key[1], "owner": owner}
        for key, owner in sorted(owners.items())
    ]


class Phase4cPersonalBankUserCountsCompositionContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = load_json(CONTRACT_PATH)
        cls.predecessor = load_json(PREDECESSOR_PATH)
        cls.effective = load_json(EFFECTIVE_PATH)
        cls.read_successor = load_read_successor_contract(ROOT)
        cls.http_implementation = load_http_implementation_successor_contract(ROOT)
        if cls.http_implementation is None:
            raise AssertionError("Phase4C HTTP implementation contract is required")

    def test_01_identity_predecessor_sources_payload_and_determinism_close(self):
        contract = self.contract
        self.assertEqual(
            "ti.phase4c.personal-bank-user-counts-composition-contract",
            contract["contract_id"],
        )
        self.assertEqual(1, contract["schema_version"])
        self.assertEqual(
            "composition_and_migration_primitives_closed_"
            "http_neutral_implementation_authorized",
            contract["status"],
        )
        self.assertEqual(
            "phase4c-personal-bank-user-counts-composition-gate",
            contract["scope"],
        )
        predecessor = contract["predecessor"]
        self.assertEqual(self.predecessor["contract_id"], predecessor["contract_id"])
        self.assertEqual(self.predecessor["status"], predecessor["status"])
        self.assertEqual(ACCEPTED_COMMIT, predecessor["accepted_commit"])
        self.assertEqual(ACCEPTED_PREDECESSOR_SHA256, sha256(PREDECESSOR_PATH))
        self.assertEqual(sha256(PREDECESSOR_PATH), predecessor["sha256"])
        self.assertTrue(predecessor["evidence_closed"])
        self.assertFalse(predecessor["implementation_authorized"])

        self.assertEqual(
            "tools/validate_phase1.py",
            contract["source_contracts"]["phase1_validator"]["source"],
        )
        read_sources = {
            reference["source"]: reference["sha256"]
            for reference in (self.read_successor or {}).get(
                "source_contracts", {}
            ).values()
        }
        read_runtime = self.read_successor["implementation"][
            "production_runtime_surface"
        ]["files"]
        implementation_delta = self.http_implementation["implementation"][
            "production_runtime_transition"
        ]["exact_delta"]
        for name, reference in contract["source_contracts"].items():
            source = ROOT / reference["source"]
            self.assertTrue(source.is_file(), name)
            current_hash = sha256(source)
            if current_hash != reference["sha256"]:
                http_successor = http_entry_successor_sha256(
                    ROOT, reference["source"]
                )
                if http_successor is not None:
                    accepted_http_predecessor = read_sources.get(
                        reference["source"], reference["sha256"]
                    )
                    self.assertEqual(
                        accepted_http_predecessor,
                        http_entry_accepted_sha256(reference["source"]),
                        name,
                    )
                    self.assertEqual(current_hash, http_successor, name)
                    continue
                read_terminal = read_sources.get(reference["source"])
                if current_hash == read_terminal:
                    continue
                implementation_successor = implementation_successor_sha256(
                    ROOT, reference["source"]
                )
                if implementation_successor is not None:
                    self.assertEqual(
                        read_terminal,
                        implementation_accepted_sha256(reference["source"]),
                        name,
                    )
                    self.assertEqual(current_hash, implementation_successor, name)
                    continue
                fixed_source = implementation_fixed_source_sha256(
                    ROOT, reference["source"]
                )
                if fixed_source is not None:
                    self.assertIsNotNone(read_terminal, name)
                    self.assertEqual(current_hash, fixed_source, name)
                    continue
                runtime_successor = implementation_runtime_successor_sha256(
                    ROOT, reference["source"]
                )
                if runtime_successor is not None:
                    changed = implementation_delta["changed_files"].get(
                        reference["source"]
                    )
                    self.assertIsNotNone(changed, name)
                    self.assertEqual(read_runtime[reference["source"]], changed[
                        "predecessor_sha256"
                    ], name)
                    self.assertEqual(reference["sha256"], changed[
                        "predecessor_sha256"
                    ], name)
                    self.assertEqual(current_hash, runtime_successor, name)
                    continue
                self.fail(f"unreviewed composition source drift: {name}")
        self.assertEqual(
            contract["document_payload_sha256"],
            document_payload_sha256(contract),
        )
        history = contract["historical_acceptance"]
        self.assertEqual(ACCEPTED_COMMIT, history["accepted_commit"])
        self.assertEqual(
            ACCEPTED_PREDECESSOR_SHA256,
            history["immutable_predecessor"]["sha256"],
        )
        self.assertTrue(history["successor_allowlist_exact"])
        self.assertTrue(history["arbitrary_source_hash_lookup_forbidden"])
        self.assertEqual(
            set(history["accepted_file_sha256"]) - {"README.md"},
            set(history["successor_aware_test_files"]),
        )
        for relative, handoff in history["successor_aware_test_files"].items():
            self.assertEqual(
                history["accepted_file_sha256"][relative],
                handoff["accepted_sha256"],
                relative,
            )
            reference = contract["source_contracts"][
                handoff["source_contract_key"]
            ]
            self.assertEqual(relative, reference["source"], relative)
            self.assertEqual(reference["sha256"], handoff["successor_sha256"])
            current_hash = sha256(ROOT / relative)
            if current_hash != handoff["successor_sha256"]:
                self.assertIsNotNone(self.read_successor, relative)
                read_history = self.read_successor[
                    "historical_successor_acceptance"
                ]
                second_handoff = {
                    **read_history["python_sources"],
                    **read_history["java_sources"],
                    **read_history["auxiliary_sources"],
                }.get(relative)
                self.assertIsNotNone(second_handoff, relative)
                self.assertEqual(
                    handoff["successor_sha256"],
                    second_handoff["accepted_sha256"],
                    relative,
                )
                if current_hash == second_handoff["successor_sha256"]:
                    continue
                http_successor = http_entry_successor_sha256(ROOT, relative)
                if http_successor is not None:
                    self.assertEqual(
                        second_handoff["successor_sha256"],
                        http_entry_accepted_sha256(relative),
                        relative,
                    )
                    self.assertEqual(current_hash, http_successor, relative)
                    continue
                implementation_successor = implementation_successor_sha256(
                    ROOT, relative
                )
                self.assertIsNotNone(implementation_successor, relative)
                self.assertEqual(
                    second_handoff["successor_sha256"],
                    implementation_accepted_sha256(relative),
                    relative,
                )
                self.assertEqual(current_hash, implementation_successor, relative)
        validate_successor_contract(contract)
        tampered = json.loads(json.dumps(contract))
        tampered_relative = (
            "tools/test_phase4b_personal_bank_user_counts_entry_contract.py"
        )
        tampered_hash = "0" * 64
        tampered["historical_acceptance"]["successor_aware_test_files"][
            tampered_relative
        ]["successor_sha256"] = tampered_hash
        tampered["source_contracts"]["phase4b_entry_contract_test"][
            "sha256"
        ] = tampered_hash
        with self.assertRaisesRegex(AssertionError, "successor hash is not fixed"):
            validate_successor_contract(tampered)

        tampered_auxiliary = json.loads(json.dumps(contract))
        tampered_auxiliary["source_contracts"]["phase2_worm_successor_gate"][
            "sha256"
        ] = tampered_hash
        with self.assertRaisesRegex(
            AssertionError, "auxiliary successor hash is not fixed"
        ):
            validate_successor_contract(tampered_auxiliary)

        missing_auxiliary = json.loads(json.dumps(contract))
        missing_auxiliary["forward_handoff"]["forward_additions"].remove(
            "Ti-Java/tools/phase2_wormhole_successor_acceptance.py"
        )
        with self.assertRaisesRegex(
            AssertionError, "new auxiliary successor is not admitted"
        ):
            validate_successor_contract(missing_auxiliary)

        if self.read_successor is None:
            with tempfile.TemporaryDirectory(prefix="ti-phase4c-composition-") as temp:
                output = Path(temp)
                subprocess.run(
                    [sys.executable, str(BUILDER_PATH), "--output-dir", str(output)],
                    cwd=ROOT,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                for name in (
                    "data-ownership-delta.csv",
                    "effective-data-ownership-status.json",
                    "personal-bank-user-counts-composition-contract.json",
                ):
                    self.assertEqual(
                        (PHASE4C / name).read_bytes(),
                        (output / name).read_bytes(),
                    )
        else:
            validate_read_successor_contract(self.read_successor, ROOT)
            self.assertEqual(
                sha256(CONTRACT_PATH),
                self.read_successor["predecessor"]["sha256"],
            )
            self.assertEqual(
                contract["contract_id"],
                self.read_successor["predecessor"]["contract_id"],
            )

    def test_02_namespace_owner_overlay_is_exact_and_preserves_phase1_history(self):
        rows = list(csv.DictReader(
            DELTA_PATH.read_text(encoding="utf-8").splitlines()
        ))
        self.assertEqual(1, len(rows))
        row = rows[0]
        self.assertEqual("db_kv_namespace", row["resource_kind"])
        self.assertEqual("bank_<bank_id>_tags", row["resource_name"])
        self.assertEqual("personalbank", row["base_owner"])
        self.assertEqual("learning", row["phase4c_owner"])
        self.assertEqual("false", row["production_cutover"])

        overlay = self.contract["ownership_overlay"]
        self.assertEqual("personalbank", overlay["historical_owner"])
        self.assertEqual("learning", overlay["phase4c_effective_owner"])
        self.assertEqual("learning", overlay["physical_table_owner"])
        self.assertTrue(overlay["scope_only"])
        self.assertTrue(overlay["other_user_progress_namespaces_unchanged"])
        self.assertEqual("learning -> personalbank::api", overlay["dependency_direction"])
        self.assertTrue(overlay["reverse_dependency_forbidden"])

        effective = self.effective["effective"]
        self.assertEqual(159, effective["resource_count"])
        self.assertEqual(159, effective["resources_with_exactly_one_owner"])
        self.assertEqual(1, len(effective["owner_overrides"]))
        self.assertEqual("learning", effective["owner_overrides"][0]["owner"])
        owner_manifest = canonical_effective_owners()
        self.assertEqual(159, len(owner_manifest))
        self.assertEqual(
            hashlib.sha256(canonical_json(owner_manifest).encode("utf-8")).hexdigest(),
            effective["canonical_owner_manifest_sha256"],
        )

    def test_03_planned_public_shapes_are_minimal_immutable_and_http_neutral(self):
        shape = self.contract["planned_public_api_shape"]
        self.assertEqual(23, shape["current_implemented_public_application_method_count"])
        self.assertEqual(27, shape["authorized_future_method_count"])

        learning = shape["learning"]
        self.assertEqual(
            "io.saksk.ti.learning.api.LearningApplicationApi",
            learning["java_api"],
        )
        self.assertEqual(["findPersonalBankUserCounts"], [
            method["name"] for method in learning["methods"]
        ])
        self.assertFalse(learning["methods"][0]["direct_http_operation"])
        self.assertEqual(
            {
                "AuthenticatedLearningViewer": ["long identityId"],
                "PersonalBankUserCountsQuery": [
                    "int bankId",
                    "String rawQuestionType",
                    "String rawSource",
                    "String rawTag",
                ],
                "PersonalBankUserCountsResult": [
                    "Outcome AVAILABLE|DENIED",
                    "Optional<PersonalBankUserCountsView> data",
                ],
                "PersonalBankUserCountsView": [
                    "long total",
                    "long favorites",
                    "long mistakes",
                    "List<String> types",
                    "boolean shuffleOptionsAvailable",
                ],
            },
            learning["immutable_types"],
        )

        personalbank = shape["personalbank"]
        self.assertTrue(personalbank["additional_public_api"])
        self.assertEqual(
            {
                "checkQuestionAccess",
                "summarizeQuestions",
                "inspectQuestionMembership",
            },
            {method["name"] for method in personalbank["methods"]},
        )
        self.assertTrue(all(
            method["direct_http_operation"] is False
            for method in personalbank["methods"]
        ))
        self.assertEqual(
            ["int", "java.util.List<java.lang.Integer>"],
            next(
                method for method in personalbank["methods"]
                if method["name"] == "inspectQuestionMembership"
            )["parameter_types"],
        )
        self.assertEqual(
            {
                "PersonalBankQuestionSelection": [
                    "int bankId",
                    "Optional<String> portableType",
                    "Optional<List<Integer>> candidateQuestionIds",
                ],
                "PersonalBankQuestionAccessResult": [
                    "Outcome AVAILABLE|DENIED",
                ],
                "PersonalBankQuestionFactsResult": [
                    "Outcome AVAILABLE|DENIED",
                    "Optional<PersonalBankQuestionFactsView> data",
                ],
                "PersonalBankQuestionFactsView": [
                    "long total",
                    "List<PersonalBankQuestionTypeCount> rawTypes",
                ],
                "PersonalBankQuestionTypeCount": [
                    "Optional<String> rawType",
                    "long count",
                ],
                "PersonalBankQuestionMembershipView": [
                    "int bankId",
                    "boolean bankExists",
                    "List<Integer> existingQuestionIds",
                    "String membershipDigest",
                ],
            },
            personalbank["immutable_types"],
        )
        self.assertTrue(all(personalbank["immutability_and_validation"].values()))
        selection = personalbank["selection_semantics"]
        self.assertIn("no candidate restriction", selection[
            "candidate_question_ids_absent"
        ])
        self.assertIn("empty result", selection[
            "candidate_question_ids_present_empty"
        ])
        forbidden = " ".join(personalbank["forbidden_exposure"])
        self.assertIn("persistence", forbidden)
        self.assertIn("learning-owned", forbidden)

    def test_04_request_normalization_and_result_mapping_match_frozen_goldens(self):
        normalization = self.contract["request_normalization"]
        self.assertIn("first value", normalization["duplicate_query_keys"])
        self.assertIn("case-insensitive all", normalization["q_type"])
        self.assertIn("exact lowercase favorites", normalization["source"])
        self.assertIn("exact lowercase all", normalization["tag"])
        self.assertIn("zero view", normalization["tag_question_ids"])
        self.assertTrue(normalization["no_pagination_or_time_window"])
        self.assertTrue(normalization[
            "evidence_boundary_900_is_not_a_production_limit"
        ])

        result = self.contract["result_semantics"]
        self.assertEqual("PostgreSQL int8 mapped to Java long", result[
            "count_jdbc_type"
        ])
        self.assertIn("omitted", result["raw_null_or_empty_type"])
        self.assertEqual("简答题", result["unknown_raw_type"])
        self.assertFalse(result["post_mapping_deduplication"])
        self.assertTrue(result["http_envelope_outside_application_api"])

    def test_05_ordered_orchestration_has_no_cross_module_transaction(self):
        orchestration = self.contract["orchestration"]
        self.assertEqual("learning", orchestration["owner"])
        self.assertIn("NOT_SUPPORTED", orchestration["outer_transaction"])
        self.assertFalse(orchestration["cross_module_transaction"])
        self.assertFalse(orchestration["n_plus_one_authorized"])
        self.assertEqual(
            [
                "access",
                "tag_membership",
                "zero_view_access_recheck",
                "total",
                "favorites",
                "mistakes",
                "types",
            ],
            [stage["stage"] for stage in orchestration["ordered_stages"]],
        )
        self.assertEqual("hard", orchestration["ordered_stages"][0]["failure"])
        self.assertIn("hard", orchestration["ordered_stages"][2]["failure"])
        self.assertEqual("hard", orchestration["ordered_stages"][3]["failure"])
        for stage in orchestration["ordered_stages"][4:]:
            self.assertIn("fallback", stage["failure"])
            self.assertIn("REQUIRES_NEW", stage["transaction"])
            self.assertIn("terminal DENIED", stage["denied"])
            self.assertIn("never DENIED", stage["fail_soft_scope"])
        recheck = orchestration["early_return_access_recheck"]
        self.assertEqual(
            [
                "tag membership is determinately empty",
                "tag membership failure falls back to empty",
                "any zero-view return before total facts",
            ],
            recheck["required_before"],
        )
        self.assertEqual(
            "personalbank::api#checkQuestionAccess",
            recheck["provider"],
        )
        self.assertIn("terminal DENIED", recheck["denied"])
        self.assertIn("hard failure", recheck["infrastructure_failure"])
        authorization = orchestration["authorization_outcome"]
        self.assertTrue(
            authorization["denied_is_terminal_for_every_personalbank_call"]
        )
        self.assertTrue(authorization["discard_partial_result_on_denied"])
        self.assertTrue(authorization["fail_soft_never_applies_to_denied"])
        self.assertTrue(
            authorization["tag_zero_view_requires_personalbank_access_recheck"]
        )
        self.assertEqual(4, len(orchestration["source_sequences"]["ALL"]))
        self.assertIn(
            "favorites-again",
            orchestration["source_sequences"]["FAVORITES"],
        )
        self.assertIn(
            "mistakes-again",
            orchestration["source_sequences"]["MISTAKES"],
        )

    def test_06_personalbank_never_reads_learning_relations(self):
        orchestration = self.contract["orchestration"]
        self.assertEqual(
            {
                "user_bank_favorites",
                "user_bank_mistakes",
                "user_progress",
                "user_question_tag_items",
            },
            set(orchestration["learning_owned_relations"]),
        )
        self.assertEqual(
            {
                "user_question_banks",
                "bank_shares",
                "bank_share_records",
                "user_bank_questions",
            },
            set(orchestration["personalbank_owned_relations"]),
        )
        main_root = ROOT / "server/src/main/java/io/saksk/ti"
        manifest = self.contract["production_baseline"][
            "learning_and_personalbank_main_source_manifest"
        ]
        current = {}
        for module in ("learning", "personalbank"):
            for path in sorted((main_root / module).rglob("*.java")):
                current[path.relative_to(ROOT).as_posix()] = sha256(path)
        baseline = self.contract["production_baseline"]
        self.assertEqual(ACCEPTED_COMMIT, baseline["accepted_commit"])
        runtime = baseline["production_runtime_surface"]
        current_runtime = production_runtime_manifest()
        if self.read_successor is None:
            self.assertEqual(manifest, current)
            self.assertEqual([], list(main_root.rglob("*UserCounts*.java")))
            self.assertEqual(current_runtime, runtime["files"])
            self.assertEqual(len(current_runtime), runtime["file_count"])
            self.assertEqual(
                ACCEPTED_PRODUCTION_SURFACE_SHA256,
                manifest_sha256(current_runtime),
            )
        else:
            implementation = self.read_successor["implementation"]
            self.assertEqual(
                implementation["learning_and_personalbank_main_source_manifest"],
                current,
            )
            self.assertEqual(40, len(current))
            read_runtime = implementation["production_runtime_surface"]
            self.assertEqual(
                288, read_runtime["file_count"],
            )
            self.assertEqual(
                read_runtime["manifest_sha256"],
                manifest_sha256(read_runtime["files"]),
            )
            transition = self.http_implementation["implementation"][
                "production_runtime_transition"
            ]
            self.assertEqual({
                "file_count": 288,
                "manifest_sha256": read_runtime["manifest_sha256"],
            }, transition["predecessor"])
            self.assertEqual(297, len(current_runtime))
            self.assertEqual(current_runtime, transition["current"]["files"])
            requirements = self.contract["successor_handoff"][
                "future_read_contract_requirements"
            ]
            self.assertEqual(
                set(requirements["expected_added_main_sources"]),
                set(current) - set(manifest),
            )
            self.assertEqual(set(), set(manifest) - set(current))
            self.assertEqual(
                set(requirements["expected_changed_main_sources"]),
                {
                    relative
                    for relative in set(manifest) & set(current)
                    if manifest[relative] != current[relative]
                },
            )
        self.assertEqual(
            ACCEPTED_PRODUCTION_SURFACE_SHA256,
            runtime["manifest_sha256"],
        )
        route_surface = baseline["route_status_surface"]
        current_routes = route_status_manifest()
        self.assertEqual(current_routes, route_surface["files"])
        self.assertEqual(ACCEPTED_ROUTE_SURFACE_SHA256, manifest_sha256(current_routes))
        self.assertEqual(
            ACCEPTED_ROUTE_SURFACE_SHA256,
            route_surface["manifest_sha256"],
        )
        build_context = subprocess.run(
            [str(ROOT / "infra/phase2/hash-java-build-context.sh")],
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        ).stdout.strip()
        if self.read_successor is None:
            self.assertEqual(ACCEPTED_JAVA_BUILD_CONTEXT_SHA256, build_context)
            self.assertEqual(build_context, baseline["java_build_context_sha256"])
        else:
            self.assertEqual(
                self.http_implementation["implementation"][
                    "java_build_context_sha256"
                ],
                build_context,
            )
            self.assertNotEqual(
                self.read_successor["implementation"]["java_build_context_sha256"],
                build_context,
            )
            self.assertNotEqual(baseline["java_build_context_sha256"], build_context)
        migration_root = ROOT / "server/src/main/resources/db"
        self.assertEqual([], list(migration_root.rglob("*")) if migration_root.exists() else [])
        self.assertEqual(11, baseline["migrated_route_count"])
        self.assertEqual(600, baseline["pending_route_count"])
        self.assertEqual(0, baseline["production_cutover_count"])
        handoff = self.contract["successor_handoff"]
        self.assertTrue(handoff["phase4b_test_is_successor_aware"])
        self.assertEqual(manifest, handoff["historical_hash_overrides"])
        self.assertEqual(
            "docs/refactor/phase4c/personal-bank-user-counts-read-contract.json",
            handoff["future_read_contract"],
        )
        self.assertTrue(handoff["read_contract_must_bind_current_main_sources"])
        requirements = handoff["future_read_contract_requirements"]
        self.assertEqual(
            "ti.phase4c.personal-bank-user-counts-read-contract",
            requirements["contract_id"],
        )
        self.assertEqual(17, len(requirements["expected_added_main_sources"]))
        self.assertEqual(1, len(requirements["expected_changed_main_sources"]))
        self.assertEqual(
            {
                "api_shape_contract_parity_test",
                "learning_composition_test",
                "personalbank_facts_service_test",
                "learning_adapter_test",
                "personalbank_adapter_test",
                "postgresql_compatibility_it",
            },
            set(requirements["required_verification_sources"]),
        )
        self.assertTrue(all(requirements["required_behavior_evidence"].values()))
        self.assertEqual(
            ["16.14", "18.4"],
            requirements["required_behavior_evidence"]["postgresql_versions"],
        )
        surface_delta = requirements["production_surface_delta"]
        self.assertEqual(18, surface_delta["exact_changed_or_added_main_sources"])
        self.assertEqual(0, surface_delta["main_source_deletions"])
        self.assertEqual(0, surface_delta["main_resources_delta"])
        self.assertEqual(
            0,
            surface_delta[
                "http_security_openapi_route_schema_deployment_delta"
            ],
        )
        self.assertIn(
            "real_data_migration_execution",
            requirements["forbidden_authorizations"],
        )
        self.assertEqual(
            "migration_global_preflight_evidence_closed",
            requirements["operator_migration_implementation_requires"],
        )

    def test_07_explicit_migration_is_operator_only_insert_only_and_idempotent(self):
        migration = self.contract["explicit_bank_tag_migration"]
        self.assertEqual("learning", migration["owner"])
        self.assertIn("operator-only", migration["execution"])
        self.assertEqual("dry-run", migration["default_mode"])
        self.assertEqual("^bank_[1-9][0-9]*_tags$", migration["source"][
            "namespace_regex"
        ])
        self.assertFalse(migration["source"]["source_mutation_or_deletion"])
        self.assertFalse(migration["target"]["target_delete_or_update"])
        self.assertIn("ON CONFLICT (", migration["target"]["insert"])
        self.assertIn("DO NOTHING", migration["target"]["insert"])
        self.assertIn("present non-list", migration["legacy_mapping"]["tags"])
        self.assertIn(
            "present non-object", migration["legacy_mapping"]["question_tags"]
        )
        self.assertIn(
            "normalized-ID conflicts", migration["legacy_mapping"]["bindings"]
        )
        self.assertIn(
            "preserves legacy 20-code-point truncation",
            migration["legacy_mapping"]["tag_cleaning_collision"],
        )
        self.assertIn(
            "block production apply",
            migration["legacy_mapping"]["tag_cleaning_collision"],
        )
        precedence = migration["target_precedence"]
        self.assertTrue(precedence["existing_scope_rows_prevent_automatic_writes"])
        self.assertTrue(precedence["precedence_requires_valid_source_plan"])
        self.assertTrue(precedence["source_plan_must_be_subset_of_target"])
        self.assertTrue(precedence["target_tags_must_be_canonical"])
        self.assertTrue(precedence[
            "positive_target_questions_must_belong_to_bank"
        ])
        self.assertFalse(migration["target_precedence"]["automatic_merge"])
        absence = migration["target_absence_after_prior_migration"]
        self.assertTrue(absence["ambiguous_without_durable_marker"])
        self.assertIn("repopulate", absence["test_primitive_behavior"])
        self.assertIn("durable migration ledger", absence["operator_requirement"])
        self.assertFalse(absence["operator_design_closed"])
        row_outcomes = {
            "MIGRATED",
            "EMPTY_NOOP",
            "TARGET_ALREADY_PRESENT",
            "TARGET_CONFLICT",
            "INVALID_KEY",
            "INVALID_DATA",
            "BANK_MISSING",
            "ORPHAN_QUESTION",
            "SOURCE_DISAPPEARED",
            "FAILED_ROLLED_BACK",
            "ROLLBACK_FAILED",
            "COMMIT_OUTCOME_UNKNOWN",
        }
        self.assertEqual(row_outcomes, set(migration["row_outcomes"]))
        groups = migration["reporting_groups"]
        grouped = [outcome for values in groups.values() for outcome in values]
        self.assertEqual(row_outcomes, set(grouped))
        self.assertEqual(len(row_outcomes), len(grouped))
        self.assertEqual("SELECT FOR UPDATE", migration["transaction"]["source_lock"])
        self.assertFalse(migration["transaction"]["test_primitive_retry"])
        self.assertIn(
            "40001 and 40P01",
            migration["transaction"]["production_operator_retry_requirement"],
        )
        self.assertIn("SQLSTATE class 08", migration["transaction"]["failure"])
        self.assertIn("40003", migration["transaction"]["failure"])
        self.assertIn(
            "session-level PostgreSQL advisory lock",
            migration["transaction"]["global_single_runner"],
        )
        self.assertIn("not closed", migration["transaction"]["operator_design_status"])
        preconditions = " ".join(migration["apply_preconditions"])
        self.assertIn("legacy source", preconditions)
        self.assertIn("normalized target", preconditions)
        self.assertIn("membership", preconditions)
        self.assertIn("zero DML", migration["idempotency"])
        self.assertFalse(migration["get_runtime_ddl"])
        self.assertFalse(migration["get_runtime_dml"])
        self.assertFalse(migration["production_schema_or_index_delta"])
        self.assertFalse(migration["real_data_execution_authorized"])

        digest = self.contract["planned_public_api_shape"]["personalbank"][
            "immutability_and_validation"
        ]["membership_digest"]
        self.assertEqual("SHA-256", digest["algorithm"])
        self.assertEqual("UTF-8", digest["encoding"])
        self.assertEqual(
            ["bank_id", "bank_exists", "existing_question_ids"],
            digest["canonical_json_key_order"],
        )
        self.assertEqual("none", digest["canonical_json_whitespace"])
        self.assertEqual(
            '{"bank_id":7101,"bank_exists":true,'
            '"existing_question_ids":[8101,8102]}',
            digest["example"],
        )

        evidence_path = ROOT / self.contract["source_contracts"][
            "migration_evidence_java"
        ]["source"]
        evidence = evidence_path.read_text(encoding="utf-8").upper()
        self.assertIn("FOR UPDATE", evidence)
        self.assertIn("ON CONFLICT (", evidence)
        self.assertIn("DO NOTHING", evidence)
        self.assertIn("INVALID_DATA", evidence)
        self.assertIn("BLOCKINGROWCOUNT", evidence)
        self.assertIn("ISAPPLYELIGIBLE", evidence)
        for forbidden in (
            "CREATE TABLE",
            "CREATE INDEX",
            "DROP TABLE",
            "DROP INDEX",
            "DELETE FROM",
            "UPDATE USER_QUESTION_TAG_ITEMS",
        ):
            self.assertNotIn(forbidden, evidence)

    def test_08_pg16_pg18_evidence_and_claim_limits_are_explicit(self):
        evidence = self.contract["migration_evidence"]
        self.assertEqual(["16.14", "18.4"], evidence["postgresql_versions"])
        proves = " ".join(evidence["proves"])
        self.assertIn("second fixture sweep is zero DML", proves)
        self.assertIn("atomic rollback", proves)
        self.assertIn("fingerprints unchanged", proves)
        self.assertIn("invalid raw field", proves)
        self.assertIn("JSON-array-string", proves)
        self.assertIn("proper-subset target evidence", proves)
        self.assertIn("duplicate object keys", proves)
        self.assertIn("Python-compatible Unicode whitespace", proves)
        self.assertIn("positive-question bank membership", proves)
        self.assertIn("rollback failure is tracked orthogonally", proves)
        self.assertIn("only ambiguous post-write commit outcomes remain unknown", proves)
        limits = " ".join(evidence["does_not_prove"])
        self.assertIn("global dry-run/preflight", limits)
        self.assertIn("target-conflict", limits)
        self.assertIn("real network commit-response loss", limits)
        self.assertIn("target deletion", limits)
        self.assertIn("connection acquisition", limits)
        self.assertIn("ON CONFLICT race", limits)
        self.assertIn("write-freeze", limits)
        self.assertIn("production data", limits)
        self.assertIn("HTTP parity", limits)
        self.assertIn("production implementation", limits)

        jdbc_path = ROOT / self.contract["source_contracts"][
            "migration_evidence_jdbc_test"
        ]["source"]
        jdbc = jdbc_path.read_text(encoding="utf-8")
        self.assertIn("POSTGRES_18", jdbc)
        self.assertIn("POSTGRES_16", jdbc)
        self.assertIn('"18.4"', jdbc)
        self.assertIn('"16.14"', jdbc)

    def test_09_approved_differences_are_exact_and_route_state_is_unchanged(self):
        expected_ids = {
            "P4C-LEARNING-001",
            "P4C-LEARNING-002",
            "P4C-LEARNING-003",
            "P4C-LEARNING-004",
            "P4C-LEARNING-005",
            "P4C-LEARNING-006",
        }
        self.assertEqual(expected_ids, set(self.contract["approved_differences"]["ids"]))
        approved = APPROVED_PATH.read_text(encoding="utf-8")
        for difference_id in expected_ids:
            self.assertEqual(1, approved.count(f"## {difference_id}"))

        baseline_rows = list(csv.DictReader(
            (ROOT / "docs/refactor/02-route-parity-matrix.csv")
            .read_text(encoding="utf-8")
            .splitlines()
        ))
        selected = {
            row["route_id"]: row for row in baseline_rows
            if row["route_id"] in {"6858f6fa506f", "006913d0d956"}
        }
        self.assertEqual(2, len(selected))
        for operation in self.contract["route_status"]["operations"]:
            row = selected[operation["route_id"]]
            self.assertEqual("personalbank", row["target_module"])
            self.assertEqual("pending", row["migration_status"])
            self.assertEqual("learning", operation["reviewed_owner"])
            self.assertEqual("pending", operation["migration_status"])
            self.assertFalse(operation["production_cutover"])
        route_status = self.contract["route_status"]
        self.assertFalse(route_status["controller_added"])
        self.assertFalse(route_status["security_matcher_added"])
        self.assertFalse(route_status["route_delta_added"])
        self.assertFalse(route_status["openapi_delta_added"])

    def test_10_authorization_only_opens_the_next_http_neutral_gate(self):
        changes = self.contract["change_budget"]
        for key in (
            "production_java_files_added",
            "production_java_files_modified",
            "http_controllers_added",
            "application_methods_added",
            "production_schema_files_added",
            "production_indexes_added",
            "route_delta_rows_added",
            "openapi_operations_migrated",
            "production_cutover_operations",
        ):
            self.assertEqual(0, changes[key], key)
        self.assertEqual(1, changes["ownership_overrides"])
        self.assertEqual(4, changes["test_only_java_files_added"])
        self.assertEqual(2, changes["test_only_sql_fixtures_added"])
        self.assertEqual(0, changes["historical_contract_files_modified"])
        self.assertEqual(6, changes["successor_aware_python_tests_modified"])
        self.assertEqual(3, changes["successor_aware_java_tests_modified"])
        self.assertEqual(1, changes["project_readme_files_modified"])
        self.assertEqual(1, changes["successor_bridge_python_files_added"])
        self.assertEqual(1, changes["successor_bridge_java_files_added"])
        self.assertEqual(1, changes["phase2_worm_successor_files_added"])
        self.assertEqual(1, changes["phase2_worm_successor_tests_added"])
        self.assertEqual(1, changes["versioned_worm_reports_added"])
        self.assertEqual(2, changes["phase2_verification_files_modified"])
        self.assertEqual(1, changes["phase2_readme_files_modified"])
        self.assertEqual(1, changes["phase1_verification_files_modified"])
        self.assertEqual(
            ACCEPTED_PRODUCTION_SURFACE_SHA256,
            changes["production_surface_manifest_sha256"],
        )
        self.assertEqual(
            ACCEPTED_JAVA_BUILD_CONTEXT_SHA256,
            changes["java_build_context_sha256"],
        )

        authorization = self.contract["authorization"]
        self.assertTrue(authorization["composition_contract_closed"])
        self.assertTrue(authorization["ownership_conflict_closed"])
        self.assertFalse(authorization["migration_design_closed"])
        self.assertTrue(authorization["migration_row_primitive_design_closed"])
        self.assertTrue(authorization[
            "migration_row_transaction_primitive_evidence_closed"
        ])
        self.assertFalse(authorization[
            "migration_global_preflight_evidence_closed"
        ])
        self.assertTrue(authorization["http_neutral_java_implementation"])
        self.assertFalse(authorization["operator_migration_implementation"])
        for key in (
            "real_data_migration_execution",
            "http_controller",
            "security_or_rate_limit",
            "route_or_openapi_delta",
            "production_schema_or_index",
            "production_cutover",
            "operator_migration_implementation",
            "migration_global_preflight_evidence_closed",
        ):
            self.assertFalse(authorization[key], key)
        security = self.contract["security_access_policy"]
        self.assertTrue(security["cross_bank_share_coherence_closed"])
        self.assertTrue(security["requested_bank_join_required"])
        self.assertTrue(security["share_record_bank_and_share_bank_must_match"])
        self.assertEqual(["read", "copy"], security["allowed_share_permissions"])
        self.assertEqual("deny", security["unknown_or_null_permission"])
        self.assertTrue(security["equal_expiry_is_denied"])
        self.assertEqual("DENIED", security["cross_bank_fixture_expected_outcome"])
        self.assertTrue(security["multiple_share_rows_are_not_fetchone_order_dependent"])
        worm = self.contract["worm_successor_evidence"]
        self.assertEqual(
            "versioned_successor_tip_verified_historical_reports_immutable",
            worm["status"],
        )
        self.assertEqual(
            ACCEPTED_PHASE4B_WORM_SHA256,
            worm["historical_anchor"]["sha256"],
        )
        self.assertEqual(
            ACCEPTED_PHASE4C_WORM_SHA256,
            worm["current_tip"]["sha256"],
        )
        self.assertEqual(
            ACCEPTED_JAVA_BUILD_CONTEXT_SHA256,
            worm["current_tip"]["java_build_context_sha256"],
        )
        self.assertEqual("18.4", worm["current_tip"]["postgresql_version"])
        self.assertEqual(70, worm["current_tip"]["public_base_tables"])
        self.assertEqual(617, worm["current_tip"]["public_columns"])
        self.assertTrue(worm["current_tip"]["readiness_passed"])
        self.assertTrue(worm["arbitrary_report_lookup_forbidden"])
        self.assertTrue(worm["runner_requires_explicit_versioned_report"])
        self.assertTrue(worm["historical_report_overwrite_forbidden"])
        requirements = self.contract["successor_handoff"][
            "future_read_contract_requirements"
        ]
        self.assertEqual(
            {
                "api_shape_contract_parity_test": [
                    "exposesExactTwentySevenMethodHttpNeutralShape",
                    "keepsLearningToPersonalbankApiDependencyOneWay",
                ],
                "learning_composition_test": [
                    "rechecksAccessBeforeReturningZeroView",
                    "deniedFromAnyPersonalbankCallIsTerminal",
                    "optionalFailuresRemainFieldLocal",
                    "preservesOrderedLegacyQuerySequence",
                ],
                "personalbank_facts_service_test": [
                    "rejectsCrossBankShareGrant",
                    "selectsDeterministicValidSameBankGrant",
                    "rechecksAccessForEveryFactsCall",
                ],
                "learning_adapter_test": [
                    "bindsCandidateIdsAsSinglePostgresqlIntegerArray",
                    "keepsOptionalQueriesInIndependentReadOnlyTransactions",
                ],
                "personalbank_adapter_test": [
                    "joinsShareRecordToRequestedBank",
                    "preservesMembershipDigestAndTypedIds",
                ],
                "postgresql_compatibility_it": [
                    "runsOnPostgres16And18",
                    "recoversFromTwentyFiveP02WithIndependentTransactions",
                    "preservesSchemaAndBusinessRows",
                ],
            },
            requirements["required_verification_test_methods"],
        )
        self.assertIn(
            "operator_migration_implementation",
            requirements["forbidden_authorizations"],
        )
        self.assertIn(
            "migration_global_preflight_evidence_closed",
            requirements["forbidden_authorizations"],
        )
        acceptance = self.contract["acceptance"]
        self.assertTrue(acceptance["passed"])
        self.assertEqual(27, acceptance["future_shape_method_count"])
        self.assertTrue(acceptance["routes_remain_pending"])
        self.assertFalse(acceptance["production_cutover"])

        handoff = self.contract["forward_handoff"]
        self.assertEqual(17, len(handoff["forward_additions"]))
        self.assertEqual(
            {
                "Ti-Java/docs/refactor/phase4c/README.md",
                "Ti-Java/docs/refactor/phase4c/approved-differences.md",
                "Ti-Java/docs/refactor/phase4c/data-ownership-delta.csv",
                "Ti-Java/docs/refactor/phase4c/effective-data-ownership-status.json",
                (
                    "Ti-Java/docs/refactor/phase4c/"
                    "personal-bank-user-counts-composition-contract.json"
                ),
                (
                    "Ti-Java/server/src/test/java/io/saksk/ti/integration/"
                    "Phase4cLegacyPersonalBankTagMigrationEvidenceIT.java"
                ),
                (
                    "Ti-Java/server/src/test/java/io/saksk/ti/architecture/"
                    "Phase4cSuccessorAcceptance.java"
                ),
                (
                    "Ti-Java/server/src/test/java/io/saksk/ti/learning/"
                    "infrastructure/persistence/"
                    "LegacyPersonalBankTagMigrationEvidence.java"
                ),
                (
                    "Ti-Java/server/src/test/java/io/saksk/ti/learning/"
                    "infrastructure/persistence/"
                    "LegacyPersonalBankTagMigrationEvidenceTest.java"
                ),
                (
                    "Ti-Java/server/src/test/resources/db/phase4c/"
                    "069-legacy-personal-bank-tag-migration-schema.sql"
                ),
                (
                    "Ti-Java/server/src/test/resources/db/phase4c/"
                    "070-legacy-personal-bank-tag-migration-seed.sql"
                ),
                (
                    "Ti-Java/tools/"
                    "build_phase4c_personal_bank_user_counts_composition_contract.py"
                ),
                "Ti-Java/tools/phase4c_successor_acceptance.py",
                (
                    "Ti-Java/tools/"
                    "test_phase4c_personal_bank_user_counts_composition_contract.py"
                ),
                (
                    "Ti-Java/docs/refactor/phase4c/"
                    "personal-bank-user-counts-entry-worm-evidence.json"
                ),
                "Ti-Java/tools/phase2_wormhole_successor_acceptance.py",
                "Ti-Java/tools/test_phase2_wormhole_successor_acceptance.py",
            },
            set(handoff["forward_additions"]),
        )
        accepted_history = set(
            self.contract["historical_acceptance"]["accepted_file_sha256"]
        )
        worm_overrides = set(handoff["historical_hash_overrides"])
        self.assertTrue(accepted_history.issubset(worm_overrides))
        self.assertEqual(
            {
                "infra/phase2/README.md",
                "infra/phase2/verify-local-reference-wormhole.sh",
                "infra/phase2/verify-static.sh",
                "tools/validate_phase1.py",
            },
            worm_overrides - accepted_history,
        )
        historical = handoff["historical_acceptance"]
        self.assertEqual(ACCEPTED_COMMIT, historical["accepted_commit"])
        self.assertEqual(
            ACCEPTED_PREDECESSOR_SHA256,
            historical["immutable_predecessor_sha256"],
        )


if __name__ == "__main__":
    unittest.main()
