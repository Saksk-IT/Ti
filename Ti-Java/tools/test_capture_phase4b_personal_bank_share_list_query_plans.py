#!/usr/bin/env python3
"""Unit tests for the fail-closed dual-PG share-list plan bridge."""

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
import capture_phase4b_personal_bank_share_list_query_plans as tool  # noqa: E402


def exact_manifest() -> dict[str, object]:
    return {
        "manifest_id": tool.MANIFEST_ID,
        "schema_version": 1,
        "source_class": tool.SOURCE_CLASS,
        "scope": "test-only-preimplementation-evidence",
        "sequential_execution_required": True,
        "join_authorized": False,
        "query_count": 2,
        "queries": [
            {
                "ordinal": 1,
                "query_id": tool.QUERY_IDS[0],
                "operation": "owner-status-probe",
                "sql": tool.EXPECTED_PROBE.upper()
                .replace(":BANK_ID", ":bank_id")
                .replace(":VIEWER_ID", ":viewer_id"),
                "parameter_order": ["bank_id", "viewer_id"],
                "parameters": {"bank_id": "integer", "viewer_id": "bigint"},
            },
            {
                "ordinal": 2,
                "query_id": tool.QUERY_IDS[1],
                "operation": "share-list",
                "sql": tool.EXPECTED_SHARE_LIST.upper().replace(":BANK_ID", ":bank_id"),
                "parameter_order": ["bank_id"],
                "parameters": {"bank_id": "integer"},
            },
        ],
    }


def write_manifest(directory: str, manifest: object) -> Path:
    path = Path(directory) / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


class ManifestAndSqlSafetyTest(unittest.TestCase):

    def test_accepts_exact_two_query_preimplementation_manifest(self) -> None:
        manifest = exact_manifest()
        with tempfile.TemporaryDirectory() as temporary:
            loaded = tool.load_sql_manifest(write_manifest(temporary, manifest))
        self.assertEqual(manifest, loaded)

    def test_rejects_identity_scope_order_count_and_parameter_drift(self) -> None:
        mutations: list[dict[str, object]] = []
        for key, value in (
            ("manifest_id", "wrong"),
            ("schema_version", 2),
            ("source_class", "wrong.Source"),
            ("scope", "runtime"),
            ("sequential_execution_required", False),
            ("join_authorized", True),
            ("query_count", 1),
        ):
            manifest = exact_manifest()
            manifest[key] = value
            mutations.append(manifest)
        reversed_queries = exact_manifest()
        reversed_queries["queries"] = list(reversed(reversed_queries["queries"]))
        mutations.append(reversed_queries)
        parameter_order = exact_manifest()
        parameter_order["queries"][0]["parameter_order"] = ["viewer_id", "bank_id"]
        mutations.append(parameter_order)
        parameter_type = exact_manifest()
        parameter_type["queries"][1]["parameters"] = {"bank_id": "bigint"}
        mutations.append(parameter_type)
        viewer_type = exact_manifest()
        viewer_type["queries"][0]["parameters"] = {
            "bank_id": "integer",
            "viewer_id": "integer",
        }
        mutations.append(viewer_type)
        for manifest in mutations:
            with self.subTest(manifest=manifest):
                with tempfile.TemporaryDirectory() as temporary:
                    with self.assertRaises(RuntimeError):
                        tool.load_sql_manifest(write_manifest(temporary, manifest))

    def test_rejects_join_projection_filter_order_tie_break_and_write_drift(self) -> None:
        probe = exact_manifest()["queries"][0]["sql"]
        shares = exact_manifest()["queries"][1]["sql"]
        unsafe = (
            (tool.QUERY_IDS[0], probe.replace("STATUS = 1", "STATUS <> 0")),
            (tool.QUERY_IDS[0], probe.replace("USER_ID =", "USER_ID <>")),
            (tool.QUERY_IDS[0], probe + " JOIN bank_shares s ON true"),
            (tool.QUERY_IDS[1], shares.replace("SELECT ID,", "SELECT")),
            (tool.QUERY_IDS[1], shares.replace("NULLS FIRST", "NULLS LAST")),
            (tool.QUERY_IDS[1], shares + ", id DESC"),
            (tool.QUERY_IDS[1], shares.replace("FROM BANK_SHARES", "FROM PG_TEMP.BANK_SHARES")),
            (tool.QUERY_IDS[1], shares + "; DELETE FROM bank_shares"),
            (tool.QUERY_IDS[1], shares + " LIMIT 10"),
        )
        for query_id, sql in unsafe:
            with self.subTest(query_id=query_id, sql=sql):
                with self.assertRaises(RuntimeError):
                    tool.validate_query_sql(query_id, sql)

    def test_manifest_export_is_target_confined_and_selects_only_exporter(self) -> None:
        root = TOOLS_DIR.parent
        output = root / "server/target/unit-phase4b-share-list-manifest.json"
        completed = subprocess.CompletedProcess([], 0, "", "")
        with patch.object(tool, "run", return_value=completed) as mocked:
            tool.export_sql_manifest(root, output)
        command = mocked.call_args.args[0]
        self.assertIn("-Dtest=PersonalBankShareListEvidenceSqlManifestTest", command)
        self.assertIn("-DskipITs", command)
        self.assertTrue(any(
            "ti.personal-bank-share-list-evidence.sql-manifest-output" in item
            for item in command
        ))
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "server/target"):
                tool.export_sql_manifest(root, Path(temporary) / "manifest.json")


