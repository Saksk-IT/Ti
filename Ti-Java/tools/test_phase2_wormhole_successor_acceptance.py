#!/usr/bin/env python3
"""Fail-closed tests for the fixed Phase 2 WORM successor chain."""

from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

try:
    from tools.phase2_wormhole_successor_acceptance import (
        EvidenceDescriptor,
        EvidenceValidationError,
        ImmutableMirror,
        CANONICAL_SCHEMA_SHA256,
        POSTGRES_IMAGE,
        sha256,
        validate_evidence_chain,
    )
except ModuleNotFoundError:  # Direct script execution from tools/.
    from phase2_wormhole_successor_acceptance import (
        EvidenceDescriptor,
        EvidenceValidationError,
        ImmutableMirror,
        CANONICAL_SCHEMA_SHA256,
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
