#!/usr/bin/env python3
"""Unit tests for deterministic dual-PG usage-stats query-plan evidence."""

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
import capture_phase4b_personal_bank_usage_stats_query_plans as tool  # noqa: E402


def exact_manifest() -> dict[str, object]:
    return {
        "manifest_id": tool.MANIFEST_ID,
        "schema_version": 1,
        "source_class": tool.SOURCE_CLASS,
        "scope": "test-only-preimplementation-evidence",
        "sequential_execution_required": True,
        "short_circuit_after_bank_probe": True,
        "shared_and_public_failure_boundaries": "independently_degrade_to_empty",
        "query_count": 3,
        "queries": [
            {
                "ordinal": ordinal,
                "query_id": query_id,
                "operation": operation,
                "sql": tool.EXPECTED_SQL[query_id].upper().replace(
                    ":BANK_ID", ":bank_id"
                ),
                "parameter_order": ["bank_id"],
                "parameters": {"bank_id": "integer"},
            }
            for ordinal, (query_id, operation) in enumerate(
                zip(
                    tool.QUERY_IDS,
                    ("bank-probe", "shared-users", "public-users"),
                ),
                start=1,
            )
        ],
    }


def write_manifest(directory: str, manifest: object) -> Path:
    path = Path(directory) / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def raw_explain(plan: dict[str, object]) -> list[dict[str, object]]:
    return [{
        "Plan": plan,
        "Planning Time": 0.25,
        "Execution Time": 1.5,
    }]


def plan_summary(explain: list[dict[str, object]]) -> dict[str, object]:
    buffers = tool.collect_numeric_fields(explain, tool.BUFFER_KEYS)
    timings = tool.collect_numeric_fields(explain, tool.TIMING_KEYS)
    normalized = tool.normalize_explain(explain)
    return tool.plan_summary(normalized, buffers, timings)


