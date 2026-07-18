#!/usr/bin/env python3
"""Fail-closed tests for the Phase 4C post-push checkpoint contract."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

try:
    from tools import (
        build_phase4c_personal_bank_user_counts_http_target_execution_post_push_contract
        as builder,
    )
    from tools import (
        phase4c_http_target_execution_post_push_successor_acceptance as acceptance,
    )
    from tools import (
        phase4c_http_target_execution_post_push_anchor_successor_acceptance
        as post_push_anchor,
    )
    from tools import (
        phase4c_http_typed_normalization_successor_acceptance
        as typed_acceptance,
    )
    from tools import phase4c_http_target_execution_successor_acceptance as target
except ModuleNotFoundError:  # Direct discovery from tools/.
    import build_phase4c_personal_bank_user_counts_http_target_execution_post_push_contract as builder
    import phase4c_http_target_execution_post_push_successor_acceptance as acceptance
    import phase4c_http_target_execution_post_push_anchor_successor_acceptance \
        as post_push_anchor
    import phase4c_http_typed_normalization_successor_acceptance \
        as typed_acceptance
    import phase4c_http_target_execution_successor_acceptance as target


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = ROOT.parent
CONTRACT_PATH = ROOT / acceptance.CONTRACT_RELATIVE


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Phase4cTargetExecutionPostPushContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    def test_01_builder_is_deterministic_and_matches_checked_in_bytes(self) -> None:
        generated = builder.build_contract(ROOT)
        self.assertEqual(self.contract, generated)
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
            generated,
            builder.build_contract(ROOT, repository_root=REPOSITORY_ROOT),
        )

    def test_02_load_is_gitless_and_explicit_git_replay_passes(self) -> None:
        with patch.object(
            acceptance,
            "validate_git_checkpoint",
            side_effect=AssertionError("ordinary load must not consult Git"),
        ):
            self.assertEqual(self.contract, acceptance.load(ROOT))
        self.assertEqual(
            self.contract,
            acceptance.load(ROOT, repository_root=REPOSITORY_ROOT),
        )

    def test_03_checkpoint_fixes_exact_nine_add_only_artifacts(self) -> None:
        checkpoint = self.contract["git_checkpoint"]
        self.assertEqual(acceptance.GIT_COMMIT_OID, checkpoint["commit_oid"])
        self.assertEqual(acceptance.GIT_ROOT_TREE_OID, checkpoint["root_tree_oid"])
        self.assertEqual(acceptance.GIT_PARENT_OID, checkpoint["parent_oid"])
        self.assertEqual(acceptance.TI_JAVA_TREE_OID, checkpoint["ti_java_tree_oid"])
        self.assertFalse(checkpoint["capture_ref_is_validation_authority"])
        self.assertEqual(acceptance.CHECKPOINT_ARTIFACTS, checkpoint["artifacts"])
        self.assertEqual(9, len(checkpoint["artifacts"]))
        self.assertEqual(
            {
                "added_count": 9,
                "modified_count": 0,
                "deleted_count": 0,
                "non_ti_java_count": 0,
                "added_total_bytes": 222675,
                "exact_add_only_delta": True,
            },
            checkpoint["diff"],
        )
        acceptance.validate_git_checkpoint(REPOSITORY_ROOT)

    def test_04_successor_allowlist_is_exact_and_cannot_self_authorize(self) -> None:
        successor = self.contract["historical_source_successors"]
        self.assertEqual(sorted(acceptance.SUCCESSOR_SOURCES), successor["successor_allowlist"])
        self.assertEqual(set(acceptance.SUCCESSOR_SOURCES), set(successor["overrides"]))
        for relative, values in acceptance.SUCCESSOR_SOURCES.items():
            self.assertEqual(values[1], acceptance.accepted_sha256(relative))
            self.assertEqual(
                sha256(ROOT / relative),
                acceptance.successor_sha256(ROOT, relative),
            )
        for relative in acceptance.CURRENT_POST_PUSH_SOURCES + ["unknown/source"]:
            self.assertIsNone(acceptance.accepted_sha256(relative))
            self.assertIsNone(acceptance.successor_sha256(ROOT, relative))

    def test_05_historical_target_bridge_uses_only_the_exact_transition(self) -> None:
        loaded = target.load_http_target_execution_successor_contract(ROOT)
        self.assertIsNotNone(loaded)
        for relative, values in acceptance.SUCCESSOR_SOURCES.items():
            if relative in target.SOURCE_PATHS.values() or relative in (
                target.HISTORICAL_SOURCE_ACCEPTED_SHA256
            ):
                resolved = (
                    target.fixed_source_sha256(ROOT, relative)
                    if relative in target.SOURCE_PATHS.values()
                    else target.successor_sha256(ROOT, relative)
                )
                self.assertEqual(sha256(ROOT / relative), resolved)
        self.assertIsNone(target.successor_sha256(ROOT, "unknown/source"))

    def test_06_manifest_is_newly_anchored_without_rewriting_history(self) -> None:
        manifest = json.loads(
            (ROOT / acceptance.JUNIT_MANIFEST_RELATIVE).read_text(encoding="utf-8")
        )
        self.assertFalse(
            manifest["confidentiality"]["manifest_bytes_external_git_anchor_complete"]
        )
        self.assertTrue(
            manifest["confidentiality"]["post_push_successor_anchor_required"]
        )
        self.assertTrue(
            self.contract["junit_execution"][
                "manifest_blob_external_git_anchor_complete"
            ]
        )
        self.assertFalse(
            self.contract["junit_execution"]["historical_manifest_document_rewritten"]
        )

    def test_07_overclaims_and_tampering_are_rejected(self) -> None:
        mutations = []
        for section, field, value in (
            ("authorization", "typed_parity_review_complete", True),
            ("authorization", "full_target_parity_closed", True),
            ("authorization", "route_migration_eligible", True),
            ("authorization", "two_legacy_get_routes_migrated", True),
            ("authorization", "production_cutover", True),
            ("acceptance", "migrated_operation_count", 13),
            ("acceptance", "pending_operation_count", 598),
            ("checkpoint_anchor", "independently_signed_provenance", True),
        ):
            changed = deepcopy(self.contract)
            changed[section][field] = value
            changed["document_payload_sha256"] = acceptance._payload_sha256(changed)
            mutations.append(changed)
        changed = deepcopy(self.contract)
        changed["git_checkpoint"]["artifacts"]["junit_manifest"]["sha256"] = "0" * 64
        changed["document_payload_sha256"] = acceptance._payload_sha256(changed)
        mutations.append(changed)
        changed = deepcopy(self.contract)
        first = next(iter(changed["historical_source_successors"]["overrides"]))
        changed["historical_source_successors"]["overrides"][first][
            "successor_sha256"
        ] = "f" * 64
        changed["document_payload_sha256"] = acceptance._payload_sha256(changed)
        mutations.append(changed)
        for changed in mutations:
            with self.subTest(changed=changed):
                with self.assertRaises(AssertionError):
                    acceptance.validate_contract(changed, ROOT)

    def test_08_plain_import_build_and_load_block_historical_modules(self) -> None:
        script = r'''
import importlib.abc
import sys
from pathlib import Path

forbidden = {
    "tools.phase2_wormhole_successor_acceptance",
    "phase2_wormhole_successor_acceptance",
    "tools.phase4c_http_target_execution_successor_acceptance",
    "phase4c_http_target_execution_successor_acceptance",
    "tools.phase4c_http_target_execution_anchor_successor_acceptance",
    "phase4c_http_target_execution_anchor_successor_acceptance",
}

class Blocker(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        if fullname in forbidden:
            raise RuntimeError(f"forbidden import: {fullname}")
        return None

sys.meta_path.insert(0, Blocker())
from tools import build_phase4c_personal_bank_user_counts_http_target_execution_post_push_contract as builder
from tools import phase4c_http_target_execution_post_push_successor_acceptance as acceptance
root = Path.cwd()
assert builder.build_contract(root)["contract_id"] == builder.CONTRACT_ID
assert acceptance.load(root)["contract_id"] == acceptance.CONTRACT_ID
assert forbidden.isdisjoint(sys.modules)
print("post-push-import-isolation=ok")
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
        self.assertIn("post-push-import-isolation=ok", completed.stdout)

    def test_09_minimal_gitless_copy_loads_without_parent_repository(self) -> None:
        relatives = {
            acceptance.CONTRACT_RELATIVE,
            acceptance.PREDECESSOR_RELATIVE,
            acceptance.JUNIT_MANIFEST_RELATIVE,
            acceptance.WORM_RELATIVE,
            *acceptance.SUCCESSOR_SOURCES,
            post_push_anchor.CONTRACT_RELATIVE,
            post_push_anchor.PREDECESSOR_RELATIVE,
            post_push_anchor.JUNIT_MANIFEST_RELATIVE,
            post_push_anchor.WORM_RELATIVE,
            *post_push_anchor.SUCCESSOR_SOURCES,
            typed_acceptance.CONTRACT_RELATIVE,
            typed_acceptance.PREDECESSOR_RELATIVE,
            *typed_acceptance.LOCAL_SOURCES,
        }
        with tempfile.TemporaryDirectory() as directory:
            isolated = Path(directory) / "Ti-Java"
            for relative in relatives:
                target_path = isolated / relative
                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / relative, target_path)
            self.assertEqual(self.contract, acceptance.load(isolated))

    def test_10_git_commands_are_read_only_and_no_dynamic_discovery_exists(self) -> None:
        completed = SimpleNamespace(returncode=0, stdout=b"ok\n", stderr=b"")
        with patch.object(acceptance.subprocess, "run", return_value=completed) as run:
            self.assertEqual(b"ok\n", acceptance._run_read_only_git(REPOSITORY_ROOT, "version"))
        environment = run.call_args.kwargs["env"]
        self.assertEqual("1", environment["GIT_NO_REPLACE_OBJECTS"])
        self.assertEqual("0", environment["GIT_OPTIONAL_LOCKS"])
        self.assertEqual("cat", environment["GIT_PAGER"])
        self.assertEqual("C", environment["LC_ALL"])
        for path in (
            ROOT / "tools/build_phase4c_personal_bank_user_counts_http_target_execution_post_push_contract.py",
            ROOT / "tools/phase4c_http_target_execution_post_push_successor_acceptance.py",
        ):
            source = path.read_text(encoding="utf-8")
            self.assertNotIn(".glob(", source)
            self.assertNotIn(".rglob(", source)
            self.assertNotIn("source_contracts", source)
            self.assertNotIn("rev-parse\", \"HEAD", source)


if __name__ == "__main__":
    unittest.main()
