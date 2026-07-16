#!/usr/bin/env python3
"""Unit checks for the question-detail runtime SQL plan evidence bridge."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest


TOOL_PATH = Path(__file__).with_name(
    "capture_phase4a_question_detail_query_plan.py"
)
SPEC = importlib.util.spec_from_file_location(
    "phase4a_question_detail_plan", TOOL_PATH
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load query-plan capture tool: {TOOL_PATH}")
TOOL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TOOL)


RUNTIME_SQL = """SELECT q.id,
       q.subject_id,
       q.type,
       q.content,
       q.options,
       q.answer,
       q.analysis,
       q.tags,
       q.difficulty,
       q.image_path,
       q.source,
       q.created_by,
       q.updated_by,
       q.created_at,
       q.updated_at
FROM questions q
WHERE q.id = :question_id"""


def runtime_manifest() -> dict[str, object]:
    return {
        "manifest_id": TOOL.MANIFEST_ID,
        "schema_version": 1,
        "adapter_class": TOOL.ADAPTER_CLASS,
        "query_count": 1,
        "queries": [
            {
                "query_id": TOOL.QUERY_ID,
                "operation": TOOL.OPERATION,
                "sql": RUNTIME_SQL,
                "parameters": {
                    TOOL.PARAMETER_NAME: {
                        "bind_kind": "jdbc-scalar",
                        "jdbc_type": "bigint",
                        "value": "1",
                    }
                },
            }
        ],
    }


def write_manifest_text(directory: str, manifest: dict[str, object]) -> Path:
    path = Path(directory) / "runtime-sql.json"
    path.write_text(
        json.dumps(manifest, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return path


def plan_summary(*, rows: int = 1) -> dict[str, object]:
    return {
        "root_node_type": "Index Scan",
        "result_row_count": rows,
        "root_actual_loops": 1,
        "node_count": 1,
        "maximum_depth": 0,
        "maximum_actual_loops": 1,
        "node_type_counts": {"Index Scan": 1},
        "relation_scan_occurrences": {"questions": 1},
        "index_names": ["questions_pkey"],
        "buffer_fields_observed_before_normalization": ["Shared Hit Blocks"],
        "nodes": [],
    }


def execution(question_id: int = 1) -> dict[str, object]:
    return {
        "mode": "prepare-execute",
        "bound_parameter_count": 1,
        "named_parameter_count": 1,
        "occurrence_names": [TOOL.PARAMETER_NAME],
        "positional_sql_sha256": "0" * 64,
        "parameters": {
            TOOL.PARAMETER_NAME: {
                "bind_kind": "jdbc-scalar",
                "postgres_type": "bigint",
                "value": question_id,
            }
        },
    }


class RuntimeSqlManifestTest(unittest.TestCase):

    def test_accepts_exact_manifest_and_bigint_parameter_shapes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            manifest = runtime_manifest()
            path = write_manifest_text(temporary, manifest)
            self.assertEqual(manifest, TOOL.load_runtime_sql_manifest(path))

            query = manifest["queries"][0]
            for parameter in (
                "bigint",
                "long",
                1,
                "1",
                {"postgres_type": "bigint", "value": TOOL.LONG_MAX_VALUE},
            ):
                query["parameters"] = {TOOL.PARAMETER_NAME: parameter}
                path = write_manifest_text(temporary, manifest)
                self.assertEqual(manifest, TOOL.load_runtime_sql_manifest(path))

    def test_rejects_manifest_identity_adapter_query_and_parameter_drift(self) -> None:
        mutations = (
            ("manifest_id", "example.wrong"),
            ("adapter_class", "example.CopyOfQuestionDetailAdapter"),
            ("query_count", 2),
        )
        for key, value in mutations:
            with self.subTest(key=key):
                manifest = runtime_manifest()
                manifest[key] = value
                with tempfile.TemporaryDirectory() as temporary:
                    path = write_manifest_text(temporary, manifest)
                    with self.assertRaises(RuntimeError):
                        TOOL.load_runtime_sql_manifest(path)

        manifest = runtime_manifest()
        query = manifest["queries"][0]
        query["query_id"] = "question-detail-copy"
        with tempfile.TemporaryDirectory() as temporary:
            path = write_manifest_text(temporary, manifest)
            with self.assertRaisesRegex(RuntimeError, "query ID drifted"):
                TOOL.load_runtime_sql_manifest(path)

        manifest = runtime_manifest()
        query = manifest["queries"][0]
        query["parameters"] = {
            TOOL.PARAMETER_NAME: {"jdbc_type": "integer", "value": 1}
        }
        with tempfile.TemporaryDirectory() as temporary:
            path = write_manifest_text(temporary, manifest)
            with self.assertRaisesRegex(RuntimeError, "must be bigint"):
                TOOL.load_runtime_sql_manifest(path)

    def test_rejects_wildcard_join_extra_bind_and_runtime_mutation(self) -> None:
        unsafe = (
            "SELECT * FROM questions q WHERE q.id=:question_id",
            (
                "SELECT q.id FROM questions q JOIN subjects s "
                "ON s.id=q.subject_id WHERE q.id=:question_id"
            ),
            (
                "SELECT q.id FROM questions q WHERE q.id=:question_id "
                "AND q.subject_id=:subject_id"
            ),
            "SELECT q.id FROM questions q WHERE q.id=:question_id; DELETE FROM questions",
            "CREATE TEMP TABLE selected_questions(id bigint)",
        )
        for sql in unsafe:
            with self.subTest(sql=sql):
                with self.assertRaises(RuntimeError):
                    TOOL.validate_runtime_sql("unsafe", sql)


class BindSurfaceTest(unittest.TestCase):

    def test_all_five_ids_remain_one_bigint_bind_and_one_statement(self) -> None:
        args = SimpleNamespace(
            question_count=TOOL.DEFAULT_QUESTION_COUNT,
            subject_count=TOOL.DEFAULT_SUBJECT_COUNT,
        )
        specs = TOOL.observation_specs(args)
        self.assertEqual(
            [
                "first-existing-question",
                "middle-existing-question",
                "last-existing-question",
                "first-missing-question",
                "signed-bigint-maximum-missing-question",
            ],
            [spec["observation_id"] for spec in specs],
        )
        self.assertEqual([1, 1, 1, 0, 0], [s["expected_rows"] for s in specs])
        self.assertEqual(TOOL.LONG_MAX_VALUE, specs[-1]["question_id"])

        positional_hashes: set[str] = set()
        for spec in specs:
            statement, binding = TOOL.prepared_execution_sql(
                spec["observation_id"],
                RUNTIME_SQL,
                spec["question_id"],
            )
            self.assertEqual(1, binding["bound_parameter_count"])
            self.assertEqual(1, binding["named_parameter_count"])
            self.assertEqual([TOOL.PARAMETER_NAME], binding["occurrence_names"])
            self.assertEqual(
                "bigint",
                binding["parameters"][TOOL.PARAMETER_NAME]["postgres_type"],
            )
            self.assertEqual(1, statement.count("PREPARE "))
            self.assertEqual(1, statement.count("EXECUTE "))
            self.assertEqual(1, statement.count("DEALLOCATE "))
            self.assertNotIn(":question_id", statement)
            positional_hashes.add(binding["positional_sql_sha256"])

        self.assertEqual(1, len(positional_hashes))

    def test_invalid_bigint_bindings_fail_closed(self) -> None:
        for value in (-1, TOOL.LONG_MAX_VALUE + 1, True, "1"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(RuntimeError, "non-negative bigint"):
                    TOOL.bound_parameter(value)


class PlanContractTest(unittest.TestCase):

    def test_normalization_removes_noise_and_redacts_index_literal(self) -> None:
        raw = {
            "Planning Time": 1.2,
            "Execution Time": 2.3,
            "Plan": {
                "Node Type": "Index Scan",
                "Relation Name": "questions",
                "Alias": "q",
                "Index Name": "questions_pkey",
                "Actual Rows": 1,
                "Actual Loops": 1,
                "Actual Total Time": 0.3,
                "Shared Hit Blocks": 4,
                "Temp Written Blocks": 0,
                "Peak Memory Usage": 16,
                "Index Cond": "(id = '9223372036854775807'::bigint)",
            },
        }
        buffers = TOOL.collect_numeric_fields(raw, TOOL.BUFFER_KEYS)
        self.assertEqual(0.0, buffers["Temp Written Blocks"])
        normalized = TOOL.normalize_explain(raw)
        serialized = json.dumps(normalized)
        self.assertNotIn("Time", serialized)
        self.assertNotIn("Memory", serialized)
        self.assertNotIn("Blocks", serialized)
        self.assertNotIn("9223372036854775807", serialized)
        index_condition = normalized["Plan"]["Index Cond"]
        self.assertEqual("planner expression omitted", index_condition["redacted"])
        self.assertRegex(index_condition["sha256"], r"^[0-9a-f]{64}$")

    def test_plan_gate_accepts_found_and_missing_primary_key_scans(self) -> None:
        for expected_rows in (1, 0):
            with self.subTest(expected_rows=expected_rows):
                spec = {
                    "observation_id": "synthetic",
                    "expected_rows": expected_rows,
                }
                passed = TOOL.assert_plan(
                    spec,
                    execution(),
                    plan_summary(rows=expected_rows),
                    {"Temp Read Blocks": 0.0, "Temp Written Blocks": 0.0},
                )
                self.assertIn("questions-primary-key-index-observed", passed)
                self.assertIn("one-bigint-bind-one-select-statement", passed)

    def test_plan_gate_rejects_seq_scan_cross_owner_temp_and_extra_loop(self) -> None:
        spec = {"observation_id": "synthetic", "expected_rows": 1}
        cases: list[tuple[str, dict[str, object], dict[str, float], str]] = []

        sequential = plan_summary()
        sequential["node_type_counts"] = {"Seq Scan": 1}
        sequential["index_names"] = []
        cases.append(("sequential", sequential, {}, "questions_pkey"))

        cross_owner = plan_summary()
        cross_owner["relation_scan_occurrences"] = {
            "questions": 1,
            "users": 1,
        }
        cases.append(("cross-owner", cross_owner, {}, "relation budget"))

        repeated = plan_summary()
        repeated["maximum_actual_loops"] = 2
        cases.append(("repeated", repeated, {}, "every node once"))

        cases.append(
            (
                "temp",
                plan_summary(),
                {"Temp Written Blocks": 1.0},
                "TEMP",
            )
        )

        for name, summary, temp_blocks, message in cases:
            with self.subTest(name=name):
                with self.assertRaisesRegex(AssertionError, message):
                    TOOL.assert_plan(spec, execution(), summary, temp_blocks)


class FixtureAndInputContractTest(unittest.TestCase):

    def test_argument_validation_requires_large_fixture_and_immutable_image(self) -> None:
        args = SimpleNamespace(
            question_count=TOOL.DEFAULT_QUESTION_COUNT,
            subject_count=TOOL.DEFAULT_SUBJECT_COUNT,
            startup_timeout_seconds=120,
            image=TOOL.DEFAULT_IMAGE,
        )
        TOOL.validate_args(args)

        args.question_count = TOOL.DEFAULT_QUESTION_COUNT - 1
        with self.assertRaisesRegex(ValueError, "at least"):
            TOOL.validate_args(args)
        args.question_count = TOOL.DEFAULT_QUESTION_COUNT
        args.image = "postgres:18.4-alpine"
        with self.assertRaisesRegex(ValueError, "immutable"):
            TOOL.validate_args(args)

    def test_fixture_has_exact_question_shape_and_primary_key_only(self) -> None:
        args = SimpleNamespace(
            question_count=150_000,
            subject_count=5_000,
        )
        sql = TOOL.fixture_sql(args)
        self.assertIn("CREATE TABLE questions", sql)
        self.assertIn("PRIMARY KEY", sql)
        self.assertIn("generate_series(1, 150000)", sql)
        self.assertIn("VACUUM (ANALYZE) questions", sql)
        self.assertNotIn("CREATE TEMP", sql)
        self.assertNotIn("CREATE INDEX", sql)

    def test_input_digest_inventory_includes_tool_test_adapter_exporter_manifest(self) -> None:
        root = Path("/synthetic/Ti-Java")
        manifest = root / "server/target/phase4a-question-detail-runtime-sql.json"
        paths = TOOL.required_input_paths(root, manifest)
        self.assertEqual(
            {
                "adapter",
                "runtime_sql_manifest",
                "runtime_sql_exporter",
                "capture_tool",
                "capture_tool_test",
            },
            set(paths),
        )
        self.assertTrue(str(paths["adapter"]).endswith("JdbcQuestionDetailQueryAdapter.java"))
        self.assertTrue(
            str(paths["runtime_sql_exporter"]).endswith(
                "QuestionDetailRuntimeSqlManifestTest.java"
            )
        )


if __name__ == "__main__":
    unittest.main()