class ManifestAndSqlSafetyTest(unittest.TestCase):

    def test_accepts_exact_three_query_manifest(self) -> None:
        manifest = exact_manifest()
        with tempfile.TemporaryDirectory() as temporary:
            loaded = tool.load_sql_manifest(write_manifest(temporary, manifest))
        self.assertEqual(manifest, loaded)

    def test_rejects_identity_scope_semantics_order_count_and_parameter_drift(self) -> None:
        mutations: list[dict[str, object]] = []
        for key, value in (
            ("manifest_id", "wrong"),
            ("schema_version", 2),
            ("source_class", "wrong.Source"),
            ("scope", "runtime"),
            ("sequential_execution_required", False),
            ("short_circuit_after_bank_probe", False),
            ("shared_and_public_failure_boundaries", "fail-together"),
            ("query_count", 2),
        ):
            manifest = exact_manifest()
            manifest[key] = value
            mutations.append(manifest)
        reversed_queries = exact_manifest()
        reversed_queries["queries"] = list(reversed(reversed_queries["queries"]))
        mutations.append(reversed_queries)
        wrong_parameter_order = exact_manifest()
        wrong_parameter_order["queries"][1]["parameter_order"] = []
        mutations.append(wrong_parameter_order)
        wrong_parameter_type = exact_manifest()
        wrong_parameter_type["queries"][2]["parameters"] = {"bank_id": "bigint"}
        mutations.append(wrong_parameter_type)
        for manifest in mutations:
            with self.subTest(manifest=manifest):
                with tempfile.TemporaryDirectory() as temporary:
                    with self.assertRaises(RuntimeError):
                        tool.load_sql_manifest(write_manifest(temporary, manifest))

    def test_rejects_projection_join_filter_parameter_and_write_drift(self) -> None:
        probe = exact_manifest()["queries"][0]["sql"]
        shared = exact_manifest()["queries"][1]["sql"]
        public = exact_manifest()["queries"][2]["sql"]
        unsafe = (
            (tool.QUERY_IDS[0], probe.replace("SELECT ID,", "SELECT")),
            (tool.QUERY_IDS[0], probe.replace("WHERE ID =", "WHERE ID <>")),
            (tool.QUERY_IDS[1], shared.replace("BSR.STATUS = 1", "BSR.STATUS <> 0")),
            (tool.QUERY_IDS[1], shared.replace("BS.IS_ACTIVE = TRUE", "TRUE")),
            (tool.QUERY_IDS[1], shared.replace("BSR.SHARE_ID = BS.ID", "TRUE")),
            (tool.QUERY_IDS[2], public.replace("DISTINCT ", "")),
            (tool.QUERY_IDS[2], public.replace(":bank_id", ":viewer_id")),
            (tool.QUERY_IDS[2], public + " LIMIT 10"),
            (tool.QUERY_IDS[2], public + "; DELETE FROM public_bank_users"),
            (
                tool.QUERY_IDS[2],
                public.replace("PUBLIC_BANK_USERS", "PG_TEMP.PUBLIC_BANK_USERS"),
            ),
        )
        for query_id, sql in unsafe:
            with self.subTest(query_id=query_id, sql=sql):
                with self.assertRaises(RuntimeError):
                    tool.validate_query_sql(query_id, sql)

    def test_manifest_export_is_target_confined_and_selects_only_exporter(self) -> None:
        root = TOOLS_DIR.parent
        output = root / "server/target/unit-phase4b-usage-stats-manifest.json"
        completed = subprocess.CompletedProcess([], 0, "", "")
        with patch.object(tool.base, "run", return_value=completed) as mocked:
            tool.export_sql_manifest(root, output)
        command = mocked.call_args.args[0]
        self.assertIn("-DskipITs", command)
        self.assertIn("-Dtest=PersonalBankUsageStatsEvidenceSqlManifestTest", command)
        self.assertTrue(any(
            "ti.personal-bank-usage-stats-evidence.sql-manifest-output" in item
            for item in command
        ))
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "server/target"):
                tool.export_sql_manifest(root, Path(temporary) / "manifest.json")

    def test_paths_are_confined_and_fixture_order_is_exact(self) -> None:
        root = TOOLS_DIR.parent
        output = root / "docs/refactor/phase4b/unit-usage-plan.json"
        manifest = root / "server/target/unit-usage-manifest.json"
        tool.validate_paths(root, output, manifest)
        self.assertEqual(
            [str((root / item).resolve()) for item in tool.FIXTURE_INPUTS],
            [str(item) for item in tool.fixture_paths(root)],
        )
        self.assertEqual(
            ["030", "062", "063", "064", "065", "066"],
            [Path(item).name.split("-", 1)[0] for item in tool.FIXTURE_INPUTS],
        )
        with tempfile.TemporaryDirectory() as temporary:
            outside = Path(temporary) / "outside.json"
            with self.assertRaisesRegex(ValueError, "docs/refactor/phase4b"):
                tool.validate_paths(root, outside, manifest)
            with self.assertRaisesRegex(ValueError, "server/target"):
                tool.validate_paths(root, output, outside)


