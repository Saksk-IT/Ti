#!/usr/bin/env python3
"""Fail-closed tests for the Phase 6 source-successor external anchor."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock


try:
    from tools import build_phase6_web_foundation_source_successor_anchor_contract as builder
    from tools import phase6_web_foundation_source_successor_anchor_acceptance as acceptance
except ModuleNotFoundError:
    import build_phase6_web_foundation_source_successor_anchor_contract as builder
    import phase6_web_foundation_source_successor_anchor_acceptance as acceptance


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = ROOT.parent


class Phase6WebFoundationSourceSuccessorAnchorContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = acceptance.load(ROOT)

    def _minimal_copy(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name) / "Ti-Java"
        root.mkdir()
        for relative in acceptance.minimal_fixture_paths():
            source = ROOT / relative
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        return temporary, root

    def test_01_builder_acceptance_and_canonical_contract_match(self) -> None:
        built = builder.build_contract(ROOT, repository_root=REPOSITORY_ROOT)
        self.assertNotEqual(self.contract, built)
        payload = builder.serialized_contract(self.contract)
        self.assertEqual(acceptance.CONTRACT_SHA256,
                         builder.sha256_bytes(payload))
        self.assertEqual(acceptance.CONTRACT_BYTE_COUNT, len(payload))
        self.assertEqual(acceptance.CONTRACT_PAYLOAD_SHA256,
                         self.contract["document_payload_sha256"])

    def test_02_fixed_40a_checkpoint_replays_exact_git_facts(self) -> None:
        builder.validate_git_checkpoint(REPOSITORY_ROOT)
        acceptance.validate_git_checkpoint(REPOSITORY_ROOT)
        checkpoint = self.contract["git_checkpoint"]
        self.assertEqual(11, checkpoint["changed_path_count"])
        self.assertEqual(6, checkpoint["added_count"])
        self.assertEqual(5, checkpoint["modified_count"])
        self.assertEqual(2_297, checkpoint["inserted_line_count"])
        self.assertEqual(28, checkpoint["deleted_line_count"])
        self.assertTrue(checkpoint["exact_eleven_path_delta"])
        self.assertEqual(set(acceptance.CHECKPOINT_PATHS),
                         set(checkpoint["artifacts"]))

    def test_03_checkpoint_groups_are_exact_disjoint_partition(self) -> None:
        controls = set(acceptance.PREDECESSOR_CONTROL_SOURCES)
        bridges = set(acceptance.TYPED_ANCHOR_BRIDGE_SOURCES)
        self.assertFalse(controls & bridges)
        self.assertEqual(set(acceptance.CHECKPOINT_PATHS), controls | bridges)
        self.assertEqual(list(acceptance.PREDECESSOR_CONTROL_SOURCES),
                         self.contract["predecessor_control_source_anchor"]
                         ["source_paths"])
        self.assertEqual(list(acceptance.TYPED_ANCHOR_BRIDGE_SOURCES),
                         self.contract["typed_anchor_bridge_source_anchor"]
                         ["source_paths"])

    def test_04_nine_successors_are_fixed_without_unknown_fallback(self) -> None:
        self.assertEqual(9, len(acceptance.SOURCE_PATHS))
        self.assertEqual(set(acceptance.SOURCE_PATHS), set(
            self.contract["source_successors"]["overrides"]
        ))
        for relative, descriptor in acceptance.SOURCE_SUCCESSORS.items():
            with self.subTest(relative=relative):
                self.assertEqual(descriptor["accepted_sha256"],
                                 acceptance.accepted_sha256(relative))
                expected = descriptor["successor_sha256"]
                if relative in acceptance.TAG_PREFLIGHT_DELEGATED_PATHS:
                    expected = (
                        acceptance
                        ._load_tag_preflight_source_successor_acceptance()
                        .successor_sha256(ROOT, relative)
                    )
                self.assertEqual(
                    expected, acceptance.successor_sha256(ROOT, relative)
                )
        self.assertIsNone(acceptance.accepted_sha256("tools/unknown.py"))
        self.assertIsNone(acceptance.successor_sha256(ROOT, "tools/unknown.py"))

    def test_05_exactly_five_checkpoint_sources_have_local_successors(self) -> None:
        changed = {
            relative for relative, descriptor
            in acceptance.SOURCE_SUCCESSORS.items()
            if descriptor["changed_after_checkpoint"]
        }
        self.assertEqual({
            "server/src/test/java/io/saksk/ti/architecture/"
            "Phase6WebFoundationSourceSuccessorAcceptance.java",
            "server/src/test/java/io/saksk/ti/architecture/"
            "Phase6WebFoundationSourceSuccessorContractParityTest.java",
            "tools/build_phase6_web_foundation_source_successor_contract.py",
            "tools/phase6_web_foundation_source_successor_acceptance.py",
            "tools/test_phase6_web_foundation_source_successor_contract.py",
        }, changed)
        for relative in changed:
            descriptor = acceptance.SOURCE_SUCCESSORS[relative]
            self.assertNotEqual(descriptor["accepted_sha256"],
                                descriptor["successor_sha256"])

    def test_06_gitless_minimal_fixture_passes(self) -> None:
        temporary, root = self._minimal_copy()
        with temporary:
            self.assertEqual(self.contract, acceptance.load(root))
            self.assertNotEqual(
                self.contract,
                builder.build_contract(root, repository_root=None),
            )
            self.assertFalse((Path(temporary.name) / ".git").exists())

    def test_07_each_successor_tamper_fails_closed(self) -> None:
        for relative in acceptance.SOURCE_PATHS:
            with self.subTest(relative=relative):
                temporary, root = self._minimal_copy()
                with temporary:
                    path = root / relative
                    path.write_bytes(path.read_bytes() + b"\n")
                    with self.assertRaisesRegex(
                        AssertionError, "successor bytes|tag-preflight successor"
                    ):
                        acceptance.successor_sha256(root, relative)

    def test_08_fixed_authority_inputs_are_tamper_evident(self) -> None:
        for relative in (
            acceptance.CONTRACT_RELATIVE,
            acceptance.PREDECESSOR_RELATIVE,
            acceptance.ROUTE_STATUS_RELATIVE,
            acceptance.HASHER_RELATIVE,
            acceptance.DOCKERFILE_RELATIVE,
            acceptance.WORM_RELATIVE,
        ):
            with self.subTest(relative=relative):
                temporary, root = self._minimal_copy()
                with temporary:
                    path = root / relative
                    path.write_bytes(path.read_bytes() + b"\n")
                    with self.assertRaisesRegex(
                        AssertionError, "fixed bytes|tag-preflight successor"
                    ):
                        acceptance.load(root)

    def test_09_symlink_and_escape_paths_are_rejected(self) -> None:
        temporary, root = self._minimal_copy()
        with temporary:
            relative = acceptance.SOURCE_PATHS[0]
            path = root / relative
            payload = path.read_bytes()
            path.unlink()
            elsewhere = root / "elsewhere.md"
            elsewhere.write_bytes(payload)
            path.symlink_to(elsewhere)
            with self.assertRaisesRegex(AssertionError, "symlink"):
                acceptance.successor_sha256(root, relative)
        with self.assertRaisesRegex(AssertionError, "escapes root"):
            acceptance._fixed_regular_file(ROOT, "../README.md")
        with self.assertRaisesRegex(AssertionError, "escapes root"):
            acceptance._fixed_regular_file(ROOT, "/tmp/README.md")

    def test_10_route_phase_and_cutover_overclaims_are_rejected(self) -> None:
        mutations = (
            ("effective_authority", "migrated_operation_count", 14),
            ("effective_authority", "pending_operation_count", 597),
            ("effective_authority", "production_cutover_operation_count", 1),
            ("authorization", "phase6_complete", True),
            ("authorization", "production_cutover", True),
            ("authorization", "operator_authorized", True),
            ("acceptance", "phase6_complete", True),
        )
        for section, field, value in mutations:
            with self.subTest(section=section, field=field):
                changed = deepcopy(self.contract)
                changed[section][field] = value
                with self.assertRaises(AssertionError):
                    acceptance.validate(changed, ROOT)

    def test_11_anchor_completion_semantics_do_not_overclaim_current_node(self) -> None:
        authorization = self.contract["authorization"]
        self.assertTrue(authorization[
            "predecessor_source_successor_checkpoint_external_git_anchor_complete"
        ])
        self.assertFalse(authorization[
            "current_successor_bytes_external_git_anchor_complete"
        ])
        for descriptor in self.contract["source_successors"]["overrides"].values():
            self.assertFalse(descriptor[
                "current_successor_bytes_external_git_anchor_complete"
            ])

    def test_12_java_boundary_reuses_fixed_worm_without_production_drift(self) -> None:
        boundary = self.contract["java_build_context_boundary"]
        self.assertTrue(boundary["server_src_main_tree_unchanged_from_parent"])
        self.assertTrue(boundary["web_tree_unchanged_from_parent"])
        self.assertFalse(boundary["new_worm_node_required"])
        self.assertEqual(acceptance.JAVA_BUILD_CONTEXT_SHA256,
                         boundary["java_build_context_sha256"])

    def test_13_current_controls_are_explicit_and_self_excluded(self) -> None:
        trust = self.contract["current_node_trust_boundary"]
        self.assertEqual(list(acceptance.CURRENT_CONTROL_SOURCES),
                         trust["control_sources"])
        self.assertFalse(set(acceptance.CURRENT_CONTROL_SOURCES)
                         & set(acceptance.SOURCE_PATHS))
        self.assertTrue(trust["control_sources_excluded_from_self_authority"])
        self.assertFalse(trust["control_sources_external_git_anchor_complete"])
        self.assertFalse(trust["independently_signed_provenance"])

    def test_14_dynamic_discovery_and_live_head_authority_are_forbidden(self) -> None:
        for relative in (
            "tools/build_phase6_web_foundation_source_successor_anchor_contract.py",
            "tools/phase6_web_foundation_source_successor_anchor_acceptance.py",
        ):
            source = (ROOT / relative).read_text(encoding="utf-8")
            for forbidden in (
                ".glob(", ".rglob(", "git ls-files", "source_contracts.keys()",
                'GIT_COMMIT_OID = "HEAD"',
            ):
                self.assertNotIn(forbidden, source)

    def test_15_stage_a_bridge_is_one_way_and_replays_stage_b_git(self) -> None:
        python_source = (ROOT / "tools/phase6_web_foundation_"
                         "source_successor_acceptance.py").read_text("utf-8")
        builder_source = (ROOT / "tools/build_phase6_web_foundation_"
                          "source_successor_contract.py").read_text("utf-8")
        java_source = (ROOT / "server/src/test/java/io/saksk/ti/architecture/"
                       "Phase6WebFoundationSourceSuccessorAcceptance.java").read_text(
                           "utf-8"
                       )
        self.assertIn("anchor_validate_git(repository_root)", python_source)
        self.assertIn("anchor_validate_git(repository_root)", builder_source)
        self.assertIn("SourceSuccessorAnchorAcceptance", java_source)
        anchor_source = (ROOT / "tools/phase6_web_foundation_"
                         "source_successor_anchor_acceptance.py").read_text("utf-8")
        self.assertNotIn("phase6_web_foundation_source_successor_acceptance as",
                         anchor_source)

    def test_16_contract_payload_is_canonical(self) -> None:
        payload = {key: value for key, value in self.contract.items()
                   if key != "document_payload_sha256"}
        self.assertEqual(
            acceptance.CONTRACT_PAYLOAD_SHA256,
            acceptance._sha256_bytes(
                acceptance._canonical_json(payload).encode("utf-8")
            ),
        )

    def test_17_typed_bridge_sources_delegate_only_to_fixed_tag_preflight(
        self,
    ) -> None:
        delegated_bridges = {
            "server/src/test/java/io/saksk/ti/architecture/"
            "Phase4cHttpTypedNormalizationAnchorSuccessorAcceptance.java",
            "server/src/test/java/io/saksk/ti/architecture/"
            "Phase4cPersonalBankUserCountsHttpTypedNormalizationAnchor"
            "ContractParityTest.java",
            "tools/phase4c_http_typed_normalization_anchor_"
            "successor_acceptance.py",
            "tools/test_phase4c_personal_bank_user_counts_http_typed_"
            "normalization_anchor_contract.py",
        }
        self.assertTrue(delegated_bridges.issubset(
            acceptance.TAG_PREFLIGHT_DELEGATED_PATHS
        ))
        tag_successor = (
            acceptance._load_tag_preflight_source_successor_acceptance()
        )
        artifacts = self.contract["typed_anchor_bridge_source_anchor"]["artifacts"]
        for relative in delegated_bridges:
            self.assertEqual(
                artifacts[relative]["sha256"],
                tag_successor.accepted_sha256(relative),
            )
            self.assertEqual(
                acceptance._sha256_bytes((ROOT / relative).read_bytes()),
                tag_successor.successor_sha256(ROOT, relative),
            )

    def test_18_typed_bridge_tamper_and_internal_import_failure_fail_closed(
        self,
    ) -> None:
        temporary, root = self._minimal_copy()
        with temporary:
            relative = (
                "tools/phase4c_http_typed_normalization_anchor_"
                "successor_acceptance.py"
            )
            path = root / relative
            path.write_bytes(path.read_bytes() + b"\n")
            with self.assertRaisesRegex(
                AssertionError, "tag-preflight successor|typed bridge"
            ):
                acceptance.load(root)

        missing = ModuleNotFoundError("missing internal dependency")
        missing.name = "internal_dependency"
        with mock.patch.object(
            acceptance.importlib,
            "import_module",
            side_effect=missing,
        ):
            with self.assertRaisesRegex(AssertionError, "dependency"):
                acceptance._load_tag_preflight_source_successor_acceptance()


if __name__ == "__main__":
    unittest.main()
