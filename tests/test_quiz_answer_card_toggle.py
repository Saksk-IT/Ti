from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_repo_file(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_web_memo_answer_card_has_toggle_hooks():
    render_js = read_repo_file(
        "app/modules/quiz/templates/quiz/partials/quiz/assets/js/_07_render_show_question.html"
    )
    parity_css = read_repo_file(
        "app/modules/quiz/templates/quiz/partials/quiz/assets/css/_09_mini_program_parity.html"
    )

    assert "data-answer-toggle-card" in render_js
    assert 'data-answer-card-ignore="1"' in render_js
    assert "toggleMemoAnswerCardHidden" in render_js
    assert ".answer-flip-card" in parity_css
    assert ".is-answer-hidden" in parity_css


def test_miniprogram_memo_answer_card_has_toggle_hooks():
    quiz_wxml = read_repo_file("miniprogram-1/miniprogram/pages/quiz/quiz.wxml")
    quiz_js = read_repo_file("miniprogram-1/miniprogram/pages/quiz/quiz.js")

    assert 'bindtap="onToggleMemoAnswerCard"' in quiz_wxml
    assert 'catchtap="onToggleAIExplain"' in quiz_wxml
    assert 'catchtap="previewImage"' in quiz_wxml
    assert "memoAnswerHidden ? 'is-hidden' : ''" in quiz_wxml
    assert "onToggleMemoAnswerCard" in quiz_js
    assert "toggleAnswerCardHidden" in quiz_js
