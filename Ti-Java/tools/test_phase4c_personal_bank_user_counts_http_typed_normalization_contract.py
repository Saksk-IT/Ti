#!/usr/bin/env python3
"""Fail-closed tests for the Phase 4C typed-normalization contract."""

from __future__ import annotations

import ast
from collections import Counter
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
        build_phase4c_personal_bank_user_counts_http_typed_normalization_contract
        as builder,
    )
    from tools import (
        phase4c_http_typed_normalization_successor_acceptance as acceptance,
    )
except ModuleNotFoundError:  # Direct discovery from tools/.
    import build_phase4c_personal_bank_user_counts_http_typed_normalization_contract as builder
    import phase4c_http_typed_normalization_successor_acceptance as acceptance


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = ROOT.parent


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


class Phase4cTypedNormalizationContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract_path = ROOT / acceptance.CONTRACT_RELATIVE
        cls.checked_raw = cls.contract_path.read_bytes()
        cls.checked = json.loads(cls.checked_raw.decode("utf-8"))
        cls.generated = builder.build_contract(ROOT)

    def _copy_minimal_root(self, directory: str) -> Path:
        isolated = Path(directory) / "Ti-Java"
        relatives = {
            acceptance.CONTRACT_RELATIVE,
            acceptance.PREDECESSOR_RELATIVE,
            *acceptance.LOCAL_SOURCES,
        }
        for relative in sorted(relatives):
            target = isolated / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, target)
        return isolated

    def test_01_builder_checked_contract_and_acceptance_agree(self) -> None:
        self.assertEqual(self.generated, self.checked)
        self.assertEqual(
            self.checked_raw,
            builder.serialized_contract(self.generated),
        )
        self.assertEqual(
            acceptance.CONTRACT_BYTE_COUNT,
            len(self.checked_raw),
        )
        self.assertEqual(
            acceptance.CONTRACT_SHA256,
            _sha256_bytes(self.checked_raw),
        )
        self.assertEqual(
            acceptance.CONTRACT_PAYLOAD_SHA256,
            acceptance._payload_sha256(self.checked),
        )
        acceptance.validate_contract(self.checked, ROOT)
        self.assertEqual(self.checked, acceptance.load(ROOT))

    def test_02_ordinary_load_is_gitless(self) -> None:
        with patch.object(
            acceptance,
            "validate_git_checkpoint",
            side_effect=AssertionError("ordinary load consulted Git"),
        ):
            self.assertEqual(self.checked, acceptance.load(ROOT))
            acceptance.validate_contract(self.checked, ROOT)

    def test_03_explicit_c38_replay_is_opt_in_and_root_fixed(self) -> None:
        acceptance.validate_git_checkpoint(REPOSITORY_ROOT)
        self.assertEqual(
            self.checked,
            acceptance.load(ROOT, repository_root=REPOSITORY_ROOT),
        )
        with self.assertRaises(AssertionError):
            acceptance.validate_git_checkpoint(ROOT)

        anchor = self.checked["predecessor_external_git_anchor"]
        self.assertEqual(acceptance.GIT_COMMIT_OID, anchor["commit_oid"])
        self.assertFalse(anchor["mutable_ref_is_validation_authority"])
        self.assertFalse(anchor["ordinary_contract_load_requires_git"])
        self.assertEqual(list(acceptance.GIT_PATHS), anchor["exact_changed_paths"])
        self.assertEqual(
            Counter({"A": 6, "M": 12}),
            Counter({
                "A": anchor["added_path_count"],
                "M": anchor["modified_path_count"],
            }),
        )

    def test_04_ledger_is_exactly_58_http_plus_one_typed_rejection(self) -> None:
        ledger = self.checked["disposition_ledger"]
        rows = ledger["rows"]
        self.assertEqual(59, len(rows))
        self.assertEqual(list(range(1, 60)), [
            row["canonical_case_ordinal"] for row in rows
        ])
        self.assertEqual(
            ledger["ledger_payload_sha256"],
            acceptance._sha256_json(rows),
        )
        http_rows = [row for row in rows if row["http_execution"]]
        typed_rows = [
            row
            for row in rows
            if row["execution_disposition"] == "EXECUTED_TYPED_REJECTION"
        ]
        self.assertEqual(58, len(http_rows))
        self.assertEqual(1, len(typed_rows))
        self.assertEqual(
            Counter({
                "EXECUTED_FULL_CONTEXT_HTTP": 47,
                "EXECUTED_FULL_CONTEXT_HTTP_WITH_POSTGRES_ABORT": 11,
                "EXECUTED_TYPED_REJECTION": 1,
            }),
            Counter(row["execution_disposition"] for row in rows),
        )
        self.assertEqual(
            Counter({200: 35, 302: 5, 401: 3, 403: 10, 500: 5}),
            Counter(row["target_status"] for row in http_rows),
        )
        self.assertEqual(
            acceptance.EXPECTED_SUMMARY,
            ledger["summary"],
        )
        self.assertEqual(acceptance.EXPECTED_SUMMARY, {
            key: self.checked["acceptance"][key]
            for key in acceptance.EXPECTED_SUMMARY
        })

    def test_05_physical_61_selects_60_without_double_counting(self) -> None:
        junit = self.checked["junit_execution"]
        self.assertEqual(60, junit["historical_physical_leaf_count"])
        self.assertEqual(1, junit["new_physical_leaf_count"])
        self.assertEqual(61, junit["aggregate_physical_leaf_count"])
        self.assertEqual(60, junit["selected_effective_proof_leaf_count"])
        self.assertEqual(59, junit["logical_disposition_leaf_count"])
        self.assertEqual(1, junit["supplementary_authentication_leaf_count"])
        self.assertEqual(1, junit["superseded_historical_representation_leaf_count"])
        self.assertEqual(1, junit["replacement_leaf_count"])
        self.assertFalse(junit["superseded_leaf_double_counted"])

        rows = self.checked["disposition_ledger"]["rows"]
        historical_ordinals = {
            row["proof"]["suite_leaf_ordinal"]
            for row in rows
            if row["proof"]["manifest"] == acceptance.HISTORICAL_MANIFEST
        }
        typed_rows = [
            row
            for row in rows
            if row["proof"]["manifest"] == acceptance.TYPED_MANIFEST
        ]
        self.assertEqual(set(range(2, 60)), historical_ordinals)
        self.assertEqual(1, len(typed_rows))
        self.assertEqual(60, typed_rows[0]["proof"]["replaces_historical_leaf_ordinal"])

    def test_06_aware_and_malformed_semantics_remain_separate(self) -> None:
        typed = self.checked["typed_normalization"]
        self.assertEqual("2026-07-17T13:00:00+08:00", typed["input"])
        self.assertEqual("2026-07-17T13:00:00-05:00",
                         typed["negative_offset_input"])
        self.assertEqual("timestamp without time zone", typed["postgresql_type"])
        self.assertEqual("2026-07-17T13:00:00", typed["canonical_local_datetime"])
        self.assertTrue(typed["offset_provenance_erased"])
        self.assertEqual(["16.14", "18.4"],
                         typed["cast_compatibility_versions"])
        self.assertEqual(["UTC", "America/Los_Angeles"],
                         typed["cast_session_time_zones"])
        self.assertTrue(typed["cross_version_equal"])
        self.assertTrue(typed["session_timezone_independent"])
        self.assertEqual("18.4", typed["full_filter_http_version"])
        self.assertEqual(
            "java_string_bind_explicit_cast_insert_before_request_trace",
            typed["http_fixture_origin"],
        )
        self.assertFalse(typed["http_fixture_sql_literal_seeded"])
        self.assertEqual(500, typed["source_status"])
        self.assertEqual(200, typed["target_status"])
        self.assertEqual(9, typed["target_data"]["total"])
        self.assertIn("not random-port Tomcat", typed["proof_scope"])
        self.assertFalse(typed["whole_test_lifecycle_zero_dml_claimed"])

        malformed = self.checked["malformed_typed_rejection"]
        self.assertEqual("22007", malformed["sqlstate"])
        self.assertFalse(malformed["http_execution"])
        self.assertIsNone(malformed["target_status"])
        self.assertEqual(0, malformed["persisted_bank_share_row_count"])
        self.assertTrue(
            malformed["no_row_http_forbidden_from_claiming_malformed_semantics"]
        )

    def test_07_routes_parity_and_cutover_remain_closed(self) -> None:
        authorization = self.checked["authorization"]
        self.assertTrue(authorization["typed_execution_normalization_complete"])
        self.assertTrue(authorization["behavior_difference_adr_documented"])
        for field in (
            "current_node_sources_external_git_anchor_complete",
            "typed_parity_review_complete",
            "pg16_pg18_termination_fingerprints_complete",
            "real_tomcat_complete_response_header_matrix_complete",
            "same_service_redis_outage_and_recovery_complete",
            "full_target_parity_closed",
            "route_migration_eligible",
            "two_legacy_get_routes_migrated",
            "derived_head_and_options_count_as_migrated",
            "production_cutover",
        ):
            self.assertFalse(authorization[field], field)
        accepted = self.checked["acceptance"]
        self.assertEqual(11, accepted["migrated_operation_count"])
        self.assertEqual(600, accepted["pending_operation_count"])
        self.assertEqual(0, accepted["production_cutover_operation_count"])
        self.assertFalse(accepted["route_migration_eligible"])
        self.assertFalse(accepted["full_target_parity_closed"])
        self.assertFalse(accepted["production_cutover"])

    def test_08_fixed_source_and_self_exclusion_allowlists_are_exact(self) -> None:
        expected_sources = {
            relative: {"path": relative, **descriptor}
            for relative, descriptor in sorted(acceptance.LOCAL_SOURCES.items())
        }
        self.assertEqual(expected_sources, self.checked["source_contracts"])
        trust = self.checked["current_node_trust_boundary"]
        self.assertEqual(sorted(acceptance.CURRENT_NODE_SOURCES), trust["source_paths"])
        self.assertEqual(6, trust["source_count"])
        self.assertTrue(trust["source_path_allowlist_exact"])
        self.assertTrue(trust["sources_excluded_from_self_authority"])
        self.assertFalse(trust["source_bytes_external_git_anchor_complete"])
        self.assertTrue(trust["dynamic_source_discovery_forbidden"])

        expected_third_hop_paths = {
            "README.md",
            "docs/refactor/05-progress.md",
            "docs/refactor/phase4c/README.md",
            "infra/phase2/README.md",
            "infra/phase2/verify-static.sh",
            "server/src/test/java/io/saksk/ti/architecture/"
            "Phase4cHttpTargetExecutionPostPushAnchorSuccessorAcceptance.java",
            "server/src/test/java/io/saksk/ti/architecture/"
            "Phase4cPersonalBankUserCountsHttpTargetExecutionPostPushAnchor"
            "ContractParityTest.java",
            "server/src/test/java/io/saksk/ti/architecture/"
            "Phase4cPersonalBankUserCountsHttpTargetExecutionPostPushContractParityTest.java",
            "tools/build_phase4c_personal_bank_user_counts_http_"
            "target_execution_post_push_anchor_contract.py",
            "tools/phase2_wormhole_successor_acceptance.py",
            "tools/phase4c_http_target_execution_post_push_anchor_"
            "successor_acceptance.py",
            "tools/test_phase2_wormhole_successor_acceptance.py",
            "tools/test_phase4c_personal_bank_user_counts_http_"
            "target_execution_post_push_anchor_contract.py",
            "tools/test_phase4c_personal_bank_user_counts_http_"
            "target_execution_post_push_contract.py",
        }
        self.assertEqual(
            expected_third_hop_paths,
            set(acceptance.THIRD_HOP_SOURCES),
        )
        for relative, descriptor in acceptance.THIRD_HOP_SOURCES.items():
            self.assertNotEqual(
                descriptor["accepted_sha256"],
                descriptor["successor_sha256"],
            )
            self.assertEqual(
                descriptor["accepted_sha256"],
                acceptance.accepted_sha256(relative),
            )
            self.assertEqual(
                _sha256_bytes((ROOT / relative).read_bytes()),
                acceptance.successor_sha256(ROOT, relative),
            )
        for relative in (
            *acceptance.CURRENT_NODE_SOURCES,
            acceptance.PREDECESSOR_RELATIVE,
            "unknown",
            "../escape",
        ):
            self.assertIsNone(acceptance.accepted_sha256(relative))
            self.assertIsNone(acceptance.successor_sha256(ROOT, relative))

    def test_09_semantic_tampering_and_overclaims_fail_closed(self) -> None:
        mutations: list[dict[str, object]] = []
        for section, field, value in (
            ("authorization", "typed_parity_review_complete", True),
            ("authorization", "route_migration_eligible", True),
            ("authorization", "production_cutover", True),
            ("acceptance", "http_execution_count", 59),
            ("acceptance", "migrated_operation_count", 13),
            ("acceptance", "pending_operation_count", 598),
            ("junit_execution", "selected_effective_proof_leaf_count", 61),
            ("junit_execution", "superseded_leaf_double_counted", True),
            ("malformed_typed_rejection", "http_execution", True),
            (
                "current_node_trust_boundary",
                "source_bytes_external_git_anchor_complete",
                True,
            ),
        ):
            changed = deepcopy(self.checked)
            changed[section][field] = value  # type: ignore[index]
            changed["document_payload_sha256"] = acceptance._payload_sha256(changed)
            mutations.append(changed)

        changed = deepcopy(self.checked)
        changed["disposition_ledger"]["rows"][0]["target_status"] = 500
        changed["disposition_ledger"]["ledger_payload_sha256"] = (
            acceptance._sha256_json(changed["disposition_ledger"]["rows"])
        )
        changed["document_payload_sha256"] = acceptance._payload_sha256(changed)
        mutations.append(changed)

        changed = deepcopy(self.checked)
        changed["source_contracts"]["unknown/source"] = {
            "path": "unknown/source",
            "sha256": "f" * 64,
            "byte_count": 1,
        }
        changed["document_payload_sha256"] = acceptance._payload_sha256(changed)
        mutations.append(changed)

        for ordinal, changed in enumerate(mutations, start=1):
            with self.subTest(mutation=ordinal):
                with self.assertRaises(AssertionError):
                    acceptance.validate_contract(changed, ROOT)

    def test_10_minimal_copy_loads_without_git_or_self_authority_sources(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            isolated = self._copy_minimal_root(directory)
            for relative in acceptance.CURRENT_NODE_SOURCES[1:]:
                self.assertFalse((isolated / relative).exists())
            with patch.object(
                acceptance,
                "validate_git_checkpoint",
                side_effect=AssertionError("minimal Gitless load consulted Git"),
            ):
                self.assertEqual(self.checked, acceptance.load(isolated))

    def test_11_contract_and_source_byte_tampering_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            isolated = self._copy_minimal_root(directory)
            contract_path = isolated / acceptance.CONTRACT_RELATIVE
            contract_path.write_bytes(contract_path.read_bytes() + b" ")
            with self.assertRaises(AssertionError):
                acceptance.load(isolated)

        with tempfile.TemporaryDirectory() as directory:
            isolated = self._copy_minimal_root(directory)
            relative = next(iter(acceptance.LOCAL_SOURCES))
            source = isolated / relative
            source.write_bytes(source.read_bytes() + b" ")
            with self.assertRaises(AssertionError):
                acceptance.load(isolated)

    def test_12_symlinks_non_regular_and_escape_paths_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "Ti-Java"
            root.mkdir()
            regular = root / "regular"
            regular.write_text("fixed", encoding="utf-8")
            link = root / "link"
            os.symlink(regular, link)
            child = root / "directory"
            child.mkdir()
            self.assertEqual(
                regular.resolve(), acceptance._fixed_regular_file(root, "regular")
            )
            for relative in ("link", "directory", "../escape", "/absolute", ""):
                with self.subTest(relative=relative):
                    with self.assertRaises(AssertionError):
                        acceptance._fixed_regular_file(root, relative)

        with tempfile.TemporaryDirectory() as directory:
            isolated = self._copy_minimal_root(directory)
            relative = next(iter(acceptance.LOCAL_SOURCES))
            copied = isolated / relative
            copied.unlink()
            os.symlink(ROOT / relative, copied)
            with self.assertRaises(AssertionError):
                acceptance.load(isolated)

    def test_13_acceptance_import_is_independent_and_discovery_free(self) -> None:
        acceptance_path = ROOT / (
            "tools/phase4c_http_typed_normalization_successor_acceptance.py"
        )
        tree = ast.parse(acceptance_path.read_text(encoding="utf-8"))
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
        forbidden = {
            "tools.build_phase4c_personal_bank_user_counts_http_typed_normalization_contract",
            "build_phase4c_personal_bank_user_counts_http_typed_normalization_contract",
            "tools.phase4c_http_target_execution_post_push_anchor_successor_acceptance",
            "phase4c_http_target_execution_post_push_anchor_successor_acceptance",
            "tools.phase2_wormhole_successor_acceptance",
            "phase2_wormhole_successor_acceptance",
        }
        self.assertTrue(forbidden.isdisjoint(imported))
        source = acceptance_path.read_text(encoding="utf-8")
        self.assertNotIn(".glob(", source)
        self.assertNotIn(".rglob(", source)
        self.assertNotIn('rev-parse", "HEAD', source)

        script = r'''
import importlib.abc
import sys
from pathlib import Path

forbidden = {
    "tools.build_phase4c_personal_bank_user_counts_http_typed_normalization_contract",
    "tools.phase4c_http_target_execution_post_push_anchor_successor_acceptance",
    "tools.phase2_wormhole_successor_acceptance",
}
class Blocker(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        if fullname in forbidden:
            raise RuntimeError(f"forbidden import: {fullname}")
        return None
sys.meta_path.insert(0, Blocker())
from tools import phase4c_http_typed_normalization_successor_acceptance as acceptance
document = acceptance.load(Path.cwd())
assert document["acceptance"]["http_execution_count"] == 58
assert forbidden.isdisjoint(sys.modules)
print("typed-normalization-import-isolation=ok")
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
        self.assertIn("typed-normalization-import-isolation=ok", completed.stdout)

    def test_14_git_helper_is_read_only_and_commit_is_code_fixed(self) -> None:
        completed = SimpleNamespace(returncode=0, stdout=b"ok\n", stderr=b"")
        with patch.object(acceptance.subprocess, "run", return_value=completed) as run:
            self.assertEqual(
                b"ok\n",
                acceptance._run_read_only_git(REPOSITORY_ROOT, "version"),
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

    def test_15_third_hop_lookup_rehashes_contract_and_requested_path(self) -> None:
        relative = "README.md"
        descriptor = acceptance.THIRD_HOP_SOURCES[relative]
        with tempfile.TemporaryDirectory() as directory:
            isolated = Path(directory) / "Ti-Java"
            for source_relative in (
                acceptance.CONTRACT_RELATIVE,
                "docs/refactor/phase4c/"
                "personal-bank-user-counts-http-typed-normalization-"
                "anchor-contract.json",
                relative,
            ):
                source = ROOT / source_relative
                target = isolated / source_relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)

            self.assertFalse((isolated / acceptance.PREDECESSOR_RELATIVE).exists())
            self.assertEqual(
                _sha256_bytes((ROOT / relative).read_bytes()),
                acceptance.successor_sha256(isolated, relative),
            )

            contract = isolated / acceptance.CONTRACT_RELATIVE
            contract.write_bytes(contract.read_bytes() + b" ")
            with self.assertRaisesRegex(AssertionError, "contract physical bytes"):
                acceptance.successor_sha256(isolated, relative)

            shutil.copy2(ROOT / acceptance.CONTRACT_RELATIVE, contract)
            successor = isolated / relative
            successor.write_bytes(successor.read_bytes() + b" ")
            with self.assertRaisesRegex(AssertionError, "typed anchor"):
                acceptance.successor_sha256(isolated, relative)

    def test_16_fixed_bootstrap_commit_partition_is_complete(self) -> None:
        local_additions = {
            "docs/refactor/phase4c/"
            "personal-bank-user-counts-typed-normalization-approved-difference.md",
            "docs/refactor/phase4c/"
            "personal-bank-user-counts-typed-normalization-junit-manifest.json",
            "server/src/test/java/io/saksk/ti/integration/"
            "LegacyPersonalBankUserCountsTypedNormalizationIT.java",
            "server/src/test/resources/db/phase4c/"
            "072-personal-bank-user-counts-typed-normalization-seed.sql",
            "tools/normalize_phase4c_personal_bank_user_counts_"
            "typed_normalization_junit.py",
            "tools/test_normalize_phase4c_personal_bank_user_counts_"
            "typed_normalization_junit.py",
        }
        self.assertTrue(local_additions.issubset(acceptance.LOCAL_SOURCES))
        expected = {
            *acceptance.THIRD_HOP_SOURCES,
            *acceptance.CURRENT_NODE_SOURCES,
            *local_additions,
        }

        bootstrap_commit = "b0861d61438f649ed48d5d5e6806e02c804fa2e4"
        tracked = subprocess.run(
            [
                "git", "--no-optional-locks", "diff", "--name-only",
                "--no-renames", acceptance.GIT_COMMIT_OID, bootstrap_commit,
                "--", "Ti-Java",
            ],
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            env={
                **os.environ,
                "GIT_NO_REPLACE_OBJECTS": "1",
                "GIT_OPTIONAL_LOCKS": "0",
                "GIT_PAGER": "cat",
                "LC_ALL": "C",
            },
        )
        self.assertEqual(0, tracked.returncode, tracked.stderr)
        actual = {
            path.removeprefix("Ti-Java/")
            for path in tracked.stdout.splitlines()
            if path.startswith("Ti-Java/")
        }
        self.assertEqual(expected, actual)


if __name__ == "__main__":
    unittest.main()
