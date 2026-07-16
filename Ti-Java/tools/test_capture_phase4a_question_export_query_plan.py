#!/usr/bin/env python3
"""Unit tests for the fail-closed question-export PG18.4 evidence bridge."""

from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


TOOL_PATH = Path(__file__).with_name(
    "capture_phase4a_question_export_query_plan.py"
)
SPEC = importlib.util.spec_from_file_location(
    "capture_phase4a_question_export_query_plan", TOOL_PATH
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot import {TOOL_PATH}")
TOOL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TOOL)


def sql_for(query_id: str) -> str:
    return TOOL.EXPECTED_NORMALIZED_SQL[query_id].upper().replace(
        ":SUBJECT_ID", ":subject_id"
    )


def runtime_manifest() -> dict[str, object]:
    return {
        "manifest_id": TOOL.MANIFEST_ID,
        "schema_version": 1,
        "adapter_class": TOOL.ADAPTER_CLASS,
        "query_count": 2,
        "queries": [
            {
                "query_id": query_id,
                "operation": TOOL.OPERATION,
                "sql": sql_for(query_id),
                "parameters": deepcopy(TOOL.EXPECTED_PARAMETER_TYPES[query_id]),
            }
            for query_id in TOOL.EXPECTED_QUERY_ORDER
        ],
    }


def write_manifest(directory: str, manifest: object) -> Path:
    path = Path(directory) / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def execution(query_id: str) -> dict[str, object]:
    parameters = TOOL.EXPECTED_PARAMETER_TYPES[query_id]
    return {
        "mode": "prepare-execute",
        "runtime_statement_count": 1,
        "bound_parameter_count": len(parameters),
        "named_parameter_count": len(parameters),
        "occurrence_names": list(parameters),
        "positional_sql_sha256": "0" * 64,
        "parameters": {
            name: {
                "bind_kind": "jdbc-scalar",
                "postgres_type": parameter_type,
                "value": 1,
            }
            for name, parameter_type in parameters.items()
        },
    }


def result_summary(rows: int = 2) -> dict[str, object]:
    return {
        "row_count": rows,
        "minimum_id": 1 if rows else None,
        "middle_id": 2 if rows else None,
        "maximum_id": rows if rows else None,
        "first_ids_asc": list(range(1, min(rows, 3) + 1)),
        "last_ids_asc": list(range(max(1, rows - 2), rows + 1)),
        "strictly_ascending_by_id": True,
        "row_column_count": 10,
        "null_subject_id_rows": 0,
        "null_subject_name_rows": 0,
        "empty_subject_name_rows": 0,
        "unicode_subject_name_rows": 0,
        "unicode_payload_rows": 0,
        "raw_malformed_payload_rows": 0,
        "edge_rows": {},
        "canonical_psql_rows_sha256": "a" * 64,
    }


def plan_summary(query_id: str, rows: int = 2) -> dict[str, object]:
    index_name = (
        "questions_pkey"
        if query_id == "question-export-all"
        else "ix_questions_subject_id"
    )
    return {
        "root_node_type": "Nested Loop",
        "result_row_count": rows,
        "root_actual_loops": 1,
        "node_count": 3,
        "maximum_depth": 1,
        "maximum_actual_loops": 1,
        "maximum_relation_scan_actual_loops": 1,
        "relation_scan_actual_loops": {"questions": [1], "subjects": [1]},
        "node_type_counts": {"Index Scan": 2, "Nested Loop": 1},
        "relation_scan_occurrences": {"questions": 1, "subjects": 1},
        "join_nodes": [
            {
                "node_type": "Nested Loop",
                "join_type": "Left",
                "actual_rows": rows,
                "actual_loops": 1,
            }
        ],
        "index_names": [index_name, "subjects_pkey"],
        "buffer_fields_observed_before_normalization": ["Shared Hit Blocks"],
        "nodes": [],
    }


def observation_spec(
    query_id: str,
    rows: int = 2,
    *,
    maximum_actual_loops: int = 1,
    subject_relation_loops: int = 1,
) -> dict[str, object]:
    return {
        "observation_id": query_id,
        "runtime_query_id": query_id,
        "expected": {"row_count": rows},
        "expected_plan_loops": {
            "maximum_actual_loops": maximum_actual_loops,
            "relation_scan_actual_loops": {
                "questions": [1],
                "subjects": [subject_relation_loops],
            },
        },
    }


