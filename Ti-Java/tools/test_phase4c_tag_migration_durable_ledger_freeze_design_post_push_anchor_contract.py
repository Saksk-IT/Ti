#!/usr/bin/env python3
"""Tests for the Phase 4C Node B post-push external anchor."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from tools import (
    build_phase4c_tag_migration_durable_ledger_freeze_design_post_push_anchor_contract
    as builder,
)
from tools import (
    phase4c_tag_migration_durable_ledger_freeze_design_post_push_anchor_successor_acceptance
    as acceptance,
)


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = ROOT.parent


class NodeBPostPushAnchorContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = (ROOT / builder.OUTPUT_RELATIVE).read_bytes()
        cls.contract = json.loads(cls.payload)

    def test_checked_in_bytes_match_gitless_builder(self) -> None:
        expected = builder.serialized_contract(builder.build_contract(ROOT))
        self.assertEqual(expected, self.payload)
        self.assertEqual(acceptance.EXPECTED_CONTRACT_BYTE_COUNT, len(self.payload))
        self.assertEqual(
            acceptance.EXPECTED_CONTRACT_SHA256,
            builder.sha256_bytes(self.payload),
        )
        self.assertEqual(
            acceptance.EXPECTED_DOCUMENT_PAYLOAD_SHA256,
            builder.document_payload_sha256(self.contract),
        )

    def test_successor_acceptance_loads_fixed_contract(self) -> None:
        self.assertEqual(self.contract, acceptance.load_contract(ROOT))

    def test_predecessor_and_transitive_node_a_are_fixed(self) -> None:
        predecessor = self.contract["predecessor"]
        self.assertEqual(builder.PREDECESSOR_SHA256, predecessor["sha256"])
        self.assertEqual(
            builder.PREDECESSOR_PAYLOAD_SHA256,
            predecessor["document_payload_sha256"],
        )
        node_a = self.contract["transitive_node_a_anchor"]
        self.assertEqual(builder.NODE_A_ANCHOR_SHA256, node_a["sha256"])
        self.assertEqual(
            builder.NODE_A_EXTERNAL_ANCHOR_COMMIT,
            node_a["external_anchor_checkpoint_commit_oid"],
        )
        self.assertEqual(6, node_a["external_anchor_artifact_count"])
        self.assertEqual(
            list(builder.NODE_A_EXTERNAL_CONTROL_SOURCES),
            node_a["external_anchor_control_sources"],
        )

    def test_checkpoint_is_exactly_eight_additions(self) -> None:
        checkpoint = self.contract["git_checkpoint"]
        self.assertEqual(builder.GIT_COMMIT_OID, checkpoint["commit_oid"])
        self.assertEqual(builder.GIT_PARENT_OID, checkpoint["parent_oid"])
        self.assertEqual(8, checkpoint["changed_path_count"])
        self.assertEqual(8, checkpoint["added_count"])
        self.assertEqual(0, checkpoint["modified_count"])
        self.assertEqual(0, checkpoint["deleted_count"])
        self.assertEqual(0, checkpoint["non_ti_java_count"])
        self.assertEqual(5_362, checkpoint["inserted_line_count"])
        self.assertEqual(0, checkpoint["deleted_line_count"])
        self.assertEqual(233_639, checkpoint["current_total_bytes"])
        self.assertEqual(builder.CHECKPOINT_CHANGES, checkpoint["artifacts"])
        self.assertTrue(checkpoint["exact_eight_added_path_delta"])

    def test_delta_equals_predecessor_control_allowlist(self) -> None:
        predecessor = json.loads(
            (ROOT / builder.PREDECESSOR_RELATIVE).read_bytes()
        )
        controls = predecessor["source_authority"]["control_sources"]
        self.assertEqual(list(builder.CHECKPOINT_PATHS), controls)
        self.assertEqual(
            set(controls), set(self.contract["git_checkpoint"]["artifacts"])
        )
        anchor = self.contract["node_b_control_source_anchor"]
        self.assertEqual(
            acceptance.EXPECTED_CONTROL_PATH_MANIFEST_SHA256,
            anchor["control_source_path_manifest_sha256"],
        )
        self.assertEqual(
            acceptance.EXPECTED_CONTROL_BLOB_MANIFEST_SHA256,
            anchor["control_source_blob_manifest_sha256"],
        )
        self.assertTrue(
            anchor["predecessor_control_sources_external_git_anchor_complete"]
        )

    def test_production_trees_route_and_gates_remain_conservative(self) -> None:
        checkpoint = self.contract["git_checkpoint"]
        self.assertEqual(
            checkpoint["server_src_main_tree_oid"],
            checkpoint["parent_server_src_main_tree_oid"],
        )
        self.assertEqual(
            checkpoint["web_tree_oid"], checkpoint["parent_web_tree_oid"]
        )
        self.assertEqual(builder.ROUTE_STATE, self.contract["route_state"])
        authorization = self.contract["inherited_evidence_and_authorization"]
        self.assertTrue(
            authorization["migration_global_preflight_evidence_closed"]
        )
        self.assertTrue(
            authorization[
                "migration_durable_ledger_freeze_design_evidence_closed"
            ]
        )
        self.assertTrue(
            authorization["node_b_control_sources_external_git_anchor_complete"]
        )
        for field in builder.PRODUCTION_FALSE_FIELDS:
            self.assertFalse(authorization[field], field)
        self.assertTrue(
            self.contract["acceptance"]["anchor_closes_no_functional_gate"]
        )

    def test_six_current_controls_are_self_excluded(self) -> None:
        current = self.contract["current_node_trust_boundary"]
        self.assertEqual(list(builder.CURRENT_CONTROL_SOURCES), current["control_sources"])
        self.assertEqual(6, current["control_source_count"])
        self.assertTrue(current["control_sources_excluded_from_self_authority"])
        self.assertFalse(current["control_sources_external_git_anchor_complete"])
        self.assertFalse(current["independently_signed_provenance"])
        self.assertTrue(
            set(builder.CURRENT_CONTROL_SOURCES).isdisjoint(
                builder.CHECKPOINT_PATHS
            )
        )

    def test_builder_replays_only_fixed_git_checkpoint(self) -> None:
        builder.validate_git_checkpoint(REPOSITORY_ROOT)
        replayed = builder.build_contract(
            ROOT, repository_root=REPOSITORY_ROOT
        )
        self.assertEqual(self.contract, replayed)

    def test_acceptance_independently_replays_git_checkpoint(self) -> None:
        with patch.object(
            builder,
            "validate_git_checkpoint",
            side_effect=AssertionError("builder replay must not be called"),
        ):
            acceptance.validate_fixed_git_checkpoint(REPOSITORY_ROOT)

    def test_live_refs_are_rejected_before_git_execution(self) -> None:
        for ref in ("HEAD", "main", "origin/main", "@", "--all"):
            with self.subTest(ref=ref):
                with self.assertRaisesRegex(AssertionError, "live"):
                    builder._run_git(REPOSITORY_ROOT, "show", ref)
                with self.assertRaisesRegex(AssertionError, "live"):
                    acceptance._run_fixed_git(REPOSITORY_ROOT, "show", ref)

    def test_minimal_gitless_fixture_builds_and_loads(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary) / "Ti-Java"
            fixture.mkdir()
            for relative in (
                builder.PREDECESSOR_RELATIVE,
                builder.NODE_A_ANCHOR_RELATIVE,
                builder.OUTPUT_RELATIVE,
            ):
                target = fixture / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / relative, target)
            self.assertFalse((Path(temporary) / ".git").exists())
            self.assertEqual(self.contract, builder.build_contract(fixture))
            self.assertEqual(self.contract, acceptance.load_contract(fixture))

    def test_predecessor_physical_tamper_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = self._minimal_fixture(Path(temporary))
            with (fixture / builder.PREDECESSOR_RELATIVE).open("ab") as stream:
                stream.write(b"\n")
            with self.assertRaisesRegex(AssertionError, "predecessor physical"):
                builder.build_contract(fixture)

    def test_transitive_node_a_physical_tamper_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = self._minimal_fixture(Path(temporary))
            with (fixture / builder.NODE_A_ANCHOR_RELATIVE).open("ab") as stream:
                stream.write(b"\n")
            with self.assertRaisesRegex(AssertionError, "transitive Node A bytes"):
                builder.build_contract(fixture)

    def test_contract_physical_tamper_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = self._minimal_fixture(Path(temporary))
            with (fixture / builder.OUTPUT_RELATIVE).open("ab") as stream:
                stream.write(b"\n")
            with self.assertRaisesRegex(AssertionError, "fixed bytes"):
                acceptance.load_contract(fixture)

    def test_symlink_unknown_and_absolute_sources_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = self._minimal_fixture(Path(temporary))
            predecessor = fixture / builder.PREDECESSOR_RELATIVE
            real = predecessor.with_suffix(".real")
            predecessor.rename(real)
            predecessor.symlink_to(real)
            with self.assertRaisesRegex(AssertionError, "symlink"):
                builder.build_contract(fixture)
        for relative in ("tools/unknown.py", "/tmp/unknown"):
            with self.subTest(relative=relative):
                with self.assertRaisesRegex(AssertionError, "unknown|absolute"):
                    builder.fixed_regular_file(ROOT, relative)

    def test_only_exact_checkpoint_sources_are_accepted(self) -> None:
        for relative, descriptor in builder.CHECKPOINT_CHANGES.items():
            self.assertEqual(
                descriptor["sha256"], acceptance.accepted_sha256(ROOT, relative)
            )
        self.assertIsNone(acceptance.accepted_sha256(ROOT, "tools/unknown.py"))

    def test_semantic_overclaim_tamper_is_rejected(self) -> None:
        tampered = deepcopy(self.contract)
        tampered["inherited_evidence_and_authorization"][
            "operator_migration_implementation"
        ] = True
        with self.assertRaisesRegex(AssertionError, "production boundary"):
            acceptance.validate_contract(tampered)
        tampered = deepcopy(self.contract)
        tampered["route_state"]["migrated_operation_count"] = 14
        with self.assertRaisesRegex(AssertionError, "route"):
            acceptance.validate_contract(tampered)

    def test_no_dynamic_discovery_in_builder_or_acceptance(self) -> None:
        for relative in (
            "tools/build_phase4c_tag_migration_durable_ledger_freeze_design_"
            "post_push_anchor_contract.py",
            "tools/phase4c_tag_migration_durable_ledger_freeze_design_"
            "post_push_anchor_successor_acceptance.py",
        ):
            source = (ROOT / relative).read_text(encoding="utf-8")
            for forbidden in (".glob(", ".rglob(", "os.walk(", "git ls-files"):
                self.assertNotIn(forbidden, source, (relative, forbidden))

    @staticmethod
    def _minimal_fixture(temporary: Path) -> Path:
        fixture = temporary / "Ti-Java"
        fixture.mkdir()
        for relative in (
            builder.PREDECESSOR_RELATIVE,
            builder.NODE_A_ANCHOR_RELATIVE,
            builder.OUTPUT_RELATIVE,
        ):
            target = fixture / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, target)
        return fixture


if __name__ == "__main__":
    unittest.main()
