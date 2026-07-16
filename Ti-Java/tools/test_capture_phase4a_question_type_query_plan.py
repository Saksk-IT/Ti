#!/usr/bin/env python3
"""Unit checks for the question-type runtime SQL plan evidence bridge."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


TOOL_PATH = Path(__file__).with_name("capture_phase4a_question_type_query_plan.py")
SPEC = importlib.util.spec_from_file_location("phase4a_question_type_plan", TOOL_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load query-plan capture tool: {TOOL_PATH}")
TOOL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TOOL)


class QuestionTypePlanToolTest(unittest.TestCase):

    def test_manifest_loader_accepts_only_the_exact_single_runtime_query(self) -> None:
        manifest = {
            "manifest_id": "ti.phase4a.question-type-runtime-sql",
            "schema_version": 1,
            "query_count": 1,
            "queries": [{
                "query_id": "question-types-distinct",
                "operation": "question-types",
                "sql": "SELECT DISTINCT q.type AS question_type FROM questions q",
                "parameters": {},
            }],
        }
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "manifest.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            self.assertEqual(manifest, TOOL.load_runtime_sql_manifest(path))

            manifest["queries"][0]["sql"] += "; DELETE FROM questions"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "unsafe"):
                TOOL.load_runtime_sql_manifest(path)

    def test_legacy_projection_retains_alias_unknown_and_blank_semantics(self) -> None:
        labels = sorted({TOOL.legacy_label(value) for value in TOOL.RAW_TYPES})
        self.assertEqual(["判断题", "填空题", "多选题", "简答题", "选择题"], labels)
        self.assertEqual("简答题", TOOL.legacy_label("   "))
        self.assertEqual("选择题", TOOL.legacy_label(" SINGLE "))
        self.assertEqual("简答题", TOOL.legacy_label("unknown"))

    def test_explain_normalization_removes_runtime_noise_but_retains_rows(self) -> None:
        raw = {
            "Plan": {
                "Node Type": "Aggregate",
                "Actual Rows": 12,
                "Actual Loops": 1,
                "Actual Total Time": 2.5,
                "Peak Memory Usage": 24,
                "Shared Hit Blocks": 3,
                "Plans": [{
                    "Node Type": "Seq Scan",
                    "Relation Name": "questions",
                    "Actual Rows": 50_000,
                    "Actual Loops": 1,
                    "Shared Hit Blocks": 3,
                }],
            },
            "Planning Time": 0.2,
            "Execution Time": 2.7,
        }

        self.assertEqual(["Shared Hit Blocks"], TOOL.collect_buffer_fields(raw))
        normalized = TOOL.normalize_explain(raw)
        serialized = json.dumps(normalized)
        self.assertNotIn("Time", serialized)
        self.assertNotIn("Memory", serialized)
        self.assertNotIn("Blocks", serialized)
        summary = TOOL.summarize_plan(normalized, ["Shared Hit Blocks"])
        self.assertEqual(12, summary["result_row_count"])
        self.assertEqual({"questions": 1}, summary["relation_scan_occurrences"])
        self.assertEqual(
            [
                "twelve-raw-distinct-values",
                "single-execution-no-n-plus-one",
                "one-questions-relation-scan",
                "bounded-plan-shape",
                "no-nested-loop",
                "buffers-captured-before-normalization",
            ],
            TOOL.assert_plan(summary),
        )

    def test_argument_validation_requires_immutable_image_and_large_fixture(self) -> None:
        class Args:
            question_count = TOOL.DEFAULT_QUESTION_COUNT
            subject_count = TOOL.DEFAULT_SUBJECT_COUNT
            startup_timeout_seconds = 120
            image = TOOL.DEFAULT_IMAGE

        TOOL.validate_args(Args())
        Args.image = "postgres:18"
        with self.assertRaisesRegex(ValueError, "immutable"):
            TOOL.validate_args(Args())


if __name__ == "__main__":
    unittest.main()
