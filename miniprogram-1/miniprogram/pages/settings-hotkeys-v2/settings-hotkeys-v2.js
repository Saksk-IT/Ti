"use strict";
var __assign = (this && this.__assign) || function () {
    __assign = Object.assign || function(t) {
        for (var s, i = 1, n = arguments.length; i < n; i++) {
            s = arguments[i];
            for (var p in s) if (Object.prototype.hasOwnProperty.call(s, p))
                t[p] = s[p];
        }
        return t;
    };
    return __assign.apply(this, arguments);
};
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
var __generator = (this && this.__generator) || function (thisArg, body) {
    var _ = { label: 0, sent: function() { if (t[0] & 1) throw t[1]; return t[1]; }, trys: [], ops: [] }, f, y, t, g;
    return g = { next: verb(0), "throw": verb(1), "return": verb(2) }, typeof Symbol === "function" && (g[Symbol.iterator] = function() { return this; }), g;
    function verb(n) { return function (v) { return step([n, v]); }; }
    function step(op) {
        if (f) throw new TypeError("Generator is already executing.");
        while (g && (g = 0, op[0] && (_ = 0)), _) try {
            if (f = 1, y && (t = op[0] & 2 ? y["return"] : op[0] ? y["throw"] || ((t = y["return"]) && t.call(y), 0) : y.next) && !(t = t.call(y, op[1])).done) return t;
            if (y = 0, t) op = [op[0] & 2, t.value];
            switch (op[0]) {
                case 0: case 1: t = op; break;
                case 4: _.label++; return { value: op[1], done: false };
                case 5: _.label++; y = op[1]; op = [0]; continue;
                case 7: op = _.ops.pop(); _.trys.pop(); continue;
                default:
                    if (!(t = _.trys, t = t.length > 0 && t[t.length - 1]) && (op[0] === 6 || op[0] === 2)) { _ = 0; continue; }
                    if (op[0] === 3 && (!t || (op[1] > t[0] && op[1] < t[3]))) { _.label = op[1]; break; }
                    if (op[0] === 6 && _.label < t[1]) { _.label = t[1]; t = op; break; }
                    if (t && _.label < t[2]) { _.label = t[2]; _.ops.push(op); break; }
                    if (t[2]) _.ops.pop();
                    _.trys.pop(); continue;
            }
            op = body.call(thisArg, _);
        } catch (e) { op = [6, e]; y = 0; } finally { f = t = 0; }
        if (op[0] & 5) throw op[1]; return { value: op[0] ? op[1] : void 0, done: true };
    }
};
Object.defineProperty(exports, "__esModule", { value: true });
var auth_1 = require("../../utils/auth");
var last_practice_1 = require("../../utils/last-practice");
var user_settings_1 = require("../../utils/user-settings");
var theme_1 = require("../../utils/theme");
var QUIZ_HOTKEYS_KEY = 'quiz_hotkeys_v1';
var DEFAULT_QUIZ_HOTKEYS = {
    prev_question: 'ArrowLeft',
    next_question: 'ArrowRight',
    toggle_favorite: 'KeyF',
    choose_option_1: 'Digit1',
    choose_option_2: 'Digit2',
    choose_option_3: 'Digit3',
    choose_option_4: 'Digit4',
    blank_prev: 'ArrowUp',
    blank_next: 'ArrowDown',
    submit_or_next: 'Enter'
};
var HOTKEY_DEFS = [
    { key: 'prev_question', label: '上一题', desc: '切换到上一题' },
    { key: 'next_question', label: '下一题', desc: '切换到下一题' },
    { key: 'toggle_favorite', label: '收藏/取消收藏', desc: '切换题目收藏状态' },
    { key: 'choose_option_1', label: '选择选项 1', desc: '选择题/判断题：选第 1 个选项（A/对）' },
    { key: 'choose_option_2', label: '选择选项 2', desc: '选择题：选第 2 个选项（B/错）' },
    { key: 'choose_option_3', label: '选择选项 3', desc: '选择题：选第 3 个选项（C）' },
    { key: 'choose_option_4', label: '选择选项 4', desc: '选择题：选第 4 个选项（D）' },
    { key: 'blank_prev', label: '填空上一个挖空', desc: '填空题输入框：聚焦时切到上一个空' },
    { key: 'blank_next', label: '填空下一个挖空', desc: '填空题输入框：聚焦时切到下一个空' },
    { key: 'submit_or_next', label: '提交/查看结果/下一题', desc: '等同 Enter 行为（避免与输入换行冲突）' }
];
function navTo(key) {
    if (key === 'account')
        return '/pages/settings-account-profile-v2/settings-account-profile-v2';
    if (key === 'theme')
        return '/pages/settings-theme-v2/settings-theme-v2';
    if (key === 'about')
        return '/pages/settings-about-v2/settings-about-v2';
    return '/pages/settings-hotkeys-v2/settings-hotkeys-v2';
}
function safeParseStorage(raw) {
    if (!raw)
        return null;
    if (typeof raw === 'object')
        return raw;
    var s = String(raw || '').trim();
    if (!s)
        return null;
    if (s.startsWith('{') || s.startsWith('[')) {
        try {
            return JSON.parse(s);
        }
        catch (e) {
            return null;
        }
    }
    return null;
}
function readHotkeys() {
    try {
        var raw = wx.getStorageSync(QUIZ_HOTKEYS_KEY);
        var js_1 = safeParseStorage(raw);
        if (!js_1 || typeof js_1 !== 'object' || Array.isArray(js_1))
            return __assign({}, DEFAULT_QUIZ_HOTKEYS);
        var out_1 = __assign({}, DEFAULT_QUIZ_HOTKEYS);
        Object.keys(DEFAULT_QUIZ_HOTKEYS).forEach(function (k) {
            if (typeof js_1[k] !== 'undefined')
                out_1[k] = String(js_1[k] || '').trim();
        });
        return out_1;
    }
    catch (e) {
        return __assign({}, DEFAULT_QUIZ_HOTKEYS);
    }
}
function writeHotkeys(hk) {
    try {
        wx.setStorageSync(QUIZ_HOTKEYS_KEY, hk);
    }
    catch (e) { }
}
function partToDisplay(part) {
    var p = String(part || '').trim();
    if (!p)
        return '';
    if (p === 'Ctrl' || p === 'Alt' || p === 'Shift' || p === 'Meta')
        return p;
    if (p === 'ArrowLeft')
        return '←';
    if (p === 'ArrowRight')
        return '→';
    if (p === 'ArrowUp')
        return '↑';
    if (p === 'ArrowDown')
        return '↓';
    if (p === 'Enter')
        return 'Enter';
    if (p === 'Space')
        return '空格';
    if (p.startsWith('Key') && p.length === 4)
        return p.slice(3);
    if (p.startsWith('Digit') && p.length === 6)
        return p.slice(5);
    return p;
}
function hotkeyToDisplay(code) {
    var raw = String(code || '').trim();
    if (!raw)
        return '—';
    var parts = raw.split('+').map(function (x) { return partToDisplay(x); }).filter(Boolean);
    return parts.length ? parts.join(' + ') : raw;
}
function buildRows() {
    var hk = readHotkeys();
    return HOTKEY_DEFS.map(function (def) { return (__assign(__assign({}, def), { display: hotkeyToDisplay(hk[def.key]) })); });
}
Page({
    data: {
        navKey: 'hotkeys',
        msg: '',
        hotkeyRows: []
    },
    onShow: function () {
        if (!(0, auth_1.checkLogin)()) {
            wx.redirectTo({ url: '/pages/login/login' });
            return;
        }
        try {
            this.setData(theme_1.themeManager.getPageData());
        }
        catch (e) { }
        this.refreshRows();
    },
    refreshRows: function () {
        this.setData({ hotkeyRows: buildRows() });
    },
    onCycleThemeModeTap: function () {
        var mode = theme_1.themeManager.cycleMode();
        this.setData(__assign(__assign({}, theme_1.themeManager.getPageData()), { themeMode: mode }));
    },
    onContinueLast: function () {
        var url = (0, last_practice_1.buildLastPracticeUrl)();
        if (!url) {
            wx.showToast({ title: '暂无上次练习记录', icon: 'none' });
            return;
        }
        wx.navigateTo({ url: url });
    },
    onSettingsNavTap: function (e) {
        var _a, _b;
        var key = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.key) || '');
        if (!key)
            return;
        var url = navTo(key);
        if (url === '/pages/settings-hotkeys-v2/settings-hotkeys-v2')
            return;
        wx.redirectTo({ url: url });
    },
    onResetDefault: function () {
        return __awaiter(this, void 0, void 0, function () {
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        writeHotkeys(__assign({}, DEFAULT_QUIZ_HOTKEYS));
                        this.refreshRows();
                        this.setData({ msg: '已恢复默认，并尝试同步到云端' });
                        return [4 /*yield*/, (0, user_settings_1.syncUserSettingsToServer)()];
                    case 1:
                        _a.sent();
                        return [2 /*return*/];
                }
            });
        });
    },
    onSyncNow: function () {
        return __awaiter(this, void 0, void 0, function () {
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0: return [4 /*yield*/, (0, user_settings_1.syncUserSettingsToServer)()];
                    case 1:
                        _a.sent();
                        this.setData({ msg: '已尝试同步到云端' });
                        return [2 /*return*/];
                }
            });
        });
    }
});
