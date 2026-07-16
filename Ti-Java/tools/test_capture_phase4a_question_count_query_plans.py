#!/usr/bin/env python3
"""Unit tests for the question-count runtime SQL plan bridge."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest


TOOL_PATH = Path(__file__).with_name(
    "capture_phase4a_question_count_query_plans.py"
)
SPEC = importlib.util.spec_from_file_location("phase4a_question_count_plans", TOOL_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load query-plan tool: {TOOL_PATH}")
TOOL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TOOL)


def array_manifest(
    postgres_type: str, start: int, end: int, step: int
) -> dict[str, object]:
    values = list(range(start, end + 1, step))
    return {
        "bind_kind": "jdbc-sql-array",
        "postgres_type": postgres_type,
        "element_type": postgres_type.removesuffix("[]"),
        "element_count": len(values),
        "canonical_encoding": "utf8-decimal-lines-with-final-newline",
        "sha256": TOOL.decimal_lines_sha256(values),
        "first": values[0],
        "last": values[-1],
        "min": min(values),
        "max": max(values),
        "value_generator": {
            "kind": "inclusive-integer-range",
            "start": start,
            "end": end,
            "step": step,
        },
    }


def runtime_manifest() -> dict[str, object]:
    base = (
        "SELECT COUNT(1) FROM questions q LEFT JOIN subjects s "
        "ON s.id=q.subject_id WHERE "
        "(s.is_locked=false OR s.is_locked IS NULL)"
    )
    queries = [
        {
            "query_id": "question-count-anonymous-all",
            "operation": "question-count",
            "sql": base,
            "parameters": {},
        },
        {
            "query_id": "question-count-auth-unrestricted",
            "operation": "question-count",
            "sql": base + " AND s.id IS NOT NULL",
            "parameters": {},
        },
        {
            "query_id": "question-count-auth-restricted",
            "operation": "question-count",
            "sql": base + (
                " AND s.id IS NOT NULL AND s.id <> ALL("
                "CAST(:excluded_subject_ids AS integer[]))"
            ),
            "parameters": {
                "excluded_subject_ids": array_manifest("integer[]", 2, 4, 2)
            },
        },
        {
            "query_id": "question-count-subject-type",
            "operation": "question-count",
            "sql": base + (
                " AND s.id IS NOT NULL AND s.name=:subject_name "
                "AND q.type=:question_type"
            ),
            "parameters": {
                "subject_name": "数学",
                "question_type": "single_choice",
            },
        },
        {
            "query_id": "question-count-candidate-large",
            "operation": "question-count",
            "sql": base + (
                " AND q.id=ANY(CAST(:candidate_question_ids AS bigint[]))"
            ),
            "parameters": {
                "candidate_question_ids": array_manifest(
                    "bigint[]", 1, 100_000, 1
                )
            },
        },
    ]
    return {
        "manifest_id": TOOL.MANIFEST_ID,
        "schema_version": 1,
        "adapter_class": TOOL.ADAPTER_CLASS,
        "query_count": len(queries),
        "queries": queries,
    }


class RuntimeSqlSafetyTest(unittest.TestCase):

    def test_accepts_one_read_only_select_and_rejects_mutation_or_temp(self) -> None:
        TOOL.validate_runtime_sql("safe", "SELECT COUNT(1) FROM questions")

        for sql in (
            "UPDATE questions SET type = 'essay'",
            "SELECT 1; SELECT 2",
            "CREATE TEMP TABLE selected_ids(id bigint)",
            "SELECT * FROM pg_temp.selected_ids",
        ):
            with self.subTest(sql=sql):
                with self.assertRaises(RuntimeError):
                    TOOL.validate_runtime_sql("unsafe", sql)


class RuntimeManifestDryRunTest(unittest.TestCase):

    def test_load_specs_and_bind_all_five_exact_runtime_variants(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "runtime-sql.json"
            path.write_text(
                json.dumps(runtime_manifest(), ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            manifest = TOOL.load_runtime_sql_manifest(path)

        args = SimpleNamespace(
            subject_count=5_000,
            baseline_question_count=50_000,
            large_question_count=150_000,
            large_candidate_count=65_536,
        )
        baseline = TOOL.query_specs(manifest, args, large=False)
        large = TOOL.query_specs(manifest, args, large=True)

        self.assertEqual(
            {spec["runtime_query"]["query_id"] for spec in baseline},
            TOOL.EXPECTED_QUERY_IDS,
        )
        candidate_counts: set[int] = set()
        for spec in baseline + large:
            query = spec["runtime_query"]
            bound = TOOL.bind_parameters(query, spec["parameters"])
            _, execution = TOOL.prepared_execution_sql(
                spec["observation_id"], query["sql"], bound, explain=True
            )
            query_id = query["query_id"]
            self.assertEqual(
                execution["bound_parameter_count"],
                len(TOOL.EXPECTED_PARAMETER_NAMES[query_id]),
            )
            if query_id == "question-count-candidate-large":
                candidate_counts.add(
                    execution["parameters"]["candidate_question_ids"][
                        "element_count"
                    ]
                )

        self.assertEqual(candidate_counts, {65_536, 100_000})

    def test_manifest_array_digest_mismatch_fails_closed(self) -> None:
        manifest = runtime_manifest()
        queries = manifest["queries"]
        self.assertIsInstance(queries, list)
        candidate = queries[-1]["parameters"]["candidate_question_ids"]
        candidate["sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "runtime-sql.json"
            path.write_text(json.dumps(manifest) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "sha256 drifted"):
                TOOL.load_runtime_sql_manifest(path)

    def test_manifest_adapter_class_mismatch_fails_closed(self) -> None:
        manifest = runtime_manifest()
        manifest["adapter_class"] = "example.CopyOfQuestionCountAdapter"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "runtime-sql.json"
            path.write_text(json.dumps(manifest) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "adapter class drifted"):
                TOOL.load_runtime_sql_manifest(path)


class ArrayBindingTest(unittest.TestCase):

    @staticmethod
    def parameters(candidate_ids: list[int]) -> dict[str, dict[str, object]]:
        return {
            "subject_name": {
                "jdbc_type": "text",
                "postgres_type": "text",
                "value": "Subject 00002",
            },
            "question_type": {
                "jdbc_type": "text",
                "postgres_type": "text",
                "value": "boolean",
            },
            "excluded_subject_ids": {
                "jdbc_type": "array",
                "postgres_type": "integer[]",
                "value": [20],
            },
            "candidate_question_ids": {
                "jdbc_type": "array",
                "postgres_type": "bigint[]",
                "value": candidate_ids,
            },
        }

    def test_65536_candidates_remain_four_bound_parameters(self) -> None:
        sql = (
            "SELECT COUNT(1) FROM questions q JOIN subjects s ON s.id=q.subject_id "
            "WHERE s.name=:subject_name AND q.type=:question_type "
            "AND s.id<>ALL(CAST(:excluded_subject_ids AS integer[])) "
            "AND q.id=ANY(CAST(:candidate_question_ids AS bigint[]))"
        )
        small_sql, small = TOOL.prepared_execution_sql(
            "small", sql, self.parameters(list(range(1, 11))), explain=True
        )
        large_sql, large = TOOL.prepared_execution_sql(
            "large", sql, self.parameters(list(range(1, 65_537))), explain=True
        )

        self.assertEqual(small["bound_parameter_count"], 4)
        self.assertEqual(large["bound_parameter_count"], 4)
        self.assertEqual(small["named_parameter_count"], 4)
        self.assertEqual(large["named_parameter_count"], 4)
        self.assertIn("PREPARE qc_small", small_sql)
        self.assertIn("PREPARE qc_large", large_sql)
        self.assertIn("bigint[]", large_sql)
        summary = large["parameters"]["candidate_question_ids"]
        self.assertEqual(summary["element_count"], 65_536)
        self.assertEqual(summary["first_values"], [1, 2, 3])
        self.assertEqual(summary["last_values"], [65_534, 65_535, 65_536])
        self.assertRegex(summary["value_sha256"], r"^[0-9a-f]{64}$")
        self.assertNotIn("value", summary)

    def test_invalid_array_elements_fail_closed(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "positive integers"):
            TOOL.postgres_parameter_literal({
                "jdbc_type": "array",
                "postgres_type": "bigint[]",
                "value": [1, 0, 3],
            })


class PlanNormalizationTest(unittest.TestCase):

    def test_removes_timing_buffers_memory_and_workers(self) -> None:
        raw = {
            "Planning Time": 1.2,
            "Execution Time": 3.4,
            "Plan": {
                "Node Type": "Aggregate",
                "Actual Rows": 1,
                "Actual Loops": 1,
                "Actual Total Time": 3.0,
                "Shared Hit Blocks": 12,
                "Peak Memory Usage": 32,
                "Workers": [{"Worker Number": 0}],
                "Plans": [{
                    "Node Type": "Seq Scan",
                    "Relation Name": "questions",
                    "Actual Rows": 50_000,
                    "Actual Loops": 1,
                    "Temp Written Blocks": 0,
                    "Index Cond": "id = ANY ('{1,2,3,4}'::bigint[])",
                }],
            },
        }

        normalized = TOOL.normalize_explain(raw)

        self.assertNotIn("Planning Time", normalized)
        self.assertNotIn("Execution Time", normalized)
        self.assertNotIn("Actual Total Time", normalized["Plan"])
        self.assertNotIn("Shared Hit Blocks", normalized["Plan"])
        self.assertNotIn("Peak Memory Usage", normalized["Plan"])
        self.assertNotIn("Workers", normalized["Plan"])
        self.assertNotIn(
            "Temp Written Blocks", normalized["Plan"]["Plans"][0]
        )
        self.assertEqual(
            normalized["Plan"]["Plans"][0]["Index Cond"]["redacted"],
            "planner expression omitted",
        )
        self.assertNotIn(
            "{1,2,3,4}",
            json.dumps(normalized, ensure_ascii=False),
        )

    def test_plan_gate_rejects_temp_spill_or_cross_owner_relation(self) -> None:
        spec = {
            "observation_id": "synthetic",
            "expected_count": 7,
            "required_index_groups": [],
        }
        execution = {
            "bound_parameter_count": 0,
            "occurrence_names": [],
        }
        summary = {
            "result_row_count": 1,
            "root_actual_loops": 1,
            "node_count": 3,
            "maximum_depth": 2,
            "maximum_actual_loops": 1,
            "relation_scan_occurrences": {"questions": 1, "subjects": 1},
            "index_names": [],
        }
        passed = TOOL.assert_plan(spec, execution, 7, summary, {})
        self.assertIn("catalog-only-fixed-relation-scan-budget", passed)

        with self.assertRaisesRegex(AssertionError, "TEMP"):
            TOOL.assert_plan(
                spec,
                execution,
                7,
                summary,
                {"Temp Written Blocks": 1.0},
            )
        cross_owner = dict(summary)
        cross_owner["relation_scan_occurrences"] = {
            "questions": 1,
            "subjects": 1,
            "favorites": 1,
        }
        with self.assertRaisesRegex(AssertionError, "crossed data owners"):
            TOOL.assert_plan(spec, execution, 7, cross_owner, {})


class FixtureContractTest(unittest.TestCase):

    def test_expected_counts_preserve_anonymous_unassigned_difference(self) -> None:
        anonymous = TOOL.expected_count(
            50_000, 5_000, require_existing_subject=False
        )
        authenticated = TOOL.expected_count(
            50_000, 5_000, require_existing_subject=True
        )

        self.assertEqual(anonymous - authenticated, 50)

    def test_large_candidate_boundary_has_expected_filtered_matches(self) -> None:
        candidates = list(range(1, 65_537))
        count = TOOL.expected_count(
            150_000,
            5_000,
            require_existing_subject=True,
            subject_name="Subject 00002",
            question_type="boolean",
            excluded_subject_ids=range(10, 5_001, 10),
            candidate_question_ids=candidates,
        )

        self.assertEqual(count, 14)


if __name__ == "__main__":
    unittest.main()
