#!/usr/bin/env python3
"""Unit tests for the fail-closed dual-PG all-shares plan bridge."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


TOOLS_DIR = Path(__file__).resolve().parent
import sys

sys.path.insert(0, str(TOOLS_DIR))
import capture_phase4b_personal_bank_all_shares_query_plans as tool  # noqa: E402


def exact_manifest() -> dict[str, object]:
    return {
        "manifest_id": tool.MANIFEST_ID,
        "schema_version": 1,
        "source_class": tool.SOURCE_CLASS,
        "scope": "test-only-preimplementation-evidence",
        "sequential_execution_required": False,
        "join_authorized": True,
        "http_derived_fields_excluded": ["share_link"],
        "query_count": 1,
        "queries": [{
            "ordinal": 1,
            "query_id": tool.QUERY_ID,
            "operation": "all-shares",
            "sql": tool.EXPECTED_SQL.upper().replace(":VIEWER_ID", ":viewer_id"),
            "parameter_order": ["viewer_id"],
            "parameters": {"viewer_id": "bigint"},
        }],
    }


def write_manifest(directory: str, manifest: object) -> Path:
    path = Path(directory) / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


class ManifestAndSqlSafetyTest(unittest.TestCase):

    def test_accepts_exact_single_query_http_neutral_manifest(self) -> None:
        manifest = exact_manifest()
        with tempfile.TemporaryDirectory() as temporary:
            loaded = tool.load_sql_manifest(write_manifest(temporary, manifest))
        self.assertEqual(manifest, loaded)

    def test_rejects_identity_scope_join_http_and_parameter_drift(self) -> None:
        mutations: list[dict[str, object]] = []
        for key, value in (
            ("manifest_id", "wrong"),
            ("schema_version", 2),
            ("source_class", "wrong.Source"),
            ("scope", "runtime"),
            ("sequential_execution_required", True),
            ("join_authorized", False),
            ("http_derived_fields_excluded", []),
            ("query_count", 2),
        ):
            manifest = exact_manifest()
            manifest[key] = value
            mutations.append(manifest)
        bad_type = exact_manifest()
        bad_type["queries"][0]["parameters"] = {"viewer_id": "integer"}
        mutations.append(bad_type)
        for manifest in mutations:
            with self.subTest(manifest=manifest):
                with tempfile.TemporaryDirectory() as temporary:
                    with self.assertRaises(RuntimeError):
                        tool.load_sql_manifest(write_manifest(temporary, manifest))

    def test_rejects_projection_filter_join_order_tie_break_and_write_drift(self) -> None:
        sql = exact_manifest()["queries"][0]["sql"]
        unsafe = (
            sql.replace("SELECT BS.ID,", "SELECT"),
            sql.replace("B.STATUS = 1", "B.STATUS <> 0"),
            sql.replace("BS.OWNER_ID =", "BS.OWNER_ID <>"),
            sql.replace("NULLS FIRST", "NULLS LAST"),
            sql + ", BS.ID DESC",
            sql + " LIMIT 10",
            sql + "; DELETE FROM bank_shares",
            sql.replace("AND B.STATUS = 1", "AND B.STATUS = 1 AND BS.IS_ACTIVE = TRUE"),
            sql.replace("B.NAME AS BANK_NAME", "B.NAME AS BANK_NAME, 'x' AS SHARE_LINK"),
        )
        for drifted in unsafe:
            with self.subTest(sql=drifted):
                with self.assertRaises(RuntimeError):
                    tool.validate_query_sql(drifted)

    def test_manifest_export_is_target_confined_and_selects_only_exporter(self) -> None:
        root = TOOLS_DIR.parent
        output = root / "server/target/unit-phase4b-all-shares-manifest.json"
        completed = subprocess.CompletedProcess([], 0, "", "")
        with patch.object(tool.base, "run", return_value=completed) as mocked:
            tool.export_sql_manifest(root, output)
        command = mocked.call_args.args[0]
        self.assertIn("-Dtest=PersonalBankAllSharesEvidenceSqlManifestTest", command)
        self.assertTrue(any(
            "ti.personal-bank-all-shares-evidence.sql-manifest-output" in item
            for item in command
        ))
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "server/target"):
                tool.export_sql_manifest(root, Path(temporary) / "manifest.json")


class BindFixtureAndResultTest(unittest.TestCase):

    def test_prepare_execute_preserves_single_bigint_bind(self) -> None:
        statement, binding = tool.prepared_explain_sql(exact_manifest()["queries"][0])
        self.assertIn("PREPARE phase4b_all_shares(bigint)", statement)
        self.assertIn("$1", statement)
        self.assertIn("EXECUTE phase4b_all_shares(4201)", statement)
        self.assertEqual(["viewer_id"], binding["occurrence_names"])
        self.assertEqual(1, binding["bound_parameter_count"])
        self.assertEqual(
            {
                "max_parallel_workers_per_gather": "0",
                "jit": "off",
                "work_mem": "64MB",
            },
            binding["session_settings"],
        )
        self.assertNotRegex(statement, r":[A-Za-z]")

    def test_fixture_models_join_filters_nulls_ties_raw_rows_and_no_index(self) -> None:
        sql = tool.fixture_sql(5_000, 150_000)
        self.assertIn("name text NOT NULL", sql)
        self.assertIn("generate_series(1, 150000)", sql)
        self.assertIn("value % 777 = 0", sql)
        self.assertIn("value % 5000 = 0 THEN NULL", sql)
        self.assertIn("value % 73 = 0 THEN NULL", sql)
        self.assertIn("(4102, 4201, 'inactive bank', 0)", sql)
        self.assertNotIn("CREATE INDEX", sql)
        self.assertNotIn("LIMIT", sql.upper())

    def test_result_proves_filters_projection_null_prefix_and_raw_rows(self) -> None:
        query = exact_manifest()["queries"][0]
        rows = [
            ["-6", "4101", "4201", "<NULL>", "<NULL>", "<NULL>",
             "<NULL>", "<NULL>", "<NULL>", "<NULL>", "<NULL>", "unicode"],
            ["-5", "4104", "4201", "A", "T1", "unexpected-value",
             "2020-01-01 00:00:00", "-1", "99", "f",
             "2026-01-01 00:00:02", ""],
            ["-1", "4101", "4201", "B", "T2", "read", "<NULL>",
             "<NULL>", "0", "t", "2026-01-01 00:00:01", "unicode"],
            ["0", "4101", "4201", "C", "T3", "read", "<NULL>",
             "<NULL>", "0", "<NULL>", "2026-01-01 00:00:01", "unicode"],
        ]
        raw = "\n".join(",".join(row) for row in rows)
        with patch.object(tool.base, "execute_psql", return_value=raw), patch.object(
            tool, "expected_row_count", return_value=4
        ), patch.object(tool, "expected_null_count", return_value=1):
            result = tool.all_shares_result("container", "database", query, 1)
        self.assertEqual(4, result["row_count"])
        self.assertEqual(12, result["column_count"])
        self.assertEqual(
            result["unordered_rows_sha256"],
            tool.base.sha256_json(sorted(rows)),
        )
        self.assertTrue(result["owner_filter_verified"])
        self.assertTrue(result["active_bank_filter_verified"])
        self.assertTrue(result["http_derived_share_link_absent"])

        bad_rows = deepcopy(rows)
        bad_rows[0][10] = "2025-01-01 00:00:00"
        bad_rows[1][10] = "<NULL>"
        with patch.object(
            tool.base,
            "execute_psql",
            return_value="\n".join(",".join(row) for row in bad_rows),
        ), patch.object(tool, "expected_row_count", return_value=4), patch.object(
            tool, "expected_null_count", return_value=1
        ):
            with self.assertRaisesRegex(RuntimeError, "NULLS FIRST"):
                tool.all_shares_result("container", "database", query, 1)


class PlanAndDocumentSafetyTest(unittest.TestCase):

    def test_plan_contract_closes_sort_join_two_scans_and_no_index(self) -> None:
        explain = [{"Plan": {
            "Node Type": "Sort",
            "Actual Rows": 4,
            "Actual Loops": 1,
            "Sort Method": "quicksort",
            "Sort Space Type": "Memory",
            "Plans": [{
                "Node Type": "Hash Join",
                "Actual Rows": 4,
                "Actual Loops": 1,
                "Plans": [
                    {"Node Type": "Seq Scan", "Relation Name": "bank_shares",
                     "Actual Rows": 4, "Actual Loops": 1},
                    {"Node Type": "Hash", "Actual Rows": 4, "Actual Loops": 1,
                     "Plans": [{"Node Type": "Seq Scan",
                                "Relation Name": "user_question_banks",
                                "Actual Rows": 4, "Actual Loops": 1}]},
                ],
            }],
        }}]
        summary = tool.base.plan_summary(explain)
        tool.assert_plan_contract(summary, 4)
        self.assertEqual(
            {"bank_shares": 1, "user_question_banks": 1},
            summary["relation_scan_occurrences"],
        )

        bad = deepcopy(summary)
        bad["index_names"] = ["invented_owner_index"]
        with self.assertRaisesRegex(RuntimeError, "index-backed"):
            tool.assert_plan_contract(bad, 4)

    def test_argument_floor_image_digest_and_payload_hash_guards(self) -> None:
        accepted = SimpleNamespace(
            bank_count=5_000,
            share_count=150_000,
            startup_timeout_seconds=120,
        )
        tool.validate_args(accepted)
        for field, value in (
            ("bank_count", 4_999),
            ("share_count", 149_999),
            ("startup_timeout_seconds", 0),
        ):
            rejected = SimpleNamespace(**vars(accepted))
            setattr(rejected, field, value)
            with self.assertRaises(ValueError):
                tool.validate_args(rejected)
        document = {"a": 1, "document_payload_sha256": "ignored"}
        self.assertEqual(
            tool.base.sha256_json({"a": 1}),
            tool.base.document_payload_sha256(document),
        )


if __name__ == "__main__":
    unittest.main()
