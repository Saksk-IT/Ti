#!/usr/bin/env python3
"""Unit tests for the fail-closed Phase 4B category query-plan bridge."""

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
    "capture_phase4b_personal_bank_category_query_plan.py"
)
SPEC = importlib.util.spec_from_file_location(
    "capture_phase4b_personal_bank_category_query_plan", TOOL_PATH
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot import {TOOL_PATH}")
TOOL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TOOL)


def runtime_manifest() -> dict[str, object]:
    return {
        "manifest_id": TOOL.MANIFEST_ID,
        "schema_version": 1,
        "adapter_class": TOOL.ADAPTER_CLASS,
        "query_count": 1,
        "queries": [{
            "query_id": TOOL.QUERY_ID,
            "operation": TOOL.OPERATION,
            "sql": TOOL.EXPECTED_NORMALIZED_SQL.upper().replace(
                ":USER_ID", ":user_id"
            ),
            "parameters": {"user_id": "bigint"},
        }],
    }


def write_manifest(directory: str, manifest: object) -> Path:
    path = Path(directory) / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def result_summary() -> dict[str, object]:
    return {
        "row_count": 5_002,
        "zero_bank_count_rows": 1_000,
        "null_sort_rows": 1,
        "empty_name_rows": 1,
        "unicode_name_rows": 1,
        "active_bank_count_sum": 134_999,
    }


def dataset_summary() -> dict[str, object]:
    return {
        "current_user_category_rows": 5_002,
        "current_user_active_associations": 134_999,
        "zero_active_bank_categories": 1_000,
    }


def plan_summary() -> dict[str, object]:
    return {
        "result_row_count": 5_002,
        "root_actual_loops": 1,
        "maximum_relation_scan_actual_loops": 1,
        "relation_scan_occurrences": {
            "user_bank_categories": 1,
            "user_question_banks": 1,
        },
    }


