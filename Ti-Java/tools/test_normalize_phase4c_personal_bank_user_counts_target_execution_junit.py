from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import normalize_phase4c_personal_bank_user_counts_target_execution_junit as normalizer


EXPECTED_MANIFEST_PHYSICAL_SHA256 = (
    "64ff60cd56bf60f585af3d55b4ed4b4f7ee30b6a4c9e3e840688a1caaa45664b"
)
EXPECTED_MANIFEST_DOCUMENT_PAYLOAD_SHA256 = (
    "9f53234730888c5e3bcd682390093331daca61814c1111c195ea3def4fbe543c"
)
EXPECTED_MANIFEST_LEAF_PAYLOAD_SHA256 = (
    "77b0f4955931f2ad3206b7a1c0f9c9649b25a18c49bf1b259c452d169e5f0e04"
)
EXPECTED_RAW_REPORT_SHA256 = (
    "bb114a5571ef645ba37864dae1862a3657d92755a60479d734ce3c72f8de24ab"
)


class Phase4cTargetExecutionJunitNormalizerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.evidence = normalizer.load_fixed_evidence()
        cls.plan = normalizer.build_leaf_plan(cls.evidence)

    def make_report(self, directory: Path) -> Path:
        root = ET.Element("testsuite", {
            normalizer.XSI_SCHEMA_ATTRIBUTE: (
                "https://maven.apache.org/surefire/maven-failsafe-plugin/"
                "xsd/failsafe-test-report.xsd"
            ),
            "version": "3.0.2",
            "name": normalizer.TEST_CLASS,
            "time": "9.125",
            "tests": "60",
            "errors": "0",
            "skipped": "0",
            "failures": "0",
            "flakes": "0",
        })
        properties = ET.SubElement(root, "properties")
        ET.SubElement(properties, "property", {
            "name": "user.home",
            "value": "/Users/private-user",
        })
        ET.SubElement(properties, "property", {
            "name": "database.password",
            "value": "DO-NOT-LEAK-password-value",
        })
        for leaf in self.plan:
            testcase = ET.SubElement(root, "testcase", {
                "name": leaf["xml_name"],
                "classname": normalizer.TEST_CLASS,
                "time": "0.001",
            })
            if leaf["ordinal"] in {2, 48}:
                output = ET.SubElement(testcase, "system-out")
                output.text = (
                    "Authorization: Bearer DO-NOT-LEAK; "
                    "Cookie=session=DO-NOT-LEAK; /root/private/path"
                )
        path = directory / normalizer.REPORT_FILENAME
        ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)
        return path

    def test_01_plan_has_exact_unique_sixty_leaf_mapping_and_hashes(self) -> None:
        self.assertEqual(list(range(1, 61)), [leaf["ordinal"] for leaf in self.plan])
        self.assertEqual(60, len({leaf["logical_id"] for leaf in self.plan}))
        self.assertEqual(60, len({leaf["xml_name"] for leaf in self.plan}))
        self.assertEqual(
            normalizer.ORDERED_LOGICAL_LEAF_IDS_SHA256,
            normalizer.sha256_json([leaf["logical_id"] for leaf in self.plan]),
        )
        self.assertEqual(
            normalizer.ORDERED_XML_NAMES_SHA256,
            normalizer.sha256_json([leaf["xml_name"] for leaf in self.plan]),
        )

    def test_02_normalization_is_deterministic_and_cli_writer_is_repeatable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            report = self.make_report(directory)
            first = normalizer.normalize_report(report)
            second = normalizer.normalize_report(report)
            self.assertEqual(first, second)
            first_output = directory / "first.json"
            second_output = directory / "second.json"
            normalizer.write_manifest(report, first_output)
            normalizer.main(["--report", str(report), "--output", str(second_output)])
            self.assertEqual(first_output.read_bytes(), second_output.read_bytes())
            self.assertEqual(
                first["document_payload_sha256"],
                normalizer.document_payload_sha256(first),
            )

    def test_03_sensitive_properties_outputs_timings_and_paths_are_removed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report = self.make_report(Path(temporary))
            manifest = normalizer.normalize_report(report)
            rendered = normalizer.render_manifest(manifest).decode("utf-8")
            for forbidden in (
                "DO-NOT-LEAK",
                "/Users/private-user",
                "/root/private/path",
                "9.125",
                "0.001",
            ):
                self.assertNotIn(forbidden, rendered)
            self.assertTrue(manifest["confidentiality"]["sensitive_output_scan_passed"])
            self.assertFalse(manifest["raw_report"]["content_embedded"])

    def test_04_testcase_identity_or_order_tampering_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report = self.make_report(Path(temporary))
            tree = ET.parse(report)
            tree.getroot().findall("testcase")[5].set("name", "tampered-leaf")
            tree.write(report, encoding="utf-8", xml_declaration=True)
            with self.assertRaisesRegex(normalizer.NormalizationError, "name/order drifted"):
                normalizer.normalize_report(report)

    def test_05_failure_error_skip_and_flake_totals_are_rejected(self) -> None:
        for field in ("failures", "errors", "skipped", "flakes"):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temporary:
                report = self.make_report(Path(temporary))
                tree = ET.parse(report)
                tree.getroot().set(field, "1")
                tree.write(report, encoding="utf-8", xml_declaration=True)
                with self.assertRaisesRegex(normalizer.NormalizationError, field):
                    normalizer.normalize_report(report)

        with tempfile.TemporaryDirectory() as temporary:
            report = self.make_report(Path(temporary))
            tree = ET.parse(report)
            ET.SubElement(tree.getroot().findall("testcase")[0], "failure").text = "boom"
            tree.write(report, encoding="utf-8", xml_declaration=True)
            with self.assertRaisesRegex(normalizer.NormalizationError, "non-passing"):
                normalizer.normalize_report(report)

    def test_06_unknown_suite_or_testcase_child_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report = self.make_report(Path(temporary))
            tree = ET.parse(report)
            ET.SubElement(tree.getroot(), "secret-data").text = "hidden"
            tree.write(report, encoding="utf-8", xml_declaration=True)
            with self.assertRaisesRegex(normalizer.NormalizationError, "unknown child"):
                normalizer.normalize_report(report)
        with tempfile.TemporaryDirectory() as temporary:
            report = self.make_report(Path(temporary))
            tree = ET.parse(report)
            ET.SubElement(tree.getroot().findall("testcase")[0], "attachment")
            tree.write(report, encoding="utf-8", xml_declaration=True)
            with self.assertRaisesRegex(normalizer.NormalizationError, "unknown testcase child"):
                normalizer.normalize_report(report)

        for injected, expected_error in (
            (b"<!-- hidden comment -->", "comments"),
            (b"<?hidden instruction?>", "processing instructions"),
        ):
            with self.subTest(injected=injected), tempfile.TemporaryDirectory() as temporary:
                report = self.make_report(Path(temporary))
                raw = report.read_bytes()
                declaration_end = raw.index(b"?>") + 2
                report.write_bytes(
                    raw[:declaration_end]
                    + b"\n"
                    + injected
                    + raw[declaration_end:]
                )
                with self.assertRaisesRegex(normalizer.NormalizationError, expected_error):
                    normalizer.normalize_report(report)

    def test_07_duplicate_logical_case_id_is_rejected_before_xml_mapping(self) -> None:
        duplicate = copy.deepcopy(self.evidence)
        duplicate["cases"][1]["case_id"] = duplicate["cases"][0]["case_id"]
        with self.assertRaisesRegex(normalizer.NormalizationError, "duplicate logical case id"):
            normalizer.build_leaf_plan(duplicate)

    def test_08_doctype_and_entity_input_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report = Path(temporary) / normalizer.REPORT_FILENAME
            report.write_bytes(
                (b" " * 5000)
                + b"<!DOCTYPE testsuite [<!ENTITY x 'secret'>]>"
                + b"<testsuite>&x;</testsuite>"
            )
            with self.assertRaisesRegex(normalizer.NormalizationError, "DTD"):
                normalizer.normalize_report(report)

        utf16_entity = (
            "<?xml version='1.0' encoding='UTF-16'?>"
            "<!DOCTYPE testsuite [<!ENTITY x 'secret'>]>"
            "<testsuite>&x;</testsuite>"
        )
        for encoding, expected_error in (
            ("utf-16", "byte-order marks"),
            ("utf-16-le", "legal UTF-8 XML 1.0 declaration"),
        ):
            with self.subTest(encoding=encoding), tempfile.TemporaryDirectory() as temporary:
                report = Path(temporary) / normalizer.REPORT_FILENAME
                report.write_bytes(utf16_entity.encode(encoding))
                with self.assertRaisesRegex(normalizer.NormalizationError, expected_error):
                    normalizer.normalize_report(report)

        for illegal in (
            b"\xef\xbb\xbf<?xml version='1.0' encoding='UTF-8'?><testsuite/>",
            b"<?xml version='1.0' encoding='ISO-8859-1'?><testsuite/>",
        ):
            with self.subTest(illegal=illegal[:24]), tempfile.TemporaryDirectory() as temporary:
                report = Path(temporary) / normalizer.REPORT_FILENAME
                report.write_bytes(illegal)
                with self.assertRaises(normalizer.NormalizationError):
                    normalizer.normalize_report(report)

    def test_09_checked_manifest_binds_the_fresh_raw_report_and_payload(self) -> None:
        manifest = json.loads(normalizer.DEFAULT_OUTPUT.read_text(encoding="utf-8"))
        self.assertEqual(
            EXPECTED_RAW_REPORT_SHA256,
            manifest["raw_report"]["sha256"],
        )
        self.assertEqual(63450, manifest["raw_report"]["byte_count"])
        self.assertEqual(60, manifest["result"]["totals"]["passed"])
        self.assertEqual(
            self.plan,
            manifest["result"]["leaves"],
        )
        self.assertEqual(normalizer.SOURCE_INPUTS, manifest["source_inputs"])
        self.assertEqual(
            EXPECTED_MANIFEST_DOCUMENT_PAYLOAD_SHA256,
            manifest["document_payload_sha256"],
        )
        self.assertEqual(
            EXPECTED_MANIFEST_DOCUMENT_PAYLOAD_SHA256,
            normalizer.document_payload_sha256(manifest),
        )
        self.assertEqual(
            EXPECTED_MANIFEST_LEAF_PAYLOAD_SHA256,
            manifest["result"]["leaf_payload_sha256"],
        )
        self.assertEqual(
            normalizer.RAW_PROJECTION_SHA256,
            manifest["result"]["raw_projection_sha256"],
        )
        self.assertEqual(
            normalizer.EXECUTION_ORDER_CASE_IDS_SHA256,
            manifest["result"]["execution_order_case_ids_sha256"],
        )
        self.assertEqual(
            normalizer.ORDERED_LOGICAL_LEAF_IDS_SHA256,
            manifest["result"]["ordered_logical_leaf_ids_sha256"],
        )
        self.assertEqual(
            normalizer.ORDERED_XML_NAMES_SHA256,
            manifest["result"]["ordered_xml_names_sha256"],
        )
        self.assertEqual(
            EXPECTED_MANIFEST_PHYSICAL_SHA256,
            hashlib.sha256(normalizer.DEFAULT_OUTPUT.read_bytes()).hexdigest(),
        )


if __name__ == "__main__":
    unittest.main()
