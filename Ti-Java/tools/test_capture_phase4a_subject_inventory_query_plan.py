#!/usr/bin/env python3
"""Unit checks for the subject-inventory runtime SQL plan evidence bridge."""

from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch


TOOL_PATH = Path(__file__).with_name(
    "capture_phase4a_subject_inventory_query_plan.py"
)
SPEC = importlib.util.spec_from_file_location("phase4a_subject_inventory_plan", TOOL_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load query-plan capture tool: {TOOL_PATH}")
TOOL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TOOL)


def exact_sql() -> str:
    return """SELECT s.id AS subject_id,
       s.name AS subject_name,
       s.is_locked AS subject_locked,
       COUNT(q.id) AS question_count
FROM subjects s
LEFT JOIN questions q ON s.id = q.subject_id
GROUP BY s.id, s.name, s.is_locked
ORDER BY s.id ASC"""


def runtime_manifest() -> dict[str, object]:
    return {
        "manifest_id": TOOL.MANIFEST_ID,
        "schema_version": 1,
        "adapter_class": TOOL.ADAPTER_CLASS,
        "query_count": 1,
        "queries": [{
            "query_id": TOOL.QUERY_ID,
            "operation": TOOL.OPERATION,
            "sql": exact_sql(),
            "parameters": {},
        }],
    }


def write_manifest(directory: str, manifest: dict[str, object]) -> Path:
    path = Path(directory) / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def result_summary(subject_count: int = 5_000) -> dict[str, object]:
    shape = TOOL.fixture_shape(SimpleNamespace(
        subject_count=subject_count,
        question_count=TOOL.DEFAULT_QUESTION_COUNT,
    ))
    return {
        "row_count": shape["total_subject_count"],
        "minimum_id": -1,
        "maximum_id": subject_count,
        "first_ids_asc": [-1, 0, 1],
        "last_ids_asc": [subject_count - 2, subject_count - 1, subject_count],
        "strictly_ascending_by_id": True,
        "row_column_count": 4,
        "lock_value_counts": {
            "false": shape["false_lock_count"],
            "null": shape["null_lock_count"],
            "true": shape["true_lock_count"],
        },
        "empty_name_count": 1,
        "unicode_name_count": 1,
        "zero_question_subject_count": shape["zero_question_subject_count"],
        "question_count_sum": shape["assigned_question_count"],
        "edge_rows": {
            "-1": {
                "id": -1,
                "name": "",
                "is_locked": None,
                "question_count": 1,
            },
            "0": {
                "id": 0,
                "name": "科目 🧪",
                "is_locked": True,
                "question_count": 0,
            },
            str(subject_count): {
                "id": subject_count,
                "name": f"Synthetic subject {subject_count}",
                "is_locked": True,
                "question_count": 0,
            },
        },
        "canonical_psql_rows_sha256": "a" * 64,
    }


def plan_summary(rows: int = 5_002) -> dict[str, object]:
    nodes = [
        {"depth": 0, "Node Type": "Sort", "Actual Rows": rows, "Actual Loops": 1},
        {"depth": 1, "Node Type": "Aggregate", "Actual Rows": rows, "Actual Loops": 1},
        {
            "depth": 2,
            "Node Type": "Hash Join",
            "Join Type": "Right",
            "Actual Rows": 150_000,
            "Actual Loops": 1,
        },
        {
            "depth": 3,
            "Node Type": "Seq Scan",
            "Relation Name": "questions",
            "Actual Rows": 150_000,
            "Actual Loops": 1,
        },
        {
            "depth": 3,
            "Node Type": "Seq Scan",
            "Relation Name": "subjects",
            "Actual Rows": rows,
            "Actual Loops": 1,
        },
    ]
    return {
        "root_node_type": "Sort",
        "result_row_count": rows,
        "root_actual_loops": 1,
        "node_count": 5,
        "maximum_depth": 3,
        "maximum_actual_loops": 1,
        "node_type_counts": {
            "Aggregate": 1,
            "Hash Join": 1,
            "Seq Scan": 2,
            "Sort": 1,
        },
        "relation_scan_occurrences": {"questions": 1, "subjects": 1},
        "index_names": [],
        "buffer_fields_observed_before_normalization": [
            "Shared Hit Blocks",
            "Temp Read Blocks",
            "Temp Written Blocks",
        ],
        "nodes": nodes,
    }


def binding() -> dict[str, object]:
    return {
        "mode": "parameter-free",
        "bound_parameter_count": 0,
        "named_parameter_count": 0,
        "occurrence_names": [],
        "parameters": {},
    }


