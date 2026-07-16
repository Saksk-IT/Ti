#!/usr/bin/env python3
"""Contract tests for pinned-source Phase 4A public-bank golden capture."""

from __future__ import annotations

import hashlib
import importlib
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest


TOOLS_DIR = Path(__file__).resolve().parent
TI_JAVA = TOOLS_DIR.parent
REPOSITORY_ROOT = TI_JAVA.parent
GOLDEN = TI_JAVA / "docs" / "refactor" / "phase4a" / "golden-public-bank-reads.json"
sys.dont_write_bytecode = True
sys.path.insert(0, str(TOOLS_DIR))

import capture_phase4a_public_bank_goldens as capture  # noqa: E402


EXPECTED_KEY_SOURCES = {
    "app/__init__.py": (
        "1f945e13969e2d4bebf8925e65f483f2a1d4cef3",
        "9b2efe8a539ee47f7bcf475708466a64669b6bb36804ccf2b1cc5a63fcb21668",
        43_489,
    ),
    "app/core/extensions.py": (
        "963753e44321f8e884f8d4ea701aa61c5b0a3263",
        "293c63c5ea2d548e1389f221909dced878a861d28f8073f305fb98d6ff334052",
        2_150,
    ),
    "app/core/utils/api_response.py": (
        "48a052d8c27eea94c396e9a9656f2e4d2d23bbbb",
        "76fe1a04c1a9849264502054002f5b89e3a8a62a973df6c6c5ecc1ea7aead5b3",
        1_072,
    ),
    "app/modules/user_bank/routes/public.py": (
        "26044f0af2097b490e36a501894cb056aac654ae",
        "6f3455e825b0316272d298d35782e73dd3230e9b2fc5271f1c078009b389a663",
        12_723,
    ),
    "app/modules/user_bank/services/plaza_metrics_service.py": (
        "147979ec1e0370d2d1cb946b4a8a6859f04478b0",
        "a356ca751c30e50b5bb3d5fcab2742ce2ca6ac8a71dc6c82b974bdb63bb51d82",
        13_375,
    ),
    "app/modules/user_bank/services/plaza_query_service.py": (
        "4d1bd61921437fa9ec8b1463e68e3b6dffe8782f",
        "4d26b12bc756a40a5c89cf9ee373753f73bd2d5eed6ee3b11c916192c58aa057",
        42_772,
    ),
}


class PublicBankGoldenSourceContractTest(unittest.TestCase):
    def test_pinned_archive_is_complete_attested_and_removed(self) -> None:
        workspace: Path | None = None
        with capture.archived_legacy_source(REPOSITORY_ROOT) as archived:
            workspace = archived.workspace
            self.assertTrue((archived.root / "app" / "__init__.py").is_file())
            attestation = archived.attestation
            self.assertEqual(capture.LEGACY_COMMIT, attestation["archive_commit"])
            self.assertEqual(
                "db528464896085fe14849baef3c5e686ad1bc253",
                attestation["archive_tree"],
            )
            self.assertEqual(
                "4f196047cefcb7c73984b0661a50cfec50f79926543593bdc32152ea1fc99034",
                attestation["archive_sha256"],
            )
            self.assertEqual(645, attestation["extracted_file_count"])
            self.assertEqual(792, attestation["member_count"])
            self.assertTrue(attestation["commit_object_verified"])
            self.assertTrue(attestation["complete_app_tree_verified"])
            self.assertEqual(set(EXPECTED_KEY_SOURCES), set(attestation["key_sources"]))
            for path, (git_blob, sha256, size_bytes) in EXPECTED_KEY_SOURCES.items():
                with self.subTest(path=path):
                    evidence = attestation["key_sources"][path]
                    self.assertEqual(git_blob, evidence["git_blob"])
                    self.assertEqual(sha256, evidence["sha256"])
                    self.assertEqual(size_bytes, evidence["size_bytes"])
                    payload = (archived.root / path).read_bytes()
                    self.assertEqual(sha256, hashlib.sha256(payload).hexdigest())

        self.assertIsNotNone(workspace)
        self.assertFalse(workspace.exists())

    def test_checked_in_golden_matches_a_fresh_pinned_archive(self) -> None:
        document = json.loads(GOLDEN.read_text(encoding="utf-8"))
        self.assertFalse((TI_JAVA / "app").exists())
        self.assertEqual(46, document["case_count"])
        self.assertEqual(capture.LEGACY_COMMIT, document["legacy_commit"])
        case_bytes = json.dumps(
            document["cases"],
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        self.assertEqual(
            "931a9646847bac303637ba1c1896260e293e7a18c1bf6eed0962a7f31bbf4ea7",
            hashlib.sha256(case_bytes).hexdigest(),
        )
        with capture.archived_legacy_source(TI_JAVA) as archived:
            self.assertEqual(
                archived.attestation,
                document["legacy_source_attestation"],
            )

    def test_safe_extraction_rejects_traversal_and_links_before_writing(self) -> None:
        malicious_archives = {
            "traversal": self._tar_bytes([
                self._file("legacy-source/app/safe.py", b"safe = True\n"),
                self._file("legacy-source/app/../../escape.py", b"escaped = True\n"),
            ]),
            "symlink": self._tar_bytes([
                self._link("legacy-source/app/link.py", "../../escape.py"),
            ]),
        }
        for label, archive_bytes in malicious_archives.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                destination = root / "extracted"
                with self.assertRaises(capture.LegacySourceArchiveError):
                    capture._safe_extract_app_archive(
                        archive_bytes,
                        destination,
                        "sha1",
                    )
                self.assertFalse((root / "escape.py").exists())
                self.assertEqual([], list(destination.rglob("*")))

    def test_import_environment_restores_process_state_and_unloads_app(self) -> None:
        original_directory = Path.cwd()
        with tempfile.TemporaryDirectory() as temporary:
            source_root = Path(temporary)
            package = source_root / "app"
            package.mkdir()
            (package / "__init__.py").write_text("PINNED = True\n", encoding="utf-8")
            with capture.archived_legacy_import_environment(source_root):
                imported = importlib.import_module("app")
                capture.assert_module_from_archive(imported, source_root)
                self.assertTrue(imported.PINNED)
                self.assertEqual(source_root.resolve(), Path.cwd().resolve())
                self.assertEqual(str(source_root), sys.path[0])
            self.assertEqual(original_directory, Path.cwd())
            self.assertNotIn(str(source_root), sys.path)
            self.assertNotIn("app", sys.modules)

    @staticmethod
    def _file(name: str, payload: bytes) -> tuple[tarfile.TarInfo, bytes]:
        member = tarfile.TarInfo(name)
        member.size = len(payload)
        return member, payload

    @staticmethod
    def _link(name: str, target: str) -> tuple[tarfile.TarInfo, bytes]:
        member = tarfile.TarInfo(name)
        member.type = tarfile.SYMTYPE
        member.linkname = target
        return member, b""

    @staticmethod
    def _tar_bytes(members: list[tuple[tarfile.TarInfo, bytes]]) -> bytes:
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w") as archive:
            for member, payload in members:
                archive.addfile(member, io.BytesIO(payload) if member.isfile() else None)
        return buffer.getvalue()


if __name__ == "__main__":
    unittest.main()