class RuntimeSqlManifestTest(unittest.TestCase):

    def test_accepts_exact_two_variant_manifest_and_closes_sql_hashes(self) -> None:
        manifest = runtime_manifest()
        with tempfile.TemporaryDirectory() as temporary:
            loaded = TOOL.load_runtime_sql_manifest(
                write_manifest(temporary, manifest)
            )
        self.assertEqual(manifest, loaded)
        queries = TOOL.manifest_queries(loaded)
        self.assertEqual(set(TOOL.EXPECTED_QUERY_ORDER), set(queries))
        hashes = {
            query_id: TOOL.sha256_text(query["sql"])
            for query_id, query in queries.items()
        }
        TOOL.assert_runtime_sql_hash_closure(hashes, loaded)

    def test_rejects_unreadable_invalid_json_and_non_object_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            missing = Path(temporary) / "missing.json"
            with self.assertRaisesRegex(RuntimeError, "cannot read"):
                TOOL.load_runtime_sql_manifest(missing)
            invalid = Path(temporary) / "invalid.json"
            invalid.write_text("{", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "cannot read"):
                TOOL.load_runtime_sql_manifest(invalid)
            with self.assertRaisesRegex(RuntimeError, "root"):
                TOOL.load_runtime_sql_manifest(
                    write_manifest(temporary, ["not", "object"])
                )

    def test_rejects_manifest_identity_schema_adapter_and_count_drift(self) -> None:
        mutations = (
            ("manifest_id", "wrong.id"),
            ("schema_version", 2),
            ("adapter_class", "example.CopyAdapter"),
            ("query_count", 1),
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

    def test_rejects_query_order_duplicate_operation_and_unknown_id_drift(self) -> None:
        cases = []
        reordered = runtime_manifest()
        reordered["queries"].reverse()
        cases.append(reordered)
        duplicate = runtime_manifest()
        duplicate["queries"][1]["query_id"] = "question-export-all"
        cases.append(duplicate)
        operation = runtime_manifest()
        operation["queries"][0]["operation"] = "question-copy"
        cases.append(operation)
        unknown = runtime_manifest()
        unknown["queries"][0]["query_id"] = "question-export-copy"
        cases.append(unknown)
        for manifest in cases:
            with self.subTest(manifest=manifest):
                with tempfile.TemporaryDirectory() as temporary:
                    with self.assertRaises(RuntimeError):
                        TOOL.load_runtime_sql_manifest(
                            write_manifest(temporary, manifest)
                        )

    def test_rejects_parameter_type_reference_and_cardinality_drift(self) -> None:
        wrong_type = runtime_manifest()
        wrong_type["queries"][1]["parameters"] = {"subject_id": "bigint"}
        copied_bind = runtime_manifest()
        copied_bind["queries"][1]["sql"] = copied_bind["queries"][1][
            "sql"
        ].replace(":subject_id", ":copied_subject_id")
        extra_bind = runtime_manifest()
        extra_bind["queries"][1]["sql"] = extra_bind["queries"][1][
            "sql"
        ].replace(":subject_id", ":subject_id + :subject_id")
        for manifest in (wrong_type, copied_bind, extra_bind):
            with self.subTest(manifest=manifest):
                with tempfile.TemporaryDirectory() as temporary:
                    with self.assertRaises(RuntimeError):
                        TOOL.load_runtime_sql_manifest(
                            write_manifest(temporary, manifest)
                        )

    def test_rejects_column_join_type_extra_join_and_wildcard_drift(self) -> None:
        base = sql_for("question-export-all")
        unsafe = (
            base.replace("Q.ID, Q.SUBJECT_ID", "Q.ID"),
            base.replace("LEFT JOIN", "INNER JOIN"),
            base.replace(
                "ORDER BY Q.ID ASC",
                "LEFT JOIN USERS U ON U.ID = Q.ID ORDER BY Q.ID ASC",
            ),
            "SELECT Q.* FROM QUESTIONS Q LEFT JOIN SUBJECTS S "
            "ON Q.SUBJECT_ID = S.ID ORDER BY Q.ID ASC",
            "SELECT * FROM QUESTIONS Q LEFT JOIN SUBJECTS S "
            "ON Q.SUBJECT_ID = S.ID ORDER BY Q.ID ASC",
        )
        for candidate in unsafe:
            with self.subTest(candidate=candidate):
                with self.assertRaises(RuntimeError):
                    TOOL.validate_runtime_sql("question-export-all", candidate)

    def test_rejects_mutation_temp_limit_offset_separator_and_comment_shapes(self) -> None:
        base = sql_for("question-export-all")
        unsafe = (
            base + "; DELETE FROM questions",
            base + " LIMIT 10",
            base + " OFFSET 1",
            base + " FETCH FIRST 1 ROW ONLY",
            base.replace("FROM QUESTIONS", "FROM TEMP QUESTIONS"),
            base.replace("SELECT", "SELECT /* copy */", 1),
            base.replace("ORDER BY", "-- copied\nORDER BY"),
            base.replace("SELECT", "CREATE TABLE x AS SELECT", 1),
        )
        for candidate in unsafe:
            with self.subTest(candidate=candidate):
                with self.assertRaises(RuntimeError):
                    TOOL.validate_runtime_sql("question-export-all", candidate)

    def test_manifest_export_is_maven_test_only_and_target_confined(self) -> None:
        root = TOOL_PATH.resolve().parents[1]
        output = root / "server/target/unit-question-export-manifest.json"
        completed = subprocess.CompletedProcess([], 0, "", "")
        with patch.object(TOOL, "run", return_value=completed) as mocked:
            TOOL.export_runtime_sql_manifest(root, output)
        command = mocked.call_args.args[0]
        self.assertIn("-Dtest=QuestionExportRuntimeSqlManifestTest", command)
        self.assertIn("-DskipITs", command)
        self.assertIn("test", command)
        self.assertTrue(any("ti.question-export.sql-manifest-output" in item for item in command))
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "server/target"):
                TOOL.export_runtime_sql_manifest(root, Path(temporary) / "x.json")