class RuntimeSqlManifestTest(unittest.TestCase):

    def test_accepts_only_the_exact_java_manifest_and_zero_bind_query(self) -> None:
        manifest = runtime_manifest()
        with tempfile.TemporaryDirectory() as temporary:
            loaded = TOOL.load_runtime_sql_manifest(
                write_manifest(temporary, manifest)
            )
        self.assertEqual(manifest, loaded)
        TOOL.validate_runtime_sql(loaded["queries"][0]["sql"])
        self.assertEqual([], TOOL.NAMED_PARAMETER.findall(exact_sql()))

    def test_rejects_manifest_identity_count_query_operation_and_parameter_drift(self) -> None:
        mutations = (
            ("manifest_id", "example.wrong"),
            ("schema_version", 2),
            ("adapter_class", "example.CopyAdapter"),
            ("query_count", 2),
        )
        for key, value in mutations:
            with self.subTest(key=key):
                manifest = runtime_manifest()
                manifest[key] = value
                with tempfile.TemporaryDirectory() as temporary:
                    with self.assertRaises(RuntimeError):
                        TOOL.load_runtime_sql_manifest(
                            write_manifest(temporary, manifest)
                        )

        for key, value in (
            ("query_id", "subject-copy"),
            ("operation", "subject-copy"),
            ("parameters", {"subject_id": "integer"}),
        ):
            with self.subTest(query_key=key):
                manifest = runtime_manifest()
                manifest["queries"][0][key] = value
                with tempfile.TemporaryDirectory() as temporary:
                    with self.assertRaises(RuntimeError):
                        TOOL.load_runtime_sql_manifest(
                            write_manifest(temporary, manifest)
                        )

    def test_rejects_count_join_column_order_write_wildcard_and_bind_drift(self) -> None:
        sql = exact_sql()
        unsafe = (
            sql.replace("COUNT(q.id)", "COUNT(*)"),
            sql.replace("LEFT JOIN", "INNER JOIN"),
            sql.replace("s.is_locked AS subject_locked,\n       ", ""),
            sql.replace("ORDER BY s.id ASC", "ORDER BY s.id DESC"),
            sql.replace(
                "LEFT JOIN questions q ON s.id = q.subject_id",
                "LEFT JOIN questions q ON s.id = q.subject_id "
                "JOIN users u ON u.id = q.id",
            ),
            sql + "; DELETE FROM subjects",
            "SELECT * FROM subjects s",
            sql + " WHERE s.id = :subject_id",
        )
        for candidate in unsafe:
            with self.subTest(candidate=candidate):
                with self.assertRaises(RuntimeError):
                    TOOL.validate_runtime_sql(candidate)


