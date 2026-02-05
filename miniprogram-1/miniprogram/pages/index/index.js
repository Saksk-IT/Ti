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
// index.ts
var api_1 = require("../../utils/api");
var auth_1 = require("../../utils/auth");
var theme_1 = require("../../utils/theme");
function parseQuery(raw) {
    var out = {};
    if (!raw)
        return out;
    var parts = raw.split('&');
    for (var _i = 0, parts_1 = parts; _i < parts_1.length; _i++) {
        var part = parts_1[_i];
        var kv = part.split('=');
        var k = kv[0];
        var v = kv[1];
        if (!k)
            continue;
        out[decodeURIComponent(k)] = decodeURIComponent(v || '');
    }
    return out;
}
function parseCompactBindScene(scene) {
    var s = (scene || '').trim();
    // B + sid(16 hex) + nonce(8 hex)
    if (!/^B[0-9a-fA-F]{24}$/.test(s))
        return null;
    var sid = s.slice(1, 17);
    var nonce = s.slice(17, 25);
    return { sid: sid, nonce: nonce };
}
Page({
    data: {
        stats: {
            total: 0,
            favorites: 0,
            mistakes: 0
        },
        lastSession: null,
        loading: false,
        userInfo: null
    },
    onLoad: function (options) {
        // 兼容后端生成二维码使用 index 作为落地页（避免 41030 invalid page）
        var sid = (options && options.sid ? String(options.sid) : '').trim();
        var nonce = (options && (options.nonce || options.n) ? String(options.nonce || options.n) : '').trim();
        var scene = (options && options.scene ? String(options.scene) : '').trim();
        if ((!sid || !nonce) && scene) {
            var decoded = decodeURIComponent(scene);
            var compactBind = parseCompactBindScene(decoded);
            if (compactBind) {
                wx.navigateTo({
                    url: "/pages/web-bind/web-bind?sid=".concat(encodeURIComponent(compactBind.sid), "&nonce=").concat(encodeURIComponent(compactBind.nonce))
                });
                return;
            }
            var q = parseQuery(decoded);
            sid = (q.sid || '').trim();
            nonce = (q.n || q.nonce || '').trim();
        }
        if (sid && nonce) {
            wx.setStorageSync('pendingWebLogin', { sid: sid, nonce: nonce, ts: Date.now() });
            var token = wx.getStorageSync('token');
            if (token) {
                wx.navigateTo({ url: "/pages/web-login/web-login?sid=".concat(encodeURIComponent(sid), "&nonce=").concat(encodeURIComponent(nonce)) });
            }
            else {
                wx.redirectTo({ url: '/pages/login/login' });
            }
            return;
        }
    },
    onShow: function () {
        // 统一走鉴权&加载，避免 onLoad/onShow 重复触发导致并发请求
        this.checkAuthAndLoad();
    },
    // 检查认证并加载数据
    checkAuthAndLoad: function () {
        return __awaiter(this, void 0, void 0, function () {
            var userInfo;
            return __generator(this, function (_a) {
                if (!(0, auth_1.checkLogin)()) {
                    // 未登录，跳转到登录页（不在首页自动登录，让用户手动登录）
                    console.log('未登录，跳转到登录页');
                    wx.redirectTo({
                        url: '/pages/login/login'
                    });
                    return [2 /*return*/];
                }
                else {
                    userInfo = wx.getStorageSync('userInfo');
                    this.setData({ userInfo: userInfo });
                    this.loadHome();
                }
                return [2 /*return*/];
            });
        });
    },
    // 加载首页数据（统计 + 上次练习）
    loadHome: function () {
        return __awaiter(this, void 0, void 0, function () {
            var results, countData, userCounts, total, favorites, mistakes, remote, local, merged, lastSession, err_1, errorMsg;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        // 再次检查token，确保token存在
                        if (!(0, auth_1.checkLogin)()) {
                            console.log('loadData: token不存在，跳转到登录页');
                            wx.redirectTo({
                                url: '/pages/login/login'
                            });
                            return [2 /*return*/];
                        }
                        this.setData({ loading: true });
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 4, , 5]);
                        return [4 /*yield*/, Promise.all([
                                api_1.api.getQuestionsCount({ subject: 'all' }),
                                api_1.api.getUserCounts({ subject: 'all' })
                            ])];
                    case 2:
                        results = _a.sent();
                        countData = results[0];
                        userCounts = results[1];
                        total = (countData && countData.count) ? countData.count : 0;
                        favorites = (userCounts && userCounts.favorites) ? userCounts.favorites : 0;
                        mistakes = (userCounts && userCounts.mistakes) ? userCounts.mistakes : 0;
                        return [4 /*yield*/, this.safeGetProgress('last_practice_session')];
                    case 3:
                        remote = _a.sent();
                        local = this.safeParseStorage(wx.getStorageSync('last_practice_session'));
                        merged = this.pickLatestSession(local, remote);
                        lastSession = this.normalizeSession(merged);
                        this.setData({
                            stats: { total: total, favorites: favorites, mistakes: mistakes },
                            lastSession: lastSession,
                            loading: false
                        });
                        return [3 /*break*/, 5];
                    case 4:
                        err_1 = _a.sent();
                        console.error('加载数据失败:', err_1);
                        errorMsg = (err_1 && err_1.message) || '加载失败';
                        // 如果是401错误，清除token并跳转到登录页（但不要立即重新登录，避免循环）
                        if (errorMsg.includes('401') || errorMsg.includes('登录') || errorMsg.includes('过期') || errorMsg.includes('unauthorized')) {
                            console.log('401错误，清除token并跳转到登录页');
                            wx.removeStorageSync('token');
                            wx.removeStorageSync('userInfo');
                            // 使用reLaunch避免返回时再次触发
                            wx.reLaunch({
                                url: '/pages/login/login'
                            });
                            return [2 /*return*/];
                        }
                        wx.showToast({ title: errorMsg, icon: 'none' });
                        this.setData({ loading: false });
                        return [3 /*break*/, 5];
                    case 5: return [2 /*return*/];
                }
            });
        });
    },
    safeGetProgress: function (key) {
        return __awaiter(this, void 0, void 0, function () {
            var e_1;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (!key)
                            return [2 /*return*/, null];
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, , 4]);
                        return [4 /*yield*/, api_1.api.getProgress(key)];
                    case 2: return [2 /*return*/, _a.sent()];
                    case 3:
                        e_1 = _a.sent();
                        return [2 /*return*/, null];
                    case 4: return [2 /*return*/];
                }
            });
        });
    },
    safeParseStorage: function (val) {
        if (!val)
            return null;
        if (typeof val === 'string') {
            try {
                return JSON.parse(val);
            }
            catch (e) {
                return null;
            }
        }
        if (typeof val === 'object')
            return val;
        return null;
    },
    pickLatestSession: function (a, b) {
        if (!a && !b)
            return null;
        if (a && !b)
            return a;
        if (!a && b)
            return b;
        var ta = Number(a && a.timestamp) || 0;
        var tb = Number(b && b.timestamp) || 0;
        return tb >= ta ? b : a;
    },
    normalizeSession: function (raw) {
        if (!raw || typeof raw !== 'object')
            return null;
        var subject = (raw.subject || '').toString().trim();
        if (!subject)
            return null;
        var mode = (raw.mode || 'quiz').toString();
        var type = (raw.type || 'all').toString();
        var source = (raw.source || 'all').toString();
        var shuffleQuestions = raw.shuffle_questions === 1 || raw.shuffle_questions === '1' || raw.shuffle_questions === true;
        var shuffleOptions = raw.shuffle_options === 1 || raw.shuffle_options === '1' || raw.shuffle_options === true;
        var timestamp = Number(raw.timestamp) || 0;
        var modeText = mode === 'memo' ? '背题' : '刷题';
        var sourceText = source === 'favorites' ? '收藏' : source === 'mistakes' ? '错题' : '全部';
        var typeText = type === 'all' ? '全部题型' : type;
        var metaText = "".concat(modeText, " \u00B7 ").concat(sourceText, " \u00B7 ").concat(typeText);
        return {
            subject: subject,
            mode: mode,
            type: type,
            source: source,
            shuffleQuestions: shuffleQuestions,
            shuffleOptions: shuffleOptions,
            timestamp: timestamp,
            timeText: this.formatTimestamp(timestamp),
            metaText: metaText
        };
    },
    formatTimestamp: function (ts) {
        var t = Number(ts) || 0;
        if (!t)
            return '';
        try {
            var d = new Date(t);
            var mm = String(d.getMonth() + 1).padStart(2, '0');
            var dd = String(d.getDate()).padStart(2, '0');
            var hh = String(d.getHours()).padStart(2, '0');
            var mi = String(d.getMinutes()).padStart(2, '0');
            return "".concat(mm, "-").concat(dd, " ").concat(hh, ":").concat(mi);
        }
        catch (e) {
            return '';
        }
    },
    onContinueTap: function () {
        var s = this.data.lastSession;
        if (!s || !s.subject) {
            wx.showToast({ title: '暂无上次练习记录', icon: 'none' });
            return;
        }
        var params = [];
        params.push("subject=".concat(encodeURIComponent(s.subject)));
        params.push("mode=".concat(encodeURIComponent(s.mode || 'quiz')));
        if (s.type && s.type !== 'all')
            params.push("type=".concat(encodeURIComponent(s.type)));
        if (s.source && s.source !== 'all')
            params.push("source=".concat(s.source));
        if (s.shuffleQuestions)
            params.push('shuffle_questions=1');
        if (s.shuffleOptions)
            params.push('shuffle_options=1');
        wx.navigateTo({ url: "/pages/quiz/quiz?".concat(params.join('&')) });
    },
    onGoSubjectsTap: function () {
        wx.switchTab({ url: '/pages/subjects/subjects' });
    },
    onToggleThemeTap: function () {
        theme_1.themeManager.cycleMode();
        wx.showToast({ title: "\u4E3B\u9898\uFF1A".concat(theme_1.themeManager.getModeName()), icon: 'none' });
    },
    // 下拉刷新
    onPullDownRefresh: function () {
        this.loadHome().finally(function () { return wx.stopPullDownRefresh(); });
    }
});