class BindAndObservationTest(unittest.TestCase):

    def test_both_variants_use_fixed_zero_or_one_typed_bind(self) -> None:
        queries = TOOL.manifest_queries(runtime_manifest())
        values = {
            "question-export-all": {},
            "question-export-by-subject": {"subject_id": -1},
        }
        counts = []
        for query_id in TOOL.EXPECTED_QUERY_ORDER:
            statement, binding = TOOL.prepared_execution_sql(
                query_id,
                queries[query_id],
                values[query_id],
                explain=True,
            )
            counts.append(binding["bound_parameter_count"])
            self.assertEqual(1, binding["runtime_statement_count"])
            self.assertEqual(1, statement.count("PREPARE "))
            self.assertEqual(1, statement.count("EXPLAIN "))
            self.assertEqual(1, statement.count("EXECUTE "))
            self.assertEqual(1, statement.count("DEALLOCATE "))
            self.assertNotRegex(statement, r":[A-Za-z]")
        self.assertEqual([0, 1], counts)

    def test_integer_binding_accepts_signed_edges_and_rejects_other_values(self) -> None:
        for value in (-2_147_483_648, -1, 0, 2_147_483_647):
            with self.subTest(value=value):
                parameter = TOOL.bound_parameter("subject_id", value)
                self.assertEqual("integer", parameter["postgres_type"])
                self.assertEqual(str(value), TOOL.postgres_literal(parameter))
        for value in (-2_147_483_649, 2_147_483_648, True, "1", None):
            with self.subTest(value=value):
                with self.assertRaisesRegex(RuntimeError, "subject_id"):
                    TOOL.bound_parameter("subject_id", value)
        with self.assertRaisesRegex(RuntimeError, "unsupported"):
            TOOL.bound_parameter("question_id", 1)

    def test_prepared_execution_rejects_missing_and_extra_parameter_values(self) -> None:
        query = TOOL.manifest_queries(runtime_manifest())[
            "question-export-by-subject"
        ]
        for values in ({}, {"subject_id": 1, "other": 2}):
            with self.subTest(values=values):
                with self.assertRaisesRegex(RuntimeError, "parameter values"):
                    TOOL.prepared_execution_sql(
                        "bad", query, values, explain=False
                    )

    def test_observations_cover_all_and_eight_filtered_integer_boundaries(self) -> None:
        args = SimpleNamespace(question_count=150_000, subject_count=5_000)
        specs = TOOL.observation_specs(args)
        self.assertEqual(9, len(specs))
        by_id = {spec["observation_id"]: spec for spec in specs}
        self.assertEqual(150_000, by_id["all-questions"]["expected"]["row_count"])
        self.assertEqual([-1, 0, 1], by_id["all-questions"]["expected"]["first_ids_asc"])
        self.assertEqual(30, by_id["first-subject"]["expected"]["row_count"])
        self.assertEqual(30, by_id["middle-subject"]["expected"]["row_count"])
        self.assertEqual(29, by_id["last-subject"]["expected"]["row_count"])
        self.assertEqual(1, by_id["zero-subject"]["expected"]["row_count"])
        self.assertEqual(1, by_id["negative-subject"]["expected"]["row_count"])
        self.assertEqual(1, by_id["missing-subject-reference"]["expected"]["row_count"])
        self.assertEqual(0, by_id["integer-min-subject"]["expected"]["row_count"])
        self.assertEqual(0, by_id["integer-max-subject"]["expected"]["row_count"])
        self.assertEqual(
            {
                "maximum_actual_loops": 150_000,
                "relation_scan_actual_loops": {
                    "questions": [1],
                    "subjects": [5_004],
                },
            },
            by_id["all-questions"]["expected_plan_loops"],
        )
        self.assertEqual(
            [0],
            by_id["integer-min-subject"]["expected_plan_loops"]
            ["relation_scan_actual_loops"]["subjects"],
        )
        self.assertEqual(
            {"question-export-all", "question-export-by-subject"},
            {spec["runtime_query_id"] for spec in specs},
        )

    def test_subject_assignment_is_exact_for_signed_null_orphan_and_positive_rows(self) -> None:
        count = 5_000
        self.assertEqual(-1, TOOL.subject_for(-1, count))
        self.assertEqual(0, TOOL.subject_for(0, count))
        self.assertIsNone(TOOL.subject_for(1, count))
        self.assertEqual(6_001, TOOL.subject_for(2, count))
        self.assertEqual(1, TOOL.subject_for(3, count))
        self.assertEqual(5_000, TOOL.subject_for(5_002, count))
        self.assertEqual(1, TOOL.subject_for(5_003, count))