class FixtureAndResultTest(unittest.TestCase):

    def test_argument_validation_requires_large_fixture_and_immutable_image(self) -> None:
        args = SimpleNamespace(
            subject_count=TOOL.DEFAULT_SUBJECT_COUNT,
            question_count=TOOL.DEFAULT_QUESTION_COUNT,
            startup_timeout_seconds=120,
            image=TOOL.DEFAULT_IMAGE,
        )
        TOOL.validate_args(args)
        args.subject_count -= 1
        with self.assertRaisesRegex(ValueError, "at least"):
            TOOL.validate_args(args)
        args.subject_count = TOOL.DEFAULT_SUBJECT_COUNT
        args.question_count -= 1
        with self.assertRaisesRegex(ValueError, "at least"):
            TOOL.validate_args(args)
        args.question_count = TOOL.DEFAULT_QUESTION_COUNT
        args.image = "postgres:18.4-alpine"
        with self.assertRaisesRegex(ValueError, "immutable"):
            TOOL.validate_args(args)

    def test_fixture_closes_signed_null_orphan_lock_name_and_zero_count_edges(self) -> None:
        args = SimpleNamespace(subject_count=5_000, question_count=150_000)
        shape = TOOL.fixture_shape(args)
        self.assertEqual(5_002, shape["total_subject_count"])
        self.assertEqual(150_000, shape["question_count"])
        self.assertEqual(1, shape["orphan_assignment_count"])
        self.assertGreater(shape["null_assignment_count"], 1)
        self.assertEqual(1_001, shape["zero_question_subject_count"])
        self.assertEqual(
            150_000 - shape["null_assignment_count"] - 1,
            shape["assigned_question_count"],
        )
        sql = TOOL.fixture_sql(args)
        for fragment in (
            "(-1, '', NULL)",
            "(0, '科目 🧪', true)",
            "generate_series(1, 5000)",
            "generate_series(1, 149997)",
            "WHEN n % 997 = 0 THEN NULL",
            "SET session_replication_role = replica",
            "Orphan assignment edge",
            "CREATE INDEX ix_questions_subject_id",
            "CREATE INDEX ix_questions_subject_type",
            "VACUUM (ANALYZE) subjects",
        ):
            self.assertIn(fragment, sql)
        self.assertNotIn("CREATE TEMP", sql)

    def test_result_parser_preserves_four_fields_nullable_lock_and_signed_order(self) -> None:
        raw = (
            "-1|||1\n"
            "0|科目 🧪|t|0\n"
            "1|Synthetic subject 1||2\n"
            "2|Synthetic subject 2|f|0"
        )
        parsed = TOOL.parse_result_rows(raw, 2)
        self.assertEqual([-1, 0, 1], parsed["first_ids_asc"])
        self.assertEqual(4, parsed["row_column_count"])
        self.assertEqual({"false": 1, "null": 2, "true": 1}, parsed["lock_value_counts"])
        self.assertEqual(3, parsed["question_count_sum"])
        self.assertTrue(parsed["strictly_ascending_by_id"])

    def test_result_parser_rejects_bad_columns_boolean_count_and_order(self) -> None:
        cases = (
            ("-1|too|few", "column count"),
            ("-1||maybe|1\n0|name|t|0\n1|one|f|0", "boolean"),
            ("-1|||negative\n0|name|t|0\n1|one|f|0", "non-negative"),
            ("0|name|t|0\n-1|||1\n1|one|f|0", "exact signed id ASC"),
        )
        for raw, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(AssertionError, message):
                    TOOL.parse_result_rows(raw, 1)


class PlanContractTest(unittest.TestCase):

    def test_normalization_removes_noise_and_redacts_planner_expressions(self) -> None:
        raw = {
            "Planning Time": 1.2,
            "Execution Time": 2.3,
            "Plan": {
                "Node Type": "Hash Join",
                "Join Type": "Right",
                "Actual Rows": 5_002,
                "Actual Loops": 1,
                "Actual Total Time": 1.5,
                "Plan Rows": 5_000,
                "Total Cost": 99.0,
                "Shared Hit Blocks": 4,
                "Temp Written Blocks": 0,
                "Peak Memory Usage": 16,
                "Hash Cond": "(q.subject_id = s.id)",
            },
        }
        buffers = TOOL.collect_numeric_fields(raw, TOOL.BUFFER_KEYS)
        normalized = TOOL.normalize_explain(raw)
        serialized = json.dumps(normalized)
        for value in ("Time", "Blocks", "Memory", "Plan Rows", "Total Cost"):
            self.assertNotIn(value, serialized)
        self.assertNotIn("q.subject_id", serialized)
        self.assertEqual(0.0, buffers["Temp Written Blocks"])
        expression = normalized["Plan"]["Hash Cond"]
        self.assertEqual("planner expression omitted", expression["redacted"])
        self.assertRegex(expression["sha256"], r"^[0-9a-f]{64}$")

    def test_plan_gate_accepts_right_outer_swap_and_zero_bind_budget(self) -> None:
        args = SimpleNamespace(subject_count=5_000, question_count=150_000)
        checks = TOOL.assert_plan(
            result_summary(),
            TOOL.fixture_shape(args),
            plan_summary(),
            {"Temp Read Blocks": 0.0, "Temp Written Blocks": 0.0},
            binding(),
        )
        self.assertIn("one-outer-join-left-right-planner-swap-allowed", checks)
        self.assertIn("subjects-and-questions-scanned-once-only", checks)
        self.assertIn("one-select-zero-bind-fixed-cardinality", checks)

    def test_plan_gate_rejects_inner_join_extra_relation_loops_temp_and_bind(self) -> None:
        args = SimpleNamespace(subject_count=5_000, question_count=150_000)
        shape = TOOL.fixture_shape(args)
        cases: list[tuple[dict[str, object], dict[str, float], dict[str, object], str]] = []

        inner = plan_summary()
        inner["nodes"][2]["Join Type"] = "Inner"
        cases.append((inner, {"Temp Read Blocks": 0.0, "Temp Written Blocks": 0.0}, binding(), "outer join"))

        relation = plan_summary()
        relation["relation_scan_occurrences"] = {
            "questions": 1,
            "subjects": 1,
            "users": 1,
        }
        cases.append((relation, {"Temp Read Blocks": 0.0, "Temp Written Blocks": 0.0}, binding(), "relation budget"))

        loops = plan_summary()
        loops["maximum_actual_loops"] = 2
        cases.append((loops, {"Temp Read Blocks": 0.0, "Temp Written Blocks": 0.0}, binding(), "every node once"))

        cases.append((plan_summary(), {"Temp Read Blocks": 0.0, "Temp Written Blocks": 1.0}, binding(), "TEMP"))

        bad_binding = binding()
        bad_binding["bound_parameter_count"] = 1
        cases.append((plan_summary(), {"Temp Read Blocks": 0.0, "Temp Written Blocks": 0.0}, bad_binding, "bind surface"))

        for summary, temp, current_binding, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(AssertionError, message):
                    TOOL.assert_plan(
                        result_summary(), shape, summary, temp, current_binding
                    )


