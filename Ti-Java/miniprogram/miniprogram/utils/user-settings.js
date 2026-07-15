"use strict";
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
    var _ = { label: 0, sent: function() { if (t[0] & 1) throw t[1]; return t[1]; }, trys: [], ops: [] }, f, y, t, g = Object.create((typeof Iterator === "function" ? Iterator : Object).prototype);
    return g.next = verb(0), g["throw"] = verb(1), g["return"] = verb(2), typeof Symbol === "function" && (g[Symbol.iterator] = function() { return this; }), g;
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
exports.syncUserSettingsFromServer = syncUserSettingsFromServer;
exports.syncUserSettingsToServer = syncUserSettingsToServer;
var api_1 = require("./api");
var theme_1 = require("./theme");
var SETTINGS_SYNC_KEY = 'user_settings_v1';
var SETTINGS_UPDATED_AT_KEY = 'settings_updated_at';
// 与 Web localStorage 约定保持一致（跨端同步在 user_settings_v1 中完成）
var HOME_VISIBLE_SUBJECTS_KEY = 'home_visible_subjects';
var QUIZ_HOTKEYS_KEY = 'quiz_hotkeys_v1';
var QUIZ_FAB_ENABLED_KEY = 'quiz_fab_enabled_v1';
var QUIZ_LAYOUT_THEME_KEY = 'quiz_layout_theme_v1';
function getLocalUpdatedAt() {
    var raw = wx.getStorageSync(SETTINGS_UPDATED_AT_KEY);
    var n = Number(raw);
    return Number.isFinite(n) ? n : 0;
}
function setLocalUpdatedAt(ts) {
    var n = Number(ts);
    if (!Number.isFinite(n) || n <= 0)
        return;
    wx.setStorageSync(SETTINGS_UPDATED_AT_KEY, String(Math.floor(n)));
}
function normalizeThemeStyle(v) {
    var s = String(v || '').trim();
    if (s === 'mist' || s === 'dune' || s === 'pine' || s === 'celadon' || s === 'default')
        return s;
    return null;
}
function normalizeStringArray(v) {
    var arr = Array.isArray(v) ? v : [];
    return arr
        .map(function (x) { return String(x || '').trim(); })
        .filter(function (x) { return !!x; });
}
function readStorageJson(key) {
    try {
        var raw = wx.getStorageSync(key);
        if (raw == null || raw === '')
            return null;
        if (typeof raw === 'object')
            return raw;
        var s = String(raw);
        if (!s)
            return null;
        if (s.trim().startsWith('{') || s.trim().startsWith('[')) {
            return JSON.parse(s);
        }
        return s;
    }
    catch (e) {
        return null;
    }
}
function writeStorageJson(key, value) {
    try {
        wx.setStorageSync(key, value);
    }
    catch (e) { }
}
function getHomeVisibleSubjects() {
    var v = readStorageJson(HOME_VISIBLE_SUBJECTS_KEY);
    return normalizeStringArray(v);
}
function setHomeVisibleSubjects(names) {
    writeStorageJson(HOME_VISIBLE_SUBJECTS_KEY, normalizeStringArray(names));
}
function isQuizFabEnabled() {
    try {
        var raw = wx.getStorageSync(QUIZ_FAB_ENABLED_KEY);
        if (raw === '' || raw == null)
            return true;
        var s = String(raw).trim();
        if (s === '0' || s === 'false' || s === 'off' || s === 'no')
            return false;
        return true;
    }
    catch (e) {
        return true;
    }
}
function setQuizFabEnabled(on) {
    try {
        wx.setStorageSync(QUIZ_FAB_ENABLED_KEY, on ? '1' : '0');
    }
    catch (e) { }
}
function getQuizLayoutTheme() {
    try {
        var raw = wx.getStorageSync(QUIZ_LAYOUT_THEME_KEY);
        var s = String(raw || '').trim().toLowerCase();
        return s === 'card' ? 'card' : 'traditional';
    }
    catch (e) {
        return 'traditional';
    }
}
function setQuizLayoutTheme(theme) {
    var t = String(theme || '').trim().toLowerCase() === 'card' ? 'card' : 'traditional';
    try {
        wx.setStorageSync(QUIZ_LAYOUT_THEME_KEY, t);
    }
    catch (e) { }
}
function getQuizHotkeys() {
    var v = readStorageJson(QUIZ_HOTKEYS_KEY);
    if (v && typeof v === 'object' && !Array.isArray(v))
        return v;
    return {};
}
function setQuizHotkeys(obj) {
    if (!obj || typeof obj !== 'object' || Array.isArray(obj))
        return;
    writeStorageJson(QUIZ_HOTKEYS_KEY, obj);
}
function syncUserSettingsFromServer() {
    return __awaiter(this, void 0, void 0, function () {
        var remote, remoteTs, localTs, style, e_1;
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0:
                    _a.trys.push([0, 4, , 5]);
                    return [4 /*yield*/, api_1.api.getProgress(SETTINGS_SYNC_KEY)];
                case 1:
                    remote = (_a.sent());
                    if (!remote || typeof remote !== 'object')
                        return [2 /*return*/];
                    remoteTs = Number(remote.updated_at || 0) || 0;
                    localTs = getLocalUpdatedAt();
                    if (remoteTs > localTs) {
                        style = normalizeThemeStyle(remote.app_theme_style_v1);
                        if (style)
                            theme_1.themeManager.setStyle(style);
                        setHomeVisibleSubjects(remote.home_visible_subjects || []);
                        if (typeof remote.quiz_fab_enabled_v1 !== 'undefined')
                            setQuizFabEnabled(!!remote.quiz_fab_enabled_v1);
                        if (typeof remote.quiz_layout_theme_v1 === 'string')
                            setQuizLayoutTheme(remote.quiz_layout_theme_v1);
                        if (remote.quiz_hotkeys_v1 && typeof remote.quiz_hotkeys_v1 === 'object')
                            setQuizHotkeys(remote.quiz_hotkeys_v1);
                        setLocalUpdatedAt(remoteTs);
                        return [2 /*return*/];
                    }
                    if (!(localTs > remoteTs)) return [3 /*break*/, 3];
                    return [4 /*yield*/, syncUserSettingsToServer()];
                case 2:
                    _a.sent();
                    _a.label = 3;
                case 3: return [3 /*break*/, 5];
                case 4:
                    e_1 = _a.sent();
                    return [3 /*break*/, 5];
                case 5: return [2 /*return*/];
            }
        });
    });
}
function syncUserSettingsToServer() {
    return __awaiter(this, void 0, void 0, function () {
        var payload, e_2;
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0:
                    _a.trys.push([0, 2, , 3]);
                    payload = {
                        version: 1,
                        home_visible_subjects: getHomeVisibleSubjects(),
                        quiz_hotkeys_v1: getQuizHotkeys(),
                        quiz_fab_enabled_v1: isQuizFabEnabled(),
                        quiz_layout_theme_v1: getQuizLayoutTheme(),
                        app_theme_style_v1: theme_1.themeManager.getStyle(),
                        updated_at: Date.now()
                    };
                    setLocalUpdatedAt(payload.updated_at || 0);
                    return [4 /*yield*/, api_1.api.saveProgress(SETTINGS_SYNC_KEY, payload)];
                case 1:
                    _a.sent();
                    return [3 /*break*/, 3];
                case 2:
                    e_2 = _a.sent();
                    return [3 /*break*/, 3];
                case 3: return [2 /*return*/];
            }
        });
    });
}