class BindFixtureAndResultTest(unittest.TestCase):

    def test_prepare_execute_preserves_order_integer_bind_and_session_settings(self) -> None:
        statements = []
        bindings = []
        for query in exact_manifest()["queries"]:
            statement, binding = tool.prepared_explain_sql(query)
            statements.append(statement)
            bindings.append(binding)
        self.assertEqual(
            [
                "phase4b_usage_bank_probe",
                "phase4b_usage_shared_users",
                "phase4b_usage_public_users",
            ],
            [binding["prepared_name"] for binding in bindings],
        )
        for statement, binding in zip(statements, bindings):
            self.assertIn("(integer) AS", statement)
            self.assertIn("$1", statement)
            self.assertIn("EXECUTE", statement)
            self.assertIn("(7101);", statement)
            self.assertIn("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)", statement)
            self.assertEqual(["bank_id"], binding["occurrence_names"])
            self.assertEqual(1, binding["bound_parameter_count"])
            self.assertEqual(
                {"max_parallel_workers_per_gather": "0", "jit": "off", "work_mem": "64MB"},
                binding["session_settings"],
            )
            self.assertEqual(
                "integer", binding["parameters"]["bank_id"]["postgres_type"]
            )
            self.assertNotRegex(statement, r":[A-Za-z]")

    def test_scale_fixture_is_deterministic_index_neutral_and_models_both_indexes(self) -> None:
        sql = tool.scale_fixture_sql(5_000, 150_000, 150_000)
        self.assertIn("generate_series(1, 5000)", sql)
        self.assertEqual(4, sql.count("generate_series(1, 150000)"))
        self.assertIn("value % 3 = 0", sql)
        self.assertIn("value % 500 = 0", sql)
        self.assertIn("value % 17 = 0 THEN 0", sql)
        self.assertIn("value % 19 = 0 THEN false", sql)
        self.assertIn("value % 23 = 0 THEN NULL", sql)
        self.assertNotRegex(sql.upper(), r"\b(?:CREATE|ALTER|DROP)\s+(?:UNIQUE\s+)?INDEX\b")
        schema = (
            TOOLS_DIR.parent
            / "server/src/test/resources/db/phase4b/065-personal-bank-usage-stats-schema.sql"
        ).read_text(encoding="utf-8")
        self.assertIn("UNIQUE (share_id, user_id)", schema)
        self.assertIn("UNIQUE (bank_id, user_id)", schema)
        self.assertIn("bank_share_records has no bank_id-leading index", schema)

    def test_shared_result_closes_filters_expiry_duplicates_and_canonical_hash(self) -> None:
        count = 100
        rows = [
            ["7001", "<NULL>"],
            ["7003", "2099-01-01 00:00:00"],
            ["7003", "<NULL>"],
            ["7004", "2020-01-01 00:00:00"],
            ["7005", "<NULL>"],
            ["7006", "<NULL>"],
            ["7007", "<NULL>"],
        ]
        for value in tool.expected_shared_values(count):
            expiry = (
                "2020-01-01 00:00:00" if value % 31 == 0
                else "<NULL>" if value % 37 == 0
                else "2099-01-01 00:00:00"
            )
            rows.append([str(tool.GENERATED_USER_OFFSET + value), expiry])
        rows.reverse()
        result = tool.shared_users_result(rows, count)
        self.assertEqual(len(rows), result["row_count"])
        self.assertEqual(1, result["pair_distinct_duplicate_user_count"])
        self.assertEqual(7, len(result["fixed_edge_rows"]))
        self.assertEqual(
            tool.base.sha256_json(sorted(rows, key=lambda row: (int(row[0]), row[1]))),
            result["unordered_rows_sha256"],
        )
        with self.assertRaisesRegex(RuntimeError, "row count"):
            tool.shared_users_result(rows[:-1], count)

    def test_public_result_closes_fixed_generated_distinct_and_canonical_hash(self) -> None:
        count = 1_000
        rows = [["7007"], ["100500"], ["7001"], ["101000"], ["7006"], ["7003"]]
        result = tool.public_users_result(rows, count)
        self.assertEqual(6, result["row_count"])
        self.assertEqual([7_001, 7_003, 7_006, 7_007], result["fixed_edge_user_ids"])
        self.assertEqual(
            tool.base.sha256_json([7_001, 7_003, 7_006, 7_007, 100_500, 101_000]),
            result["canonical_user_ids_sha256"],
        )
        with self.assertRaisesRegex(RuntimeError, "result drifted"):
            tool.public_users_result(rows + [["999"]], count)


