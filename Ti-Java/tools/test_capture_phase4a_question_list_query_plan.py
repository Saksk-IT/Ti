#!/usr/bin/env python3
"""Unit checks for the question-list runtime SQL plan evidence bridge."""

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
    "capture_phase4a_question_list_query_plan.py"
)
SPEC = importlib.util.spec_from_file_location(
    "phase4a_question_list_plan", TOOL_PATH
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load query-plan capture tool: {TOOL_PATH}")
TOOL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TOOL)


def sql_for(query_id: str) -> str:
    return TOOL.EXPECTED_NORMALIZED_SQL[query_id].upper().replace(
        ":SUBJECT_ID", ":subject_id"
    ).replace(":QUESTION_TYPE", ":question_type")


def runtime_manifest() -> dict[str, object]:
    return {
        "manifest_id": TOOL.MANIFEST_ID,
        "schema_version": 1,
        "adapter_class": TOOL.ADAPTER_CLASS,
        "query_count": 4,
        "queries": [
            {
                "query_id": query_id,
                "operation": TOOL.OPERATION,
                "sql": sql_for(query_id),
                "parameters": TOOL.EXPECTED_PARAMETER_TYPES[query_id],
            }
            for query_id in TOOL.EXPECTED_QUERY_ORDER
        ],
    }


