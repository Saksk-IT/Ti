#!/usr/bin/env python3
"""Fail-closed tests for the Phase 4C post-push external Git anchor."""

from __future__ import annotations

import ast
from copy import deepcopy
import hashlib
import json
import os
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
        build_phase4c_personal_bank_user_counts_http_target_execution_post_push_anchor_contract
        as builder,
    )
    from tools import (
        phase4c_http_target_execution_post_push_anchor_successor_acceptance
        as acceptance,
    )
    from tools import (
        phase4c_http_typed_normalization_successor_acceptance
        as typed_acceptance,
    )
    from tools import (
        phase4c_tag_migration_global_preflight_successor_acceptance
        as tag_preflight,
    )
except ModuleNotFoundError:  # Direct discovery from tools/.
    import build_phase4c_personal_bank_user_counts_http_target_execution_post_push_anchor_contract as builder
    import phase4c_http_target_execution_post_push_anchor_successor_acceptance as acceptance
    import phase4c_http_typed_normalization_successor_acceptance as typed_acceptance
    import phase4c_tag_migration_global_preflight_successor_acceptance as tag_preflight


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = ROOT.parent


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


class Phase4cTargetExecutionPostPushAnchorContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.generated = builder.build_contract(ROOT)

    def test_01_builder_and_independent_acceptance_agree_exactly(self) -> None:
        self.assertEqual(self.generated, builder.build_contract(ROOT))
        self.assertEqual(self.generated, acceptance._expected_contract())
        acceptance.validate_contract(self.generated, ROOT)
        self.assertEqual(
            self.generated["document_payload_sha256"],
            builder.document_payload_sha256(self.generated),
        )
        self.assertEqual(
            self.generated["document_payload_sha256"],
            acceptance._payload_sha256(self.generated),
        )
        serialized = builder.serialized_contract(self.generated)
        self.assertEqual(serialized, builder.serialized_contract(builder.build_contract(ROOT)))
        if acceptance.CONTRACT_SHA256 != acceptance.ZERO_SHA256:
            self.assertEqual(acceptance.CONTRACT_SHA256, _sha256_bytes(serialized))
            self.assertEqual(
                acceptance.CONTRACT_PAYLOAD_SHA256,
                self.generated["document_payload_sha256"],
            )

    def test_02_ordinary_build_and_validation_are_gitless(self) -> None:
        with patch.object(
            builder,
            "validate_git_checkpoint",
            side_effect=AssertionError("ordinary builder must not consult Git"),
        ):
            self.assertEqual(self.generated, builder.build_contract(ROOT))
        with patch.object(
            acceptance,
            "validate_git_checkpoint",
            side_effect=AssertionError("ordinary validation must not consult Git"),
        ):
            acceptance.validate_contract(self.generated, ROOT)

    def test_03_explicit_git_replay_fixes_the_whole_checkpoint(self) -> None:
        self.assertEqual(
            self.generated,
            builder.build_contract(ROOT, repository_root=REPOSITORY_ROOT),
        )
        builder.validate_git_checkpoint(REPOSITORY_ROOT)
        acceptance.validate_git_checkpoint(REPOSITORY_ROOT)
        with self.assertRaises(AssertionError):
            acceptance.validate_git_checkpoint(ROOT)

    def test_04_exact_sixteen_path_delta_and_six_source_anchor(self) -> None:
        checkpoint = self.generated["git_checkpoint"]
        self.assertEqual(acceptance.GIT_COMMIT_OID, checkpoint["commit_oid"])
        self.assertEqual(acceptance.GIT_ROOT_TREE_OID, checkpoint["root_tree_oid"])
        self.assertEqual(acceptance.GIT_PARENT_OID, checkpoint["parent_oid"])
        self.assertEqual(acceptance.TI_JAVA_TREE_OID, checkpoint["ti_java_tree_oid"])
        self.assertFalse(checkpoint["capture_ref_is_validation_authority"])
        self.assertEqual(16, len(checkpoint["artifacts"]))
        self.assertEqual(6, sum(
            item["change_type"] == "A" for item in checkpoint["artifacts"].values()
        ))
        self.assertEqual(10, sum(
            item["change_type"] == "M" for item in checkpoint["artifacts"].values()
        ))
        self.assertEqual(
            {
                "added_count": 6,
                "modified_count": 10,
                "deleted_count": 0,
                "non_ti_java_count": 0,
                "inserted_line_count": 3799,
                "deleted_line_count": 89,
                "current_total_bytes": 605312,
                "added_total_bytes": 145892,
                "modified_current_total_bytes": 459420,
                "modified_parent_total_bytes": 436774,
                "net_byte_increase": 168538,
                "exact_sixteen_path_delta": True,
            },
            checkpoint["diff"],
        )

        anchor = self.generated["post_push_source_anchor"]
        self.assertEqual(sorted(acceptance.POST_PUSH_SOURCE_PATHS), anchor["source_paths"])
        self.assertEqual(set(anchor["source_paths"]), set(anchor["artifacts"]))
        self.assertEqual(6, anchor["source_count"])
        self.assertEqual(145892, anchor["source_total_bytes"])
        self.assertEqual(
            145892,
            sum(item["byte_count"] for item in anchor["artifacts"].values()),
        )
        self.assertTrue(
            anchor["predecessor_current_sources_external_git_anchor_complete"]
        )

    def test_05_second_hop_allowlist_is_exact_and_unknown_is_closed(self) -> None:
        historical = self.generated["historical_source_successors"]
        self.assertEqual(sorted(acceptance.SUCCESSOR_SOURCES), historical["successor_allowlist"])
        self.assertEqual(set(acceptance.SUCCESSOR_SOURCES), set(historical["overrides"]))
        self.assertEqual(
            10, historical["predecessor_historical_successor_allowlist_count"]
        )
        self.assertEqual(12, historical["second_hop_successor_allowlist_count"])
        self.assertEqual(12, len(historical["overrides"]))
        for relative, descriptor in acceptance.SUCCESSOR_SOURCES.items():
            self.assertEqual(
                descriptor["accepted_sha256"], acceptance.accepted_sha256(relative)
            )
            expected = (
                typed_acceptance.successor_sha256(ROOT, relative)
                if relative in typed_acceptance.THIRD_HOP_SOURCES
                else (
                    tag_preflight.successor_sha256(ROOT, relative)
                    if relative in typed_acceptance.NODEA_OWNED_POST_PUSH_SOURCES
                    else acceptance.SUCCESSOR_SHA256[relative]
                )
            )
            self.assertEqual(expected, acceptance.successor_sha256(ROOT, relative))
        for relative in acceptance.CURRENT_ANCHOR_SOURCES + [
            "unknown/source",
            "../escape",
            "/absolute/path",
        ]:
            self.assertIsNone(acceptance.accepted_sha256(relative))
            self.assertIsNone(acceptance.successor_sha256(ROOT, relative))

        settled = acceptance.successor_constants_settled()
        self.assertEqual(settled, historical["successor_transitions_settled"])
        self.assertEqual(
            settled,
            self.generated["authorization"][
                "historical_successor_transitions_settled"
            ],
        )
        if not settled:
            self.assertTrue(all(
                item["successor_sha256"] == acceptance.ZERO_SHA256
                and item["successor_byte_count"] == 0
                for item in historical["overrides"].values()
            ))

    def test_06_new_six_sources_cannot_authorize_themselves(self) -> None:
        anchor = self.generated["post_push_source_anchor"]
        self.assertEqual(6, len(acceptance.CURRENT_ANCHOR_SOURCES))
        self.assertEqual(
            sorted(acceptance.CURRENT_ANCHOR_SOURCES),
            anchor["current_anchor_sources"],
        )
        self.assertTrue(anchor["current_anchor_sources_excluded_from_self_authority"])
        self.assertFalse(
            anchor["current_anchor_source_bytes_external_git_anchor_complete"]
        )
        self.assertTrue(
            set(acceptance.CURRENT_ANCHOR_SOURCES).isdisjoint(
                acceptance.SUCCESSOR_SOURCES
            )
        )
        serialized = builder.serialized_contract(self.generated).decode("utf-8")
        for relative in (
            "tools/build_phase4c_personal_bank_user_counts_http_"
            "target_execution_post_push_anchor_contract.py",
            "tools/phase4c_http_target_execution_post_push_anchor_"
            "successor_acceptance.py",
            "tools/test_phase4c_personal_bank_user_counts_http_"
            "target_execution_post_push_anchor_contract.py",
        ):
            self.assertNotIn(_sha256_bytes((ROOT / relative).read_bytes()), serialized)

    def test_07_overclaims_and_fixed_fact_tampering_are_rejected(self) -> None:
        mutations: list[dict[str, object]] = []
        for section, field, value in (
            ("authorization", "typed_parity_review_complete", True),
            ("authorization", "full_target_parity_closed", True),
            ("authorization", "route_migration_eligible", True),
            ("authorization", "two_legacy_get_routes_migrated", True),
            ("authorization", "production_cutover", True),
            ("acceptance", "migrated_operation_count", 13),
            ("acceptance", "pending_operation_count", 598),
            ("post_push_source_anchor", "independently_signed_provenance", True),
            (
                "post_push_source_anchor",
                "current_anchor_source_bytes_external_git_anchor_complete",
                True,
            ),
        ):
            changed = deepcopy(self.generated)
            changed[section][field] = value  # type: ignore[index]
            changed["document_payload_sha256"] = acceptance._payload_sha256(changed)
            mutations.append(changed)

        changed = deepcopy(self.generated)
        changed["git_checkpoint"]["artifacts"][acceptance.PREDECESSOR_RELATIVE][
            "sha256"
        ] = "f" * 64
        changed["document_payload_sha256"] = acceptance._payload_sha256(changed)
        mutations.append(changed)

        changed = deepcopy(self.generated)
        changed["historical_source_successors"]["successor_allowlist"].append(
            "unknown/source"
        )
        changed["document_payload_sha256"] = acceptance._payload_sha256(changed)
        mutations.append(changed)

        for changed in mutations:
            with self.subTest(mutation=changed):
                with self.assertRaises(AssertionError):
                    acceptance.validate_contract(changed, ROOT)

    def test_08_symlink_escape_and_non_regular_paths_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "Ti-Java"
            root.mkdir()
            regular = root / "regular"
            regular.write_text("fixed", encoding="utf-8")
            link = root / "link"
            os.symlink(regular, link)
            child = root / "directory"
            child.mkdir()

            for resolver in (builder.fixed_regular_file, acceptance._fixed_regular_file):
                self.assertEqual(regular.resolve(), resolver(root, "regular"))
                for relative in ("link", "directory", "../escape", "/absolute"):
                    with self.subTest(resolver=resolver.__module__, relative=relative):
                        with self.assertRaises(AssertionError):
                            resolver(root, relative)

    def test_09_minimal_gitless_copy_loads_without_parent_repository(self) -> None:
        relatives = {
            acceptance.PREDECESSOR_RELATIVE,
            acceptance.JUNIT_MANIFEST_RELATIVE,
            acceptance.WORM_RELATIVE,
            typed_acceptance.CONTRACT_RELATIVE,
            typed_acceptance.PREDECESSOR_RELATIVE,
            *typed_acceptance.LOCAL_SOURCES,
            *tag_preflight.minimal_fixture_paths(),
            "docs/refactor/phase4c/"
            "personal-bank-user-counts-http-typed-normalization-anchor-contract.json",
        }
        if acceptance.successor_constants_settled():
            relatives.update(acceptance.SUCCESSOR_SOURCES)
        serialized = builder.serialized_contract(self.generated)
        physical_sha256 = _sha256_bytes(serialized)
        payload_sha256 = self.generated["document_payload_sha256"]
        with tempfile.TemporaryDirectory() as directory:
            isolated = Path(directory) / "Ti-Java"
            for relative in relatives:
                target = isolated / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / relative, target)
            contract_path = isolated / acceptance.CONTRACT_RELATIVE
            contract_path.parent.mkdir(parents=True, exist_ok=True)
            contract_path.write_bytes(serialized)
            with (
                patch.object(acceptance, "CONTRACT_SHA256", physical_sha256),
                patch.object(
                    acceptance, "CONTRACT_PAYLOAD_SHA256", payload_sha256
                ),
                patch.object(
                    acceptance,
                    "validate_git_checkpoint",
                    side_effect=AssertionError("Gitless load consulted Git"),
                ),
            ):
                self.assertEqual(self.generated, acceptance.load(isolated))

    def test_10_plain_import_is_independent_of_history_and_phase2(self) -> None:
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
    "tools.phase4c_http_target_execution_post_push_successor_acceptance",
    "phase4c_http_target_execution_post_push_successor_acceptance",
}

