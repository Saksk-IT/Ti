#!/usr/bin/env python3
"""Fail-closed tests for the typed-normalization external Git anchor."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock


try:
    from tools import (
        build_phase4c_personal_bank_user_counts_http_typed_normalization_anchor_contract
        as builder,
    )
    from tools import (
        phase4c_http_typed_normalization_anchor_successor_acceptance
        as acceptance,
    )
except ModuleNotFoundError:
    import build_phase4c_personal_bank_user_counts_http_typed_normalization_anchor_contract as builder
    import phase4c_http_typed_normalization_anchor_successor_acceptance as acceptance


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = ROOT.parent


class TypedNormalizationAnchorContractTest(unittest.TestCase):
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

    def test_01_builder_and_acceptance_match_canonical_contract(self) -> None:
        self.assertEqual(
            acceptance.CONTRACT_PAYLOAD_SHA256,
            self.contract["document_payload_sha256"],
        )
        self.assertEqual(
            acceptance.CONTRACT_SHA256,
            builder.sha256_bytes(builder.serialized_contract(self.contract)),
        )
        self.assertEqual(
            acceptance.CONTRACT_BYTE_COUNT,
            len(builder.serialized_contract(self.contract)),
        )
        with self.assertRaisesRegex(AssertionError, "successor drifted"):
            builder.build_contract(ROOT, repository_root=REPOSITORY_ROOT)

    def test_02_fixed_git_checkpoint_replay_passes(self) -> None:
        builder.validate_git_checkpoint(REPOSITORY_ROOT)
        acceptance.validate_git_checkpoint(REPOSITORY_ROOT)

    def test_03_exact_26_path_commit_and_six_source_anchor_are_fixed(self) -> None:
        checkpoint = self.contract["git_checkpoint"]
        self.assertEqual(26, len(checkpoint["artifacts"]))
        self.assertEqual(acceptance.GIT_COMMIT_OID, checkpoint["commit_oid"])
        self.assertEqual(list(acceptance.GIT_PATHS), checkpoint["exact_changed_paths"])
        self.assertEqual(
            {"A": 12, "M": 14},
            {
                kind: sum(
                    descriptor["change_type"] == kind
                    for descriptor in checkpoint["artifacts"].values()
                )
                for kind in ("A", "M")
            },
        )
        anchor = self.contract["typed_normalization_source_anchor"]
        self.assertEqual(6, anchor["source_count"])
        self.assertEqual(280_664, anchor["source_total_bytes"])
        self.assertEqual(
            sorted(acceptance.TYPED_SOURCE_PATHS),
            anchor["source_paths"],
        )
        self.assertEqual(
            set(acceptance.TYPED_SOURCE_PATHS),
            set(anchor["artifacts"]),
        )

    def test_04_anchor_closes_only_predecessor_sources(self) -> None:
        anchor = self.contract["typed_normalization_source_anchor"]
        self.assertTrue(
            anchor["predecessor_current_sources_external_git_anchor_complete"]
        )
        self.assertTrue(anchor["current_anchor_sources_excluded_from_self_authority"])
        self.assertFalse(
            anchor["current_anchor_source_bytes_external_git_anchor_complete"]
        )
        authorization = self.contract["authorization"]
        self.assertTrue(authorization["typed_execution_normalization_complete"])
        self.assertTrue(
            authorization[
                "typed_normalization_checkpoint_and_six_excluded_sources_"
                "external_git_anchor_complete"
            ]
        )
        for field in (
            "typed_parity_review_complete",
            "pg16_pg18_termination_fingerprints_complete",
            "real_tomcat_complete_response_header_matrix_complete",
            "same_service_redis_outage_and_recovery_complete",
            "full_target_parity_closed",
            "route_migration_eligible",
            "production_cutover",
        ):
            self.assertFalse(authorization[field], field)
        self.assertEqual(11, self.contract["acceptance"]["migrated_operation_count"])
        self.assertEqual(600, self.contract["acceptance"]["pending_operation_count"])
        self.assertEqual(
            0,
            self.contract["acceptance"]["production_cutover_operation_count"],
        )

    def test_05_successor_lookup_is_exact_and_tamper_evident(self) -> None:
        self.assertEqual(
            set(acceptance.SUCCESSOR_PATHS),
            set(self.contract["historical_source_successors"]["overrides"]),
        )
        for relative in acceptance.SUCCESSOR_PATHS:
            self.assertEqual(
                acceptance.CHECKPOINT_CHANGES[relative]["sha256"],
                acceptance.accepted_sha256(relative),
            )
            expected = acceptance.SUCCESSOR_SHA256[relative]
            if relative in acceptance.TAG_PREFLIGHT_SOURCE_SUCCESSOR_PATHS:
                expected = (
                    acceptance
                    ._load_tag_preflight_source_successor_acceptance()
                    .successor_sha256(ROOT, relative)
                )
            elif relative in acceptance.PHASE6_SOURCE_SUCCESSOR_PATHS:
                expected = (
                    acceptance
                    ._load_phase6_source_successor_acceptance()
                    .successor_sha256(ROOT, relative)
                )
            self.assertEqual(expected, acceptance.successor_sha256(ROOT, relative))
        self.assertIsNone(acceptance.accepted_sha256("tools/unknown.py"))
        self.assertIsNone(acceptance.successor_sha256(ROOT, "tools/unknown.py"))

        temporary, root = self._minimal_copy()
        with temporary:
            relative = "infra/phase2/README.md"
            path = root / relative
            path.write_bytes(path.read_bytes() + b"\n")
            with self.assertRaisesRegex(
                AssertionError, "fixed bytes|tag-preflight successor"
            ):
                acceptance.successor_sha256(root, relative)

    def test_05b_only_three_paths_delegate_to_fixed_phase6_successor(self) -> None:
        self.assertEqual(
            {
                "README.md",
                "docs/refactor/05-progress.md",
                "docs/refactor/phase4c/README.md",
            },
            set(acceptance.PHASE6_SOURCE_SUCCESSOR_PATHS),
        )
        successor = acceptance._load_phase6_source_successor_acceptance()
        for relative in acceptance.PHASE6_SOURCE_SUCCESSOR_PATHS:
            self.assertEqual(
                acceptance.SUCCESSOR_SHA256[relative],
                successor.accepted_sha256(relative),
            )
            self.assertNotEqual(
                acceptance.SUCCESSOR_SHA256[relative],
                acceptance.successor_sha256(ROOT, relative),
            )

    def test_05c_only_exact_nodea_paths_delegate_to_tag_preflight(self) -> None:
        self.assertEqual(
            {
                "infra/phase2/README.md",
                "infra/phase2/verify-static.sh",
                "tools/phase2_wormhole_successor_acceptance.py",
                "tools/test_phase2_wormhole_successor_acceptance.py",
                "tools/phase4c_http_typed_normalization_"
                "successor_acceptance.py",
                "server/src/test/java/io/saksk/ti/architecture/"
                "Phase4cHttpTypedNormalizationSuccessorAcceptance.java",
                "tools/test_phase4c_personal_bank_user_counts_http_"
                "target_execution_post_push_contract.py",
                "tools/test_phase4c_personal_bank_user_counts_http_"
                "target_execution_post_push_anchor_contract.py",
            },
            set(acceptance.TAG_PREFLIGHT_SOURCE_SUCCESSOR_PATHS),
        )
        successor = acceptance._load_tag_preflight_source_successor_acceptance()
        for relative in acceptance.TAG_PREFLIGHT_SOURCE_SUCCESSOR_PATHS:
            self.assertEqual(
                acceptance.SUCCESSOR_SHA256[relative],
                successor.accepted_sha256(relative),
            )
            self.assertNotEqual(
                acceptance.SUCCESSOR_SHA256[relative],
                acceptance.successor_sha256(ROOT, relative),
            )

    def test_06_gitless_minimal_fixture_passes(self) -> None:
        temporary, root = self._minimal_copy()
        with temporary:
            self.assertEqual(self.contract, acceptance.load(root))
            with self.assertRaisesRegex(AssertionError, "successor drifted"):
                builder.build_contract(root, repository_root=None)
            self.assertFalse((Path(temporary.name) / ".git").exists())

    def test_07_predecessor_tamper_and_symlink_are_rejected(self) -> None:
        temporary, root = self._minimal_copy()
        with temporary:
            predecessor = root / acceptance.PREDECESSOR_RELATIVE
            predecessor.write_bytes(predecessor.read_bytes() + b"\n")
            with self.assertRaisesRegex(AssertionError, "fixed bytes drifted"):
                acceptance.load(root)

        temporary, root = self._minimal_copy()
        with temporary:
            relative = acceptance.TYPED_MANIFEST_RELATIVE
            path = root / relative
            original = path.read_bytes()
            path.unlink()
            elsewhere = root / "elsewhere.json"
            elsewhere.write_bytes(original)
            path.symlink_to(elsewhere)
            with self.assertRaisesRegex(AssertionError, "symlink"):
                acceptance.load(root)

    def test_08_structural_tamper_and_route_overclaim_are_rejected(self) -> None:
        changed = deepcopy(self.contract)
        changed["git_checkpoint"]["artifacts"].pop(next(iter(
            changed["git_checkpoint"]["artifacts"]
        )))
        with self.assertRaisesRegex(AssertionError, "artifact set"):
            acceptance.validate(changed, ROOT)

        changed = deepcopy(self.contract)
        changed["authorization"]["route_migration_eligible"] = True
        with self.assertRaisesRegex(AssertionError, "overclaims"):
            acceptance.validate(changed, ROOT)

        changed = deepcopy(self.contract)
        changed["typed_normalization_source_anchor"][
            "current_anchor_source_bytes_external_git_anchor_complete"
        ] = True
        with self.assertRaisesRegex(AssertionError, "trust boundary"):
            acceptance.validate(changed, ROOT)

    def test_09_current_anchor_sources_are_not_successor_authority(self) -> None:
        for relative in acceptance.CURRENT_ANCHOR_SOURCES:
            self.assertNotIn(relative, acceptance.SUCCESSOR_PATHS)
            self.assertIsNone(acceptance.accepted_sha256(relative))
            self.assertIsNone(acceptance.successor_sha256(ROOT, relative))

    def test_10_builder_and_acceptance_forbid_dynamic_discovery(self) -> None:
        for path in (
            ROOT / "tools/build_phase4c_personal_bank_user_counts_http_"
            "typed_normalization_anchor_contract.py",
            ROOT / "tools/phase4c_http_typed_normalization_anchor_"
            "successor_acceptance.py",
        ):
            source = path.read_text(encoding="utf-8")
            self.assertNotIn(".glob(", source)
            self.assertNotIn(".rglob(", source)
            self.assertNotIn("GIT_COMMIT_OID = \"HEAD\"", source)
            self.assertNotIn("git ls-files", source)
            self.assertNotIn("source_contracts.keys()", source)

    def test_11_typed_bootstrap_test_uses_fixed_commit_not_live_worktree(self) -> None:
        source = (
            ROOT
            / "tools/test_phase4c_personal_bank_user_counts_http_"
            "typed_normalization_contract.py"
        ).read_text(encoding="utf-8")
        self.assertIn(acceptance.GIT_COMMIT_OID, source)
        self.assertNotIn("git ls-files --others", source)
        self.assertNotIn("current worktree", source.lower())

    def test_12_contract_payload_is_canonical(self) -> None:
        payload = {
            key: value
            for key, value in self.contract.items()
            if key != "document_payload_sha256"
        }
        self.assertEqual(
            acceptance.CONTRACT_PAYLOAD_SHA256,
            acceptance._sha256_bytes(
                acceptance._canonical_json(payload).encode("utf-8")
            ),
        )

    def test_13_tag_preflight_loader_rejects_internal_dependency_failure(
        self,
    ) -> None:
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
