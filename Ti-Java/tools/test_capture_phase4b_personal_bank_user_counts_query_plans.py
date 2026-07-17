#!/usr/bin/env python3
"""Unit tests for deterministic dual-PG user-counts query-plan evidence."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


TOOLS_DIR = Path(__file__).resolve().parent
TI_JAVA = TOOLS_DIR.parent
sys.path.insert(0, str(TOOLS_DIR))

import capture_phase4b_personal_bank_user_counts_query_plans as tool  # noqa: E402


def evidence_query(
    query_id: str,
    operation: str,
    ordinal: int,
    q_type_filter: bool,
    tag_parameter_count: int,
) -> dict[str, object]:
    order = tool.expected_parameter_order(
        query_id, q_type_filter, tag_parameter_count
    )
    return {
        "ordinal": ordinal,
        "query_id": query_id,
        "operation": operation,
        "sql": tool.expected_sql(query_id, q_type_filter, tag_parameter_count),
        "parameter_order": order,
        "parameters": tool.expected_parameter_types(order),
    }


def exact_manifest() -> dict[str, object]:
    queries = [
        evidence_query(query_id, operation, ordinal, False, 0)
        for ordinal, (query_id, operation) in enumerate(
            zip(tool.QUERY_IDS, tool.EXPECTED_OPERATIONS), start=1
        )
    ]
    variants = []
    for variant_id, q_type_filter, tag_count in tool.EXPECTED_VARIANTS:
        variant_queries = [
            evidence_query(query_id, operation, ordinal, q_type_filter, tag_count)
            for ordinal, (query_id, operation) in enumerate(
                zip(tool.STATISTICS_QUERY_IDS, tool.EXPECTED_OPERATIONS[2:]),
                start=1,
            )
        ]
        variants.append({
            "variant_id": variant_id,
            "q_type_filter": q_type_filter,
            "tag_parameter_count": tag_count,
            "query_count": 6,
            "queries": variant_queries,
        })
    large_names = [f"tq_{index}" for index in range(900)]
    return {
        "manifest_id": tool.MANIFEST_ID,
        "schema_version": 1,
        "source_class": tool.SOURCE_CLASS,
        "scope": "test-only-preimplementation-evidence",
        "baseline_route_owner": "personalbank",
        "production_owner_authorized": False,
        "implementation_authorized": False,
        "schema_or_index_delta_authorized": False,
        "cross_context_table_owner": "learning",
        "cross_context_table_owner_approval": "not-granted",
        "runtime_tag_ddl_or_legacy_migration_in_scope": False,
        "postgres_transaction_poisoning_sqlstate": "25P02",
        "q_type_parameter_type_evidence": {
            "parameter_name": "q_type_f",
            "manifest_parameters_field_scope": (
                "postgresql-explicit-prepare-declaration-for-query-plan-evidence"
            ),
            "manifest_prepare_type": "text",
            "jdbc_client_observation_scope": (
                "spring-jdbcclient-java-string-binding-in-compatibility-it"
            ),
            "jdbc_client_observed_pg_typeof": "character varying",
            "legacy_runtime_bind_type_claimed": False,
            "cross_scope_type_identity_claimed": False,
            "legacy_q_type_predicate_changed": False,
        },
        "jdbc_compatibility_evidence": {
            "integration_test": (
                "io.saksk.ti.integration."
                "Phase4bPersonalBankUserCountsEvidenceJdbcCompatibilityIT"
            ),
            "postgres_versions": ["16.14", "18.4"],
            "initial_statement_failure_sqlstate": "42703",
            "poisoned_followup_sqlstate": "25P02",
            "rollback_recovery_required": True,
        },
        "access_query_count": 2,
        "statistics_query_count_per_nonempty_read": 4,
        "query_family_count": 8,
        "query_order": list(tool.QUERY_IDS),
        "queries": queries,
        "statistics_sequences": deepcopy(tool.EXPECTED_SEQUENCES),
        "canonical_variants": variants,
        "empty_resolved_tag_ids": {
            "http_result": "zero-count-success",
            "statistics_query_count": 0,
            "dynamic_in_query_emitted": False,
        },
        "raw_type_projection": {
            "jdbc_type": "text",
            "nullable": True,
            "blank_and_unknown_values_preserved": True,
            "application_type_mapping_in_scope": False,
        },
        "legacy_join_shape": {
            "favorites_bank_id_predicate": False,
            "mistakes_bank_id_predicate": False,
        },
        "large_tag_safety": {
            "canonical_variant_id": "tag-900-boundary",
            "evidence_render_bound": 900,
            "evidence_renderer_overflow_rejected": True,
            "legacy_explicit_tag_id_limit_present": False,
            "legacy_explicit_tag_id_limit": None,
            "overflow_above_evidence_bound": "not-a-captured-legacy-rejection",
            "production_limit_strategy_authorized": False,
            "values_interpolated_into_sql": False,
            "full_query_plan_required": False,
            "predicate": "q.id IN (" + ", ".join(
                f":{name}" for name in large_names
            ) + ")",
            "parameter_order": large_names,
            "parameter_names_unique": True,
        },
    }


def write_manifest(directory: Path, manifest: object) -> Path:
    path = directory / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def raw_explain(plan: dict[str, object]) -> list[dict[str, object]]:
    return [{
        "Plan": plan,
        "Planning Time": 0.25,
        "Execution Time": 1.5,
    }]


def summarized(plan: dict[str, object]) -> dict[str, object]:
    explain = raw_explain(plan)
    buffers = tool.collect_numeric_fields(explain, tool.BUFFER_KEYS)
    timings = tool.collect_numeric_fields(explain, tool.TIMING_KEYS)
    return tool.plan_summary(tool.normalize_explain(explain), buffers, timings)


class ManifestAndSqlSafetyTest(unittest.TestCase):

    def test_accepts_exact_eight_family_manifest_and_variants(self) -> None:
        manifest = exact_manifest()
        with tempfile.TemporaryDirectory() as temporary:
            loaded = tool.load_sql_manifest(
                write_manifest(Path(temporary), manifest)
            )
        self.assertEqual(manifest, loaded)
        self.assertEqual(
            [*tool.QUERY_IDS[:2], *tool.STATISTICS_QUERY_IDS, *tool.STATISTICS_QUERY_IDS],
            [query["query_id"] for query in tool.plan_queries(loaded)],
        )
        self.assertEqual(14, len(tool.plan_queries(loaded)))

    def test_rejects_owner_scope_sequence_large_tag_and_25p02_drift(self) -> None:
        mutations = []
        for key, value in (
            ("manifest_id", "wrong"),
            ("schema_version", 2),
            ("baseline_route_owner", "learning"),
            ("production_owner_authorized", True),
            ("schema_or_index_delta_authorized", True),
            ("cross_context_table_owner_approval", "granted"),
            ("postgres_transaction_poisoning_sqlstate", "00000"),
            ("query_family_count", 7),
        ):
            manifest = exact_manifest()
            manifest[key] = value
            mutations.append(manifest)
        sequence = exact_manifest()
        sequence["statistics_sequences"]["favorites"] = list(
            reversed(sequence["statistics_sequences"]["favorites"])
        )
        mutations.append(sequence)
        large = exact_manifest()
        large["large_tag_safety"]["legacy_explicit_tag_id_limit_present"] = True
        mutations.append(large)
        jdbc = exact_manifest()
        jdbc["jdbc_compatibility_evidence"]["poisoned_followup_sqlstate"] = "40001"
        mutations.append(jdbc)
        q_type_scope = exact_manifest()
        q_type_scope["q_type_parameter_type_evidence"][
            "cross_scope_type_identity_claimed"
        ] = True
        mutations.append(q_type_scope)
        for manifest in mutations:
            with self.subTest(keys=manifest.keys()):
                with tempfile.TemporaryDirectory() as temporary:
                    with self.assertRaises(RuntimeError):
                        tool.load_sql_manifest(
                            write_manifest(Path(temporary), manifest)
                        )

    def test_rejects_query_order_type_shape_injection_and_write_drift(self) -> None:
        unsafe = []
        parameter_order = exact_manifest()
        parameter_order["canonical_variants"][4]["queries"][1][
            "parameter_order"
        ] = ["uid", "bank_id", "q_type_f", "tq_0", "tq_1", "tq_2"]
        unsafe.append(parameter_order)
        parameter_type = exact_manifest()
        parameter_type["canonical_variants"][4]["queries"][0]["parameters"][
            "q_type_f"
        ] = "varchar"
        unsafe.append(parameter_type)
        for suffix in (
            " LIMIT 1",
            "; DELETE FROM user_bank_questions",
            " /* comment */",
        ):
            manifest = exact_manifest()
            manifest["queries"][2]["sql"] += suffix
            unsafe.append(manifest)
        system_schema = exact_manifest()
        system_schema["queries"][2]["sql"] = system_schema["queries"][2][
            "sql"
        ].replace("user_bank_questions", "pg_temp.user_bank_questions")
        unsafe.append(system_schema)
        for manifest in unsafe:
            with tempfile.TemporaryDirectory() as temporary:
                with self.assertRaises(RuntimeError):
                    tool.load_sql_manifest(
                        write_manifest(Path(temporary), manifest)
                    )

    def test_manifest_export_is_target_confined_and_selects_only_exporter(self) -> None:
        output = TI_JAVA / "server/target/unit-user-counts-manifest.json"
        completed = subprocess.CompletedProcess([], 0, "", "")
        with patch.object(tool.base, "run", return_value=completed) as mocked:
            tool.export_sql_manifest(TI_JAVA, output)
        command = mocked.call_args.args[0]
        self.assertIn("-DskipITs", command)
        self.assertIn(
            "-Dtest=PersonalBankUserCountsEvidenceSqlManifestTest", command
        )
        self.assertTrue(any(
            "ti.personal-bank-user-counts-evidence.sql-manifest-output" in item
            for item in command
        ))
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "server/target"):
                tool.export_sql_manifest(
                    TI_JAVA, Path(temporary) / "manifest.json"
                )

    def test_paths_are_confined_and_fixture_order_is_exact(self) -> None:
        output = TI_JAVA / "docs/refactor/phase4b/unit-user-counts-plan.json"
        manifest = TI_JAVA / "server/target/unit-user-counts-manifest.json"
        tool.validate_paths(TI_JAVA, output, manifest)
        self.assertEqual(
            [str((TI_JAVA / item).resolve()) for item in tool.FIXTURE_INPUTS],
            [str(item) for item in tool.fixture_paths(TI_JAVA)],
        )
        self.assertEqual(
            ["030", "062", "063", "064", "065", "066", "067", "068"],
            [Path(item).name.split("-", 1)[0] for item in tool.FIXTURE_INPUTS],
        )
        with tempfile.TemporaryDirectory() as temporary:
            outside = Path(temporary) / "outside.json"
            with self.assertRaisesRegex(ValueError, "docs/refactor/phase4b"):
                tool.validate_paths(TI_JAVA, outside, manifest)
            with self.assertRaisesRegex(ValueError, "server/target"):
                tool.validate_paths(TI_JAVA, output, outside)


class BindSequenceScaleAndResultTest(unittest.TestCase):

    def test_source_sequences_preserve_repeated_query_occurrences(self) -> None:
        metadata = tool.sequence_occurrence_metadata(exact_manifest())
        self.assertEqual(
            {
                tool.QUERY_IDS[3]: {
                    "occurrence_count": 2,
                    "one_based_positions": [1, 2],
                    "same_sql_family_reused": True,
                }
            },
            metadata["favorites"]["repeated_query_families"],
        )
        self.assertEqual(
            {
                tool.QUERY_IDS[4]: {
                    "occurrence_count": 2,
                    "one_based_positions": [1, 3],
                    "same_sql_family_reused": True,
                }
            },
            metadata["mistakes"]["repeated_query_families"],
        )
        self.assertEqual(4, metadata["all"]["runtime_statement_count"])

    def test_prepare_execute_preserves_bind_order_types_and_values(self) -> None:
        manifest = exact_manifest()
        queries = tool.plan_queries(manifest)
        share = queries[1]
        self.assertEqual(["user_id", "bank_id"], share["parameter_order"])
        self.assertEqual(
            {"user_id": "bigint", "bank_id": "integer"},
            share["parameters"],
        )
        self.assertNotIn(":uid", share["sql"])
        self.assertTrue(all(
            "uid" in query["parameter_order"]
            for query in queries
            if query["query_id"] in {
                tool.QUERY_IDS[3], tool.QUERY_IDS[4],
                tool.QUERY_IDS[6], tool.QUERY_IDS[7],
            }
        ))
        for query in queries:
            statement, binding = tool.prepared_statement(query, explain=True)
            self.assertIn("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)", statement)
            self.assertNotRegex(statement, r":[A-Za-z]")
            self.assertEqual(
                binding["occurrence_names"],
                [item["name"] for item in binding["ordered_bindings"]],
            )
            self.assertEqual(
                binding["postgres_types_in_order"],
                [item["postgres_type"] for item in binding["ordered_bindings"]],
            )
            self.assertEqual(
                list(range(1, binding["bound_parameter_count"] + 1)),
                [item["position"] for item in binding["ordered_bindings"]],
            )
            self.assertIn("$1", statement)

    def test_tag_1_tag_3_and_exported_900_boundary_are_safe(self) -> None:
        manifest = exact_manifest()
        safety = tool.manifest_tag_safety(manifest, 900)
        self.assertEqual(900, safety["large_tag_parameter_count"])
        self.assertEqual(903, safety["maximum_large_bind_count"])
        self.assertTrue(safety["contiguous_named_parameters"])
        self.assertTrue(safety["integer_tag_bind_types"])
        self.assertFalse(safety["legacy_explicit_tag_id_limit_present"])
        self.assertEqual(
            "not-a-captured-legacy-rejection",
            safety["overflow_above_evidence_bound"],
        )
        large = tool.build_large_tag_queries(manifest, 900)
        self.assertEqual(6, len(large))
        self.assertEqual(902, len(large[0]["parameter_order"]))
        self.assertEqual(903, len(large[1]["parameter_order"]))
        with self.assertRaises(ValueError):
            tool.build_large_tag_queries(manifest, 901)

    def test_scale_fixture_is_deterministic_large_and_index_neutral(self) -> None:
        sql = tool.scale_fixture_sql(5_000, 150_000)
        self.assertEqual(2, sql.count("generate_series(1, 5000)"))
        self.assertEqual(3, sql.count("generate_series(1, 150000)"))
        self.assertIn("value % 4 = 0", sql)
        self.assertIn("value % 6 = 0", sql)
        self.assertIn("ELSE NULL", sql)
        self.assertNotRegex(
            sql.upper(), r"\b(?:CREATE|ALTER|DROP)\s+(?:UNIQUE\s+)?INDEX\b"
        )
        self.assertRegex(tool.base.sha256_text(sql), r"^[0-9a-f]{64}$")

    def test_result_contract_closes_all_eight_canonical_families(self) -> None:
        bank_row = [[str(i) for i in range(22)]]
        bank_row[0][0], bank_row[0][1], bank_row[0][6], bank_row[0][13] = (
            "7101", "7001", "f", "1"
        )
        bank = tool.result_summary(
            tool.QUERY_IDS[0], bank_row,
            "access-unfiltered", 150_000
        )
        share = tool.result_summary(
            tool.QUERY_IDS[1], [[str(i) for i in range(10)]],
            "access-unfiltered", 150_000
        )
        self.assertEqual(1, bank["row_count"])
        self.assertEqual(
            "id,user_id,is_public,status",
            bank["cross_version_stable_projection"],
        )
        self.assertEqual(10, share["column_count"])
        expected = {
            tool.QUERY_IDS[2]: ([['1']], 1),
            tool.QUERY_IDS[3]: ([['1']], 1),
            tool.QUERY_IDS[4]: ([['0']], 0),
        }
        for query_id, (rows, value) in expected.items():
            self.assertEqual(
                value,
                tool.result_summary(
                    query_id, rows, "q-type+tag-3", 150_000
                )["count_value"],
            )
        self.assertEqual(
            [tool.TARGET_Q_TYPE],
            tool.result_summary(
                tool.QUERY_IDS[5], [[tool.TARGET_Q_TYPE]],
                "q-type+tag-3", 150_000
            )[
                "raw_type_values"
            ],
        )
        self.assertEqual(
            [],
            tool.result_summary(
                tool.QUERY_IDS[7], [], "q-type+tag-3", 150_000
            )["raw_type_values"],
        )
        unfiltered = {
            tool.QUERY_IDS[5]: [
                "", "boolean", "essay", "fill", "multi_choice",
                "single_choice", "unexpected_type", "<NULL>",
            ],
            tool.QUERY_IDS[6]: [
                "essay", "fill", "multi_choice", "single_choice", "<NULL>",
            ],
            tool.QUERY_IDS[7]: [
                "", "boolean", "fill", "multi_choice", "single_choice", "<NULL>",
            ],
        }
        for query_id, values in unfiltered.items():
            self.assertEqual(
                values,
                tool.result_summary(
                    query_id, [[value] for value in values], "unfiltered", 150_000
                )["raw_type_values"],
            )
        with self.assertRaisesRegex(RuntimeError, "result drifted"):
            tool.result_summary(
                tool.QUERY_IDS[2], [["2"]], "q-type+tag-3", 150_000
            )

    def test_copy_rows_preserves_blank_and_null_raw_type_values(self) -> None:
        query = exact_manifest()["canonical_variants"][0]["queries"][3]
        completed = subprocess.CompletedProcess(
            [], 0, "\nboolean\n<NULL>\n", ""
        )
        with patch.object(tool.base, "run", return_value=completed):
            rows = tool.copy_rows("container", "database", query)
        self.assertEqual([[""], ["boolean"], ["<NULL>"]], rows)


class PlanEngineAndDocumentSupportTest(unittest.TestCase):

    def test_checked_in_evidence_closes_dual_version_fourteen_observations(self) -> None:
        evidence_path = (
            TI_JAVA / "docs/refactor/phase4b/"
            "personal-bank-user-counts-query-plan-evidence.json"
        )
        document = json.loads(evidence_path.read_text(encoding="utf-8"))
        self.assertEqual(
            "ti.phase4b.personal-bank-user-counts-query-plan-evidence",
            document["contract_id"],
        )
        self.assertEqual(
            document["document_payload_sha256"],
            tool.base.document_payload_sha256(document),
        )
        route = document["route_migration_status"]
        self.assertEqual("personalbank", route["baseline_target_module"])
        self.assertEqual("learning", route["reviewed_use_case_owner"])
        self.assertEqual("learning", route["reviewed_http_owner"])
        self.assertIn("does not authorize", route["query_plan_disposition"])

        self.assertEqual(
            ["16.14", "18.4"],
            [engine["server_version"] for engine in document["engines"]],
        )
        for engine in document["engines"]:
            self.assertEqual(14, len(engine["observations"]))
            self.assertEqual(
                {"access-unfiltered", "unfiltered", "q-type+tag-3"},
                {item["evidence_variant"] for item in engine["observations"]},
            )
            self.assertEqual(
                set(tool.QUERY_IDS),
                {item["query_id"] for item in engine["observations"]},
            )
            self.assertTrue(engine["schema_index_and_data_fingerprints_unchanged"])
            poison = engine["transaction_poisoning_and_rollback_recovery"]
            self.assertEqual("42703", poison["initial_failure_sqlstate"])
            self.assertEqual("25P02", poison["subsequent_statement_sqlstate"])
            self.assertTrue(poison["rollback_restored_readability"])
            self.assertTrue(
                engine["large_tag_prepare_execute_probe"][
                    "prepare_execute_succeeded"
                ]
            )
        self.assertEqual(
            900,
            document["dynamic_tag_manifest_safety"][
                "large_tag_parameter_count"
            ],
        )
        self.assertFalse(
            document["dynamic_tag_manifest_safety"][
                "legacy_explicit_tag_id_limit_present"
            ]
        )
        cross = document["cross_version_contract"]
        self.assertEqual(14, cross["observation_count_per_version"])
        self.assertEqual(8, cross["unique_query_family_count"])
        self.assertTrue(cross["fourteen_observations_in_order_per_version"])
        self.assertTrue(cross["canonical_results_equal_across_versions"])
        self.assertTrue(cross["schema_index_and_data_fingerprints_unchanged"])
        self.assertTrue(
            cross["explicit_prepare_bind_order_and_declared_types_closed"]
        )
        self.assertFalse(cross["jdbc_client_runtime_type_equivalence_claimed"])
        self.assertTrue(cross["passed"])
        q_type = document["sql_contract"]["q_type_parameter_type_evidence"]
        self.assertEqual("text", q_type["manifest_prepare_type"])
        self.assertEqual(
            "character varying", q_type["jdbc_client_observed_pg_typeof"]
        )
        self.assertFalse(q_type["cross_scope_type_identity_claimed"])
        for key in (
            "sql_manifest_sha256",
            "sql_manifest_payload_sha256",
        ):
            self.assertRegex(document["inputs"][key], r"^[0-9a-f]{64}$")

    def test_plan_normalization_and_all_relation_budgets(self) -> None:
        plans = {
            tool.QUERY_IDS[0]: {
                "Node Type": "Index Scan",
                "Relation Name": "user_question_banks",
                "Index Name": "user_question_banks_pkey",
                "Actual Rows": 1,
                "Actual Loops": 1,
            },
            tool.QUERY_IDS[1]: {
                "Node Type": "Nested Loop",
                "Actual Rows": 1,
                "Actual Loops": 1,
                "Plans": [
                    {"Node Type": "Seq Scan", "Relation Name": "bank_share_records", "Actual Rows": 1, "Actual Loops": 1},
                    {"Node Type": "Index Scan", "Relation Name": "bank_shares", "Actual Rows": 1, "Actual Loops": 1},
                ],
            },
        }
        statistic_relations = {
            tool.QUERY_IDS[2]: ["user_bank_questions"],
            tool.QUERY_IDS[3]: ["user_bank_questions", "user_bank_favorites"],
            tool.QUERY_IDS[4]: ["user_bank_questions", "user_bank_mistakes"],
            tool.QUERY_IDS[5]: ["user_bank_questions"],
            tool.QUERY_IDS[6]: ["user_bank_questions", "user_bank_favorites"],
            tool.QUERY_IDS[7]: ["user_bank_questions", "user_bank_mistakes"],
        }
        for query_id, relations in statistic_relations.items():
            plans[query_id] = {
                "Node Type": "Aggregate",
                "Actual Rows": 1,
                "Actual Loops": 1,
                "Plans": [
                    {
                        "Node Type": "Index Scan",
                        "Relation Name": relation,
                        "Actual Rows": 1,
                        "Actual Loops": 1,
                    }
                    for relation in relations
                ],
            }
        for query_id, plan in plans.items():
            plan["Shared Hit Blocks"] = 3
            plan["Temp Read Blocks"] = 0
            plan["Temp Written Blocks"] = 0
            summary = summarized(plan)
            expected_rows = 1
            tool.assert_plan_contract(query_id, summary, expected_rows)
            self.assertEqual(0, summary["temp_read_blocks_observed"])
            self.assertEqual(0, summary["temp_written_blocks_observed"])

    def test_fixed_images_argument_floors_and_redaction(self) -> None:
        self.assertEqual(
            ["16.14", "18.4"], [item["version"] for item in tool.POSTGRES_IMAGES]
        )
        accepted = SimpleNamespace(
            bank_count=5_000,
            question_count=150_000,
            large_tag_parameter_count=900,
            startup_timeout_seconds=120,
        )
        tool.validate_args(accepted)
        for field, value in (
            ("bank_count", 4_999),
            ("question_count", 149_999),
            ("large_tag_parameter_count", 0),
            ("large_tag_parameter_count", 901),
            ("startup_timeout_seconds", 0),
        ):
            rejected = SimpleNamespace(**vars(accepted))
            setattr(rejected, field, value)
            with self.assertRaises(ValueError):
                tool.validate_args(rejected)
        for document in (
            {"password": "x"},
            {"nested": {"value": "/Users/private/path"}},
            {"nested": ["ti-phase4b-user-counts-plan-abcdef"]},
            {"nested": "person@test.invalid"},
        ):
            with self.assertRaises(RuntimeError):
                tool.assert_redacted(document)

    def test_transaction_probe_requires_42703_25p02_and_recovery(self) -> None:
        completed = subprocess.CompletedProcess(
            [], 0, "150010\n", "ERROR:  42703\nERROR:  25P02\n"
        )
        with patch.object(tool.base, "run", return_value=completed):
            result = tool.transaction_poisoning_probe(
                "container", "database", 150_010
            )
        self.assertEqual("42703", result["initial_failure_sqlstate"])
        self.assertEqual("25P02", result["subsequent_statement_sqlstate"])
        self.assertTrue(result["rollback_restored_readability"])

        drifted = subprocess.CompletedProcess(
            [], 0, "150010\n", "ERROR:  42703\nERROR:  40001\n"
        )
        with patch.object(tool.base, "run", return_value=drifted):
            with self.assertRaisesRegex(RuntimeError, "SQLSTATE drifted"):
                tool.transaction_poisoning_probe("container", "database", 150_010)

    def test_cleanup_runs_when_container_readiness_fails(self) -> None:
        args = SimpleNamespace(
            bank_count=5_000,
            question_count=150_000,
            large_tag_parameter_count=900,
            startup_timeout_seconds=1,
        )
        started = subprocess.CompletedProcess([], 0, "container-id\n", "")
        with patch.object(tool.base, "run", return_value=started) as mocked_run, patch.object(
            tool.base, "wait_for_postgres", side_effect=RuntimeError("not ready")
        ):
            with self.assertRaisesRegex(RuntimeError, "not ready"):
                tool.capture_engine(
                    tool.POSTGRES_IMAGES[0], exact_manifest(), args, TI_JAVA
                )
        commands = [call.args[0] for call in mocked_run.call_args_list]
        self.assertEqual("docker", commands[0][0])
        self.assertEqual(["docker", "rm", "-f", "-v"], commands[-1][:4])
        self.assertEqual(
            commands[0][commands[0].index("--name") + 1], commands[-1][-1]
        )

    def test_document_payload_render_and_tool_input_hashes_are_deterministic(self) -> None:
        document = {"z": [3, 2, 1], "a": {"unicode": "高数"}}
        digest = tool.base.document_payload_sha256(document)
        with_digest = {**document, "document_payload_sha256": digest}
        self.assertEqual(digest, tool.base.document_payload_sha256(with_digest))
        self.assertEqual(
            tool.base.render_document(with_digest),
            tool.base.render_document(deepcopy(with_digest)),
        )
        self.assertTrue(tool.base.render_document(with_digest).endswith("\n"))

        manifest_path = TI_JAVA / "server/target/unit-user-counts-input.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(exact_manifest()), encoding="utf-8")
        inputs = tool.tool_inputs(TI_JAVA, manifest_path)
        self.assertEqual(
            "server/target/unit-user-counts-input.json",
            inputs["sql_manifest_path"],
        )
        for key, value in inputs.items():
            if key.endswith("_sha256"):
                self.assertRegex(value, r"^[0-9a-f]{64}$", key)


if __name__ == "__main__":
    unittest.main()
