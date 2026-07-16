#!/usr/bin/env python3
"""Unit checks for the subject-context runtime SQL plan evidence bridge."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest


TOOL_PATH = Path(__file__).with_name(
    "capture_phase4a_subject_context_query_plan.py"
)
SPEC = importlib.util.spec_from_file_location(
    "phase4a_subject_context_plan", TOOL_PATH
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load query-plan capture tool: {TOOL_PATH}")
TOOL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TOOL)


RUNTIME_SQL = """SELECT s.id AS subject_id,
       s.name AS subject_name
FROM subjects s
WHERE s.id = :subject_id"""


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
        "relation_scan_occurrences": {"subjects": 1},
        "index_names": ["subjects_pkey"],
        "buffer_fields_observed_before_normalization": ["Shared Hit Blocks"],
        "nodes": [],
    }


def execution(subject_id: int = 1) -> dict[str, object]:
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
                "value": subject_id,
            }
        },
    }


class RuntimeSqlManifestTest(unittest.TestCase):

    def test_accepts_only_exact_manifest_sql_and_bigint_parameter_shapes(self) -> None:
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

    def test_rejects_manifest_identity_adapter_query_operation_and_type_drift(self) -> None:
        for key, value in (
            ("manifest_id", "example.wrong"),
            ("schema_version", 2),
            ("adapter_class", "example.CopySubjectAdapter"),
            ("query_count", 2),
        ):
            with self.subTest(key=key):
                manifest = runtime_manifest()
                manifest[key] = value
                with tempfile.TemporaryDirectory() as temporary:
                    with self.assertRaises(RuntimeError):
                        TOOL.load_runtime_sql_manifest(
                            write_manifest_text(temporary, manifest)
                        )

        for key, value in (
            ("query_id", "subject-context-copy"),
            ("operation", "subject-copy"),
            (
                "parameters",
                {TOOL.PARAMETER_NAME: {"jdbc_type": "integer", "value": 1}},
            ),
        ):
            with self.subTest(query_key=key):
                manifest = runtime_manifest()
                manifest["queries"][0][key] = value
                with tempfile.TemporaryDirectory() as temporary:
                    with self.assertRaises(RuntimeError):
                        TOOL.load_runtime_sql_manifest(
                            write_manifest_text(temporary, manifest)
                        )

    def test_rejects_projection_relation_predicate_join_bind_and_mutation_drift(self) -> None:
        unsafe = (
            RUNTIME_SQL.replace(
                "s.id AS subject_id,\n       s.name AS subject_name",
                "s.name AS subject_name,\n       s.id AS subject_id",
            ),
            RUNTIME_SQL.replace("s.name AS subject_name", "s.description AS subject_name"),
            RUNTIME_SQL.replace("subjects s", "questions s"),
            RUNTIME_SQL.replace("s.id = :subject_id", "s.name = :subject_id"),
            RUNTIME_SQL + " AND s.is_locked = false",
            RUNTIME_SQL + " JOIN users u ON u.id = s.id",
            RUNTIME_SQL + " AND s.id = :copy_id",
            RUNTIME_SQL + "; DELETE FROM subjects",
            "SELECT * FROM subjects s WHERE s.id = :subject_id",
            "CREATE TEMP TABLE selected_subjects(id bigint)",
        )
        for sql in unsafe:
            with self.subTest(sql=sql):
                with self.assertRaises(RuntimeError):
                    TOOL.validate_runtime_sql("unsafe", sql)


class BindSurfaceTest(unittest.TestCase):

    def test_all_five_ids_remain_one_bigint_bind_and_one_statement(self) -> None:
        specs = TOOL.observation_specs()
        self.assertEqual(
            [
                1,
                75_000,
                150_000,
                150_001,
                TOOL.LONG_MAX_VALUE,
            ],
            [spec["subject_id"] for spec in specs],
        )
        self.assertEqual(
            [1, 1, 1, 0, 0],
            [spec["expected_rows"] for spec in specs],
        )

        positional_hashes: set[str] = set()
        for spec in specs:
            statement, binding = TOOL.prepared_execution_sql(
                spec["observation_id"], RUNTIME_SQL, spec["subject_id"]
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
            self.assertNotIn(":subject_id", statement)
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
                "Relation Name": "subjects",
                "Alias": "s",
                "Index Name": "subjects_pkey",
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
                self.assertIn("subjects-primary-key-index-observed", passed)
                self.assertIn("one-bigint-bind-one-select-statement", passed)
                self.assertIn("selective-index-scan-without-join", passed)

    def test_plan_gate_rejects_row_overflow_seq_join_relation_loop_temp_and_bind(self) -> None:
        spec = {"observation_id": "synthetic", "expected_rows": 1}
        cases: list[
            tuple[
                str,
                dict[str, object],
                dict[str, object],
                dict[str, float],
                str,
            ]
        ] = []

        overflow = plan_summary(rows=2)
        cases.append(("rows", overflow, execution(), {}, "returned"))

        sequential = plan_summary()
        sequential["node_type_counts"] = {"Seq Scan": 1}
        sequential["index_names"] = []
        cases.append(("sequential", sequential, execution(), {}, "subjects_pkey"))

        joined = plan_summary()
        joined["node_type_counts"] = {"Hash Join": 1, "Index Scan": 1}
        cases.append(("join", joined, execution(), {}, "join"))

        relation = plan_summary()
        relation["relation_scan_occurrences"] = {"subjects": 1, "users": 1}
        cases.append(("relation", relation, execution(), {}, "relation budget"))

        repeated = plan_summary()
        repeated["maximum_actual_loops"] = 2
        cases.append(("loops", repeated, execution(), {}, "every node once"))

        cases.append(
            (
                "temp",
                plan_summary(),
                execution(),
                {"Temp Written Blocks": 1.0},
                "TEMP",
            )
        )

        wrong_bind = execution()
        wrong_bind["bound_parameter_count"] = 2
        cases.append(("bind", plan_summary(), wrong_bind, {}, "fixed at one"))

        for name, summary, binding, temp_blocks, message in cases:
            with self.subTest(name=name):
                with self.assertRaisesRegex(AssertionError, message):
                    TOOL.assert_plan(spec, binding, summary, temp_blocks)


class FixtureAndInputContractTest(unittest.TestCase):

    def test_argument_validation_requires_immutable_image(self) -> None:
        args = SimpleNamespace(
            startup_timeout_seconds=120,
            image=TOOL.DEFAULT_IMAGE,
        )
        TOOL.validate_args(args)
        args.startup_timeout_seconds = 0
        with self.assertRaisesRegex(ValueError, "positive"):
            TOOL.validate_args(args)
        args.startup_timeout_seconds = 120
        args.image = "postgres:18.4-alpine"
        with self.assertRaisesRegex(ValueError, "immutable"):
            TOOL.validate_args(args)

    def test_fixture_has_exact_fixed_subject_shape_and_primary_key_only(self) -> None:
        sql = TOOL.fixture_sql()
        for fragment in (
            "CREATE TABLE subjects",
            "PRIMARY KEY",
            "generate_series(1, 150000)",
            "VACUUM (ANALYZE) subjects",
        ):
            self.assertIn(fragment, sql)
        self.assertNotIn("CREATE TEMP", sql)
        self.assertNotIn("CREATE INDEX", sql)
        self.assertNotIn("questions", sql)
        self.assertNotIn("users", sql)

    def test_input_digest_inventory_includes_tool_test_adapter_exporter_manifest(self) -> None:
        root = Path("/synthetic/Ti-Java")
        manifest = root / "server/target/phase4a-subject-context-runtime-sql.json"
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
        self.assertTrue(
            str(paths["adapter"]).endswith("JdbcSubjectContextQueryAdapter.java")
        )
        self.assertTrue(
            str(paths["runtime_sql_exporter"]).endswith(
                "SubjectContextRuntimeSqlManifestTest.java"
            )
        )

    def test_dataset_expected_shape_is_exactly_150000_subjects(self) -> None:
        expected = {
            "subjects": TOOL.DEFAULT_SUBJECT_COUNT,
            "minimum_subject_id": 1,
            "maximum_subject_id": TOOL.DEFAULT_SUBJECT_COUNT,
            "contiguous_positive_subjects": TOOL.DEFAULT_SUBJECT_COUNT,
        }
        self.assertEqual(150_000, expected["subjects"])
        self.assertEqual(150_000, expected["maximum_subject_id"])


if __name__ == "__main__":
    unittest.main()