class BindFixtureAndResultTest(unittest.TestCase):

    def test_prepare_execute_preserves_query_order_and_exact_mixed_binds(self) -> None:
        manifest = exact_manifest()
        probe_sql, probe_binding = tool.prepared_explain_sql(manifest["queries"][0])
        list_sql, list_binding = tool.prepared_explain_sql(manifest["queries"][1])
        self.assertIn("PREPARE phase4b_share_probe(integer, bigint)", probe_sql)
        self.assertIn("$1", probe_sql)
        self.assertIn("$2", probe_sql)
        self.assertIn("EXECUTE phase4b_share_probe(4101, 4201)", probe_sql)
        self.assertEqual(["bank_id", "viewer_id"], probe_binding["occurrence_names"])
        self.assertEqual(2, probe_binding["bound_parameter_count"])
        self.assertEqual(
            "integer",
            probe_binding["parameters"]["bank_id"]["postgres_type"],
        )
        self.assertEqual(
            "bigint",
            probe_binding["parameters"]["viewer_id"]["postgres_type"],
        )
        self.assertIn("PREPARE phase4b_share_list(integer)", list_sql)
        self.assertIn("EXECUTE phase4b_share_list(4101)", list_sql)
        self.assertEqual(["bank_id"], list_binding["occurrence_names"])
        self.assertEqual(1, list_binding["bound_parameter_count"])
        self.assertNotRegex(probe_sql + list_sql, r":[A-Za-z]")

    def test_fixture_models_no_index_null_boolean_ties_and_unbounded_history(self) -> None:
        sql = tool.fixture_sql(5_000, 150_000)
        self.assertIn("bank_id integer NOT NULL", sql)
        self.assertIn("created_at timestamp without time zone", sql)
        self.assertIn("generate_series(1, 150000)", sql)
        self.assertIn("value % 500 = 0", sql)
        self.assertIn("value % 5000 = 0 THEN NULL", sql)
        self.assertIn("value % 73 = 0 THEN NULL", sql)
        self.assertIn("value % 71 = 0 THEN false", sql)
        self.assertNotIn("CREATE INDEX", sql)
        self.assertNotIn("LIMIT", sql.upper())

    def test_share_result_proves_null_prefix_desc_ties_boolean_and_raw_rows(self) -> None:
        query = exact_manifest()["queries"][1]
        rows = [
            ["-2", "4101", "4202", "<NULL>", "<NULL>", "<NULL>",
             "<NULL>", "<NULL>", "<NULL>", "<NULL>", "<NULL>"],
            ["1", "4101", "4201", "A", "T1", "unexpected-value",
             "<NULL>", "-1", "-2", "f", "2026-01-01 00:00:02"],
            ["2", "4101", "4201", "B", "T2", "read",
             "<NULL>", "<NULL>", "0", "t", "2026-01-01 00:00:01"],
            ["3", "4101", "4201", "C", "T3", "read",
             "<NULL>", "<NULL>", "0", "<NULL>", "2026-01-01 00:00:01"],
        ]
        raw = "\n".join(",".join(row) for row in rows)
        with patch.object(tool, "execute_psql", return_value=raw):
            result = tool.share_result("container", "database", query, 500)
        self.assertEqual(4, result["row_count"])
        self.assertEqual(1, result["leading_null_created_at_count"])
        self.assertTrue(result["non_null_created_at_descending"])
        self.assertEqual("unordered_within_group", result["equal_created_at_order_contract"])
        self.assertEqual(["<NULL>", "f", "t"], result["postgres_boolean_values"])
        self.assertTrue(result["cross_owner_rows_present"])

        bad_rows = deepcopy(rows)
        bad_rows[0][10] = "2025-01-01 00:00:00"
        bad_rows[1][10] = "<NULL>"
        with patch.object(
            tool,
            "execute_psql",
            return_value="\n".join(",".join(row) for row in bad_rows),
        ):
            with self.assertRaisesRegex(RuntimeError, "NULLS FIRST"):
                tool.share_result("container", "database", query, 500)


class PlanAndDocumentSafetyTest(unittest.TestCase):

    def test_plan_summary_sanitization_and_contract_close_two_distinct_shapes(self) -> None:
        probe = [{"Plan": {
            "Node Type": "Index Scan",
            "Relation Name": "user_question_banks",
            "Index Name": "user_question_banks_pkey",
            "Actual Rows": 1,
            "Actual Loops": 1,
            "Execution Time": 0.1,
            "Shared Hit Blocks": 3,
        }}]
        shares = [{"Plan": {
            "Node Type": "Sort",
            "Actual Rows": 303,
            "Actual Loops": 1,
            "Sort Method": "quicksort",
            "Sort Space Type": "Memory",
            "Plans": [{
                "Node Type": "Seq Scan",
                "Relation Name": "bank_shares",
                "Actual Rows": 303,
                "Actual Loops": 1,
                "Temp Read Blocks": 0,
                "Temp Written Blocks": 0,
            }],
        }}]
        probe_summary = tool.plan_summary(probe)
        share_summary = tool.plan_summary(shares)
        tool.assert_plan_contract(tool.QUERY_IDS[0], probe_summary, 1)
        tool.assert_plan_contract(tool.QUERY_IDS[1], share_summary, 303)
        sanitized = tool.sanitized_plan(probe)
        self.assertNotIn("Execution Time", sanitized[0]["Plan"])
        self.assertNotIn("Shared Hit Blocks", sanitized[0]["Plan"])
        self.assertEqual(["Sort", "Seq Scan"], share_summary["node_types_preorder"])
        self.assertEqual({"bank_shares": 1}, share_summary["relation_scan_occurrences"])

        bad = deepcopy(share_summary)
        bad["index_names"] = ["invented_bank_id_index"]
        with self.assertRaisesRegex(RuntimeError, "index-backed"):
            tool.assert_plan_contract(tool.QUERY_IDS[1], bad, 303)

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
        self.assertEqual(tool.sha256_json({"a": 1}), tool.document_payload_sha256(document))


if __name__ == "__main__":
    unittest.main()
