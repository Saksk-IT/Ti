# -*- coding: utf-8 -*-
"""刷题页编辑弹窗删除题目的前端契约测试。"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_web_edit_question_modal_exposes_user_bank_delete_action():
    modal = _read("app/modules/quiz/templates/quiz/partials/quiz/modals/_modals_edit_question.html")
    script = _read("app/modules/quiz/templates/quiz/partials/quiz/assets/js/_03_question_edit.html")

    assert 'id="editQuestionDeleteBtn"' in modal
    assert 'onclick="deleteCurrentQuestionFromEditModal()"' in modal
    assert "function deleteCurrentQuestionFromEditModal()" in script
    assert "if (!IS_USER_BANK || !BANK_ID)" in script
    assert "method: 'DELETE'" in script
    assert "getUserBankApiPrefix()}/questions/${encodeURIComponent(String(qid))}" in script


def test_miniprogram_edit_question_modal_exposes_bank_delete_action():
    wxml = _read("miniprogram-1/miniprogram/pages/quiz/quiz.wxml")
    page_ts = _read("miniprogram-1/miniprogram/pages/quiz/quiz.ts")
    endpoints_ts = _read("miniprogram-1/miniprogram/utils/api-endpoints.ts")
    endpoints_js = _read("miniprogram-1/miniprogram/utils/api-endpoints.js")

    assert 'wx:if="{{sourceType === \'bank\'}}"' in wxml
    assert 'class="edit-delete-btn"' in wxml
    assert 'bindtap="onDeleteQuestion"' in wxml
    assert "editDeleting: false" in page_ts
    assert "async onDeleteQuestion()" in page_ts
    assert "confirmDeleteQuestion()" in page_ts
    assert "saveProgressAfterQuestionDelete" in page_ts
    assert "api.deleteBankQuestion(Number(sourceId), questionId)" in page_ts
    assert "deleteBankQuestion: (bankId: number, questionId: number)" in endpoints_ts
    assert "deleteBankQuestion: function (bankId, questionId)" in endpoints_js
