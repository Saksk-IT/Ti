#!/usr/bin/env python3
"""Validate the append-only Phase 6 public-bank Web foundation acceptance."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import unittest
from pathlib import Path


PHASE6_DIR = Path(__file__).resolve().parent
TI_JAVA = PHASE6_DIR.parents[2]
REPO = TI_JAVA.parent
CONTRACT_PATH = PHASE6_DIR / "web-foundation-acceptance.json"
WEB_ROOT = TI_JAVA / "web"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class WebFoundationAcceptanceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    def test_contract_identity_and_completion_boundary(self) -> None:
        self.assertEqual(self.contract["contract_id"], "phase6-web-foundation-acceptance-v1")
        self.assertEqual(self.contract["status"], "complete")
        disposition = self.contract["phase6_disposition"]
        self.assertTrue(disposition["foundation_complete"])
        self.assertFalse(disposition["phase6_complete"])
        self.assertFalse(disposition["gateway_or_production_cutover_authorized"])

    def test_fixed_worker_commit_has_declared_base_and_scope_when_git_is_available(self) -> None:
        if not (REPO / ".git").exists():
            self.skipTest("Gitless extraction: content manifest remains authoritative")
        integration = self.contract["integration"]
        parent = subprocess.check_output(
            ["git", "show", "-s", "--format=%P", integration["implementation_sha"]],
            cwd=REPO,
            text=True,
        ).strip()
        self.assertEqual(parent, integration["base_sha"])
        paths = subprocess.check_output(
            [
                "git",
                "diff",
                "--name-only",
                integration["base_sha"],
                integration["implementation_sha"],
            ],
            cwd=REPO,
            text=True,
        ).splitlines()
        self.assertEqual(len(paths), integration["changed_file_count"])
        self.assertTrue(all(path.startswith("Ti-Java/web/") for path in paths))

    def test_web_content_manifest(self) -> None:
        config = self.contract["web_content"]
        ignored = set(config["ignored_generated_directories"])
        rows: list[tuple[str, str, int]] = []
        for path in sorted(WEB_ROOT.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(WEB_ROOT)
            if any(part in ignored for part in relative.parts):
                continue
            data = path.read_bytes()
            rows.append((relative.as_posix(), hashlib.sha256(data).hexdigest(), len(data)))
        digest = hashlib.sha256()
        for relative, file_digest, byte_count in rows:
            digest.update(relative.encode("utf-8"))
            digest.update(b"\0")
            digest.update(file_digest.encode("ascii"))
            digest.update(b"\0")
            digest.update(str(byte_count).encode("ascii"))
            digest.update(b"\n")
        self.assertEqual(len(rows), config["file_count"])
        self.assertEqual(sum(row[2] for row in rows), config["byte_count"])
        self.assertEqual(digest.hexdigest(), config["manifest_sha256"])

    def test_openapi_sources_are_physically_fixed(self) -> None:
        for source in self.contract["runtime_scope"]["openapi_sources"]:
            self.assertEqual(sha256(REPO / source["path"]), source["sha256"])

    def test_runtime_operation_manifest_is_exact_and_get_only(self) -> None:
        scope = self.contract["runtime_scope"]
        source_manifest = (WEB_ROOT / "src/api/contracts/sourceManifest.ts").read_text(encoding="utf-8")
        actual = re.findall(r"legacy_[a-f0-9]+_(?:get|post|put|patch|delete)", source_manifest)
        self.assertEqual(actual, scope["public_bank_runtime_operation_ids"])
        self.assertEqual(scope["runtime_operation_count"], 5)
        self.assertEqual(scope["runtime_methods"], ["GET"])

    def test_transport_is_same_origin_and_request_traced(self) -> None:
        transport = (WEB_ROOT / "src/api/transport/configureGeneratedClients.ts").read_text(
            encoding="utf-8"
        )
        facade = (WEB_ROOT / "src/api/facade/publicBankFacade.ts").read_text(encoding="utf-8")
        self.assertIn("baseUrl: ''", transport)
        self.assertIn("credentials: 'same-origin'", transport)
        self.assertIn("headers.set(REQUEST_ID_HEADER, createRequestId())", transport)
        self.assertIn("const PUBLIC_READ_TIMEOUT_MS = 12_000", facade)

    def test_generated_sdk_is_only_imported_by_facade(self) -> None:
        imports: list[str] = []
        for path in (WEB_ROOT / "src").rglob("*"):
            if not path.is_file() or path.suffix not in {".ts", ".vue"}:
                continue
            if "api/generated/phase4aPublicBank/sdk.gen" in path.read_text(encoding="utf-8"):
                imports.append(path.relative_to(WEB_ROOT).as_posix())
        self.assertEqual(imports, ["src/api/facade/publicBankFacade.ts"])

    def test_spa_has_no_legacy_runtime_fallback(self) -> None:
        forbidden = ("iframe", "render_template", "jinja", "flask")
        for path in (WEB_ROOT / "src").rglob("*"):
            if not path.is_file() or path.suffix not in {".ts", ".vue", ".css"}:
                continue
            if "generated" in path.relative_to(WEB_ROOT / "src").parts:
                continue
            content = path.read_text(encoding="utf-8").lower()
            for token in forbidden:
                self.assertNotIn(token, content, f"{token} found in {path.relative_to(WEB_ROOT)}")

    def test_phase6_page_candidates_remain_pending(self) -> None:
        candidates = self.contract["phase6_disposition"]["page_shell_candidates"]
        self.assertEqual(len(candidates), 4)
        self.assertTrue(all(item["migration_status"] == "pending" for item in candidates))
        self.assertTrue(all(item["production_cutover"] is False for item in candidates))

    def test_effective_route_authority_is_unchanged(self) -> None:
        authority = self.contract["effective_authority"]
        status_path = REPO / authority["route_status_path"]
        self.assertEqual(sha256(status_path), authority["route_status_sha256"])
        status = json.loads(status_path.read_text(encoding="utf-8"))
        self.assertEqual(
            status["effective"]["migration_status"],
            {
                "migrated": authority["migrated_operations"],
                "pending": authority["pending_operations"],
            },
        )
        self.assertEqual(
            status["effective"]["production_cutover_operation_count"],
            authority["production_cutover_operations"],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
