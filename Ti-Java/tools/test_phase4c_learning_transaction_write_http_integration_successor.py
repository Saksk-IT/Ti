"""The main reconciliation accepts only fixed predecessors and reviewed bytes."""
import hashlib
from pathlib import Path
import shutil
import tempfile
import unittest

from tools import phase4c_learning_transaction_write_http_integration_successor as integration

ROOT = Path(__file__).resolve().parents[1]
PROGRESS = "docs/refactor/05-progress.md"


class TransactionWriteIntegrationSuccessorTest(unittest.TestCase):
    def fixture(self, directory):
        root = Path(directory)
        for relative in (integration.CONTRACT, PROGRESS):
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, target)
        return root

    def test_all_recorded_predecessors_compose_to_exact_current_bytes(self):
        document = integration.load(ROOT)
        self.assertEqual(28, len(document["transitions"]))
        self.assertFalse(document["authorization"]["route_migration_eligible"])
        for relative, transition in document["transitions"].items():
            physical = (ROOT / relative).read_bytes()
            self.assertEqual(transition["current"]["sha256"], hashlib.sha256(physical).hexdigest())
            self.assertEqual(transition["current"]["byte_count"], len(physical))
            for accepted in transition["accepted"]:
                self.assertTrue(integration.accepts(ROOT, relative, accepted["sha256"], accepted["byte_count"]))

    def test_unknown_path_or_predecessor_is_rejected(self):
        self.assertFalse(integration.accepts(ROOT, "unknown", "0" * 64, 0))
        self.assertFalse(integration.accepts(ROOT, PROGRESS, "0" * 64, 0))

    def test_gitless_fixture_accepts_but_rejects_changed_current_bytes(self):
        accepted = integration.load(ROOT)["transitions"][PROGRESS]["accepted"][0]
        with tempfile.TemporaryDirectory() as directory:
            root = self.fixture(directory)
            self.assertTrue(integration.accepts(root, PROGRESS, accepted["sha256"], accepted["byte_count"]))
            path = root / PROGRESS
            path.write_bytes(path.read_bytes() + b"\n")
            self.assertFalse(integration.accepts(root, PROGRESS, accepted["sha256"], accepted["byte_count"]))

    def test_modified_contract_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.fixture(directory)
            path = root / integration.CONTRACT
            path.write_bytes(path.read_bytes() + b"\n")
            with self.assertRaises(AssertionError):
                integration.load(root)

    def test_symlinks_and_path_escape_are_rejected(self):
        accepted = integration.load(ROOT)["transitions"][PROGRESS]["accepted"][0]
        with tempfile.TemporaryDirectory() as directory:
            root = self.fixture(directory)
            path = root / PROGRESS
            target = root / "outside.md"
            path.rename(target)
            path.symlink_to(target)
            with self.assertRaises(AssertionError):
                integration.accepts(root, PROGRESS, accepted["sha256"], accepted["byte_count"])
        for relative in ("../outside", "/tmp/outside", "a/../b", "a\\b"):
            with self.assertRaises(AssertionError):
                integration.fixed_file(ROOT, relative)
