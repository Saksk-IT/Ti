#!/usr/bin/env python3
"""Contract checks for pinned dual-route question-count golden evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import unittest


TOOLS_DIR = Path(__file__).resolve().parent
TI_JAVA = TOOLS_DIR.parent
REPOSITORY_ROOT = TI_JAVA.parent
GOLDEN = TI_JAVA / "docs" / "refactor" / "phase4a" / "golden-question-count-reads.json"
sys.dont_write_bytecode = True
sys.path.insert(0, str(TOOLS_DIR))

import capture_phase4a_question_count_goldens as capture  # noqa: E402


LEGACY_COMMIT = "700006dfdfa063deb4387be572911e782bcea0d9"
CASE_PAYLOAD_SHA256 = "db02705cf8de357398c888f1575cd591d7091324c23a409b48ab1f3a6efb397d"
MATRIX_SHA256 = "fdbdfedf3dd70cd09778b2a7072711d103eee8461d0e7dd356d797006fc92c74"
EXPECTED_SOURCE_SHA256 = {
    "app/__init__.py": "9b2efe8a539ee47f7bcf475708466a64669b6bb36804ccf2b1cc5a63fcb21668",
    "app/core/errors.py": "e27f21eb06a9041f28378e5d7aa5e13cfa0aec89bf173855a0a03ba21f55935b",
    "app/core/extensions.py": "293c63c5ea2d548e1389f221909dced878a861d28f8073f305fb98d6ff334052",
    "app/core/utils/cache_utils.py": "2dca082e18bb78a2d7e7e8a0f0ffa3479a6816ea2d5f74fa9c9ad08cf706d170",
    "app/core/utils/portable_question_format.py": "229c3d5a4d26b68020ed7b8e305ffa0ebf902faf597e7e9584fc172b5add8112",
    "app/core/utils/rate_limit.py": "ed6868f842700b19dfdb824c7f7a7f195ba06b4b704bbd80981190887b292208",
    "app/core/utils/redis_utils.py": "26864bebbe52871865e9748c0e62a1a95b3debc56414a3495530ce76f05849c9",
    "app/core/utils/subject_permissions.py": "83717dd3833d1f297311e3af8cc34f350760a86d8bba3020284efd033aa2562d",
    "app/core/utils/user_question_tags.py": "ce6628efc499228fc9230c67bc5092eb7778fb2a445725bea918d09a47b2b28a",
    "app/modules/quiz/__init__.py": "f1c646b823534fcff2bbe14c575595aeaaef0c0d964ab494c5efbd2a0ea3c24e",
    "app/modules/quiz/routes/api.py": "a4016eeca13abd13e4f7c407ddab7b35c45dbf7fc8995735e3ef44d4cedf53e8",
    "app/modules/quiz/routes/api_shared.py": "6d869caef7241719acdb9e3690dc252b1e964cc80cad4626455e055fa89331da",
    "app/modules/quiz/routes/api_components/core.py": "cee9606ad15b40ead85fd409cace6cf6621ef0e6b65b3068837bcf066142e600",
    "app/modules/quiz/routes/api_components/core_counts.py": "01cdbb4254f71b87d61de406524944b560c4e480d7f370ecb522effa8d325063",
    "app/modules/quiz/services/question_tags_service.py": "2d80ad51181e72ad44ffa7e4dc4162e5136cc3b5f1711a374481b766c1ade203",
}


class QuestionCountGoldenContractTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.serialized = GOLDEN.read_text(encoding="utf-8")
        cls.document = json.loads(cls.serialized)
        cls.by_id = {case["case_id"]: case for case in cls.document["cases"]}

    def test_checked_in_contract_is_complete_self_consistent_and_redacted(self) -> None:
        document = self.document
        self.assertEqual("ti.phase4a.question-count-read-goldens", document["contract_id"])
        self.assertEqual(LEGACY_COMMIT, capture.pinned_source.LEGACY_COMMIT)
        self.assertEqual(LEGACY_COMMIT, document["legacy_commit"])
        self.assertEqual(36, document["case_count"])
        self.assertEqual(36, len(document["cases"]))
        self.assertEqual(CASE_PAYLOAD_SHA256, document["case_payload_sha256"])
        self.assertEqual(CASE_PAYLOAD_SHA256, capture.sha256_json(document["cases"]))
        self.assertEqual("catalog", document["route_status"]["target_module_in_frozen_matrix"])
        self.assertEqual("pending", document["route_status"]["migration_status"])
        self.assertFalse(document["route_status"]["production_cutover"])
        self.assertEqual(
            {"c618fb5f9f97", "bb21e7730d04"},
            {route["route_id"] for route in document["route_status"]["routes"]},
        )
        self.assertEqual(capture.render_document(document), self.serialized)
        capture.assert_case_contracts(document["cases"])

        self.assertTrue(all(
            case["observed_get_effects"]["tables_unchanged"]
            and case["observed_get_effects"]["sql"]["question_write_attempts"] == 0
            and set(case["observed_get_effects"]["tables_before"]) == set(capture.TABLE_ORDER)
            for case in document["cases"]
        ))
        self.assertNotIn("eyJ", self.serialized)
        self.assertNotIn("public-test-only-password-hash", self.serialized)

    def test_complete_archive_key_sources_and_route_matrix_are_attested(self) -> None:
        recorded = self.document["legacy_source_attestation"]
        matrix = recorded["frozen_route_matrix"]
        self.assertEqual(MATRIX_SHA256, matrix["sha256"])
        self.assertEqual(capture.matrix_attestation(), matrix)

        workspace: Path | None = None
        with capture.pinned_source.archived_legacy_source(REPOSITORY_ROOT) as archived:
            workspace = archived.workspace
            self.assertEqual(archived.attestation, recorded["complete_app_archive"])
            observed = capture.key_source_attestation(archived)
            self.assertEqual(observed, recorded["question_count_key_sources"])
            self.assertEqual(set(EXPECTED_SOURCE_SHA256), set(observed))
            for path, expected_sha256 in EXPECTED_SOURCE_SHA256.items():
                with self.subTest(path=path):
                    evidence = observed[path]
                    self.assertEqual(expected_sha256, evidence["sha256"])
                    self.assertEqual(
                        expected_sha256,
                        hashlib.sha256((archived.root / path).read_bytes()).hexdigest(),
                    )

        self.assertIsNotNone(workspace)
        self.assertFalse(workspace.exists())

    def test_catalog_primitives_and_future_learning_intersections_are_explicit(self) -> None:
        expected = {
            "alias-anonymous-default": ([7301, 7302, 7303, 7304, 7306], [7301, 7302, 7303, 7304, 7306]),
            "alias-ordinary-default": ([7301, 7302, 7303], [7301, 7302, 7303]),
            "alias-anonymous-locked": ([], []),
            "alias-ordinary-type-chinese": ([7301], [7301]),
            "alias-anonymous-type-unknown": ([7303, 7306], [7303, 7306]),
            "alias-ordinary-favorites": ([7301, 7302, 7303], [7301]),
            "blueprint-ordinary-favorites": ([7301, 7302, 7303], [7301]),
            "alias-ordinary-mistakes": ([7301, 7302, 7303], [7302, 7303]),
            "blueprint-ordinary-mistakes": ([7301, 7302, 7303], [7302, 7303]),
            "alias-ordinary-tag": ([7301, 7302, 7303], [7301, 7302]),
            "blueprint-ordinary-tag": ([7301, 7302, 7303], [7301, 7302]),
        }
        for case_id, (candidates, composed) in expected.items():
            with self.subTest(case_id=case_id):
                case = self.by_id[case_id]
                self.assertEqual(candidates, case["catalog_primitive"]["candidate_question_ids"])
                self.assertEqual(
                    composed,
                    case["future_learning_composition"]["expected_result_question_ids_if_authorized"],
                )

        composition = self.document["future_learning_composition"]
        self.assertEqual("learning", composition["owner"])
        self.assertEqual(
            ["favorites", "mistakes", "user_question_tag_items", "user_progress"],
            composition["facts"],
        )
        self.assertFalse(self.document["catalog_primitive_contract"]["learning_tables_required"])

    def test_parameter_and_credential_precedence_edges_are_locked(self) -> None:
        for case_id in ("alias-source-over-mode", "blueprint-source-over-mode"):
            with self.subTest(case_id=case_id):
                case = self.by_id[case_id]
                self.assertEqual(1, case["response"]["body"]["count"])
                self.assertEqual([7301], case["future_learning_composition"]["expected_result_question_ids_if_authorized"])

        duplicate = self.by_id["alias-duplicate-subject-first"]
        self.assertEqual(
            [["subject", "开放甲"], ["subject", "开放乙"]],
            duplicate["request"]["query"],
        )
        self.assertEqual([7301, 7302, 7303], duplicate["catalog_primitive"]["candidate_question_ids"])
        self.assertEqual(3, duplicate["response"]["body"]["count"])

        tag_all = self.by_id["blueprint-tag-upper-all"]
        self.assertEqual(3, tag_all["response"]["body"]["count"])
        self.assertEqual([7301, 7302, 7303], tag_all["future_learning_composition"]["expected_result_question_ids_if_authorized"])

        alias_invalid = self.by_id["alias-invalid-bearer"]
        blueprint_invalid = self.by_id["blueprint-invalid-bearer"]
        self.assertEqual((200, 5), (alias_invalid["response"]["status"], alias_invalid["response"]["body"]["count"]))
        self.assertEqual(401, blueprint_invalid["response"]["status"])

        session_over_bearer = self.by_id["blueprint-session-over-bearer"]
        self.assertEqual("session+valid_bearer", session_over_bearer["credential_mode"])
        self.assertEqual([7301, 7302, 7303, 7304], session_over_bearer["catalog_primitive"]["candidate_question_ids"])
        self.assertEqual(4, session_over_bearer["response"]["body"]["count"])

    def test_get_runtime_effects_and_pre_auth_stops_are_recorded(self) -> None:
        for case_id in (
            "blueprint-anonymous-default",
            "blueprint-anonymous-source-favorites",
            "alias-anonymous-mode-favorites",
            "blueprint-invalid-bearer",
        ):
            with self.subTest(case_id=case_id):
                effects = self.by_id[case_id]["observed_get_effects"]
                self.assertFalse(effects["route_limiter_consumed"])
                self.assertEqual(0, effects["sql"]["statement_count"])
                self.assertEqual([], effects["cache"]["response_cache_get_keys"])
                self.assertEqual([], effects["cache"]["response_cache_set_attempts"])

        for case_id in ("alias-ordinary-default", "blueprint-ordinary-default"):
            with self.subTest(case_id=case_id):
                effects = self.by_id[case_id]["observed_get_effects"]
                self.assertTrue(effects["route_limiter_consumed"])
                self.assertEqual(1, len(effects["cache"]["response_cache_get_keys"]))
                self.assertEqual(1, len(effects["cache"]["response_cache_set_attempts"]))
                self.assertGreater(effects["sql"]["catalog_selects"], 0)

        for case_id in ("alias-count-failure", "blueprint-count-failure"):
            with self.subTest(case_id=case_id):
                case = self.by_id[case_id]
                self.assertEqual(500, case["response"]["status"])
                self.assertEqual(1, case["observed_get_effects"]["sql"]["question_count_select_attempts"])
                self.assertEqual([], case["observed_get_effects"]["cache"]["response_cache_set_attempts"])

    def test_legacy_tag_fallback_limitation_is_source_attested(self) -> None:
        observation = self.document["future_learning_composition"]["legacy_tag_fallback_observation"]
        source = observation["source"]
        self.assertEqual("app/modules/quiz/services/question_tags_service.py", source)
        self.assertEqual(
            self.document["legacy_source_attestation"]["question_count_key_sources"][source]["sha256"],
            observation["source_sha256"],
        )
        self.assertIn("migration DML is not reached", observation["captured_fixed_stack_result"])
        self.assertIn("row['data']", observation["reason"])

        for case_id in ("alias-legacy-tag-store", "blueprint-legacy-tag-store"):
            with self.subTest(case_id=case_id):
                case = self.by_id[case_id]
                self.assertEqual(0, case["response"]["body"]["count"])
                self.assertEqual(
                    [7303],
                    case["future_learning_composition"]["expected_result_question_ids_if_authorized"],
                )
                sql = case["observed_get_effects"]["sql"]
                self.assertGreater(sql["tag_schema_ddl_attempts"], 0)
                self.assertEqual(0, sql["learning_data_write_attempts"])
                self.assertTrue(case["observed_get_effects"]["tables_unchanged"])


if __name__ == "__main__":
    unittest.main()