def write_manifest(directory: str, manifest: dict[str, object]) -> Path:
    path = Path(directory) / "runtime-sql.json"
    path.write_text(
        json.dumps(manifest, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return path


def execution(query_id: str) -> dict[str, object]:
    names = list(TOOL.EXPECTED_PARAMETER_TYPES[query_id])
    parameters: dict[str, object] = {}
    for name in names:
        value = 1 if name == "subject_id" else "single_choice"
        parameters[name] = TOOL.bound_parameter(name, value)
    return {
        "mode": "prepare-execute",
        "bound_parameter_count": len(names),
        "named_parameter_count": len(names),
        "occurrence_names": names,
        "positional_sql_sha256": "0" * 64,
        "parameters": parameters,
    }


def result_summary(rows: int = 2) -> dict[str, object]:
    return {
        "row_count": rows,
        "minimum_id": 1 if rows else None,
        "maximum_id": rows if rows else None,
        "first_ids_desc": list(range(rows, max(0, rows - 3), -1)),
        "last_ids_desc": list(range(min(rows, 3), 0, -1)),
        "strictly_descending_by_id": True,
        "row_column_count": 9,
        "canonical_psql_rows_sha256": "a" * 64,
    }


def plan_summary(rows: int = 2) -> dict[str, object]:
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


class RuntimeSqlManifestTest(unittest.TestCase):

    def test_accepts_exact_four_variant_manifest_and_closes_sql_hashes(self) -> None:
        manifest = runtime_manifest()
        with tempfile.TemporaryDirectory() as temporary:
            path = write_manifest(temporary, manifest)
            loaded = TOOL.load_runtime_sql_manifest(path)
        self.assertEqual(manifest, loaded)
        queries = TOOL.manifest_queries(loaded)
        self.assertEqual(set(TOOL.EXPECTED_QUERY_ORDER), set(queries))
        for query_id, query in queries.items():
            TOOL.validate_runtime_sql(query_id, query["sql"])
            digest = TOOL.sha256_text(query["sql"])
            self.assertRegex(digest, r"^[0-9a-f]{64}$")
            self.assertEqual(digest, TOOL.sha256_text(query["sql"]))

    def test_rejects_manifest_identity_count_order_operation_and_query_drift(self) -> None:
        mutations = (
            ("manifest_id", "example.wrong"),
            ("schema_version", 2),
            ("adapter_class", "example.CopyAdapter"),
            ("query_count", 3),
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

        cases = []
        reordered = runtime_manifest()
        reordered["queries"][0], reordered["queries"][1] = (
            reordered["queries"][1],
            reordered["queries"][0],
        )
        cases.append(reordered)
        operation = runtime_manifest()
        operation["queries"][0]["operation"] = "question-copy"
        cases.append(operation)
        duplicate = runtime_manifest()
        duplicate["queries"][1]["query_id"] = duplicate["queries"][0]["query_id"]
        cases.append(duplicate)
        for manifest in cases:
            with tempfile.TemporaryDirectory() as temporary:
                with self.assertRaises(RuntimeError):
                    TOOL.load_runtime_sql_manifest(
                        write_manifest(temporary, manifest)
                    )

    def test_rejects_parameter_type_and_reference_drift(self) -> None:
        manifest = runtime_manifest()
        manifest["queries"][1]["parameters"] = {"subject_id": "bigint"}
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(RuntimeError, "parameter types"):
                TOOL.load_runtime_sql_manifest(write_manifest(temporary, manifest))

        manifest = runtime_manifest()
        manifest["queries"][2]["sql"] = manifest["queries"][2]["sql"].replace(
            ":question_type", ":copied_type"
        )
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(RuntimeError):
                TOOL.load_runtime_sql_manifest(write_manifest(temporary, manifest))

    def test_rejects_column_join_filter_order_statement_and_wildcard_drift(self) -> None:
        base = sql_for("question-summaries-all")
        unsafe = (
            base.replace("Q.ID, Q.SUBJECT_ID", "Q.ID"),
            base.replace(
                "FROM QUESTIONS Q",
                "FROM QUESTIONS Q JOIN USERS U ON U.ID = Q.CREATED_BY",
            ),
            base.replace("ORDER BY Q.ID DESC", "ORDER BY Q.ID ASC"),
            base + "; DELETE FROM questions",
            "SELECT * FROM questions q ORDER BY q.id DESC",
        )
        for candidate in unsafe:
            with self.subTest(candidate=candidate):
                with self.assertRaises(RuntimeError):
                    TOOL.validate_runtime_sql("question-summaries-all", candidate)


class BindAndObservationTest(unittest.TestCase):

    def test_all_variants_use_fixed_zero_one_one_two_typed_bind_counts(self) -> None:
        manifest = runtime_manifest()
        queries = TOOL.manifest_queries(manifest)
        values = {
            "question-summaries-all": {},
            "question-summaries-by-subject": {"subject_id": 1},
            "question-summaries-by-type": {"question_type": "single_choice"},
            "question-summaries-by-subject-and-type": {
                "subject_id": 1,
                "question_type": "single_choice",
            },
        }
        actual_counts = []
        for query_id in TOOL.EXPECTED_QUERY_ORDER:
            statement, binding = TOOL.prepared_execution_sql(
                query_id,
                queries[query_id],
                values[query_id],
                explain=True,
            )
            actual_counts.append(binding["bound_parameter_count"])
            self.assertEqual(
                len(TOOL.EXPECTED_PARAMETER_TYPES[query_id]),
                binding["named_parameter_count"],
            )
            self.assertEqual(1, statement.count("PREPARE "))
            self.assertEqual(1, statement.count("EXPLAIN "))
            self.assertEqual(1, statement.count("EXECUTE "))
            self.assertEqual(1, statement.count("DEALLOCATE "))
            self.assertNotRegex(statement, r":[A-Za-z]")
        self.assertEqual([0, 1, 1, 2], actual_counts)

    def test_invalid_parameter_values_fail_closed_and_text_is_quoted(self) -> None:
        for value in (-2_147_483_649, 2_147_483_648, True, "1"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(RuntimeError, "subject_id"):
                    TOOL.bound_parameter("subject_id", value)
        self.assertEqual(
            -2_147_483_648,
            TOOL.bound_parameter("subject_id", -2_147_483_648)["value"],
        )
        self.assertEqual(
            2_147_483_647,
            TOOL.bound_parameter("subject_id", 2_147_483_647)["value"],
        )
        self.assertEqual("", TOOL.bound_parameter("question_type", "")["value"])
        self.assertEqual(
            "x" * 1024,
            TOOL.bound_parameter("question_type", "x" * 1024)["value"],
        )
        for value in (1, None):
            with self.subTest(value=value):
                with self.assertRaisesRegex(RuntimeError, "question_type"):
                    TOOL.bound_parameter("question_type", value)
        parameter = TOOL.bound_parameter("question_type", "single'choice")
        self.assertEqual("'single''choice'", TOOL.postgres_literal(parameter))

    def test_observations_cover_all_existing_missing_and_combined_boundaries(self) -> None:
        args = SimpleNamespace(
            question_count=TOOL.DEFAULT_QUESTION_COUNT,
            subject_count=TOOL.DEFAULT_SUBJECT_COUNT,
        )
        specs = TOOL.observation_specs(args)
        self.assertEqual(9, len(specs))
        self.assertEqual(set(TOOL.EXPECTED_QUERY_ORDER), {
            spec["runtime_query_id"] for spec in specs
        })
        by_id = {spec["observation_id"]: spec for spec in specs}
        self.assertEqual(150_000, by_id["all-questions"]["expected"]["row_count"])
        self.assertEqual(-1, by_id["all-questions"]["expected"]["minimum_id"])
        self.assertEqual(149_998, by_id["all-questions"]["expected"]["maximum_id"])
        self.assertEqual(30_000, by_id["common-question-type"]["expected"]["row_count"])
        self.assertEqual(0, by_id["unknown-question-type"]["expected"]["row_count"])
        self.assertEqual(0, by_id["empty-question-type"]["expected"]["row_count"])
        self.assertEqual(0, by_id["missing-subject"]["expected"]["row_count"])
        self.assertEqual(0, by_id["negative-subject"]["expected"]["row_count"])
        self.assertEqual(30_000, sum(
            1
            for question_id in range(-1, 149_999)
            if TOOL.question_type_for(question_id) == "essay"
        ))
        for question_type in TOOL.QUESTION_TYPES:
            self.assertEqual(30_000, sum(
                1
                for question_id in range(-1, 149_999)
                if TOOL.question_type_for(question_id) == question_type
            ))


class ResultAndPlanContractTest(unittest.TestCase):

    def test_result_parser_closes_count_boundaries_columns_digest_and_order(self) -> None:
        rows = (
            "3|1|single_choice|q3|1|[]||7|2026-01-01 00:00:03\n"
            "1|1|single_choice|q1|1|[]||7|2026-01-01 00:00:01\n"
            "-1|1|essay|q-1|1|[]|||2026-01-01 00:00:00"
        )
        expected = {
            "row_count": 3,
            "minimum_id": -1,
            "maximum_id": 3,
            "first_ids_desc": [3, 1, -1],
            "last_ids_desc": [3, 1, -1],
        }
        parsed = TOOL.parse_result_rows(rows, expected)
        self.assertTrue(parsed["strictly_descending_by_id"])
        self.assertEqual(9, parsed["row_column_count"])
        self.assertRegex(parsed["canonical_psql_rows_sha256"], r"^[0-9a-f]{64}$")

    def test_result_parser_rejects_bad_column_count_order_and_boundary(self) -> None:
        expected = {
            "row_count": 2,
            "minimum_id": 1,
            "maximum_id": 2,
            "first_ids_desc": [2, 1],
            "last_ids_desc": [2, 1],
        }
        with self.assertRaisesRegex(AssertionError, "column count"):
            TOOL.parse_result_rows("2|too|few", expected)
        with self.assertRaisesRegex(AssertionError, "boundary|ordered"):
            TOOL.parse_result_rows(
                "1|a|b|c|d|e|f|g|h\n2|a|b|c|d|e|f|g|h",
                expected,
            )

    def test_normalization_removes_noise_and_redacts_plan_expressions(self) -> None:
        raw = {
            "Planning Time": 1.2,
            "Execution Time": 2.3,
            "Plan": {
                "Node Type": "Index Scan",
                "Relation Name": "questions",
                "Index Name": "ix_questions_subject_id",
                "Actual Rows": 30,
                "Actual Loops": 1,
                "Actual Total Time": 0.3,
                "Plan Rows": 29,
                "Total Cost": 99.0,
                "Shared Hit Blocks": 4,
                "Temp Written Blocks": 0,
                "Peak Memory Usage": 16,
                "Index Cond": "(subject_id = 6001)",
            },
        }
        buffers = TOOL.collect_numeric_fields(raw, TOOL.BUFFER_KEYS)
        normalized = TOOL.normalize_explain(raw)
        serialized = json.dumps(normalized)
        for value in ("Time", "Blocks", "Memory", "Plan Rows", "Total Cost", "6001"):
            self.assertNotIn(value, serialized)
        self.assertEqual(0.0, buffers["Temp Written Blocks"])
        expression = normalized["Plan"]["Index Cond"]
        self.assertEqual("planner expression omitted", expression["redacted"])
        self.assertRegex(expression["sha256"], r"^[0-9a-f]{64}$")

    def test_plan_gate_accepts_each_fixed_bind_surface(self) -> None:
        for query_id, parameter_types in TOOL.EXPECTED_PARAMETER_TYPES.items():
            with self.subTest(query_id=query_id):
                spec = {
                    "observation_id": query_id,
                    "runtime_query_id": query_id,
                    "expected": {"row_count": 2},
                }
                checks = TOOL.assert_plan(
                    spec,
                    execution(query_id),
                    result_summary(),
                    plan_summary(),
                    {"Temp Read Blocks": 0.0, "Temp Written Blocks": 0.0},
                )
                self.assertIn("questions-once-users-subjects-zero", checks)
                self.assertIn("strict-id-desc-runtime-order", checks)
                self.assertEqual(
                    len(parameter_types), execution(query_id)["bound_parameter_count"]
                )

    def test_plan_gate_rejects_tampered_rows_order_relations_loops_temp_and_bind(self) -> None:
        query_id = "question-summaries-by-subject"
        spec = {
            "observation_id": "tampered",
            "runtime_query_id": query_id,
            "expected": {"row_count": 2},
        }
        cases = []
        wrong_rows = plan_summary(rows=1)
        cases.append((execution(query_id), result_summary(), wrong_rows, {}, "plan rows"))
        bad_order = result_summary()
        bad_order["strictly_descending_by_id"] = False
        cases.append((execution(query_id), bad_order, plan_summary(), {}, "ordering"))
        users = plan_summary()
        users["relation_scan_occurrences"] = {"questions": 1, "users": 1}
        cases.append((execution(query_id), result_summary(), users, {}, "relation budget"))
        subjects = plan_summary()
        subjects["relation_scan_occurrences"] = {"questions": 1, "subjects": 1}
        cases.append((execution(query_id), result_summary(), subjects, {}, "relation budget"))
        loops = plan_summary()
        loops["maximum_actual_loops"] = 2
        cases.append((execution(query_id), result_summary(), loops, {}, "every node once"))
        cases.append((
            execution(query_id),
            result_summary(),
            plan_summary(),
            {"Temp Written Blocks": 1.0},
            "TEMP",
        ))
        binds = execution(query_id)
        binds["bound_parameter_count"] = 2
        cases.append((binds, result_summary(), plan_summary(), {}, "bind surface"))
        for current_execution, result, summary, temp, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(AssertionError, message):
                    TOOL.assert_plan(spec, current_execution, result, summary, temp)


class FixtureEvidenceAndCleanupTest(unittest.TestCase):

    def test_argument_validation_requires_large_fixture_and_immutable_image(self) -> None:
        args = SimpleNamespace(
            question_count=TOOL.DEFAULT_QUESTION_COUNT,
            subject_count=TOOL.DEFAULT_SUBJECT_COUNT,
            startup_timeout_seconds=120,
            image=TOOL.DEFAULT_IMAGE,
        )
        TOOL.validate_args(args)
        args.question_count -= 1
        with self.assertRaisesRegex(ValueError, "at least"):
            TOOL.validate_args(args)
        args.question_count = TOOL.DEFAULT_QUESTION_COUNT
        args.image = "postgres:18.4-alpine"
        with self.assertRaisesRegex(ValueError, "immutable"):
            TOOL.validate_args(args)

    def test_fixture_has_150k_questions_5k_subjects_uniform_types_sparse_raws_and_test_indexes(self) -> None:
        args = SimpleNamespace(question_count=150_000, subject_count=5_000)
        sql = TOOL.fixture_sql(args)
        self.assertIn("CREATE TABLE subjects", sql)
        self.assertIn("CREATE TABLE questions", sql)
        self.assertIn("generate_series(-1, 149998)", sql)
        self.assertIn("generate_series(1, 5000)", sql)
        for question_type in TOOL.QUESTION_TYPES:
            self.assertIn(question_type, sql)
        self.assertIn("raw-synthetic-tag", sql)
        self.assertIn("THEN NULL", sql)
        self.assertIn("CREATE INDEX ix_questions_subject_id", sql)
        self.assertIn("CREATE INDEX ix_questions_subject_type", sql)
        self.assertIn("TEST-ONLY synthetic indexes", sql)
        self.assertIn("ALTER COLUMN subject_id SET STATISTICS 10000", sql)
        self.assertIn("ALTER COLUMN type SET STATISTICS 10000", sql)
        self.assertNotIn("CREATE TEMP", sql)

    def test_input_inventory_and_content_hashes_close_without_private_values(self) -> None:
        root = TOOL_PATH.resolve().parents[1]
        manifest_path = root / "server/target/phase4a-question-list-runtime-sql.json"
        paths = TOOL.required_input_paths(root, manifest_path)
        self.assertEqual({
            "adapter",
            "runtime_sql_manifest",
            "runtime_sql_exporter",
            "capture_tool",
            "capture_tool_test",
        }, set(paths))
        self.assertTrue(str(paths["adapter"]).endswith(
            "JdbcQuestionSummaryQueryAdapter.java"
        ))
        self.assertTrue(str(paths["runtime_sql_exporter"]).endswith(
            "QuestionListRuntimeSqlManifestTest.java"
        ))
        with tempfile.TemporaryDirectory() as temporary:
            sample = Path(temporary) / "sample"
            sample.write_text("public deterministic\n", encoding="utf-8")
            self.assertEqual(
                TOOL.sha256_text("public deterministic\n"),
                TOOL.sha256_file(sample),
            )

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
            paths = {"adapter": source}
            recorded = {"adapter_sha256": TOOL.sha256_file(source)}
            TOOL.assert_input_hash_closure(recorded, paths)
            source.write_text("drifted source\n", encoding="utf-8")
            with self.assertRaisesRegex(AssertionError, "source drifted"):
                TOOL.assert_input_hash_closure(recorded, paths)

    def test_public_evidence_gate_rejects_private_paths_container_ids_and_sensitive_keys(self) -> None:
        TOOL.assert_public_evidence({"safe": "public synthetic"})
        unsafe = (
            {"path": "/Users/example/project"},
            {"container": "ti-phase4a-question-list-plan-deadbeef"},
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
