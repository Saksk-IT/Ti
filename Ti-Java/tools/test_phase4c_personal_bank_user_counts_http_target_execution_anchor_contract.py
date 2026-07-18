#!/usr/bin/env python3
"""Fail-closed tests for the Phase 4C target-execution external anchor."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

try:
    from tools import (
        build_phase4c_personal_bank_user_counts_http_target_execution_anchor_contract
        as builder,
    )
    from tools import phase4c_http_target_execution_anchor_successor_acceptance as acceptance
except ModuleNotFoundError:  # Direct discovery from tools/.
    import build_phase4c_personal_bank_user_counts_http_target_execution_anchor_contract as builder
    import phase4c_http_target_execution_anchor_successor_acceptance as acceptance


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = ROOT.parent
CONTRACT_PATH = ROOT / acceptance.CONTRACT_RELATIVE


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Phase4cTargetExecutionAnchorContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        cls.generated_without_git = builder.build_contract(ROOT)

    def test_01_builder_is_deterministic_and_matches_checked_in_bytes(self) -> None:
        self.assertEqual(self.contract, self.generated_without_git)
        self.assertEqual(acceptance.CONTRACT_SHA256, sha256(CONTRACT_PATH))
        self.assertEqual(
            acceptance.CONTRACT_PAYLOAD_SHA256,
            self.contract["document_payload_sha256"],
        )
        self.assertEqual(
            acceptance.CONTRACT_PAYLOAD_SHA256,
            builder.document_payload_sha256(self.contract),
        )
        self.assertEqual(
            self.generated_without_git,
            builder.build_contract(
                ROOT,
                repository_root=REPOSITORY_ROOT,
                replay_phase2_fixed_acceptance=True,
            ),
        )

    def test_02_load_is_git_independent_and_explicit_git_replay_passes(self) -> None:
        with patch.object(
            acceptance,
            "validate_git_anchor",
            side_effect=AssertionError("Git must not be consulted"),
        ):
            self.assertEqual(self.contract, acceptance.load(ROOT))
        self.assertEqual(
            self.contract,
            acceptance.load(ROOT, repository_root=REPOSITORY_ROOT),
        )
        self.assertEqual(
            self.contract,
            acceptance.load(ROOT, replay_phase2_fixed_acceptance=True),
        )

        bridge_paths = {
            acceptance.ANCHOR_ARTIFACTS["python_successor_bridge"][0],
            acceptance.ANCHOR_ARTIFACTS["java_successor_bridge"][0],
        }
        original_acceptance_file = acceptance._fixed_regular_file

        def reject_current_bridges(root: Path, relative: str) -> Path:
            if relative in bridge_paths:
                raise AssertionError("current bridge bytes must not be read")
            return original_acceptance_file(root, relative)

        with patch.object(
            acceptance,
            "_fixed_regular_file",
            side_effect=reject_current_bridges,
        ):
            self.assertEqual(self.contract, acceptance.load(ROOT))

        original_builder_file = builder.fixed_regular_file

        def reject_builder_bridges(root: Path, relative: str) -> Path:
            if relative in bridge_paths:
                raise AssertionError("builder must not read current bridge bytes")
            return original_builder_file(root, relative)

        with patch.object(
            builder,
            "fixed_regular_file",
            side_effect=reject_builder_bridges,
        ):
            self.assertEqual(self.contract, builder.build_contract(ROOT))

    def test_03_plain_import_build_and_load_never_import_historical_bridges(self) -> None:
        script = r'''
import importlib.abc
import sys
from pathlib import Path

forbidden = {
    "tools.phase2_wormhole_successor_acceptance",
    "phase2_wormhole_successor_acceptance",
    "tools.phase4c_http_target_execution_successor_acceptance",
    "phase4c_http_target_execution_successor_acceptance",
    "tools.phase4c_read_successor_acceptance",
    "phase4c_read_successor_acceptance",
}

class Blocker(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        if fullname in forbidden:
            raise RuntimeError(f"forbidden import: {fullname}")
        return None

sys.meta_path.insert(0, Blocker())
from tools import build_phase4c_personal_bank_user_counts_http_target_execution_anchor_contract as builder
from tools import phase4c_http_target_execution_anchor_successor_acceptance as acceptance
root = Path.cwd()
assert builder.build_contract(root)["contract_id"] == builder.CONTRACT_ID
assert acceptance.load(root)["contract_id"] == acceptance.CONTRACT_ID
assert forbidden.isdisjoint(sys.modules)
print("plain-import-build-load=ok")
'''
        completed = subprocess.run(
            [sys.executable, "-B", "-c", script],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertIn("plain-import-build-load=ok", completed.stdout)

    def test_04_git_anchor_fixes_commit_tree_parent_subtree_and_ten_blobs(self) -> None:
        anchor = self.contract["git_anchor"]
        self.assertEqual(acceptance.GIT_OBJECT_FORMAT, anchor["object_format"])
        self.assertEqual(acceptance.GIT_COMMIT_OID, anchor["commit_oid"])
        self.assertEqual(acceptance.GIT_ROOT_TREE_OID, anchor["root_tree_oid"])
        self.assertEqual(acceptance.GIT_PARENT_OID, anchor["parent_oid"])
        self.assertEqual(acceptance.TI_JAVA_TREE_OID, anchor["ti_java_tree_oid"])
        self.assertEqual(acceptance.GIT_AUTHORED_AT, anchor["authored_at"])
        self.assertEqual(acceptance.GIT_COMMITTED_AT, anchor["committed_at"])
        self.assertEqual(acceptance.GIT_SUBJECT, anchor["subject"])
        self.assertEqual(set(acceptance.ANCHOR_ARTIFACTS), set(anchor["artifacts"]))
        self.assertEqual(10, len(anchor["artifacts"]))
        acceptance.validate_git_anchor(REPOSITORY_ROOT)

    def test_05_git_commands_disable_replace_refs_and_optional_locks(self) -> None:
        completed = SimpleNamespace(returncode=0, stdout=b"ok\n", stderr=b"")
        with patch.object(acceptance.subprocess, "run", return_value=completed) as run:
            self.assertEqual(
                b"ok\n",
                acceptance._run_read_only_git(REPOSITORY_ROOT, "version"),
            )
        environment = run.call_args.kwargs["env"]
        self.assertEqual("1", environment["GIT_NO_REPLACE_OBJECTS"])
        self.assertEqual("0", environment["GIT_OPTIONAL_LOCKS"])
        self.assertEqual("cat", environment["GIT_PAGER"])
        self.assertEqual("C", environment["LC_ALL"])

        with patch.object(builder.subprocess, "run", return_value=completed) as build_run:
            self.assertEqual(
                b"ok\n",
                builder._run_read_only_git(REPOSITORY_ROOT, "version"),
            )
        build_environment = build_run.call_args.kwargs["env"]
        self.assertEqual("1", build_environment["GIT_NO_REPLACE_OBJECTS"])
        self.assertEqual("0", build_environment["GIT_OPTIONAL_LOCKS"])

    def test_06_manifest_binds_the_same_ten_committed_inputs_and_sixty_leaves(self) -> None:
        manifest = json.loads(
            (ROOT / builder.JUNIT_MANIFEST_RELATIVE).read_text(encoding="utf-8")
        )
        self.assertEqual(set(builder.ANCHOR_ARTIFACTS), set(manifest["source_inputs"]))
        for name, descriptor in builder.ANCHOR_ARTIFACTS.items():
            source = manifest["source_inputs"][name]
            self.assertEqual(descriptor["ti_java_relative_path"], source["path"])
            self.assertEqual(descriptor["sha256"], source["sha256"])
        self.assertEqual(60, manifest["result"]["totals"]["tests"])
        self.assertEqual(60, manifest["result"]["totals"]["passed"])
        self.assertEqual(60, len(manifest["result"]["leaves"]))
        self.assertEqual(
            builder.JUNIT_LEAF_PAYLOAD_SHA256,
            builder.sha256_json(manifest["result"]["leaves"]),
        )
        self.assertFalse(manifest["confidentiality"]["independently_signed_provenance"])
        self.assertTrue(manifest["confidentiality"]["sensitive_output_scan_passed"])
        self.assertFalse(manifest["confidentiality"]["repository_tamper_evident"])
        self.assertFalse(
            manifest["confidentiality"]["manifest_bytes_external_git_anchor_complete"]
        )
        self.assertTrue(
            manifest["confidentiality"]["post_push_successor_anchor_required"]
        )

    def test_07_full_phase2_fixed_acceptance_and_fifth_worm_stay_closed(self) -> None:
        worm = self.contract["worm_evidence"]
        self.assertEqual(5, worm["fixed_chain_node_count"])
        self.assertEqual(builder.WORM_SHA256, worm["sha256"])
        self.assertEqual(
            builder.WORM_PREDECESSOR_SHA256,
            worm["predecessor_sha256"],
        )
        self.assertEqual(
            builder.CANONICAL_SCHEMA_DUMP_SHA256,
            worm["canonical_schema_dump_sha256"],
        )
        self.assertTrue(worm["phase2_fixed_acceptance_closed"])
        self.assertFalse(worm["temporary_privilege"])
        self.assertTrue(worm["sensitive_information_scan_passed"])
        self.assertFalse(worm["new_worm"])
        self.assertFalse(worm["new_worm_report_created"])
        self.assertTrue(worm["production_build_context_unchanged"])

    def test_08_only_external_anchor_and_normalized_junit_binding_are_opened(self) -> None:
        external = self.contract["external_anchor"]
        self.assertTrue(external["external_git_and_bridge_bytes_anchor_complete"])
        self.assertTrue(external["current_anchor_bridge_self_authorization_forbidden"])
        authorization = self.contract["authorization"]
        self.assertTrue(authorization["external_git_and_bridge_bytes_anchor_complete"])
        self.assertTrue(authorization["normalized_junit_manifest_bound"])
        self.assertTrue(authorization["junit_manifest_tests_passed"])
        self.assertFalse(
            authorization["junit_manifest_bytes_external_git_anchor_complete"]
        )
        self.assertTrue(
            authorization["post_push_junit_manifest_successor_anchor_required"]
        )
        self.assertFalse(
            self.contract["junit_manifest"]
            ["manifest_bytes_external_git_anchor_complete"]
        )
        self.assertTrue(
            self.contract["junit_manifest"]["post_push_successor_anchor_required"]
        )
        for field in (
            "typed_parity_review_complete",
            "full_target_parity_closed",
            "route_migration_eligible",
            "two_legacy_get_routes_migrated",
            "production_cutover",
        ):
            self.assertFalse(authorization[field], field)
        acceptance_claims = self.contract["acceptance"]
        self.assertEqual(11, acceptance_claims["migrated_operation_count"])
        self.assertEqual(600, acceptance_claims["pending_operation_count"])
        self.assertEqual(0, acceptance_claims["production_cutover_operation_count"])

    def test_09_unknown_and_current_anchor_sources_cannot_self_authorize(self) -> None:
        self.assertIsNone(acceptance.anchored_sha256(
            "tools/phase4c_http_target_execution_anchor_successor_acceptance.py"
        ))
        self.assertIsNone(acceptance.anchored_sha256(
            "tools/build_phase4c_personal_bank_user_counts_http_"
            "target_execution_anchor_contract.py"
        ))
        self.assertIsNone(acceptance.anchored_sha256("unknown/self-authorized"))
        self.assertEqual(
            builder.PREDECESSOR_SHA256,
            acceptance.anchored_sha256(builder.PREDECESSOR_RELATIVE),
        )
        forbidden = {
            acceptance.CONTRACT_RELATIVE,
            "tools/phase4c_http_target_execution_anchor_successor_acceptance.py",
            "tools/test_phase4c_personal_bank_user_counts_http_"
            "target_execution_anchor_contract.py",
        }
        self.assertTrue(forbidden.isdisjoint(
            descriptor[0] for descriptor in acceptance.ANCHOR_ARTIFACTS.values()
        ))

    def test_10_contract_tampering_and_overclaims_are_rejected(self) -> None:
        mutations = {
            "commit": lambda value: value["git_anchor"].__setitem__(
                "commit_oid", "0" * 40
            ),
            "tree": lambda value: value["git_anchor"].__setitem__(
                "root_tree_oid", "0" * 40
            ),
            "parent": lambda value: value["git_anchor"].__setitem__(
                "parent_oid", "0" * 40
            ),
            "blob": lambda value: value["git_anchor"]["artifacts"]
            ["target_execution_contract"].__setitem__("git_blob_oid", "0" * 40),
            "artifact path": lambda value: value["git_anchor"]["artifacts"]
            ["target_execution_contract"].__setitem__(
                "repository_path", "Ti-Java/unknown"
            ),
            "extra artifact": lambda value: value["git_anchor"]["artifacts"].__setitem__(
                "self_authorized", deepcopy(
                    value["git_anchor"]["artifacts"]["target_execution_contract"]
                ),
            ),
            "typed parity": lambda value: value["authorization"].__setitem__(
                "typed_parity_review_complete", True
            ),
            "full parity": lambda value: value["authorization"].__setitem__(
                "full_target_parity_closed", True
            ),
            "route migration": lambda value: value["authorization"].__setitem__(
                "route_migration_eligible", True
            ),
            "manifest external anchor": lambda value: value["authorization"].__setitem__(
                "junit_manifest_bytes_external_git_anchor_complete", True
            ),
            "manifest successor gate": lambda value: value["acceptance"].__setitem__(
                "post_push_junit_manifest_successor_anchor_required", False
            ),
            "cutover": lambda value: value["authorization"].__setitem__(
                "production_cutover", True
            ),
            "canonical schema": lambda value: value["worm_evidence"].__setitem__(
                "canonical_schema_dump_sha256", "0" * 64
            ),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                changed = deepcopy(self.contract)
                mutate(changed)
                with self.assertRaises(AssertionError):
                    acceptance.validate_contract(changed, ROOT)

    def test_11_no_dynamic_discovery_or_mutable_ref_authority_exists(self) -> None:
        sources = [
            Path(builder.__file__).read_text(encoding="utf-8"),
            Path(acceptance.__file__).read_text(encoding="utf-8"),
        ]
        for source in sources:
            self.assertNotIn(".glob(", source)
            self.assertNotIn(".rglob(", source)
            self.assertNotIn("refs/replace", source)
            self.assertIn('"GIT_NO_REPLACE_OBJECTS": "1"', source)
        anchor = self.contract["git_anchor"]
        self.assertTrue(anchor["mutable_ref_is_not_validation_authority"])
        self.assertTrue(anchor["artifact_paths_are_code_fixed"])
        self.assertTrue(self.contract["external_anchor"]
                        ["arbitrary_git_object_lookup_forbidden"])
        self.assertTrue(self.contract["external_anchor"]
                        ["dynamic_source_discovery_forbidden"])


if __name__ == "__main__":
    unittest.main()