class RuntimeSqlManifestTest(unittest.TestCase):

    def test_accepts_exact_single_query_manifest(self) -> None:
        manifest = runtime_manifest()
        with tempfile.TemporaryDirectory() as temporary:
            loaded = TOOL.load_runtime_sql_manifest(
                write_manifest(temporary, manifest)
            )
        self.assertEqual(manifest, loaded)

    def test_rejects_unreadable_invalid_and_non_object_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(RuntimeError, "cannot read"):
                TOOL.load_runtime_sql_manifest(Path(temporary) / "missing.json")
            invalid = Path(temporary) / "invalid.json"
            invalid.write_text("{", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "cannot read"):
                TOOL.load_runtime_sql_manifest(invalid)
            with self.assertRaisesRegex(RuntimeError, "root"):
                TOOL.load_runtime_sql_manifest(
                    write_manifest(temporary, ["not", "an", "object"])
                )

    def test_rejects_manifest_identity_count_query_and_parameter_drift(self) -> None:
        mutations: list[dict[str, object]] = []
        for key, value in (
            ("manifest_id", "wrong"),
            ("schema_version", 2),
            ("adapter_class", "wrong.Adapter"),
            ("query_count", 2),
        ):
            manifest = runtime_manifest()
            manifest[key] = value
            mutations.append(manifest)
        query_id = runtime_manifest()
        query_id["queries"][0]["query_id"] = "wrong"
        mutations.append(query_id)
        operation = runtime_manifest()
        operation["queries"][0]["operation"] = "wrong"
        mutations.append(operation)
        parameter = runtime_manifest()
        parameter["queries"][0]["parameters"] = {"user_id": "integer"}
        mutations.append(parameter)
        for manifest in mutations:
            with self.subTest(manifest=manifest):
                with tempfile.TemporaryDirectory() as temporary:
                    with self.assertRaises(RuntimeError):
                        TOOL.load_runtime_sql_manifest(
                            write_manifest(temporary, manifest)
                        )

    def test_rejects_projection_filter_owner_status_order_and_bind_drift(self) -> None:
        base = runtime_manifest()["queries"][0]["sql"]
        unsafe = (
            base.replace("C.ID AS CATEGORY_ID,", ""),
            base.replace("LEFT JOIN", "INNER JOIN"),
            base.replace("B.STATUS = 1", "B.STATUS <> 0"),
            base.replace("C.USER_ID = :user_id", "C.USER_ID > :user_id"),
            base.replace("NULLS LAST", "NULLS FIRST"),
            base.replace("B.CATEGORY_ID = C.ID", "B.CATEGORY_ID = C.ID AND B.USER_ID = C.USER_ID"),
            base.replace(":user_id", ":identity_id"),
            base.replace(":user_id", ":user_id + :user_id"),
        )
        for candidate in unsafe:
            with self.subTest(candidate=candidate):
                with self.assertRaises(RuntimeError):
                    TOOL.validate_runtime_sql(candidate)

    def test_rejects_mutation_multi_statement_comment_wildcard_and_pagination(self) -> None:
        base = runtime_manifest()["queries"][0]["sql"]
        unsafe = (
            base + "; DELETE FROM user_bank_categories",
            base.replace("SELECT", "SELECT /* hidden */", 1),
            base.replace("SELECT", "SELECT C.* ,", 1),
            base + " LIMIT 10",
            base.replace("FROM USER_BANK_CATEGORIES", "FROM PG_TEMP.USER_BANK_CATEGORIES"),
        )
        for candidate in unsafe:
            with self.subTest(candidate=candidate):
                with self.assertRaises(RuntimeError):
                    TOOL.validate_runtime_sql(candidate)

    def test_manifest_export_is_target_confined_and_selects_only_exporter_test(self) -> None:
        root = TOOL_PATH.resolve().parents[1]
        output = root / "server/target/unit-phase4b-category-manifest.json"
        completed = subprocess.CompletedProcess([], 0, "", "")
        with patch.object(TOOL, "run", return_value=completed) as mocked:
            TOOL.export_runtime_sql_manifest(root, output)
        command = mocked.call_args.args[0]
        self.assertIn("-Dtest=PersonalBankCategoryRuntimeSqlManifestTest", command)
        self.assertIn("-DskipITs", command)
        self.assertTrue(any(
            "ti.personal-bank-category.sql-manifest-output" in item
            for item in command
        ))
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "server/target"):
                TOOL.export_runtime_sql_manifest(
                    root, Path(temporary) / "manifest.json"
                )