class FixtureAndResultTest(unittest.TestCase):

    def test_argument_validation_requires_large_fixture_and_immutable_pg_image(self) -> None:
        args = SimpleNamespace(
            question_count=TOOL.DEFAULT_QUESTION_COUNT,
            subject_count=TOOL.DEFAULT_SUBJECT_COUNT,
            startup_timeout_seconds=120,
            image=TOOL.DEFAULT_IMAGE,
        )
        TOOL.validate_args(args)
        for field, value in (
            ("question_count", 149_999),
            ("subject_count", 4_999),
            ("startup_timeout_seconds", 0),
        ):
            changed = SimpleNamespace(**vars(args))
            setattr(changed, field, value)
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    TOOL.validate_args(changed)
        args.image = "postgres:18.4-alpine"
        with self.assertRaisesRegex(ValueError, "immutable"):
            TOOL.validate_args(args)

    def test_fixture_has_150k_questions_5002_subjects_and_public_edge_payloads(self) -> None:
        args = SimpleNamespace(question_count=150_000, subject_count=5_000)
        sql = TOOL.fixture_sql(args)
        self.assertIn("generate_series(-1, 149998)", sql)
        self.assertIn("generate_series(1, 5000)", sql)
        self.assertIn("(-1, '')", sql)
        self.assertIn("(0, '科目 🧪')", sql)
        self.assertIn("WHEN n = 1 THEN NULL", sql)
        self.assertIn("WHEN n = 2 THEN 6001", sql)
        self.assertIn("公开合成汉字🙂题干", sql)
        self.assertIn("not-json:{broken]", sql)
        self.assertIn("RAW<未闭合", sql)
        self.assertIn("raw-malformed-tags:{]", sql)
        self.assertIn("CREATE INDEX ix_questions_subject_id", sql)
        self.assertIn("TEST-ONLY synthetic index", sql)
        self.assertIn("SET STATISTICS 10000", sql)
        self.assertNotIn("CREATE TEMP", sql)

    def test_dataset_metadata_gate_accepts_exact_edges_and_rejects_drift(self) -> None:
        args = SimpleNamespace(question_count=150_000, subject_count=5_000)
        metadata = {
            "questions": 150_000,
            "subjects": 5_002,
            "minimum_question_id": -1,
            "maximum_question_id": 149_998,
            "minimum_subject_id": -1,
            "maximum_subject_id": 5_000,
            "negative_subject_ids": 1,
            "zero_subject_ids": 1,
            "empty_subject_names": 1,
            "unicode_subject_names": 1,
            "null_question_subject_rows": 1,
            "orphan_question_subject_rows": 1,
            "unicode_payload_rows": 1,
            "raw_malformed_payload_rows": 1,
            "nullable_options_rows": 2,
            "nullable_answer_rows": 2,
            "nullable_analysis_rows": 2,
            "nullable_difficulty_rows": 2,
            "nullable_tags_rows": 2,
        }
        TOOL.assert_dataset_metadata(metadata, args)
        changed = deepcopy(metadata)
        changed["orphan_question_subject_rows"] = 0
        with self.assertRaisesRegex(AssertionError, "orphan"):
            TOOL.assert_dataset_metadata(changed, args)
        changed = deepcopy(metadata)
        changed["nullable_options_rows"] = 0
        with self.assertRaisesRegex(AssertionError, "nullable"):
            TOOL.assert_dataset_metadata(changed, args)

    def test_result_parser_preserves_ten_columns_signed_null_empty_unicode_and_raw(self) -> None:
        rows = (
            "-1|-1||essay|公开合成汉字🙂题干|not-json:{broken]|RAW<未闭合|"
            "分析🙂 invalid-json:[}|1|raw-malformed-tags:{]\n"
            "0|0|科目 🧪|fill|||||1|[]\n"
            f"1|{TOOL.NULL_MARKER}|{TOOL.NULL_MARKER}|single_choice|q1|"
            f"{TOOL.NULL_MARKER}|a|b|{TOOL.NULL_MARKER}|[]\n"
            f"2|6001|{TOOL.NULL_MARKER}|multi_choice|q2|[]|a|b|2|[]"
        )
        expected = {
            "row_count": 4,
            "minimum_id": -1,
            "middle_id": 1,
            "maximum_id": 2,
            "first_ids_asc": [-1, 0, 1],
            "last_ids_asc": [0, 1, 2],
        }
        parsed = TOOL.parse_result_rows(rows, expected)
        self.assertTrue(parsed["strictly_ascending_by_id"])
        self.assertEqual(10, parsed["row_column_count"])
        self.assertEqual(1, parsed["null_subject_id_rows"])
        self.assertEqual(2, parsed["null_subject_name_rows"])
        self.assertEqual(1, parsed["empty_subject_name_rows"])
        self.assertEqual(1, parsed["unicode_subject_name_rows"])
        self.assertEqual(1, parsed["raw_malformed_payload_rows"])
        self.assertTrue(parsed["edge_rows"]["-1"]["unicode_payload"])
        self.assertRegex(parsed["canonical_psql_rows_sha256"], r"^[0-9a-f]{64}$")

    def test_result_parser_accepts_empty_result_with_stable_digest(self) -> None:
        expected = {
            "row_count": 0,
            "minimum_id": None,
            "middle_id": None,
            "maximum_id": None,
            "first_ids_asc": [],
            "last_ids_asc": [],
        }
        parsed = TOOL.parse_result_rows("", expected)
        self.assertEqual(TOOL.sha256_text(""), parsed["canonical_psql_rows_sha256"])
        self.assertTrue(parsed["strictly_ascending_by_id"])

    def test_result_parser_rejects_column_id_order_and_boundary_drift(self) -> None:
        expected = {
            "row_count": 2,
            "minimum_id": 1,
            "middle_id": 2,
            "maximum_id": 2,
            "first_ids_asc": [1, 2],
            "last_ids_asc": [1, 2],
        }
        invalid_rows = (
            "1|too|few",
            "x|1|s|t|c|o|a|n|1|[]",
            "1|x|s|t|c|o|a|n|1|[]",
            "2|1|s|t|c|o|a|n|1|[]\n1|1|s|t|c|o|a|n|1|[]",
        )
        for raw in invalid_rows:
            with self.subTest(raw=raw):
                with self.assertRaises(AssertionError):
                    TOOL.parse_result_rows(raw, expected)


