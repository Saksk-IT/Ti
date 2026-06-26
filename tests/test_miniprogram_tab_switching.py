import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MINI_ROOT = ROOT / "miniprogram-1" / "miniprogram"
TAB_PAGES = [
    "pages/hub-v2/hub-v2",
    "pages/public-bank-v2/public-bank-v2",
    "pages/my-banks-v2/my-banks-v2",
    "pages/campus/campus",
    "pages/mine/mine",
]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_miniprogram_uses_custom_tabbar_for_switch_transition():
    app_config = json.loads(_read(MINI_ROOT / "app.json"))
    tab_bar = app_config["tabBar"]

    assert tab_bar["custom"] is True
    assert [item["pagePath"] for item in tab_bar["list"]] == TAB_PAGES

    tabbar_dir = MINI_ROOT / "custom-tab-bar"
    for name in ["index.json", "index.wxml", "index.less", "index.ts", "index.js"]:
        assert (tabbar_dir / name).exists()

    tabbar_wxml = _read(tabbar_dir / "index.wxml")
    tabbar_ts = _read(tabbar_dir / "index.ts")
    assert "tab-route-cover" in tabbar_wxml
    assert "wx.switchTab" in tabbar_ts
    assert "SWITCH_DELAY_MS" in tabbar_ts


def test_miniprogram_tab_pages_keep_themed_background_during_switch():
    for page in TAB_PAGES:
        page_json = json.loads(_read(MINI_ROOT / f"{page}.json"))
        assert page_json["backgroundColor"] == "@backgroundColor"
        assert page_json["backgroundColorTop"] == "@backgroundColor"
        assert page_json["backgroundColorBottom"] == "@backgroundColor"
        assert page_json["backgroundColorContent"] == "@backgroundColor"

    hub_less = _read(MINI_ROOT / "pages/hub-v2/hub-v2.less")
    assert "transform: translateX(100%)" not in hub_less
    assert "padding-bottom: calc(164rpx + env(safe-area-inset-bottom))" in hub_less

    app_less = _read(MINI_ROOT / "app.less")
    page_block = re.search(r"page\s*\{(?P<body>.*?)\n\}", app_less, re.S)
    assert page_block
    assert "background: var(--app-bg);" in page_block.group("body")
    assert "background: transparent;" not in page_block.group("body")
