from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROFILE_DIR = ROOT / "miniprogram-1" / "miniprogram" / "pages" / "settings-account-profile-v2"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_account_profile_page_allows_editing_nickname():
    wxml = _read(PROFILE_DIR / "settings-account-profile-v2.wxml")
    ts = _read(PROFILE_DIR / "settings-account-profile-v2.ts")
    js = _read(PROFILE_DIR / "settings-account-profile-v2.js")

    assert 'value="{{username}}"' in wxml
    assert 'disabled="{{!editing}}"' in wxml
    assert 'bindinput="onUsernameInput"' in wxml
    assert 'maxlength="8"' in wxml
    assert "当前不支持在此页修改" not in wxml

    assert "onUsernameInput(e: any)" in ts
    assert "validateProfileNickname" in ts
    assert "const usernameChanged = username !== originalUsername;" in ts
    assert "if (usernameChanged) {" in ts
    assert "username: String(this.data.username || '').trim()" in ts
    assert "strict_nickname: true" in ts
    assert "wx.setStorageSync('userInfo'" in ts

    assert "onUsernameInput: function (e)" in js
    assert "usernameChanged = username !== originalUsername" in js
    assert "if (usernameChanged) {" in js
    assert "username: String(this.data.username || '').trim()" in js
    assert "strict_nickname: true" in js
