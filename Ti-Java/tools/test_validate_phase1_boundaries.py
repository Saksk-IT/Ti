#!/usr/bin/env python3
"""Regression tests for validate_phase1_boundaries.py (standard library only)."""

from __future__ import annotations

import csv
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


TOOLS_DIR = Path(__file__).resolve().parent
TI_JAVA = TOOLS_DIR.parent
PHASE1 = TI_JAVA / "docs" / "refactor" / "phase1"
sys.path.insert(0, str(TOOLS_DIR))

from validate_phase1_boundaries import validate_all  # noqa: E402


class Phase1BoundaryValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.contracts = self.root / "module-contracts.json"
        self.invariants = self.root / "business-invariants.json"
        self.ownership = self.root / "03-data-ownership.csv"
        self.protocol = self.root / "comparison-cutover-protocol.md"
        shutil.copy2(PHASE1 / self.contracts.name, self.contracts)
        shutil.copy2(PHASE1 / self.invariants.name, self.invariants)
        shutil.copy2(TI_JAVA / "docs" / "refactor" / self.ownership.name, self.ownership)
        shutil.copy2(PHASE1 / self.protocol.name, self.protocol)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def validate(self) -> list[str]:
        return validate_all(
            self.contracts,
            self.invariants,
            self.ownership,
            self.protocol,
        )

    @staticmethod
    def read_json(path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def write_json(path: Path, document: dict) -> None:
        path.write_text(
            json.dumps(document, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def module(document: dict, module_id: str) -> dict:
        return next(
            module for module in document["modules"] if module["module_id"] == module_id
        )

    def assert_error_contains(self, errors: list[str], expected: str) -> None:
        self.assertTrue(
            any(expected in error for error in errors),
            f"expected error containing {expected!r}, got {errors!r}",
        )

    def test_repository_contracts_are_valid(self) -> None:
        self.assertEqual([], self.validate())

    def test_missing_owned_table_is_rejected(self) -> None:
        document = self.read_json(self.contracts)
        identity = self.module(document, "identity")
        removed = identity["owned_tables"].pop()
        self.write_json(self.contracts, document)

        self.assert_error_contains(
            self.validate(), f"missing owned resource: table:{removed}"
        )

    def test_table_owned_by_two_modules_is_rejected(self) -> None:
        document = self.read_json(self.contracts)
        catalog = self.module(document, "catalog")
        identity = self.module(document, "identity")
        duplicated = catalog["owned_tables"][0]
        identity["owned_tables"].append(duplicated)
        self.write_json(self.contracts, document)

        self.assert_error_contains(self.validate(), f"table is owned more than once: {duplicated}")

    def test_duplicate_ownership_matrix_row_is_rejected(self) -> None:
        with self.ownership.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
            headers = list(rows[0])
        with self.ownership.open("a", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=headers)
            writer.writerow(rows[0])

        self.assert_error_contains(self.validate(), "ownership CSV resource appears more than once")

    def test_dependency_cycle_is_rejected(self) -> None:
        document = self.read_json(self.contracts)
        identity = self.module(document, "identity")
        identity["allowed_dependencies"].append("web")
        self.write_json(self.contracts, document)

        self.assert_error_contains(self.validate(), "module dependency cycle")

    def test_duplicate_json_key_is_rejected(self) -> None:
        text = self.contracts.read_text(encoding="utf-8")
        text = text.replace(
            '  "schema_version": 1,',
            '  "schema_version": 1,\n  "schema_version": 2,',
            1,
        )
        self.contracts.write_text(text, encoding="utf-8")

        self.assert_error_contains(self.validate(), "duplicate JSON key: schema_version")

    def test_stale_java_root_package_is_rejected(self) -> None:
        document = self.read_json(self.contracts)
        document["java_root_package"] = "cn.ti"
        self.module(document, "identity")["base_package"] = "cn.ti.identity"
        self.write_json(self.contracts, document)

        errors = self.validate()
        self.assert_error_contains(errors, "java_root_package must be io.saksk.ti")
        self.assert_error_contains(errors, "stale cn.ti package names")

    def test_web_adapter_cannot_own_a_table(self) -> None:
        document = self.read_json(self.contracts)
        web = self.module(document, "web")
        web["owned_tables"].append("users")
        self.write_json(self.contracts, document)

        self.assert_error_contains(
            self.validate(), "web adapter boundary must not own tables/JPA persistence"
        )

    def test_messaging_domain_dependency_cannot_become_synchronous(self) -> None:
        document = self.read_json(self.contracts)
        messaging = self.module(document, "messaging")
        assessment = next(
            item
            for item in messaging["dependency_contracts"]
            if item["provider"] == "assessment"
        )
        assessment["interaction"] = "public_application_api"
        assessment["mode"] = "narrow_synchronous_query"
        self.write_json(self.contracts, document)

        self.assert_error_contains(
            self.validate(),
            "messaging -> assessment must be public-event asynchronous-only",
        )

    def test_missing_required_business_invariant_is_rejected(self) -> None:
        document = self.read_json(self.invariants)
        missing = "assessment.single-final-submission"
        document["invariants"] = [
            item for item in document["invariants"] if item["invariant_id"] != missing
        ]
        self.write_json(self.invariants, document)

        self.assert_error_contains(
            self.validate(), f"required business invariant is missing: {missing}"
        )

    def test_v1_precision_rule_cannot_be_claimed_as_legacy_contract(self) -> None:
        document = self.read_json(self.invariants)
        document["score_precision_policy"]["scope"] = "legacy_and_v1"
        document["score_precision_policy"][
            "legacy_compatibility_precision_status"
        ] = "proven"
        self.write_json(self.invariants, document)

        errors = self.validate()
        self.assert_error_contains(errors, "scoped to the new v1 target rule")
        self.assert_error_contains(errors, "must remain unknown until evidenced")

    def test_missing_protocol_marker_is_rejected(self) -> None:
        text = self.protocol.read_text(encoding="utf-8")
        self.protocol.write_text(
            text.replace("\nFREEZE\n", "\nFREEZE_REMOVED\n", 1),
            encoding="utf-8",
        )

        self.assert_error_contains(self.validate(), "protocol marker FREEZE must appear once")

    def test_post_write_recovery_order_is_rejected_when_reversed(self) -> None:
        text = self.protocol.read_text(encoding="utf-8")
        text = text.replace("**前向修复（默认优先）**", "**TEMP_DECISION**", 1)
        text = text.replace("**反向迁移**", "**前向修复（默认优先）**", 1)
        text = text.replace("**TEMP_DECISION**", "**反向迁移**", 1)
        self.protocol.write_text(text, encoding="utf-8")

        self.assert_error_contains(self.validate(), "post-write recovery order")

    def test_percentage_split_cutover_is_rejected(self) -> None:
        text = self.protocol.read_text(encoding="utf-8")
        text = text.replace(
            "一次性把完整入口整体指向 Java",
            "网关按批准步长开放流量",
            1,
        )
        self.protocol.write_text(text, encoding="utf-8")

        self.assert_error_contains(
            self.validate(), "contains forbidden strategy: 网关按批准步长开放流量"
        )


if __name__ == "__main__":
    unittest.main()