class Blocker(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        if fullname in forbidden:
            raise RuntimeError(f"forbidden import: {fullname}")
        return None

sys.meta_path.insert(0, Blocker())
from tools import build_phase4c_personal_bank_user_counts_http_target_execution_post_push_anchor_contract as builder
from tools import phase4c_http_target_execution_post_push_anchor_successor_acceptance as acceptance
root = Path.cwd()
document = builder.build_contract(root)
acceptance.validate_contract(document, root)
assert document == acceptance._expected_contract()
assert forbidden.isdisjoint(sys.modules)
print("post-push-anchor-import-isolation=ok")
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
        self.assertIn("post-push-anchor-import-isolation=ok", completed.stdout)

        forbidden_imports = {
            "tools.phase2_wormhole_successor_acceptance",
            "phase2_wormhole_successor_acceptance",
            "tools.phase4c_http_target_execution_successor_acceptance",
            "phase4c_http_target_execution_successor_acceptance",
            "tools.phase4c_http_target_execution_anchor_successor_acceptance",
            "phase4c_http_target_execution_anchor_successor_acceptance",
            "tools.phase4c_http_target_execution_post_push_successor_acceptance",
            "phase4c_http_target_execution_post_push_successor_acceptance",
        }
        for path in (
            ROOT / "tools/build_phase4c_personal_bank_user_counts_http_"
            "target_execution_post_push_anchor_contract.py",
            ROOT / "tools/phase4c_http_target_execution_post_push_anchor_"
            "successor_acceptance.py",
        ):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            imported = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported.update(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported.add(node.module)
            self.assertTrue(forbidden_imports.isdisjoint(imported))

    def test_11_git_commands_are_read_only_and_paths_are_code_fixed(self) -> None:
        completed = SimpleNamespace(returncode=0, stdout=b"ok\n", stderr=b"")
        for module in (builder, acceptance):
            with patch.object(module.subprocess, "run", return_value=completed) as run:
                self.assertEqual(
                    b"ok\n",
                    module._run_read_only_git(REPOSITORY_ROOT, "version"),
                )
            command = run.call_args.args[0]
            self.assertEqual("git", command[0])
            self.assertIn("--no-optional-locks", command)
            self.assertNotIn("HEAD", command)
            environment = run.call_args.kwargs["env"]
            self.assertEqual("1", environment["GIT_NO_REPLACE_OBJECTS"])
            self.assertEqual("0", environment["GIT_OPTIONAL_LOCKS"])
            self.assertEqual("cat", environment["GIT_PAGER"])
            self.assertEqual("C", environment["LC_ALL"])
            self.assertEqual(30, run.call_args.kwargs["timeout"])

        for path in (
            ROOT / "tools/build_phase4c_personal_bank_user_counts_http_"
            "target_execution_post_push_anchor_contract.py",
            ROOT / "tools/phase4c_http_target_execution_post_push_anchor_"
            "successor_acceptance.py",
        ):
            source = path.read_text(encoding="utf-8")
            self.assertNotIn(".glob(", source)
            self.assertNotIn(".rglob(", source)
            self.assertNotIn('rev-parse", "HEAD', source)

    def test_12_route_typed_and_cutover_boundaries_remain_closed(self) -> None:
        authorization = self.generated["authorization"]
        for field in (
            "current_anchor_source_bytes_external_git_anchor_complete",
            "typed_parity_review_complete",
            "full_target_parity_closed",
            "route_migration_eligible",
            "two_legacy_get_routes_migrated",
            "derived_head_and_options_count_as_migrated",
            "operator_migration_implementation",
            "production_schema_or_index",
            "real_data_migration_execution",
            "client_change",
            "gateway_or_proxy_change",
            "production_cutover",
        ):
            self.assertFalse(authorization[field], field)
        acceptance_section = self.generated["acceptance"]
        self.assertEqual(11, acceptance_section["migrated_operation_count"])
        self.assertEqual(600, acceptance_section["pending_operation_count"])
        self.assertEqual(0, acceptance_section["production_cutover_operation_count"])
        self.assertFalse(acceptance_section["production_cutover"])
        self.assertEqual(builder.NEXT_GATE, acceptance_section["next_gate"])


if __name__ == "__main__":
    unittest.main()