class PlanContractTest(unittest.TestCase):

    def test_normalization_removes_noise_and_redacts_join_sort_and_index_expressions(self) -> None:
        raw = {
            "Planning Time": 1.2,
            "Execution Time": 2.3,
            "Plan": {
                "Node Type": "Hash Join",
                "Join Type": "Left",
                "Actual Rows": 30,
                "Actual Loops": 1,
                "Actual Total Time": 0.3,
                "Plan Rows": 29,
                "Total Cost": 99.0,
                "Shared Hit Blocks": 4,
                "Temp Written Blocks": 0,
                "Peak Memory Usage": 16,
                "Hash Cond": "(q.subject_id = s.id)",
                "Sort Key": ["q.id"],
                "Plans": [
                    {
                        "Node Type": "Index Scan",
                        "Relation Name": "questions",
                        "Actual Rows": 30,
                        "Actual Loops": 1,
                        "Index Cond": "(subject_id = 6001)",
                    }
                ],
            },
        }
        buffers = TOOL.collect_numeric_fields(raw, TOOL.BUFFER_KEYS)
        normalized = TOOL.normalize_explain(raw)
        serialized = json.dumps(normalized)
        for value in ("Time", "Blocks", "Memory", "Plan Rows", "Total Cost", "6001"):
            self.assertNotIn(value, serialized)
        self.assertEqual(0.0, buffers["Temp Written Blocks"])
        self.assertRegex(normalized["Plan"]["Hash Cond"]["sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(normalized["Plan"]["Sort Key"]["sha256"], r"^[0-9a-f]{64}$")

    def test_plan_summary_records_one_join_relations_indexes_and_relation_loops(self) -> None:
        normalized = {
            "Plan": {
                "Node Type": "Nested Loop",
                "Join Type": "Left",
                "Actual Rows": 3,
                "Actual Loops": 1,
                "Plans": [
                    {
                        "Node Type": "Index Scan",
                        "Relation Name": "questions",
                        "Index Name": "ix_questions_subject_id",
                        "Actual Rows": 3,
                        "Actual Loops": 1,
                    },
                    {
                        "Node Type": "Materialize",
                        "Actual Rows": 1,
                        "Actual Loops": 3,
                        "Plans": [
                            {
                                "Node Type": "Index Scan",
                                "Relation Name": "subjects",
                                "Index Name": "subjects_pkey",
                                "Actual Rows": 1,
                                "Actual Loops": 1,
                            }
                        ],
                    },
                ],
            }
        }
        summary = TOOL.summarize_plan(normalized, {"Temp Written Blocks": 0.0})
        self.assertEqual(3, summary["maximum_actual_loops"])
        self.assertEqual(1, summary["maximum_relation_scan_actual_loops"])
        self.assertEqual({"questions": 1, "subjects": 1}, summary["relation_scan_occurrences"])
        self.assertEqual("Left", summary["join_nodes"][0]["join_type"])
        self.assertEqual(["ix_questions_subject_id", "subjects_pkey"], summary["index_names"])

    def test_plan_gate_accepts_all_and_filtered_with_bounded_helper_loops(self) -> None:
        for query_id, rows in (("question-export-all", 2), ("question-export-by-subject", 30)):
            with self.subTest(query_id=query_id):
                summary = plan_summary(query_id, rows)
                if query_id == "question-export-by-subject":
                    summary["maximum_actual_loops"] = rows
                checks = TOOL.assert_plan(
                    observation_spec(
                        query_id,
                        rows,
                        maximum_actual_loops=(
                            rows
                            if query_id == "question-export-by-subject"
                            else 1
                        ),
                    ),
                    execution(query_id),
                    result_summary(rows),
                    summary,
                    {"Temp Read Blocks": 0.0, "Temp Written Blocks": 0.0},
                )
                self.assertIn("questions-and-subjects-scanned-once-only", checks)
                self.assertIn("one-outer-join-left-right-planner-swap-allowed", checks)
                self.assertIn("one-select-fixed-typed-bind-cardinality", checks)

    def test_plan_gate_rejects_result_rows_columns_digest_order_and_plan_row_drift(self) -> None:
        query_id = "question-export-all"
        base = result_summary()
        cases = []
        wrong_count = deepcopy(base)
        wrong_count["row_count"] = 1
        cases.append((wrong_count, plan_summary(query_id), "row count"))
        wrong_columns = deepcopy(base)
        wrong_columns["row_column_count"] = 9
        cases.append((wrong_columns, plan_summary(query_id), "ten columns"))
        wrong_digest = deepcopy(base)
        wrong_digest["canonical_psql_rows_sha256"] = "missing"
        cases.append((wrong_digest, plan_summary(query_id), "digest"))
        wrong_order = deepcopy(base)
        wrong_order["strictly_ascending_by_id"] = False
        cases.append((wrong_order, plan_summary(query_id), "ordering"))
        wrong_plan = plan_summary(query_id)
        wrong_plan["result_row_count"] = 1
        cases.append((base, wrong_plan, "plan rows"))
        for result, summary, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(AssertionError, message):
                    TOOL.assert_plan(
                        observation_spec(query_id),
                        execution(query_id),
                        result,
                        summary,
                        {"Temp Read Blocks": 0.0, "Temp Written Blocks": 0.0},
                    )

    def test_plan_gate_rejects_root_relation_and_helper_loop_drift(self) -> None:
        query_id = "question-export-by-subject"
        cases = []
        root = plan_summary(query_id)
        root["root_actual_loops"] = 2
        cases.append((root, "root"))
        relation = plan_summary(query_id)
        relation["relation_scan_actual_loops"] = {
            "questions": [1],
            "subjects": [2],
        }
        cases.append((relation, "relation scan loops"))
        helper = plan_summary(query_id)
        helper["maximum_actual_loops"] = 3
        cases.append((helper, "helper-node"))
        for summary, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(AssertionError, message):
                    TOOL.assert_plan(
                        observation_spec(query_id),
                        execution(query_id),
                        result_summary(),
                        summary,
                        {"Temp Read Blocks": 0.0, "Temp Written Blocks": 0.0},
                    )

    def test_plan_gate_rejects_relation_join_temp_buffer_bind_and_index_drift(self) -> None:
        query_id = "question-export-by-subject"
        cases = []
        relation = plan_summary(query_id)
        relation["relation_scan_occurrences"] = {"questions": 1, "users": 1}
        cases.append((execution(query_id), relation, {"Temp Read Blocks": 0.0, "Temp Written Blocks": 0.0}, "relation budget"))
        join = plan_summary(query_id)
        join["join_nodes"] = []
        cases.append((execution(query_id), join, {"Temp Read Blocks": 0.0, "Temp Written Blocks": 0.0}, "outer join"))
        cases.append((execution(query_id), plan_summary(query_id), {"Temp Read Blocks": 0.0, "Temp Written Blocks": 1.0}, "TEMP"))
        no_buffers = plan_summary(query_id)
        no_buffers["buffer_fields_observed_before_normalization"] = []
        cases.append((execution(query_id), no_buffers, {"Temp Read Blocks": 0.0, "Temp Written Blocks": 0.0}, "BUFFERS"))
        binding = execution(query_id)
        binding["bound_parameter_count"] = 2
        cases.append((binding, plan_summary(query_id), {"Temp Read Blocks": 0.0, "Temp Written Blocks": 0.0}, "bind surface"))
        no_index = plan_summary(query_id)
        no_index["index_names"] = ["subjects_pkey"]
        cases.append((execution(query_id), no_index, {"Temp Read Blocks": 0.0, "Temp Written Blocks": 0.0}, "synthetic index"))
        for binding, summary, temp, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(AssertionError, message):
                    TOOL.assert_plan(
                        observation_spec(query_id),
                        binding,
                        result_summary(),
                        summary,
                        temp,
                    )


class EvidenceClosureAndCleanupTest(unittest.TestCase):

    def test_input_inventory_includes_adapter_exporter_manifest_tool_and_test(self) -> None:
        root = TOOL_PATH.resolve().parents[1]
        manifest_path = root / "server/target/phase4a-question-export-runtime-sql.json"
        paths = TOOL.required_input_paths(root, manifest_path)
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
        self.assertTrue(str(paths["adapter"]).endswith("JdbcQuestionExportQueryAdapter.java"))
        self.assertTrue(str(paths["runtime_sql_exporter"]).endswith("QuestionExportRuntimeSqlManifestTest.java"))

    def test_source_and_runtime_hash_closures_reject_post_capture_drift(self) -> None:
        manifest = runtime_manifest()
        runtime_hashes = {
            query["query_id"]: TOOL.sha256_text(query["sql"])
            for query in manifest["queries"]
        }
        TOOL.assert_runtime_sql_hash_closure(runtime_hashes, manifest)
        changed_manifest = deepcopy(manifest)
        changed_manifest["queries"][0]["sql"] += "\n"
        with self.assertRaisesRegex(AssertionError, "runtime SQL hash drifted"):
            TOOL.assert_runtime_sql_hash_closure(runtime_hashes, changed_manifest)
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "Adapter.java"
            source.write_text("final source\n", encoding="utf-8")
            recorded = {"adapter_sha256": TOOL.sha256_file(source)}
            TOOL.assert_input_hash_closure(recorded, {"adapter": source})
            source.write_text("drifted source\n", encoding="utf-8")
            with self.assertRaisesRegex(AssertionError, "source drifted"):
                TOOL.assert_input_hash_closure(recorded, {"adapter": source})

    def test_attestation_closes_canonical_payload_and_rejects_tampering(self) -> None:
        document = {"evidence_id": "public", "values": ["汉字", 1]}
        TOOL.add_attestation(document)
        TOOL.assert_attestation(document)
        self.assertRegex(
            document["attestation"]["canonical_payload_excluding_attestation_sha256"],
            r"^[0-9a-f]{64}$",
        )
        document["values"].append(2)
        with self.assertRaisesRegex(AssertionError, "hash drifted"):
            TOOL.assert_attestation(document)

    def test_public_evidence_gate_rejects_private_paths_container_ids_and_sensitive_keys(self) -> None:
        TOOL.assert_public_evidence({"safe": "public synthetic"})
        unsafe = (
            {"path": "/Users/example/project"},
            {"container": "ti-phase4a-question-export-plan-deadbeef1234"},
            {"database_password": "example"},
            {"api-key": "example"},
        )
        for document in unsafe:
            with self.subTest(document=document):
                with self.assertRaises(AssertionError):
                    TOOL.assert_public_evidence(document)

    def test_environment_gate_requires_exact_pg184_and_deterministic_settings(self) -> None:
        metadata = {
            "server_version_num": "180004",
            "work_mem": "64MB",
            "max_parallel_workers_per_gather": "0",
        }
        TOOL.assert_environment_metadata(metadata)
        for key, value in (
            ("server_version_num", "180003"),
            ("work_mem", "4MB"),
            ("max_parallel_workers_per_gather", "2"),
        ):
            changed = deepcopy(metadata)
            changed[key] = value
            with self.subTest(key=key):
                with self.assertRaises(AssertionError):
                    TOOL.assert_environment_metadata(changed)

    def test_image_metadata_requires_resolved_expected_digest(self) -> None:
        expected = TOOL.DEFAULT_IMAGE.split("@", 1)[1]
        payload = json.dumps(
            [
                {
                    "Id": expected,
                    "RepoDigests": [f"postgres@{expected}"],
                    "Os": "linux",
                    "Architecture": "arm64",
                }
            ]
        )
        completed = subprocess.CompletedProcess([], 0, payload, "")
        with patch.object(TOOL, "run", return_value=completed):
            metadata = TOOL.image_metadata(TOOL.DEFAULT_IMAGE)
        self.assertEqual(expected, metadata["expected_digest"])
        changed = subprocess.CompletedProcess(
            [],
            0,
            json.dumps([{"Id": "x", "RepoDigests": []}]),
            "",
        )
        with patch.object(TOOL, "run", return_value=changed):
            with self.assertRaisesRegex(AssertionError, "expected digest"):
                TOOL.image_metadata(TOOL.DEFAULT_IMAGE)

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

    def test_cleanup_removes_container_and_fails_if_inspect_still_finds_it(self) -> None:
        removed = subprocess.CompletedProcess([], 0, "", "")
        absent = subprocess.CompletedProcess([], 1, "", "not found")
        with patch.object(TOOL, "run", side_effect=[removed, absent]) as mocked:
            TOOL.cleanup_container("synthetic-container")
        self.assertEqual(
            ["docker", "rm", "--force", "synthetic-container"],
            mocked.call_args_list[0].args[0],
        )
        with patch.object(TOOL, "run", side_effect=[removed, removed]):
            with self.assertRaisesRegex(RuntimeError, "was not removed"):
                TOOL.cleanup_container("leaked-container")


if __name__ == "__main__":
    unittest.main()
