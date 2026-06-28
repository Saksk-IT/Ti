# -*- coding: utf-8 -*-

import json

from app.core.utils.portable_question_format import (
    internal_question_to_portable,
    portable_question_to_internal,
)


def test_portable_import_decodes_html_snippet_entities_for_text_renderers():
    item = {
        "type": "single_choice",
        "content": "查看如下 HTML 代码：&lt;div style=&quot;float:left;&quot;&gt;文本&lt;/div&gt;",
        "options": [
            "&lt;a href=&quot;url&quot; target=&quot;_blank&quot;&gt;",
            "&amp;lt;pre&amp;gt;...&amp;lt;/pre&amp;gt;",
            "普通文本",
        ],
        "answer": [0],
    }

    internal, errors = portable_question_to_internal(item, scope="question_center")

    assert errors == []
    assert internal["content"] == '查看如下 HTML 代码：<div style="float:left;">文本</div>'
    assert internal["options"] == [
        'A. <a href="url" target="_blank">',
        "B. <pre>...</pre>",
        "C. 普通文本",
    ]


def test_internal_export_normalizes_html_snippets_to_literal_portable_json():
    portable = internal_question_to_portable(
        q_id=1,
        q_type="选择题",
        content="标签&lt;hr/&gt;实现的功能是什么?",
        options=json.dumps(
            [
                "A. &lt;html&gt;",
                "B. &amp;lt;body&amp;gt;",
            ],
            ensure_ascii=False,
        ),
        answer="A",
        explanation="解析：&lt;code&gt;hr&lt;/code&gt;",
        difficulty=1,
        tags=[],
    )

    assert portable["content"] == "标签<hr/>实现的功能是什么?"
    assert portable["options"] == ["<html>", "<body>"]
    assert portable["analysis"] == "解析：<code>hr</code>"