class BindFixtureAndResultTest(unittest.TestCase):

    def test_prepare_execute_uses_one_bigint_bind_and_exact_positional_sql(self) -> None:
        sql = runtime_manifest()["queries"][0]["sql"]
        statement, binding = TOOL.prepared_sql(sql, 9_001, explain=True)
        self.assertEqual(1, statement.count("PREPARE "))
        self.assertEqual(1, statement.count("EXPLAIN "))
        self.assertEqual(1, statement.count("EXECUTE "))
        self.assertEqual(1, statement.count("DEALLOCATE "))
        self.assertNotRegex(statement, r":[A-Za-z]")
        self.assertIn("$1", statement)
        self.assertEqual(1, binding["bound_parameter_count"])
        self.assertEqual("postgresql-prepare-execute", binding["mode"])
        self.assertEqual(
            "postgresql-prepared-statement-parameter",
            binding["parameters"]["user_id"]["bind_kind"],
        )
        self.assertEqual("bigint", binding["parameters"]["user_id"]["postgres_type"])

    def test_bigint_binding_accepts_signed_edges_and_rejects_invalid_values(self) -> None:
        sql = runtime_manifest()["queries"][0]["sql"]
        for value in (-(2**63), -1, 0, 2**63 - 1):
            with self.subTest(value=value):
                _statement, binding = TOOL.prepared_sql(sql, value, explain=False)
                self.assertEqual(value, binding["parameters"]["user_id"]["value"])
        for value in (-(2**63) - 1, 2**63, True, "9001", None):
            with self.subTest(value=value):
                with self.assertRaisesRegex(RuntimeError, "user_id"):
                    TOOL.prepared_sql(sql, value, explain=False)

    def test_fixture_models_int4_users_status_edges_and_no_extra_index(self) -> None:
        sql = TOOL.fixture_sql(5_000, 150_000)
        self.assertIn("user_id integer NOT NULL", sql)
        self.assertIn("status integer", sql)
        self.assertIn("WHEN g % 101 = 0 THEN 2", sql)
        self.assertIn("WHEN g % 103 = 0 THEN NULL", sql)
        self.assertIn("WHEN g % 10 = 0 THEN 0", sql)
        self.assertIn("WHEN g = 5000 THEN NULL", sql)
        self.assertIn("generate_series(1, 150000)", sql)
        self.assertNotIn("CREATE INDEX", sql)
        self.assertIn("VACUUM (ANALYZE) user_bank_categories", sql)
        self.assertEqual(
            {
                "status_one_bank_rows": 132_365,
                "status_zero_bank_rows": 14_708,
                "status_two_bank_rows": 1_485,
                "status_null_bank_rows": 1_442,
            },
            TOOL.expected_bank_status_counts(150_000),
        )

    def test_parse_result_rows_proves_sort_nulls_last_and_raw_edges(self) -> None:
        separator = "\x1f"
        raw = "\n".join((
            separator.join(("-1", "9001", "Negative", "signed", "-5",
                            "2026-07-17 08:00:00", "2026-07-17 09:00:00", "2")),
            separator.join(("0", "9001", "", "", "0",
                            "2026-07-17 08:00:00", "2026-07-17 09:00:00", "1")),
            separator.join(("1", "9001", "高数・α／🧪", "Description", "1",
                            "2026-07-17 08:00:00", "2026-07-17 09:00:00", "0")),
            separator.join(("2", "9001", "Tail", "<NULL>", "<NULL>",
                            "<NULL>", "<NULL>", "0")),
        ))
        result = TOOL.parse_result_rows(raw, 2)
        self.assertEqual(4, result["row_count"])
        self.assertEqual(-1, result["first_id"])
        self.assertEqual(2, result["last_id"])
        self.assertEqual(1, result["null_sort_rows"])
        self.assertEqual(1, result["unicode_name_rows"])
        self.assertEqual(3, result["active_bank_count_sum"])
        with self.assertRaises(AssertionError):
            TOOL.parse_result_rows("\n".join(reversed(raw.splitlines())), 2)

    def test_measurement_gate_rejects_n_plus_one_temp_and_count_drift(self) -> None:
        binding = {"bound_parameter_count": 1}
        accepted = TOOL.assert_measurement(
            result_summary(), dataset_summary(), plan_summary(),
            {"Temp Read Blocks": 0, "Temp Written Blocks": 0}, binding,
        )
        self.assertEqual(6, len(accepted))

        mutations = []
        bad_result = result_summary()
        bad_result["active_bank_count_sum"] = 1
        mutations.append((bad_result, dataset_summary(), plan_summary(), {}, binding))
        bad_plan = plan_summary()
        bad_plan["maximum_relation_scan_actual_loops"] = 2
        mutations.append((result_summary(), dataset_summary(), bad_plan, {}, binding))
        mutations.append((result_summary(), dataset_summary(), plan_summary(),
                          {"Temp Written Blocks": 1}, binding))
        for values in mutations:
            with self.subTest(values=values):
                with self.assertRaises(AssertionError):
                    TOOL.assert_measurement(*values)