class PlanDocumentAndCleanupTest(unittest.TestCase):

    def test_plan_normalization_retains_rows_loops_shapes_and_audits_removed_fields(self) -> None:
        explain = raw_explain({
            "Node Type": "Seq Scan",
            "Relation Name": "public_bank_users",
            "Alias": "public_bank_users",
            "Actual Rows": 5,
            "Actual Loops": 1,
            "Actual Startup Time": 0.01,
            "Actual Total Time": 0.25,
            "Startup Cost": 0.0,
            "Total Cost": 42.0,
            "Plan Rows": 10,
            "Shared Hit Blocks": 7,
            "Temp Read Blocks": 0,
            "Temp Written Blocks": 0,
            "Filter": "(bank_id = 7101)",
        })
        normalized = tool.normalize_explain(explain)
        node = normalized[0]["Plan"]
        self.assertEqual(5, node["Actual Rows"])
        self.assertEqual(1, node["Actual Loops"])
        self.assertEqual("planner expression omitted", node["Filter"]["redacted"])
        for key in (
            "Actual Startup Time", "Actual Total Time", "Startup Cost", "Total Cost",
            "Plan Rows", "Shared Hit Blocks", "Temp Read Blocks", "Temp Written Blocks",
        ):
            self.assertNotIn(key, node)
        summary = plan_summary(explain)
        self.assertIn("Planning Time", summary["timing_fields_observed_before_normalization"])
        self.assertIn("Execution Time", summary["timing_fields_observed_before_normalization"])
        self.assertIn("Shared Hit Blocks", summary["buffer_fields_observed_before_normalization"])
        self.assertEqual(0, summary["temp_read_blocks_observed"])
        self.assertEqual(0, summary["temp_written_blocks_observed"])

    def test_three_plan_contracts_allow_public_index_and_require_shared_seq_scan(self) -> None:
        probe = plan_summary(raw_explain({
            "Node Type": "Index Scan",
            "Relation Name": "user_question_banks",
            "Index Name": "user_question_banks_pkey",
            "Actual Rows": 1,
            "Actual Loops": 1,
            "Shared Hit Blocks": 3,
            "Temp Read Blocks": 0,
            "Temp Written Blocks": 0,
        }))
        shared = plan_summary(raw_explain({
            "Node Type": "Aggregate",
            "Strategy": "Hashed",
            "Actual Rows": 10,
            "Actual Loops": 1,
            "Shared Hit Blocks": 8,
            "Temp Read Blocks": 0,
            "Temp Written Blocks": 0,
            "Plans": [{
                "Node Type": "Hash Join",
                "Join Type": "Inner",
                "Actual Rows": 10,
                "Actual Loops": 1,
                "Plans": [
                    {
                        "Node Type": "Seq Scan",
                        "Relation Name": "bank_share_records",
                        "Alias": "bsr",
                        "Actual Rows": 10,
                        "Actual Loops": 1,
                    },
                    {
                        "Node Type": "Hash",
                        "Actual Rows": 20,
                        "Actual Loops": 1,
                        "Plans": [{
                            "Node Type": "Seq Scan",
                            "Relation Name": "bank_shares",
                            "Alias": "bs",
                            "Actual Rows": 20,
                            "Actual Loops": 1,
                        }],
                    },
                ],
            }],
        }))
        public = plan_summary(raw_explain({
            "Node Type": "Unique",
            "Actual Rows": 5,
            "Actual Loops": 1,
            "Shared Hit Blocks": 2,
            "Temp Read Blocks": 0,
            "Temp Written Blocks": 0,
            "Plans": [{
                "Node Type": "Index Only Scan",
                "Relation Name": "public_bank_users",
                "Index Name": "public_bank_users_bank_id_user_id_key",
                "Actual Rows": 5,
                "Actual Loops": 1,
            }],
        }))
        tool.assert_plan_contract(tool.QUERY_IDS[0], probe, 1)
        tool.assert_plan_contract(tool.QUERY_IDS[1], shared, 10)
        tool.assert_plan_contract(tool.QUERY_IDS[2], public, 5)
        self.assertIn("public_bank_users_bank_id_user_id_key", public["index_names"])

        drifted = deepcopy(shared)
        record_node = next(
            node for node in drifted["nodes"]
            if node.get("Relation Name") == "bank_share_records"
        )
        record_node["Node Type"] = "Index Scan"
        drifted["index_names"] = ["invented_bank_share_records_bank_id_idx"]
        with self.assertRaisesRegex(RuntimeError, "no-bank_id-index scan"):
            tool.assert_plan_contract(tool.QUERY_IDS[1], drifted, 10)

    def test_public_contract_does_not_lock_planner_to_one_scan_type(self) -> None:
        for scan_type in ("Seq Scan", "Bitmap Heap Scan", "Index Scan", "Index Only Scan"):
            with self.subTest(scan_type=scan_type):
                summary = plan_summary(raw_explain({
                    "Node Type": scan_type,
                    "Relation Name": "public_bank_users",
                    "Index Name": "public_bank_users_bank_id_user_id_key",
                    "Actual Rows": 4,
                    "Actual Loops": 1,
                    "Shared Hit Blocks": 1,
                    "Temp Read Blocks": 0,
                    "Temp Written Blocks": 0,
                }))
                tool.assert_plan_contract(tool.QUERY_IDS[2], summary, 4)

    def test_fixed_images_argument_floors_hashes_and_redaction(self) -> None:
        self.assertEqual(["16.14", "18.4"], [item["version"] for item in tool.POSTGRES_IMAGES])
        self.assertEqual(
            [
                "57c72fd2a128e416c7fcc499958864df5301e940bca0a56f58fddf30ffc07777",
                "9a8afca54e7861fd90fab5fdf4c42477a6b1cb7d293595148e674e0a3181de15",
            ],
            [item["image"].rsplit("sha256:", 1)[1] for item in tool.POSTGRES_IMAGES],
        )
        accepted = SimpleNamespace(
            bank_count=5_000,
            share_record_count=150_000,
            public_user_count=150_000,
            startup_timeout_seconds=120,
        )
        tool.validate_args(accepted)
        for field, value in (
            ("bank_count", 4_999),
            ("share_record_count", 149_999),
            ("public_user_count", 149_999),
            ("startup_timeout_seconds", 0),
        ):
            rejected = SimpleNamespace(**vars(accepted))
            setattr(rejected, field, value)
            with self.assertRaises(ValueError):
                tool.validate_args(rejected)
        for document in (
            {"password": "x"},
            {"nested": {"value": "/Users/private/path"}},
            {"nested": ["ti-phase4b-usage-plan-abcdef"]},
            {"nested": "person@test.invalid"},
        ):
            with self.assertRaises(RuntimeError):
                tool.assert_redacted(document)

    def test_cleanup_runs_when_container_readiness_fails(self) -> None:
        args = SimpleNamespace(
            bank_count=5_000,
            share_record_count=150_000,
            public_user_count=150_000,
            startup_timeout_seconds=1,
        )
        started = subprocess.CompletedProcess([], 0, "container-id\n", "")
        with patch.object(tool.base, "run", return_value=started) as mocked_run, patch.object(
            tool.base,
            "wait_for_postgres",
            side_effect=RuntimeError("not ready"),
        ):
            with self.assertRaisesRegex(RuntimeError, "not ready"):
                tool.capture_engine(tool.POSTGRES_IMAGES[0], exact_manifest(), args, TOOLS_DIR.parent)
        commands = [call.args[0] for call in mocked_run.call_args_list]
        self.assertEqual("docker", commands[0][0])
        self.assertEqual(["docker", "rm", "-f", "-v"], commands[-1][:4])
        self.assertEqual(commands[0][commands[0].index("--name") + 1], commands[-1][-1])

    def test_document_payload_and_render_are_byte_deterministic(self) -> None:
        document = {"z": [3, 2, 1], "a": {"unicode": "高数"}}
        digest = tool.base.document_payload_sha256(document)
        with_digest = {**document, "document_payload_sha256": digest}
        self.assertEqual(digest, tool.base.document_payload_sha256(with_digest))
        self.assertEqual(
            tool.base.render_document(with_digest),
            tool.base.render_document(deepcopy(with_digest)),
        )
        self.assertTrue(tool.base.render_document(with_digest).endswith("\n"))

    def test_tool_inputs_hash_manifest_sql_tools_tests_and_all_fixtures(self) -> None:
        root = TOOLS_DIR.parent
        manifest_path = (
            root / "server/target/phase4b-personal-bank-usage-stats-evidence-sql.json"
        )
        inputs = tool.tool_inputs(root, manifest_path)
        self.assertEqual(
            "server/target/phase4b-personal-bank-usage-stats-evidence-sql.json",
            inputs["sql_manifest_path"],
        )
        for key in (
            "evidence_sql_sha256",
            "sql_contract_test_sha256",
            "sql_manifest_exporter_sha256",
            "jdbc_compatibility_test_sha256",
            "base_capture_support_sha256",
            "capture_tool_sha256",
            "capture_tool_test_sha256",
            "sql_manifest_sha256",
            "sql_manifest_payload_sha256",
        ):
            self.assertRegex(inputs[key], r"^[0-9a-f]{64}$")
        for index, fixture in enumerate(tool.FIXTURE_INPUTS, start=1):
            self.assertEqual(fixture, inputs[f"fixture_{index}"])
            self.assertRegex(inputs[f"fixture_{index}_sha256"], r"^[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
