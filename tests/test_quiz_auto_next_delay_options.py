from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MINI_QUIZ_TS = ROOT / "miniprogram-1/miniprogram/pages/quiz/quiz.ts"
MINI_QUIZ_JS = ROOT / "miniprogram-1/miniprogram/pages/quiz/quiz.js"
MINI_QUIZ_WXML = ROOT / "miniprogram-1/miniprogram/pages/quiz/quiz.wxml"
WEB_FAB_JS = ROOT / "app/modules/quiz/templates/quiz/partials/quiz/assets/js/_05_core_state_fab.html"
WEB_CHECK_JS = ROOT / "app/modules/quiz/templates/quiz/partials/quiz/assets/js/_08_check_answer.html"
WEB_SETTINGS_JS = ROOT / "app/modules/quiz/templates/quiz/partials/quiz/assets/js/_09_settings_modal.html"
WEB_FEATURES_HTML = ROOT / "app/modules/quiz/templates/quiz/partials/quiz/modals/_modals_features.html"


def test_miniprogram_auto_next_delay_has_three_user_options():
    ts = MINI_QUIZ_TS.read_text(encoding="utf-8")
    js = MINI_QUIZ_JS.read_text(encoding="utf-8")
    wxml = MINI_QUIZ_WXML.read_text(encoding="utf-8")

    assert "AUTO_NEXT_DELAY_OPTIONS" in ts
    assert "{ key: 'fast', label: '快', delay: 150 }" in ts
    assert "{ key: 'normal', label: '标准', delay: 350 }" in ts
    assert "{ key: 'slow', label: '慢', delay: 650 }" in ts
    assert "getAutoNextDelayMs()" in ts
    assert "return found ? found.delay : 150;" in ts
    assert "{ key: 'fast', label: '快', delay: 150 }" in js
    assert "{ key: 'normal', label: '标准', delay: 350 }" in js
    assert "{ key: 'slow', label: '慢', delay: 650 }" in js
    assert "return found ? found.delay : 150;" in js
    assert "autoNextDelayKey" in ts
    assert "bindtap=\"onAutoNextDelaySelect\"" in wxml


def test_web_auto_next_delay_has_matching_user_options():
    fab_js = WEB_FAB_JS.read_text(encoding="utf-8")
    settings_js = WEB_SETTINGS_JS.read_text(encoding="utf-8")
    check_js = WEB_CHECK_JS.read_text(encoding="utf-8")
    html = WEB_FEATURES_HTML.read_text(encoding="utf-8")

    assert "AUTO_NEXT_DELAY_OPTIONS" in fab_js
    assert "{ key: 'fast', label: '快', delay: 150 }" in fab_js
    assert "{ key: 'normal', label: '标准', delay: 350 }" in fab_js
    assert "{ key: 'slow', label: '慢', delay: 650 }" in fab_js
    assert "getAutoNextDelayMs()" in fab_js
    assert "return found ? found.delay : 150;" in fab_js
    assert "onFeatureAutoNextDelaySelect('fast')" in html
    assert "syncFeatureAutoNextDelayUI()" in settings_js
    assert "getAutoNextDelayMs()" in check_js
    assert "}, 350)" not in check_js
    assert "}, 500)" not in check_js