class EvidenceSafetyTest(unittest.TestCase):

    def test_required_inputs_bind_postgres_compatibility_claim_to_source_and_fixture(self) -> None:
        root = TOOL_PATH.resolve().parents[1]
        paths = TOOL.required_input_paths(
            root, root / "server/target/phase4b-personal-bank-category-runtime-sql.json"
        )
        expected = {
            "postgres_compatibility_test": (
                "server/src/test/java/io/saksk/ti/integration/"
                "Phase4bPersonalBankCategoryJdbcCompatibilityIT.java"
            ),
            "postgres_schema": (
                "server/src/test/resources/db/phase4b/"
                "060-personal-bank-category-schema.sql"
            ),
            "postgres_fixture": (
                "server/src/test/resources/db/phase4b/"
                "061-personal-bank-category-seed.sql"
            ),
        }
        for key, relative_path in expected.items():
            with self.subTest(key=key):
                self.assertEqual(root / relative_path, paths[key])
                self.assertTrue(paths[key].is_file())

    def test_argument_gate_requires_scale_timeout_and_digest(self) -> None:
        valid = SimpleNamespace(
            category_count=5_000,
            bank_count=150_000,
            startup_timeout_seconds=120,
            image=TOOL.DEFAULT_IMAGE,
        )
        TOOL.validate_args(valid)
        for key, value in (
            ("category_count", 4_999),
            ("bank_count", 149_999),
            ("startup_timeout_seconds", 0),
            ("image", "postgres:18.4-alpine"),
        ):
            mutated = SimpleNamespace(**vars(valid))
            setattr(mutated, key, value)
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    TOOL.validate_args(mutated)

    def test_category_id_distribution_description_uses_actual_scale(self) -> None:
        self.assertEqual(
            "-1, 0 and inclusive 1..6001",
            TOOL.current_user_category_ids_description(6_001),
        )
        for invalid in (0, -1, True, "5000"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    TOOL.current_user_category_ids_description(invalid)

    def test_public_evidence_rejects_secrets_paths_and_container_identity(self) -> None:
        TOOL.assert_public_evidence({"safe": "public synthetic"})
        unsafe = (
            {"password": "value"},
            {"path": "/Users/example/private"},
            {"container": "ti-phase4b-personal-bank-category-plan-abcdef123456"},
        )
        for document in unsafe:
            with self.subTest(document=document):
                with self.assertRaises(AssertionError):
                    TOOL.assert_public_evidence(document)

    def test_atomic_writer_is_canonical_and_leaves_no_temporary_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "evidence.json"
            TOOL.write_json_atomic(output, {"value": "中文", "count": 1})
            self.assertEqual(
                '{\n  "value": "中文",\n  "count": 1\n}\n',
                output.read_text(encoding="utf-8"),
            )
            self.assertFalse(output.with_name(output.name + ".tmp").exists())

    def test_cleanup_is_fail_closed(self) -> None:
        removed = subprocess.CompletedProcess([], 0, "", "")
        for message in (
            "Error: No such object: safe-name",
            "Error response from daemon: No such container: safe-name",
        ):
            absent = subprocess.CompletedProcess([], 1, "", message)
            with self.subTest(message=message):
                with patch.object(TOOL, "run", side_effect=(removed, absent)) as mocked:
                    TOOL.cleanup_container("safe-name")
                self.assertEqual(
                    ["docker", "rm", "--force", "safe-name"],
                    mocked.call_args_list[0].args[0],
                )
        with patch.object(TOOL, "run", side_effect=(removed, removed)):
            with self.assertRaisesRegex(RuntimeError, "remains"):
                TOOL.cleanup_container("safe-name")
        for detail in (
            "Cannot connect to the Docker daemon",
            "permission denied while trying to connect",
            "unexpected inspect failure",
        ):
            failed = subprocess.CompletedProcess([], 1, "", detail)
            with self.subTest(detail=detail):
                with patch.object(TOOL, "run", side_effect=(removed, failed)):
                    with self.assertRaisesRegex(RuntimeError, "could not verify"):
                        TOOL.cleanup_container("safe-name")


if __name__ == "__main__":
    unittest.main()
