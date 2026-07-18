from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

import normalize_phase4c_personal_bank_user_counts_typed_normalization_junit as normalizer


EXPECTED_MANIFEST_SHA256 = (
    "b6c619ee1ed4be44fd68903c2449188fd6a65ee39b7c855b1796c901d3a0268c"
)
EXPECTED_PAYLOAD_SHA256 = (
    "08bdcc19ee0f3607d4e367a135d9a6544a5a9b5e5e999a2738180bc3258c8236"
)
EXPECTED_PROOF_SHA256 = (
    "8ea42f371664c6a664b0cd8b408c292a8a2a57524215a718a71c634a0bc93047"
)
EXPECTED_RAW_SHA256 = (
    "e1d5caebd6dfc7c792c8e4b4af337081246f718da5d1c4c82e072f46d6a1603b"
)


class TypedNormalizationJunitNormalizerTest(unittest.TestCase):
    def make_report(self, directory: Path) -> Path:
        root = ET.Element("testsuite", {
            normalizer.XSI_SCHEMA_ATTRIBUTE: (
                "https://maven.apache.org/surefire/maven-failsafe-plugin/"
                "xsd/failsafe-test-report.xsd"
            ),
            "version": "3.0.2",
            "name": normalizer.TEST_CLASS,
            "time": "5.125",
            "tests": "1",
            "errors": "0",
            "skipped": "0",
            "failures": "0",
            "flakes": "0",
        })
        properties = ET.SubElement(root, "properties")
        ET.SubElement(properties, "property", {
            "name": "database.password",
            "value": "DO-NOT-LEAK-password",
        })
        testcase = ET.SubElement(root, "testcase", {
            "name": normalizer.TEST_METHOD,
            "classname": normalizer.TEST_CLASS,
            "time": "4.125",
        })
        output = ET.SubElement(testcase, "system-out")
        output.text = (
            "Authorization: Bearer DO-NOT-LEAK; Cookie=session=DO-NOT-LEAK; "
            "/Users/private/path"
        )
        path = directory / normalizer.REPORT_FILENAME
        ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)
        return path

    def test_01_fixed_predecessors_golden_and_direct_sources_are_bound(self) -> None:
        historical, evidence, golden = normalizer.validate_fixed_sources()
        self.assertEqual(60, historical["result"]["totals"]["tests"])
        self.assertEqual(59, len(evidence["cases"]))
        self.assertEqual(normalizer.CASE_ID, golden["case_id"])
        self.assertEqual(500, golden["response"]["status"])

    def test_02_normalization_is_deterministic_and_strips_sensitive_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report = self.make_report(Path(temporary))
            first = normalizer.normalize_report(report)
            second = normalizer.normalize_report(report)
            self.assertEqual(first, second)
            rendered = normalizer.render_manifest(first).decode("utf-8")
            for forbidden in (
                "DO-NOT-LEAK",
                "/Users/private/path",
                "5.125",
                "4.125",
            ):
                self.assertNotIn(forbidden, rendered)
            self.assertEqual(
                first["document_payload_sha256"],
                normalizer.document_payload_sha256(first),
            )

    def test_03_identity_totals_and_nonpassing_children_fail_closed(self) -> None:
        mutations = (
            ("name", "otherTest", "identity"),
            ("classname", "other.Class", "identity"),
        )
        for attribute, value, message in mutations:
            with self.subTest(attribute=attribute), tempfile.TemporaryDirectory() as temporary:
                report = self.make_report(Path(temporary))
                tree = ET.parse(report)
                tree.getroot().find("testcase").set(attribute, value)
                tree.write(report, encoding="utf-8", xml_declaration=True)
                with self.assertRaisesRegex(normalizer.NormalizationError, message):
                    normalizer.normalize_report(report)

        for field in ("tests", "failures", "errors", "skipped", "flakes"):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temporary:
                report = self.make_report(Path(temporary))
                tree = ET.parse(report)
                tree.getroot().set(field, "2" if field == "tests" else "1")
                tree.write(report, encoding="utf-8", xml_declaration=True)
                with self.assertRaisesRegex(normalizer.NormalizationError, field):
                    normalizer.normalize_report(report)

        with tempfile.TemporaryDirectory() as temporary:
            report = self.make_report(Path(temporary))
            tree = ET.parse(report)
            ET.SubElement(tree.getroot().find("testcase"), "failure").text = "secret"
            tree.write(report, encoding="utf-8", xml_declaration=True)
            with self.assertRaisesRegex(normalizer.NormalizationError, "non-passing"):
                normalizer.normalize_report(report)

    def test_04_unknown_xml_comments_processing_instructions_and_dtd_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report = self.make_report(Path(temporary))
            tree = ET.parse(report)
            ET.SubElement(tree.getroot(), "attachment")
            tree.write(report, encoding="utf-8", xml_declaration=True)
            with self.assertRaisesRegex(normalizer.NormalizationError, "unknown"):
                normalizer.normalize_report(report)

        for injected, message in (
            (b"<!-- hidden -->", "comments"),
            (b"<?hidden instruction?>", "processing instructions"),
        ):
            with self.subTest(message=message), tempfile.TemporaryDirectory() as temporary:
                report = self.make_report(Path(temporary))
                raw = report.read_bytes()
                end = raw.index(b"?>") + 2
                report.write_bytes(raw[:end] + b"\n" + injected + raw[end:])
                with self.assertRaisesRegex(normalizer.NormalizationError, message):
                    normalizer.normalize_report(report)

        for raw, message in (
            (
                b"<?xml version='1.0' encoding='UTF-8'?>"
                b"<!DOCTYPE testsuite [<!ENTITY x 'secret'>]>"
                b"<testsuite>&x;</testsuite>",
                "DTD",
            ),
            (
                b"\xef\xbb\xbf<?xml version='1.0' encoding='UTF-8'?><testsuite/>",
                "byte-order",
            ),
            (
                b"<?xml version='1.0' encoding='UTF-16'?><testsuite/>",
                "legal UTF-8",
            ),
        ):
            with self.subTest(message=message), tempfile.TemporaryDirectory() as temporary:
                report = Path(temporary) / normalizer.REPORT_FILENAME
                report.write_bytes(raw)
                with self.assertRaisesRegex(normalizer.NormalizationError, message):
                    normalizer.normalize_report(report)

    def test_05_effective_ledger_replaces_one_leaf_without_double_counting(self) -> None:
        manifest = json.loads(normalizer.DEFAULT_OUTPUT.read_text(encoding="utf-8"))
        physical = manifest["result"]["physical_evidence"]
        effective = manifest["result"]["effective_evidence"]
        summary = manifest["result"]["effective_summary"]
        self.assertEqual(61, physical["aggregate_leaf_count"])
        self.assertEqual(60, effective["selected_effective_proof_leaf_count"])
        self.assertEqual(59, effective["logical_disposition_count"])
        self.assertEqual(1, effective["superseded_historical_representation_leaf_count"])
        self.assertFalse(effective["superseded_leaf_double_counted"])
        self.assertEqual(58, summary["http_disposition_count"])
        self.assertEqual(1, summary["typed_rejection_count"])
        self.assertEqual(50, summary["business_jdbc_http_count"])
        self.assertEqual({"200": 35, "302": 5, "401": 3, "403": 10, "500": 5},
                         summary["http_status_counts"])
        override = manifest["result"]["effective_override"]
        self.assertEqual("EXECUTED_TYPED_COLLAPSE",
                         override["historical_execution_disposition"])
        self.assertEqual("EXECUTED_FULL_CONTEXT_HTTP",
                         override["effective_execution_disposition"])
        self.assertEqual((500, 200),
                         (override["historical_source_status"], override["target_status"]))
        self.assertEqual(normalizer.RUNTIME_SCOPE, manifest["result"]["runtime_scope"])
        cast = manifest["result"]["runtime_scope"]["typed_cast_compatibility"]
        self.assertEqual(["16.14", "18.4"], cast["postgresql_versions"])
        self.assertEqual(["UTC", "America/Los_Angeles"],
                         cast["session_time_zones"])
        self.assertTrue(cast["cross_version_equal"])
        self.assertTrue(cast["session_timezone_independent"])
        http = manifest["result"]["runtime_scope"]["full_filter_http"]
        self.assertEqual("18.4", http["postgresql_version"])
        self.assertEqual(
            "java_string_bind_explicit_cast_insert_before_request_trace",
            http["fixture_origin"],
        )
        self.assertFalse(http["fixture_sql_literal_seeded"])

    def test_06_checked_manifest_binds_the_green_raw_report_and_payload(self) -> None:
        payload = normalizer.DEFAULT_OUTPUT.read_bytes()
        manifest = json.loads(payload)
        self.assertEqual(EXPECTED_MANIFEST_SHA256, hashlib.sha256(payload).hexdigest())
        self.assertEqual(EXPECTED_RAW_SHA256, manifest["raw_report"]["sha256"])
        self.assertEqual(51_169, manifest["raw_report"]["byte_count"])
        self.assertEqual(EXPECTED_PAYLOAD_SHA256,
                         manifest["document_payload_sha256"])
        self.assertEqual(EXPECTED_PAYLOAD_SHA256,
                         normalizer.document_payload_sha256(manifest))
        self.assertEqual(EXPECTED_PROOF_SHA256,
                         manifest["result"]["proof_payload_sha256"])
        self.assertEqual(normalizer.SOURCE_INPUTS, manifest["source_inputs"])
        self.assertFalse(manifest["authorization"]
                         ["current_manifest_and_source_bytes_external_git_anchor_complete"])
        self.assertFalse(manifest["authorization"]["route_migration_eligible"])


if __name__ == "__main__":
    unittest.main()
