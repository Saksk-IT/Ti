#!/usr/bin/env python3
"""Fail-closed tests for the fixed Phase 2 WORM successor chain."""

from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import subprocess
import tempfile
import types
import unittest
from unittest import mock

try:
    from tools import phase2_wormhole_successor_acceptance as phase2_acceptance
    from tools import (
        phase4c_http_target_execution_post_push_successor_acceptance
        as post_push_acceptance,
    )
    from tools import (
        phase4c_http_target_execution_successor_acceptance
        as target_execution_acceptance,
    )
    from tools.phase2_wormhole_successor_acceptance import (
        EvidenceDescriptor,
        EvidenceValidationError,
        FIXED_EVIDENCE_CHAIN,
        ImmutableMirror,
        CANONICAL_SCHEMA_SHA256,
        PHASE4C_HTTP_IMPLEMENTATION_BUILD_CONTEXT_SHA256,
        PHASE4C_HTTP_IMPLEMENTATION_REPORT_PATH,
        PHASE4C_HTTP_IMPLEMENTATION_REPORT_SHA256,
        PHASE4C_READ_ACCESS_REPORT_SHA256,
        POSTGRES_IMAGE,
        sha256,
        validate_evidence_chain,
    )
except ModuleNotFoundError:  # Direct script execution from tools/.
    import phase2_wormhole_successor_acceptance as phase2_acceptance
    import phase4c_http_target_execution_post_push_successor_acceptance \
        as post_push_acceptance
    import phase4c_http_target_execution_successor_acceptance \
        as target_execution_acceptance
    from phase2_wormhole_successor_acceptance import (
        EvidenceDescriptor,
        EvidenceValidationError,
        FIXED_EVIDENCE_CHAIN,
        ImmutableMirror,
        CANONICAL_SCHEMA_SHA256,
        PHASE4C_HTTP_IMPLEMENTATION_BUILD_CONTEXT_SHA256,
        PHASE4C_HTTP_IMPLEMENTATION_REPORT_PATH,
        PHASE4C_HTTP_IMPLEMENTATION_REPORT_SHA256,
        PHASE4C_READ_ACCESS_REPORT_SHA256,
        POSTGRES_IMAGE,
        sha256,
        validate_evidence_chain,
    )


ROOT = Path(__file__).resolve().parents[1]


