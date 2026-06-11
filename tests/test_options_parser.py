# -*- coding: utf-8 -*-

import json

from app.core.utils.options_parser import parse_options
from app.core.utils.portable_question_sync import build_portable_columns


def test_parse_options_preserves_cplusplus_plain_text_options():
    raw_options = [
        "C是面向过程，C++是纯面向对象\n",
        "C++是C的超集\n",
        "C++是对C的错误的修改\n",
        "C++和C没有关系\n",
    ]

    parsed = parse_options(raw_options)

    assert [item["key"] for item in parsed] == ["A", "B", "C", "D"]
    assert [item["value"] for item in parsed] == [
        "C是面向过程，C++是纯面向对象",
        "C++是C的超集",
        "C++是对C的错误的修改",
        "C++和C没有关系",
    ]


def test_parse_options_preserves_cplusplus_at_start_of_multiple_options():
    raw_options = [
        "C++程序的每行只能写一条语句\n",
        "C++语言的输入/输出功能通常是通过输入/输出流对象cin和cout实现的\n",
        "在C++程序中，main函数必须位于程序的最前面\n",
        "在对一个C++程序进行编译的过程中，可以发现注释中的拼写错误\n",
    ]

    parsed = parse_options(raw_options)

    assert [item["key"] for item in parsed] == ["A", "B", "C", "D"]
    assert [item["value"] for item in parsed] == [
        "C++程序的每行只能写一条语句",
        "C++语言的输入/输出功能通常是通过输入/输出流对象cin和cout实现的",
        "在C++程序中，main函数必须位于程序的最前面",
        "在对一个C++程序进行编译的过程中，可以发现注释中的拼写错误",
    ]


def test_parse_options_keeps_legacy_compact_prefix_when_sequential():
    parsed = parse_options(["A正确", "B错误"])

    assert parsed == [
        {"key": "A", "value": "正确"},
        {"key": "B", "value": "错误"},
    ]


def test_build_portable_columns_preserves_cplusplus_for_user_bank_import():
    pqf = build_portable_columns(
        q_id=None,
        q_type="选择题",
        content="关于C和C++的描述中，正确的是（ ）",
        options=[
            "C是面向过程，C++是纯面向对象\n",
            "C++是C的超集\n",
            "C++是对C的错误的修改\n",
            "C++和C没有关系\n",
        ],
        answer="B",
        explanation="",
        difficulty=3,
        tags=[],
    )

    assert json.loads(pqf["options"]) == [
        "C是面向过程，C++是纯面向对象",
        "C++是C的超集",
        "C++是对C的错误的修改",
        "C++和C没有关系",
    ]
    assert json.loads(pqf["answer"]) == [1]
