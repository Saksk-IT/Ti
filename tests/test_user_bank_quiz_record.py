# -*- coding: utf-8 -*-
"""个人题库刷题记录接口回归测试。"""

from __future__ import annotations

import pytest

from app.modules.user_bank.routes.api_quiz import _normalize_quiz_record_is_correct


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        (True, True),
        (False, False),
        (1, True),
        (0, False),
        ("true", True),
        ("false", False),
        ("1", True),
        ("0", False),
        ("yes", True),
        ("no", False),
    ],
)
def test_normalize_quiz_record_is_correct_accepts_common_client_values(raw_value, expected):
    assert _normalize_quiz_record_is_correct(raw_value) is expected


@pytest.mark.parametrize("raw_value", [None, "", "maybe", 2, [], {}])
def test_normalize_quiz_record_is_correct_rejects_invalid_values(raw_value):
    with pytest.raises(ValueError):
        _normalize_quiz_record_is_correct(raw_value)
