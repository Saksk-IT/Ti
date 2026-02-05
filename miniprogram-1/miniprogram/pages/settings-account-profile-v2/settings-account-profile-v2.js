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
var api_1 = require("../../utils/api");
var auth_1 = require("../../utils/auth");
var nav_1 = require("../../utils/nav");
var user_settings_1 = require("../../utils/user-settings");
var last_practice_1 = require("../../utils/last-practice");
var theme_1 = require("../../utils/theme");
var avatar_1 = require("../../utils/avatar");
function navTo(key) {
    if (key === 'practice')
        return '/pages/settings-practice-v2/settings-practice-v2';
    if (key === 'theme')
        return '/pages/settings-theme-v2/settings-theme-v2';
    if (key === 'about')
        return '/pages/settings-about-v2/settings-about-v2';
    return '/pages/settings-account-profile-v2/settings-account-profile-v2';
}
function accTo(key) {
    if (key === 'security')
        return '/pages/settings-account-security-v2/settings-account-security-v2';
    if (key === 'bindings')
        return '/pages/settings-account-bindings-v2/settings-account-bindings-v2';
    return '/pages/settings-account-profile-v2/settings-account-profile-v2';
}
function maskEmail(email) {
    var s = (email == null) ? '' : String(email).trim();
    if (!s || !s.includes('@'))
        return s || '未绑定';
    var parts = s.split('@');
    if (parts.length < 2)
        return s;
    var name = parts[0] || '';
    var domain = parts.slice(1).join('@') || '';
    if (!name)
        return "***@".concat(domain);
    if (name.length === 1)
        return "".concat(name, "***@").concat(domain);
    return "".concat(name.slice(0, 2), "***@").concat(domain);
}
function clampLen(s, max) {
    var v = String(s || '');
    if (v.length <= max)
        return v;
    return v.slice(0, max);
}
Page({
    data: {
        drawerOpen: false,
        navKey: 'account',
        accTab: 'profile',
        loading: false,
        saving: false,
        editing: false,
        errorMsg: '',
        msg: '',
        username: '—',
        avatarUrl: '',
        avatarInitial: 'U',
        roleText: '普通用户',
        createdAtText: '—',
        college: '',
        signature: '',
        signatureCount: 0,
        contact: '',
        emailMasked: '未绑定',
        emailBadge: '未绑定',
        passwordBadge: '未设置',
        wechatBadge: '未绑定'
    },
    onLoad: function (options) {
        var qs = ['navKey=account', 'accTab=profile'];
        try {
            var edit = String((options === null || options === void 0 ? void 0 : options.edit) || '');
            if (edit === '1')
                qs.push('edit=1');
        }
        catch (e) { }
        wx.redirectTo({ url: "/pages/settings-center-v2/settings-center-v2?".concat(qs.join('&')) });
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
        if (!this.data.loading)
            this.loadProfile(false);
    },
    onHamburgerTap: function () {
        this.setData({ drawerOpen: true });
    },
    onDrawerClose: function () {
        this.setData({ drawerOpen: false });
    },
    onDrawerNavigate: function (e) {
        var _a, _b;
        var url = (_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.url;
        var navType = (_b = e === null || e === void 0 ? void 0 : e.detail) === null || _b === void 0 ? void 0 : _b.navType;
        this.setData({ drawerOpen: false });
        if (!url)
            return;
        (0, nav_1.safeNavigate)(url, navType);
    },
    onDrawerSelectStyle: function (e) {
        return __awaiter(this, void 0, void 0, function () {
            var style;
            var _a;
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0:
                        style = (((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.style) || 'default');
                        theme_1.themeManager.setStyle(style);
                        this.setData(theme_1.themeManager.getPageData());
                        this.setData({ drawerOpen: false });
                        return [4 /*yield*/, (0, user_settings_1.syncUserSettingsToServer)()];
                    case 1:
                        _b.sent();
                        return [2 /*return*/];
                }
            });
        });
    },
    onPullDownRefresh: function () {
        var _this = this;
        Promise.resolve()
            .then(function () { return __awaiter(_this, void 0, void 0, function () {
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0: return [4 /*yield*/, this.loadProfile(true)];
                    case 1:
                        _a.sent();
                        return [2 /*return*/];
                }
            });
        }); })
            .finally(function () {
            wx.stopPullDownRefresh();
        });
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
        if (url === '/pages/settings-account-profile-v2/settings-account-profile-v2')
            return;
        wx.redirectTo({ url: url });
    },
    onAccountSubTap: function (e) {
        var _a, _b;
        var key = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.key) || '');
        if (!key)
            return;
        var url = accTo(key);
        if (url === '/pages/settings-account-profile-v2/settings-account-profile-v2')
            return;
        wx.redirectTo({ url: url });
    },
    onEdit: function () {
        this.setData({ editing: true, msg: '', errorMsg: '' });
    },
    onCancel: function () {
        var self = this;
        var original = self.__originalProfile || {};
        this.setData({
            editing: false,
            msg: '',
            errorMsg: '',
            college: String(original.college || ''),
            contact: String(original.contact || ''),
            signature: String(original.signature || ''),
            signatureCount: String(original.signature || '').length
        });
    },
    onCollegeInput: function (e) {
        var _a;
        var v = clampLen((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.value, 40);
        this.setData({ college: v });
    },
    onContactInput: function (e) {
        var _a;
        var v = clampLen((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.value, 60);
        this.setData({ contact: v });
    },
    onSignatureInput: function (e) {
        var _a;
        var v = clampLen((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.value, 80);
        this.setData({ signature: v, signatureCount: v.length });
    },
    onSave: function () {
        return __awaiter(this, void 0, void 0, function () {
            var e_1;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (this.data.saving)
                            return [2 /*return*/];
                        this.setData({ saving: true, msg: '', errorMsg: '' });
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 4, 5, 6]);
                        return [4 /*yield*/, api_1.api.updateProfile({
                                college: String(this.data.college || '').trim(),
                                contact: String(this.data.contact || '').trim(),
                                signature: String(this.data.signature || '').trim()
                            })];
                    case 2:
                        _a.sent();
                        this.setData({ editing: false, msg: '已保存' });
                        return [4 /*yield*/, this.loadProfile(true)];
                    case 3:
                        _a.sent();
                        return [3 /*break*/, 6];
                    case 4:
                        e_1 = _a.sent();
                        this.setData({ errorMsg: (e_1 === null || e_1 === void 0 ? void 0 : e_1.message) || '保存失败，请稍后重试' });
                        return [3 /*break*/, 6];
                    case 5:
                        this.setData({ saving: false });
                        return [7 /*endfinally*/];
                    case 6: return [2 /*return*/];
                }
            });
        });
    },
    onAvatarTap: function () {
        return __awaiter(this, void 0, void 0, function () {
            var currentUrl, idx, filePath, res, url, e_2;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (this.data.loading || this.data.saving)
                            return [2 /*return*/];
                        currentUrl = String(this.data.avatarUrl || '').trim();
                        if (!currentUrl) return [3 /*break*/, 2];
                        return [4 /*yield*/, new Promise(function (resolve) {
                                wx.showActionSheet({
                                    itemList: ['预览头像', '更换头像'],
                                    success: function (res) { return resolve(Number(res === null || res === void 0 ? void 0 : res.tapIndex)); },
                                    fail: function () { return resolve(-1); }
                                });
                            })];
                    case 1:
                        idx = _a.sent();
                        if (idx === 0) {
                            wx.previewImage({ urls: [currentUrl], current: currentUrl });
                            return [2 /*return*/];
                        }
                        if (idx !== 1)
                            return [2 /*return*/];
                        _a.label = 2;
                    case 2: return [4 /*yield*/, new Promise(function (resolve) {
                            var pick = wx.chooseMedia ? 'chooseMedia' : 'chooseImage';
                            if (pick === 'chooseMedia') {
                                wx.chooseMedia({
                                    count: 1,
                                    mediaType: ['image'],
                                    sourceType: ['album', 'camera'],
                                    success: function (res) { var _a, _b; return resolve(String(((_b = (_a = res === null || res === void 0 ? void 0 : res.tempFiles) === null || _a === void 0 ? void 0 : _a[0]) === null || _b === void 0 ? void 0 : _b.tempFilePath) || '')); },
                                    fail: function () { return resolve(''); }
                                });
                                return;
                            }
                            wx.chooseImage({
                                count: 1,
                                sizeType: ['compressed'],
                                sourceType: ['album', 'camera'],
                                success: function (res) { var _a; return resolve(String(((_a = res === null || res === void 0 ? void 0 : res.tempFilePaths) === null || _a === void 0 ? void 0 : _a[0]) || '')); },
                                fail: function () { return resolve(''); }
                            });
                        })];
                    case 3:
                        filePath = _a.sent();
                        if (!filePath)
                            return [2 /*return*/];
                        this.setData({ msg: '', errorMsg: '' });
                        wx.showLoading({ title: '上传中…', mask: true });
                        _a.label = 4;
                    case 4:
                        _a.trys.push([4, 7, 8, 9]);
                        return [4 /*yield*/, api_1.api.uploadProfileAvatar(filePath)];
                    case 5:
                        res = _a.sent();
                        (0, avatar_1.bumpAvatarRev)();
                        url = (0, avatar_1.decorateAvatarUrl)((0, api_1.resolveUploadUrl)(res === null || res === void 0 ? void 0 : res.avatar_url));
                        this.setData({ avatarUrl: url, msg: '头像已更新' });
                        return [4 /*yield*/, this.loadProfile(true)];
                    case 6:
                        _a.sent();
                        return [3 /*break*/, 9];
                    case 7:
                        e_2 = _a.sent();
                        wx.showToast({ title: (e_2 === null || e_2 === void 0 ? void 0 : e_2.message) || '上传失败', icon: 'none' });
                        return [3 /*break*/, 9];
                    case 8:
                        wx.hideLoading();
                        return [7 /*endfinally*/];
                    case 9: return [2 /*return*/];
                }
            });
        });
    },
    onAvatarError: function () {
        var url = String(this.data.avatarUrl || '').trim();
        if (!url || !/^https?:\/\//i.test(url)) {
            this.setData({ avatarUrl: '' });
            return;
        }
        var self = this;
        if (self.__avatarDlTried) {
            self.setData({ avatarUrl: '' });
            return;
        }
        self.__avatarDlTried = true;
        wx.downloadFile({
            url: url,
            timeout: 15000,
            success: function (res) {
                var tempFilePath = String((res && res.tempFilePath) || '').trim();
                self.setData({ avatarUrl: tempFilePath || '' });
            },
            fail: function () {
                self.setData({ avatarUrl: '' });
            }
        });
    },
    loadProfile: function () {
        return __awaiter(this, arguments, void 0, function (force) {
            var self, now, lastAt, p, username, avatar, isAdmin, createdAtText, college, contact, signature, emailMasked, emailVerified, hasPasswordSet, wechatBound, emailBadge, passwordBadge, wechatBadge, e_3;
            if (force === void 0) { force = false; }
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (this.data.loading)
                            return [2 /*return*/];
                        self = this;
                        now = Date.now();
                        lastAt = Number(self.__lastLoadedAt || 0) || 0;
                        if (!force && now - lastAt < 8000)
                            return [2 /*return*/];
                        self.__lastLoadedAt = now;
                        this.setData({ loading: true, errorMsg: '' });
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, 4, 5]);
                        return [4 /*yield*/, api_1.api.getProfile()];
                    case 2:
                        p = _a.sent();
                        username = String((p === null || p === void 0 ? void 0 : p.username) || '用户');
                        avatar = (0, avatar_1.decorateAvatarUrl)((0, api_1.resolveUploadUrl)(p === null || p === void 0 ? void 0 : p.avatar));
                        isAdmin = !!(p === null || p === void 0 ? void 0 : p.is_admin);
                        createdAtText = (p === null || p === void 0 ? void 0 : p.created_at) ? "\u6CE8\u518C\u65F6\u95F4 ".concat(String(p.created_at)) : '—';
                        college = String((p === null || p === void 0 ? void 0 : p.college) || '');
                        contact = String((p === null || p === void 0 ? void 0 : p.contact) || '');
                        signature = String((p === null || p === void 0 ? void 0 : p.signature) || '');
                        emailMasked = maskEmail(p === null || p === void 0 ? void 0 : p.email);
                        emailVerified = !!(p === null || p === void 0 ? void 0 : p.email_verified);
                        hasPasswordSet = !!(p === null || p === void 0 ? void 0 : p.has_password_set);
                        wechatBound = !!(p === null || p === void 0 ? void 0 : p.wechat_bound);
                        emailBadge = (p === null || p === void 0 ? void 0 : p.email) ? (emailVerified ? '已验证' : '未验证') : '未绑定';
                        passwordBadge = hasPasswordSet ? '已设置' : '未设置';
                        wechatBadge = wechatBound ? '已绑定' : '未绑定';
                        this.setData({
                            username: username,
                            avatarUrl: avatar,
                            avatarInitial: (username || 'U').charAt(0).toUpperCase(),
                            roleText: isAdmin ? '管理员' : '普通用户',
                            createdAtText: createdAtText,
                            college: college,
                            contact: contact,
                            signature: signature,
                            signatureCount: signature.length,
                            emailMasked: emailMasked || '未绑定',
                            emailBadge: emailBadge,
                            passwordBadge: passwordBadge,
                            wechatBadge: wechatBadge
                        });
                        self.__originalProfile = { college: college, contact: contact, signature: signature };
                        return [3 /*break*/, 5];
                    case 3:
                        e_3 = _a.sent();
                        this.setData({ errorMsg: (e_3 === null || e_3 === void 0 ? void 0 : e_3.message) || '加载失败，请稍后重试' });
                        return [3 /*break*/, 5];
                    case 4:
                        this.setData({ loading: false });
                        return [7 /*endfinally*/];
                    case 5: return [2 /*return*/];
                }
            });
        });
    }
});
