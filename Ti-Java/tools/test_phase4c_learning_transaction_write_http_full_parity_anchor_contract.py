"""Contract integrity, extracted fixtures, fixed endpoints and negative cases."""
from copy import deepcopy
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from tools import build_phase4c_learning_transaction_write_http_full_parity_anchor_contract as builder
from tools import phase4c_learning_transaction_write_http_full_parity_anchor_successor_acceptance as acceptance
from tools import phase4c_learning_transaction_write_http_full_parity_successor_acceptance as bootstrap
from tools import phase4c_learning_transaction_write_http_integration_successor as integration

ROOT = Path(__file__).resolve().parents[1]
SECURITY = "server/src/main/java/io/saksk/ti/web/config/SecurityConfiguration.java"


class TransactionWriteFullParityAnchorTest(unittest.TestCase):
    def fixture(self, parent):
        root = Path(parent) / "extracted"
        for relative in acceptance.minimal_fixture_paths():
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, target)
        return root

    def test_deterministic_contract_and_complete_checkpoint(self):
        document = acceptance.load(ROOT)
        self.assertEqual(builder.serialized_contract(document),
                         (ROOT / builder.OUTPUT_RELATIVE).read_bytes())
        checkpoint = document["git_checkpoint"]
        self.assertEqual((8, 6, 2), tuple(checkpoint[key] for key in
                         ("changed_path_count", "added_path_count", "modified_path_count")))
        self.assertEqual(set(checkpoint["artifacts"]), set(document["bootstrap_sources"]))
        self.assertEqual("6ed81347467a4155887300b7e4ae36589204af79", checkpoint["commit_oid"])

    def test_gitless_fixture_never_invokes_git(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.fixture(temporary)
            with patch.object(builder.subprocess, "run", side_effect=AssertionError("Git forbidden")):
                self.assertEqual(acceptance.load(ROOT), acceptance.load(root))
                bootstrap.load(root)

    def test_progress_transition_composes_to_fixed_current_bytes(self):
        descriptor = bootstrap.source_transition(ROOT, builder.PROGRESS_PATH)
        expected = builder.PROGRESS_TRANSITION
        current = integration.load(ROOT)["transitions"][builder.PROGRESS_PATH]["current"]
        self.assertTrue(integration.accepts(ROOT, builder.PROGRESS_PATH,
                                           expected["successor_sha256"], expected["successor_byte_count"]))
        self.assertEqual(current["sha256"], descriptor["successor_sha256"])
        self.assertEqual(current["byte_count"], descriptor["successor_byte_count"])
        self.assertIsNone(acceptance.progress_successor(ROOT, "unknown", "0" * 64, 0))
        with self.assertRaises(AssertionError):
            acceptance.progress_successor(ROOT, builder.PROGRESS_PATH, "0" * 64, 0)

    def test_each_fixed_input_rejects_tampering(self):
        for relative in (builder.OUTPUT_RELATIVE, builder.SNAPSHOT_PATH,
                         builder.PROGRESS_PATH, SECURITY, *builder.UNCHANGED_BOOTSTRAP_SOURCES):
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as temporary:
                root = self.fixture(temporary)
                path = root / relative
                path.write_bytes(path.read_bytes() + b"\n")
                with self.assertRaises(AssertionError):
                    acceptance.load(root)

    def test_symlink_and_escape_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.fixture(temporary)
            target = root / builder.SNAPSHOT_PATH
            copy = root / "elsewhere.json"
            target.rename(copy)
            target.symlink_to(copy)
            with self.assertRaisesRegex(AssertionError, "symlink"):
                acceptance.load(root)
        for relative in ("../outside", "/tmp/outside", "C:/outside", "a/../outside", "a\\b"):
            with self.subTest(relative=relative), self.assertRaises(AssertionError):
                builder.fixed_regular_file(ROOT, relative)

    def test_rehashed_overclaims_and_metadata_tampering_are_rejected(self):
        original = acceptance.load(ROOT)
        for field in ("route_migration_eligible", "production_cutover",
                      "nine_transaction_write_operations_migrated",
                      "current_anchor_sources_external_git_anchor_complete"):
            changed = deepcopy(original)
            changed["authorization"][field] = True
            changed["document_payload_sha256"] = builder.payload_sha256(changed)
            with self.subTest(field=field), self.assertRaises(AssertionError):
                acceptance.validate(changed, ROOT)
        changed = deepcopy(original)
        changed["git_checkpoint"]["artifacts"].pop(next(iter(builder.CHECKPOINT["artifacts"])))
        changed["document_payload_sha256"] = builder.payload_sha256(changed)
        with self.assertRaises(AssertionError):
            acceptance.validate(changed, ROOT)

    def test_all_modified_preimages_are_preserved(self):
        snapshot = builder.read_snapshot(ROOT)
        for path, descriptor in builder.CHECKPOINT["artifacts"].items():
            versions = snapshot["sources"][path]
            self.assertEqual(descriptor["git_blob_oid"], builder.git_blob_oid(versions["after"].encode("utf-8")))
            if descriptor["change_type"] == "M":
                self.assertEqual(descriptor["previous_git_blob_oid"],
                                 builder.git_blob_oid(versions["before"].encode("utf-8")))
            else:
                self.assertIsNone(versions["before"])



if __name__ == "__main__":
    unittest.main()
