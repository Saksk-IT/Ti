#!/usr/bin/env python3
"""Focused regression tests for the phase-0 legacy inventory parser."""

from __future__ import annotations

import unittest
from pathlib import Path

from inventory_legacy import extract_path_calls, literal_matches_rule, structurally_matches


class ClientCallExtractionTest(unittest.TestCase):
    def test_fetch_method_is_scoped_to_current_call(self) -> None:
        source = """
        function load() {
          return fetch('/user/banks/api/overview?scope=all', {
            credentials: 'same-origin'
          });
        }
        function remove() {
          return fetch('/user/banks/api/42', {
            method: 'DELETE',
            headers: {'X-Requested-With': 'XMLHttpRequest'}
          });
        }
        """

        calls, _endpoint_refs = extract_path_calls(
            "web",
            Path("/legacy/static/example.js"),
            source,
            Path("/legacy"),
        )

        self.assertEqual(
            [(path, method) for path, method, _source in calls],
            [
                ("/user/banks/api/overview", "GET"),
                ("/user/banks/api/42", "DELETE"),
            ],
        )

    def test_literal_route_match_respects_integer_converter(self) -> None:
        self.assertFalse(
            literal_matches_rule(
                "/user/banks/api/overview",
                "/user/banks/api/<int:bank_id>",
            )
        )
        self.assertTrue(
            literal_matches_rule(
                "/user/banks/api/42",
                "/user/banks/api/<int:bank_id>",
            )
        )

    def test_template_expression_can_match_dynamic_rule(self) -> None:
        for client_path in (
            "/api/subjects/${subjectId}/export",
            "/api/subjects/{{ subject.id }}/export",
            "/api/subjects/{subject_id}/export",
        ):
            with self.subTest(client_path=client_path):
                self.assertTrue(
                    structurally_matches(
                        client_path,
                        "/api/subjects/<int:subject_id>/export",
                    )
                )

    def test_literal_route_match_allows_one_canonical_trailing_slash(self) -> None:
        self.assertTrue(literal_matches_rule("/user/banks", "/user/banks/"))


if __name__ == "__main__":
    unittest.main()
