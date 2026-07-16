#!/usr/bin/env python3
"""Unit checks for the runtime-SQL query-plan evidence bridge."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


TOOL_PATH = Path(__file__).with_name("capture_phase4a_public_bank_query_plans.py")
SPEC = importlib.util.spec_from_file_location("phase4a_public_bank_plans", TOOL_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load query-plan capture tool: {TOOL_PATH}")
TOOL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TOOL)


class PreparedExplainSqlTest(unittest.TestCase):

    def test_repeated_named_parameters_become_typed_positional_occurrences(self) -> None:
        execution_sql, metadata = TOOL.prepared_explain_sql(
            "quoted-value",
            "SELECT :textValue, :textValue, :integerValue",
            {
                "textValue": {"jdbc_type": "text", "value": "O'Reilly"},
                "integerValue": {"jdbc_type": "integer", "value": 7},
            },
        )

        self.assertIn("PREPARE phase4a_quoted_value (text, text, integer)", execution_sql)
        self.assertIn("SELECT $1, $2, $3", execution_sql)
        self.assertIn("EXECUTE phase4a_quoted_value ('O''Reilly', 'O''Reilly', 7)", execution_sql)
        self.assertEqual(metadata["mode"], "prepare-execute")
        self.assertEqual(
            [item["name"] for item in metadata["parameter_occurrences"]],
            ["textValue", "textValue", "integerValue"],
        )
        self.assertRegex(metadata["prepared_sql_sha256"], r"^[0-9a-f]{64}$")

    def test_parameterless_runtime_sql_is_explained_directly(self) -> None:
        execution_sql, metadata = TOOL.prepared_explain_sql(
            "parameterless", "SELECT 1", {})

        self.assertEqual(
            execution_sql,
            "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)\nSELECT 1;",
        )
        self.assertEqual(metadata["mode"], "direct")
        self.assertEqual(metadata["parameter_occurrences"], [])
        self.assertIsNone(metadata["prepared_sql_sha256"])

    def test_manifest_parameter_drift_fails_before_postgres_execution(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "undeclared parameters"):
            TOOL.prepared_explain_sql("missing", "SELECT :missing", {})
        with self.assertRaisesRegex(RuntimeError, "unused parameters"):
            TOOL.prepared_explain_sql(
                "unused",
                "SELECT 1",
                {"unused": {"jdbc_type": "bigint", "value": "1"}},
            )
        with self.assertRaisesRegex(RuntimeError, "statement separator"):
            TOOL.prepared_explain_sql("separator", "SELECT 1; SELECT 2", {})

    def test_bigint_and_time_parameters_preserve_manifest_text(self) -> None:
        execution_sql, metadata = TOOL.prepared_explain_sql(
            "typed",
            "SELECT :identity, :localCutoff, :instantCutoff, :enabled",
            {
                "identity": {"jdbc_type": "bigint", "value": "700001"},
                "localCutoff": {
                    "jdbc_type": "timestamp",
                    "value": "2026-07-09T12:00",
                },
                "instantCutoff": {
                    "jdbc_type": "timestamptz",
                    "value": "2026-07-09T04:00Z",
                },
                "enabled": {"jdbc_type": "boolean", "value": True},
            },
        )

        self.assertIn("(bigint, timestamp, timestamptz, boolean)", execution_sql)
        self.assertIn(
            "(700001, '2026-07-09T12:00', '2026-07-09T04:00Z', true)",
            execution_sql,
        )
        self.assertEqual(len(metadata["parameter_occurrences"]), 4)


if __name__ == "__main__":
    unittest.main()