class EvidenceClosureTest(unittest.TestCase):

    def test_input_inventory_and_hash_closures_fail_on_drift(self) -> None:
        root = TOOL_PATH.resolve().parents[1]
        manifest_path = root / "server/target/phase4a-subject-inventory-runtime-sql.json"
        paths = TOOL.required_input_paths(root, manifest_path)
        self.assertEqual({
            "adapter",
            "runtime_sql_manifest",
            "runtime_sql_exporter",
            "capture_tool",
            "capture_tool_test",
        }, set(paths))
        self.assertTrue(str(paths["adapter"]).endswith(
            "JdbcSubjectInventoryQueryAdapter.java"
        ))
        self.assertTrue(str(paths["runtime_sql_exporter"]).endswith(
            "SubjectInventoryRuntimeSqlManifestTest.java"
        ))

        manifest = runtime_manifest()
        digest = TOOL.sha256_text(manifest["queries"][0]["sql"])
        TOOL.assert_runtime_sql_hash_closure(digest, manifest)
        changed = deepcopy(manifest)
        changed["queries"][0]["sql"] += "\n"
        with self.assertRaisesRegex(AssertionError, "runtime SQL hash drifted"):
            TOOL.assert_runtime_sql_hash_closure(digest, changed)

        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "Adapter.java"
            source.write_text("final source\n", encoding="utf-8")
            recorded = {"adapter_sha256": TOOL.sha256_file(source)}
            TOOL.assert_input_hash_closure(recorded, {"adapter": source})
            source.write_text("drifted source\n", encoding="utf-8")
            with self.assertRaisesRegex(AssertionError, "source drifted"):
                TOOL.assert_input_hash_closure(recorded, {"adapter": source})

    def test_public_evidence_gate_rejects_private_paths_ids_and_sensitive_keys(self) -> None:
        TOOL.assert_public_evidence({"safe": "public synthetic"})
        unsafe = (
            {"path": "/Users/example/project"},
            {"container": "ti-phase4a-subject-inventory-plan-deadbeefcafe"},
            {"database_password": "example"},
        )
        for document in unsafe:
            with self.subTest(document=document):
                with self.assertRaises(AssertionError):
                    TOOL.assert_public_evidence(document)

    def test_atomic_writer_is_byte_stable_and_removes_temporary_file(self) -> None:
        document = {"b": [1, 2], "a": "公开合成数据"}
        with tempfile.TemporaryDirectory() as temporary:
            first = Path(temporary) / "first.json"
            second = Path(temporary) / "second.json"
            TOOL.write_json_atomic(first, document)
            TOOL.write_json_atomic(second, document)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertFalse(first.with_name("first.json.tmp").exists())
            self.assertFalse(second.with_name("second.json.tmp").exists())

    def test_cleanup_removes_container_and_fails_if_it_remains(self) -> None:
        removed = subprocess.CompletedProcess([], 0, "", "")
        absent = subprocess.CompletedProcess([], 1, "", "not found")
        with patch.object(TOOL, "run", side_effect=[removed, absent]) as mocked:
            TOOL.cleanup_container("synthetic-container")
        self.assertEqual(
            ["docker", "rm", "--force", "synthetic-container"],
            mocked.call_args_list[0].args[0],
        )

        present = subprocess.CompletedProcess([], 0, "", "")
        with patch.object(TOOL, "run", side_effect=[removed, present]):
            with self.assertRaisesRegex(RuntimeError, "remains"):
                TOOL.cleanup_container("synthetic-container")


if __name__ == "__main__":
    unittest.main()