class Phase2WormholeSuccessorAcceptanceTest(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / "reports").mkdir(parents=True)
        (self.root / "infra/phase2").mkdir(parents=True)

        self.manifest_path = self.root / "infra/phase2/reference-drift-manifest.json"
        self.manifest_path.write_text(
            json.dumps(
                {
                    "legacySourceCommit": "legacy-commit",
                    "alembicHead": "alembic-head",
                    "observedReference": {
                        "postgresVersion": "18.4",
                        "postgresVersionNum": 180004,
                        "physicalTableCount": 70,
                        "physicalColumnCount": 617,
                    },
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        self.anchor_build = "a" * 64
        self.successor_build = "b" * 64
        self.anchor_dockerfile = "c" * 64
        self.successor_dockerfile = "d" * 64
        self.anchor_path = self.root / "reports/anchor.json"
        self.successor_path = self.root / "reports/successor.json"
        self.mirror_path = self.root / "reports/anchor-mirror.json"
        self._write_report(
            self.anchor_path, self.anchor_build, self.anchor_dockerfile
        )
        self._write_report(
            self.successor_path,
            self.successor_build,
            self.successor_dockerfile,
        )
        self.mirror_path.write_bytes(self.anchor_path.read_bytes())

        self.anchor = EvidenceDescriptor(
            label="historical-anchor",
            relative_path="reports/anchor.json",
            sha256=sha256(self.anchor_path),
            build_context_sha256=self.anchor_build,
            dockerfile_sha256=self.anchor_dockerfile,
            predecessor_sha256=None,
        )
        self.successor = EvidenceDescriptor(
            label="reviewed-successor",
            relative_path="reports/successor.json",
            sha256=sha256(self.successor_path),
            build_context_sha256=self.successor_build,
            dockerfile_sha256=self.successor_dockerfile,
            predecessor_sha256=self.anchor.sha256,
        )
        self.mirror = ImmutableMirror(
            label="historical-contract-mirror",
            relative_path="reports/anchor-mirror.json",
        )

    def _report(self, build_context: str, dockerfile: str) -> dict:
        return {
            "schemaVersion": 1,
            "capturedAt": "2026-07-17T12:00:00Z",
            "source": {
                "classification": "explicitly-approved-local-development-reference",
                "legacySourceCommit": "legacy-commit",
                "alembicHead": "alembic-head",
                "serverVersion": "18.4",
                "serverVersionNum": "180004",
                "publicBaseTables": 70,
                "publicColumns": 617,
            },
            "restore": {
                "image": POSTGRES_IMAGE,
                "serverVersion": "18.4",
                "serverVersionNum": "180004",
                "publicBaseTables": 70,
                "publicColumns": 617,
                "canonicalSchemaDumpSha256": CANONICAL_SCHEMA_SHA256,
                "schemaDumpPersisted": False,
            },
            "readRole": {
                "selectPassed": True,
                "defaultTransactionReadOnly": True,
                "temporaryPrivilege": False,
                "aclVerifiedWithReadOnlyDefaultDisabled": True,
                "insertRejected": True,
                "updateRejected": True,
                "deleteRejected": True,
                "ddlRejected": True,
                "temporaryDdlRejected": True,
            },
            "java": {
                "dockerfileSha256": dockerfile,
                "buildContextSha256": build_context,
                "hibernateDdlAuto": "validate",
                "startupPassed": True,
                "readinessPassed": True,
            },
            "productionDatabaseVersion": "unknown",
            "flywayBaselineCreated": False,
        }

    def _write_report(self, path: Path, build_context: str, dockerfile: str) -> None:
        path.write_text(
            json.dumps(self._report(build_context, dockerfile), indent=2) + "\n",
            encoding="utf-8",
        )

    def _successor_after(
        self,
        predecessor: EvidenceDescriptor,
        *,
        filename: str,
        label: str,
        build_context: str,
    ) -> tuple[Path, EvidenceDescriptor]:
        path = self.root / f"reports/{filename}"
        self._write_report(path, build_context, self.successor_dockerfile)
        return path, EvidenceDescriptor(
            label=label,
            relative_path=f"reports/{filename}",
            sha256=sha256(path),
            build_context_sha256=build_context,
            dockerfile_sha256=self.successor_dockerfile,
            predecessor_sha256=predecessor.sha256,
        )

    def _validate(
        self,
        *,
        chain: tuple[EvidenceDescriptor, ...] | None = None,
        mirrors: tuple[ImmutableMirror, ...] | None = None,
        current_build: str | None = None,
        current_dockerfile: str | None = None,
    ) -> EvidenceDescriptor:
        return validate_evidence_chain(
            self.root,
            self.manifest_path,
            current_dockerfile or self.successor_dockerfile,
            current_build or self.successor_build,
            chain=chain or (self.anchor, self.successor),
            immutable_mirrors=mirrors or (self.mirror,),
        )

    def test_fixed_anchor_successor_and_historical_mirror_pass(self) -> None:
        tip = self._validate()
        self.assertEqual(self.successor, tip)

        extra = self.root / "reports/arbitrary-matching-report.json"
        extra.write_bytes(self.successor_path.read_bytes())
        self.assertEqual(self.successor, self._validate())

    def test_historical_anchor_and_mirror_digest_drift_fail_closed(self) -> None:
        self.anchor_path.write_text(
            self.anchor_path.read_text(encoding="utf-8") + " ", encoding="utf-8"
        )
        with self.assertRaisesRegex(EvidenceValidationError, "report digest drift"):
            self._validate()

        self._write_report(
            self.anchor_path, self.anchor_build, self.anchor_dockerfile
        )
        self.mirror_path.write_text(
            self.mirror_path.read_text(encoding="utf-8") + " ", encoding="utf-8"
        )
        with self.assertRaisesRegex(
            EvidenceValidationError, "historical mirror digest drift"
        ):
            self._validate()

    def test_broken_predecessor_and_duplicate_build_context_fail_closed(self) -> None:
        broken = replace(self.successor, predecessor_sha256="f" * 64)
        with self.assertRaisesRegex(EvidenceValidationError, "broken predecessor"):
            self._validate(chain=(self.anchor, broken))

        duplicate = replace(
            self.successor,
            build_context_sha256=self.anchor.build_context_sha256,
        )
        with self.assertRaisesRegex(
            EvidenceValidationError, "duplicate evidence build-context"
        ):
            self._validate(chain=(self.anchor, duplicate))

    def test_four_node_chain_requires_each_exact_predecessor(self) -> None:
        _, third = self._successor_after(
            self.successor,
            filename="third.json",
            label="second-reviewed-successor",
            build_context="e" * 64,
        )
        _, fourth = self._successor_after(
            third,
            filename="fourth.json",
            label="third-reviewed-successor",
            build_context="f" * 64,
        )
        self.assertEqual(
            fourth,
            self._validate(
                chain=(self.anchor, self.successor, third, fourth),
                current_build=fourth.build_context_sha256,
            ),
        )

        broken_third = replace(third, predecessor_sha256=self.anchor.sha256)
        with self.assertRaisesRegex(EvidenceValidationError, "broken predecessor"):
            self._validate(
                chain=(self.anchor, self.successor, broken_third, fourth),
                current_build=fourth.build_context_sha256,
            )

        broken_fourth = replace(fourth, predecessor_sha256=self.successor.sha256)
        with self.assertRaisesRegex(EvidenceValidationError, "broken predecessor"):
            self._validate(
                chain=(self.anchor, self.successor, third, broken_fourth),
                current_build=fourth.build_context_sha256,
            )

    def test_fixed_fifth_node_links_the_immutable_read_access_tip(self) -> None:
        self.assertEqual(5, len(FIXED_EVIDENCE_CHAIN))
        tip = FIXED_EVIDENCE_CHAIN[-1]
        self.assertEqual(
            "phase4c-personal-bank-user-counts-http-implementation", tip.label
        )
        self.assertEqual(PHASE4C_HTTP_IMPLEMENTATION_REPORT_PATH, tip.relative_path)
        self.assertEqual(PHASE4C_HTTP_IMPLEMENTATION_REPORT_SHA256, tip.sha256)
        self.assertEqual(
            PHASE4C_HTTP_IMPLEMENTATION_BUILD_CONTEXT_SHA256,
            tip.build_context_sha256,
        )
        self.assertEqual(PHASE4C_READ_ACCESS_REPORT_SHA256, tip.predecessor_sha256)

    def test_historical_bridge_uses_no_successor_when_bytes_are_unchanged(
        self,
    ) -> None:
        declared = "1" * 64
        resolve = getattr(
            target_execution_acceptance,
            "_current_or_post_push_successor_sha256",
        )
        with mock.patch.object(
            target_execution_acceptance,
            "_load_post_push_successor_acceptance",
            side_effect=AssertionError("post-push bridge must remain lazy"),
        ):
            self.assertEqual(
                declared,
                resolve(
                    self.root,
                    "fixed/source.py",
                    declared,
                    declared,
                    label="fixed source",
                ),
            )

    def test_historical_bridge_delegates_only_an_exact_hash_transition(
        self,
    ) -> None:
        declared = "1" * 64
        physical = "2" * 64
        resolve = getattr(
            target_execution_acceptance,
            "_current_or_post_push_successor_sha256",
        )
        acceptance = types.SimpleNamespace(
            accepted_sha256=lambda relative: (
                declared if relative == "fixed/source.py" else None
            ),
            successor_sha256=lambda root, relative: (
                physical
                if root == self.root and relative == "fixed/source.py"
                else None
            ),
        )
        with mock.patch.object(
            target_execution_acceptance,
            "_load_post_push_successor_acceptance",
            return_value=acceptance,
        ):
            self.assertEqual(
                physical,
                resolve(
                    self.root,
                    "fixed/source.py",
                    declared,
                    physical,
                    label="fixed source",
                ),
            )

    def test_historical_bridge_rejects_unknown_or_mismatched_transition(
        self,
    ) -> None:
        declared = "1" * 64
        physical = "2" * 64
        resolve = getattr(
            target_execution_acceptance,
            "_current_or_post_push_successor_sha256",
        )
        unknown = types.SimpleNamespace(
            accepted_sha256=lambda relative: None,
            successor_sha256=lambda root, relative: physical,
        )
        with mock.patch.object(
            target_execution_acceptance,
            "_load_post_push_successor_acceptance",
            return_value=unknown,
        ):
            with self.assertRaisesRegex(
                AssertionError,
                "does not accept historical bytes",
            ):
                resolve(
                    self.root,
                    "unknown/source.py",
                    declared,
                    physical,
                    label="unknown source",
                )

        wrong_successor = types.SimpleNamespace(
            accepted_sha256=lambda relative: declared,
            successor_sha256=lambda root, relative: "3" * 64,
        )
        with mock.patch.object(
            target_execution_acceptance,
            "_load_post_push_successor_acceptance",
            return_value=wrong_successor,
        ):
            with self.assertRaisesRegex(
                AssertionError,
                "does not bind current bytes",
            ):
                resolve(
                    self.root,
                    "fixed/source.py",
                    declared,
                    physical,
                    label="fixed source",
                )

    def test_post_push_bridge_is_lazy_for_unchanged_bytes(self) -> None:
        declared = "4" * 64
        resolve = getattr(
            post_push_acceptance,
            "_current_or_post_push_anchor_successor_sha256",
        )
        with mock.patch.object(
            post_push_acceptance,
            "_load_post_push_anchor_successor_acceptance",
            side_effect=AssertionError("anchor bridge must remain lazy"),
        ):
            self.assertEqual(
                declared,
                resolve(
                    self.root,
                    "fixed/post-push.py",
                    declared,
                    declared,
                    label="post-push source",
                ),
            )

    def test_post_push_bridge_delegates_only_exact_second_hop(self) -> None:
        accepted = "4" * 64
        physical = "5" * 64
        resolve = getattr(
            post_push_acceptance,
            "_current_or_post_push_anchor_successor_sha256",
        )
        terminal = types.SimpleNamespace(
            accepted_sha256=lambda relative: (
                accepted if relative == "fixed/post-push.py" else None
            ),
            successor_sha256=lambda root, relative: (
                physical
                if root == self.root and relative == "fixed/post-push.py"
                else None
            ),
        )
        with mock.patch.object(
            post_push_acceptance,
            "_load_post_push_anchor_successor_acceptance",
            return_value=terminal,
        ):
            self.assertEqual(
                physical,
                resolve(
                    self.root,
                    "fixed/post-push.py",
                    accepted,
                    physical,
                    label="post-push source",
                ),
            )

    def test_post_push_bridge_rejects_unknown_or_wrong_second_hop(self) -> None:
        accepted = "4" * 64
        physical = "5" * 64
        resolve = getattr(
            post_push_acceptance,
            "_current_or_post_push_anchor_successor_sha256",
        )
        unknown = types.SimpleNamespace(
            accepted_sha256=lambda relative: None,
            successor_sha256=lambda root, relative: physical,
        )
        with mock.patch.object(
            post_push_acceptance,
            "_load_post_push_anchor_successor_acceptance",
            return_value=unknown,
        ):
            with self.assertRaisesRegex(
                AssertionError,
                "does not accept historical",
            ):
                resolve(
                    self.root,
                    "unknown/post-push.py",
                    accepted,
                    physical,
                    label="post-push source",
                )

        wrong = types.SimpleNamespace(
            accepted_sha256=lambda relative: accepted,
            successor_sha256=lambda root, relative: "6" * 64,
        )
        with mock.patch.object(
            post_push_acceptance,
            "_load_post_push_anchor_successor_acceptance",
            return_value=wrong,
        ):
            with self.assertRaisesRegex(
                AssertionError,
                "does not bind current",
            ):
                resolve(
                    self.root,
                    "fixed/post-push.py",
                    accepted,
                    physical,
                    label="post-push source",
                )

    def test_fixed_acceptance_requires_target_execution_successor(self) -> None:
        modules = {
            phase2_acceptance.READ_SUCCESSOR_MODULE: types.SimpleNamespace(
                load_read_successor_contract=lambda root: {"validated": True},
            ),
            phase2_acceptance.TARGET_EXECUTION_SUCCESSOR_MODULE:
                types.SimpleNamespace(
                    load_http_target_execution_successor_contract=lambda root: None,
                ),
            phase2_acceptance.TARGET_EXECUTION_POST_PUSH_SUCCESSOR_MODULE:
                types.SimpleNamespace(load=lambda root: {"validated": True}),
            phase2_acceptance.TARGET_EXECUTION_POST_PUSH_ANCHOR_SUCCESSOR_MODULE:
                types.SimpleNamespace(load=lambda root: {"validated": True}),
            phase2_acceptance.TYPED_NORMALIZATION_SUCCESSOR_MODULE:
                types.SimpleNamespace(load=lambda root: {"validated": True}),
        }
        with mock.patch.object(
            phase2_acceptance.importlib,
            "import_module",
            side_effect=lambda name: modules[name],
        ):
            with self.assertRaisesRegex(
                EvidenceValidationError,
                "fixed target-execution successor contract is required",
            ):
                phase2_acceptance.validate_fixed_acceptance(
                    self.root,
                    self.manifest_path,
                    self.successor_dockerfile,
                    self.successor_build,
                )

    def test_fixed_acceptance_requires_post_push_successor(self) -> None:
        modules = {
            phase2_acceptance.READ_SUCCESSOR_MODULE: types.SimpleNamespace(
                load_read_successor_contract=lambda root: {"validated": True},
            ),
            phase2_acceptance.TARGET_EXECUTION_SUCCESSOR_MODULE:
                types.SimpleNamespace(
                    load_http_target_execution_successor_contract=lambda root: {
                        "validated": True,
                    },
                ),
            phase2_acceptance.TARGET_EXECUTION_POST_PUSH_SUCCESSOR_MODULE:
                types.SimpleNamespace(load=lambda root: None),
            phase2_acceptance.TARGET_EXECUTION_POST_PUSH_ANCHOR_SUCCESSOR_MODULE:
                types.SimpleNamespace(load=lambda root: {"validated": True}),
            phase2_acceptance.TYPED_NORMALIZATION_SUCCESSOR_MODULE:
                types.SimpleNamespace(load=lambda root: {"validated": True}),
        }
        with mock.patch.object(
            phase2_acceptance.importlib,
            "import_module",
            side_effect=lambda name: modules[name],
        ):
            with self.assertRaisesRegex(
                EvidenceValidationError,
                "fixed target-execution post-push successor contract is required",
            ):
                phase2_acceptance.validate_fixed_acceptance(
                    self.root,
                    self.manifest_path,
                    self.successor_dockerfile,
                    self.successor_build,
                )

    def test_fixed_acceptance_propagates_post_push_tamper_failure(self) -> None:
        def reject_tamper(root: Path) -> dict:
            raise AssertionError("post-push contract physical hash drifted")

        modules = {
            phase2_acceptance.READ_SUCCESSOR_MODULE: types.SimpleNamespace(
                load_read_successor_contract=lambda root: {"validated": True},
            ),
            phase2_acceptance.TARGET_EXECUTION_SUCCESSOR_MODULE:
                types.SimpleNamespace(
                    load_http_target_execution_successor_contract=lambda root: {
                        "validated": True,
                    },
                ),
            phase2_acceptance.TARGET_EXECUTION_POST_PUSH_SUCCESSOR_MODULE:
                types.SimpleNamespace(load=reject_tamper),
            phase2_acceptance.TARGET_EXECUTION_POST_PUSH_ANCHOR_SUCCESSOR_MODULE:
                types.SimpleNamespace(load=lambda root: {"validated": True}),
            phase2_acceptance.TYPED_NORMALIZATION_SUCCESSOR_MODULE:
                types.SimpleNamespace(load=lambda root: {"validated": True}),
        }
        with mock.patch.object(
            phase2_acceptance.importlib,
            "import_module",
            side_effect=lambda name: modules[name],
        ):
            with self.assertRaisesRegex(
                AssertionError,
                "post-push contract physical hash drifted",
            ):
                phase2_acceptance.validate_fixed_acceptance(
                    self.root,
                    self.manifest_path,
                    self.successor_dockerfile,
                    self.successor_build,
                )

    def test_fixed_acceptance_fails_when_post_push_module_is_missing(self) -> None:
        modules = {
            phase2_acceptance.READ_SUCCESSOR_MODULE: types.SimpleNamespace(
                load_read_successor_contract=lambda root: {"validated": True},
            ),
            phase2_acceptance.TARGET_EXECUTION_SUCCESSOR_MODULE:
                types.SimpleNamespace(
                    load_http_target_execution_successor_contract=lambda root: {
                        "validated": True,
                    },
                ),
        }

        def import_or_reject(name: str) -> object:
            if name in modules:
                return modules[name]
            raise ModuleNotFoundError(name=name)

        with mock.patch.object(
            phase2_acceptance.importlib,
            "import_module",
            side_effect=import_or_reject,
        ):
            with self.assertRaisesRegex(
                EvidenceValidationError,
                "fixed target-execution post-push successor acceptance module is required",
            ):
                phase2_acceptance.validate_fixed_acceptance(
                    self.root,
                    self.manifest_path,
                    self.successor_dockerfile,
                    self.successor_build,
                )

    def test_fixed_acceptance_requires_post_push_anchor_successor(self) -> None:
        modules = {
            phase2_acceptance.READ_SUCCESSOR_MODULE: types.SimpleNamespace(
                load_read_successor_contract=lambda root: {"validated": True},
            ),
            phase2_acceptance.TARGET_EXECUTION_SUCCESSOR_MODULE:
                types.SimpleNamespace(
                    load_http_target_execution_successor_contract=lambda root: {
                        "validated": True,
                    },
                ),
            phase2_acceptance.TARGET_EXECUTION_POST_PUSH_SUCCESSOR_MODULE:
                types.SimpleNamespace(load=lambda root: {"validated": True}),
            phase2_acceptance.TARGET_EXECUTION_POST_PUSH_ANCHOR_SUCCESSOR_MODULE:
                types.SimpleNamespace(load=lambda root: None),
            phase2_acceptance.TYPED_NORMALIZATION_SUCCESSOR_MODULE:
                types.SimpleNamespace(load=lambda root: {"validated": True}),
        }
        with mock.patch.object(
            phase2_acceptance.importlib,
            "import_module",
            side_effect=lambda name: modules[name],
        ):
            with self.assertRaisesRegex(
                EvidenceValidationError,
                "fixed target-execution post-push anchor successor contract is required",
            ):
                phase2_acceptance.validate_fixed_acceptance(
                    self.root,
                    self.manifest_path,
                    self.successor_dockerfile,
                    self.successor_build,
                )

    def test_fixed_acceptance_fails_when_post_push_anchor_module_is_missing(
        self,
    ) -> None:
        modules = {
            phase2_acceptance.READ_SUCCESSOR_MODULE: types.SimpleNamespace(
                load_read_successor_contract=lambda root: {"validated": True},
            ),
            phase2_acceptance.TARGET_EXECUTION_SUCCESSOR_MODULE:
                types.SimpleNamespace(
                    load_http_target_execution_successor_contract=lambda root: {
                        "validated": True,
                    },
                ),
            phase2_acceptance.TARGET_EXECUTION_POST_PUSH_SUCCESSOR_MODULE:
                types.SimpleNamespace(load=lambda root: {"validated": True}),
        }

        def import_or_reject(name: str) -> object:
            if name in modules:
                return modules[name]
            raise ModuleNotFoundError(name=name)

        with mock.patch.object(
            phase2_acceptance.importlib,
            "import_module",
            side_effect=import_or_reject,
        ):
            with self.assertRaisesRegex(
                EvidenceValidationError,
                "fixed target-execution post-push anchor successor acceptance module is required",
            ):
                phase2_acceptance.validate_fixed_acceptance(
                    self.root,
                    self.manifest_path,
                    self.successor_dockerfile,
                    self.successor_build,
                )

    def test_fixed_acceptance_requires_typed_normalization_successor(self) -> None:
        modules = {
            phase2_acceptance.READ_SUCCESSOR_MODULE: types.SimpleNamespace(
                load_read_successor_contract=lambda root: {"validated": True},
            ),
            phase2_acceptance.TARGET_EXECUTION_SUCCESSOR_MODULE:
                types.SimpleNamespace(
                    load_http_target_execution_successor_contract=lambda root: {
                        "validated": True,
                    },
                ),
            phase2_acceptance.TARGET_EXECUTION_POST_PUSH_SUCCESSOR_MODULE:
                types.SimpleNamespace(load=lambda root: {"validated": True}),
            phase2_acceptance.TARGET_EXECUTION_POST_PUSH_ANCHOR_SUCCESSOR_MODULE:
                types.SimpleNamespace(load=lambda root: {"validated": True}),
            phase2_acceptance.TYPED_NORMALIZATION_SUCCESSOR_MODULE:
                types.SimpleNamespace(load=lambda root: None),
        }
        with mock.patch.object(
            phase2_acceptance.importlib,
            "import_module",
            side_effect=lambda name: modules[name],
        ):
            with self.assertRaisesRegex(
                EvidenceValidationError,
                "fixed HTTP typed-normalization successor contract is required",
            ):
                phase2_acceptance.validate_fixed_acceptance(
                    self.root,
                    self.manifest_path,
                    self.successor_dockerfile,
                    self.successor_build,
                )

    def test_fixed_acceptance_fails_when_typed_normalization_module_is_missing(
        self,
    ) -> None:
        modules = {
            phase2_acceptance.READ_SUCCESSOR_MODULE: types.SimpleNamespace(
                load_read_successor_contract=lambda root: {"validated": True},
            ),
            phase2_acceptance.TARGET_EXECUTION_SUCCESSOR_MODULE:
                types.SimpleNamespace(
                    load_http_target_execution_successor_contract=lambda root: {
                        "validated": True,
                    },
                ),
            phase2_acceptance.TARGET_EXECUTION_POST_PUSH_SUCCESSOR_MODULE:
                types.SimpleNamespace(load=lambda root: {"validated": True}),
            phase2_acceptance.TARGET_EXECUTION_POST_PUSH_ANCHOR_SUCCESSOR_MODULE:
                types.SimpleNamespace(load=lambda root: {"validated": True}),
        }

        def import_or_reject(name: str) -> object:
            if name in modules:
                return modules[name]
            raise ModuleNotFoundError(name=name)

        with mock.patch.object(
            phase2_acceptance.importlib,
            "import_module",
            side_effect=import_or_reject,
        ):
            with self.assertRaisesRegex(
                EvidenceValidationError,
                "fixed HTTP typed-normalization successor acceptance module is required",
            ):
                phase2_acceptance.validate_fixed_acceptance(
                    self.root,
                    self.manifest_path,
                    self.successor_dockerfile,
                    self.successor_build,
                )

    def test_import_and_fixed_chain_do_not_import_successor_modules(self) -> None:
        script = r'''
import importlib.abc
import pathlib
import sys

blocked = {
    "tools.phase4c_read_successor_acceptance",
    "tools.phase4c_http_target_execution_successor_acceptance",
    "tools.phase4c_http_target_execution_post_push_successor_acceptance",
    "tools.phase4c_http_target_execution_post_push_anchor_successor_acceptance",
    "tools.phase4c_http_typed_normalization_successor_acceptance",
}

class Blocker(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        if fullname in blocked:
            raise RuntimeError(f"forbidden eager import: {fullname}")
        return None

sys.meta_path.insert(0, Blocker())
from tools import phase2_wormhole_successor_acceptance as acceptance

if blocked.intersection(sys.modules):
    raise SystemExit("a successor module was imported eagerly")

acceptance.validate_evidence_chain = lambda *args, **kwargs: "fixed-tip"
tip = acceptance.validate_fixed_chain(
    pathlib.Path.cwd(),
    pathlib.Path("unused-manifest.json"),
    "a" * 64,
    "b" * 64,
)
if tip != "fixed-tip":
    raise SystemExit("validate_fixed_chain did not remain independent")
if blocked.intersection(sys.modules):
    raise SystemExit("validate_fixed_chain imported a successor module")
'''
        completed = subprocess.run(
            ["python3", "-c", script],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)

    def test_fourth_node_tampering_fails_even_when_digest_is_reaccepted(self) -> None:
        _, third = self._successor_after(
            self.successor,
            filename="third.json",
            label="second-reviewed-successor",
            build_context="e" * 64,
        )
        fourth_path, fourth = self._successor_after(
            third,
            filename="fourth.json",
            label="third-reviewed-successor",
            build_context="f" * 64,
        )
        chain = (self.anchor, self.successor, third, fourth)
        self.assertEqual(
            fourth,
            self._validate(
                chain=chain,
                current_build=fourth.build_context_sha256,
            ),
        )

        document = json.loads(fourth_path.read_text(encoding="utf-8"))
        document["readRole"]["deleteRejected"] = False
        fourth_path.write_text(
            json.dumps(document, indent=2) + "\n", encoding="utf-8"
        )
        with self.assertRaisesRegex(EvidenceValidationError, "report digest drift"):
            self._validate(
                chain=chain,
                current_build=fourth.build_context_sha256,
            )

        reaccepted = replace(fourth, sha256=sha256(fourth_path))
        with self.assertRaisesRegex(EvidenceValidationError, "read-role ACL"):
            self._validate(
                chain=(self.anchor, self.successor, third, reaccepted),
                current_build=fourth.build_context_sha256,
            )

    def test_only_fixed_tip_may_match_current_build_context(self) -> None:
        with self.assertRaisesRegex(EvidenceValidationError, "tip is stale"):
            self._validate(current_build="f" * 64)
        with self.assertRaisesRegex(EvidenceValidationError, "Dockerfile"):
            self._validate(current_dockerfile="f" * 64)

    def test_structural_acl_mutation_fails_even_when_digest_is_updated(self) -> None:
        document = json.loads(self.successor_path.read_text(encoding="utf-8"))
        document["readRole"]["updateRejected"] = False
        self.successor_path.write_text(
            json.dumps(document, indent=2) + "\n", encoding="utf-8"
        )
        changed = replace(self.successor, sha256=sha256(self.successor_path))
        with self.assertRaisesRegex(EvidenceValidationError, "read-role ACL"):
            self._validate(chain=(self.anchor, changed))

    def test_canonical_schema_digest_mutation_fails_even_when_report_is_reaccepted(
        self,
    ) -> None:
        document = json.loads(self.successor_path.read_text(encoding="utf-8"))
        document["restore"]["canonicalSchemaDumpSha256"] = "f" * 64
        self.successor_path.write_text(
            json.dumps(document, indent=2) + "\n", encoding="utf-8"
        )
        changed = replace(self.successor, sha256=sha256(self.successor_path))
        with self.assertRaisesRegex(EvidenceValidationError, "canonical schema"):
            self._validate(chain=(self.anchor, changed))

    def test_symlink_report_is_rejected_without_directory_scanning(self) -> None:
        link = self.root / "reports/successor-link.json"
        link.symlink_to("successor.json")
        linked = replace(self.successor, relative_path="reports/successor-link.json")
        with self.assertRaisesRegex(EvidenceValidationError, "symbolic link"):
            self._validate(chain=(self.anchor, linked))

    def test_runner_requires_versioned_report_and_refuses_historical_reports(
        self,
    ) -> None:
        runner = ROOT / "infra/phase2/verify-local-reference-wormhole.sh"
        base_command = [
            str(runner),
            "--source-container",
            "unused-source",
            "--source-user",
            "unused-user",
            "--source-db",
            "unused-db",
        ]
        missing = subprocess.run(
            base_command,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(2, missing.returncode)
        self.assertIn("--report", missing.stdout + missing.stderr)

        immutable_paths = [
            ROOT / "infra/phase2/local-reference-verification.json",
            ROOT
            / "docs/refactor/phase4b/personal-bank-share-list-worm-evidence.json",
            ROOT
            / (
                "docs/refactor/phase4c/"
                "personal-bank-user-counts-entry-worm-evidence.json"
            ),
            ROOT
            / (
                "docs/refactor/phase4c/"
                "personal-bank-user-counts-read-worm-evidence.json"
            ),
            ROOT
            / (
                "docs/refactor/phase4c/"
                "personal-bank-user-counts-read-access-worm-evidence.json"
            ),
            ROOT
            / (
                "docs/refactor/phase4c/"
                "personal-bank-user-counts-http-implementation-worm-evidence.json"
            ),
        ]
        before = {path: sha256(path) for path in immutable_paths}
        for path in immutable_paths:
            rejected = subprocess.run(
                [*base_command, "--report", str(path)],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(2, rejected.returncode, rejected.stderr)
            self.assertIn("existing WORM report", rejected.stdout + rejected.stderr)
        self.assertEqual(before, {path: sha256(path) for path in immutable_paths})

        with tempfile.TemporaryDirectory(
            dir=ROOT / "docs/refactor/phase4c",
            prefix=".worm-existing-target-",
        ) as directory:
            temporary_root = Path(directory)
            arbitrary = temporary_root / "arbitrary-existing.json"
            arbitrary.write_text("do-not-overwrite\n", encoding="utf-8")
            symlink = temporary_root / "existing-link.json"
            symlink.symlink_to(arbitrary.name)
            existing_directory = temporary_root / "existing-directory"
            existing_directory.mkdir()
            for target in (arbitrary, symlink, existing_directory):
                rejected = subprocess.run(
                    [*base_command, "--report", str(target)],
                    cwd=ROOT,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                )
                self.assertEqual(2, rejected.returncode, rejected.stderr)
                self.assertIn(
                    "existing WORM report", rejected.stdout + rejected.stderr
                )
            self.assertEqual("do-not-overwrite\n", arbitrary.read_text(encoding="utf-8"))

        case_alias = immutable_paths[-1].with_name(immutable_paths[-1].name.upper())
        if case_alias.exists() and case_alias.samefile(immutable_paths[-1]):
            rejected = subprocess.run(
                [*base_command, "--report", str(case_alias)],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(2, rejected.returncode, rejected.stderr)
            self.assertIn("existing WORM report", rejected.stdout + rejected.stderr)

        runner_source = runner.read_text(encoding="utf-8")
        self.assertIn("prebuild_java_build_context_sha256", runner_source)
        self.assertIn("postbuild_java_build_context_sha256", runner_source)
        self.assertIn("os.link(source, target, follow_symlinks=False)", runner_source)
        self.assertNotIn('mv "$report_tmp" "$report_file"', runner_source)


if __name__ == "__main__":
    unittest.main()
