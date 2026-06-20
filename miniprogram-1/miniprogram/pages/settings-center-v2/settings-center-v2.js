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
var api_1 = require("../../utils/api");
var auth_1 = require("../../utils/auth");
var user_settings_1 = require("../../utils/user-settings");
var last_practice_1 = require("../../utils/last-practice");
var theme_1 = require("../../utils/theme");
var font_1 = require("../../utils/font");
var avatar_1 = require("../../utils/avatar");
var typed_set_data_1 = require("../../utils/typed-set-data");
function normalizeNavKey(raw) {
    var v = String(raw || '').trim().toLowerCase();
    if (v === 'practice' || v === 'theme' || v === 'about')
        return v;
    return 'account';
}
function normalizeAccTab(raw) {
    var v = String(raw || '').trim().toLowerCase();
    if (v === 'security' || v === 'bindings')
        return v;
    return 'profile';
}
function normalizeAboutTab(raw) {
    var v = String(raw || '').trim().toLowerCase();
    return v === 'legal' ? 'legal' : 'app';
}
function maskEmail(email) {
    var s = email == null ? '' : String(email).trim();
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
function isStrongPassword(pwd) {
    var v = String(pwd || '');
    if (v.length < 8)
        return false;
    return /[a-zA-Z]/.test(v) && /\d/.test(v);
}
function validateEmail(email) {
    var v = String(email || '').trim();
    var emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!v)
        return { ok: false, msg: '请输入邮箱地址' };
    if (!emailRegex.test(v))
        return { ok: false, msg: '邮箱格式不正确' };
    return { ok: true, value: v };
}
function summarizeUsername() {
    var userInfo = (wx.getStorageSync('userInfo') || {});
    var name = String(userInfo.username || userInfo.name || userInfo.email || '').trim();
    return name || '已登录';
}
function bumpScrollTop(n) {
    var v = Number(n || 0) || 0;
    return v === 0 ? 1 : 0;
}
var _ps = new WeakMap();
function _p(ctx) {
    var s = _ps.get(ctx);
    if (!s) {
        s = {};
        _ps.set(ctx, s);
    }
    return s;
}
Page({
    data: {
        navKey: 'account',
        accTab: 'profile',
        aboutTab: 'app',
        scrollTop: 0,
        profileMounted: true,
        securityMounted: false,
        bindingsMounted: false,
        practiceMounted: false,
        themeMounted: false,
        aboutMounted: false,
        profile: {
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
        security: {
            loading: false,
            submitting: false,
            errorMsg: '',
            msg: '',
            hasPasswordSet: false,
            pwdChip: '-',
            pwdSub: '用于修改或设置登录密码。',
            submitText: '提交',
            currentPassword: '',
            newPassword: '',
            confirmPassword: '',
            showCurrent: false,
            showNew: false,
            showConfirm: false
        },
        bindings: {
            loading: false,
            errorMsg: '',
            msg: '',
            emailChip: '-',
            emailDesc: '加载中…',
            emailActionText: '绑定',
            emailFormOpen: false,
            bindEmail: '',
            bindCode: '',
            sendingCode: false,
            countdown: 0,
            sendCodeText: '发送验证码',
            sendCodeDisabled: false,
            bindingEmail: false,
            wechatBound: false,
            wechatChip: '-',
            wechatDesc: '加载中…',
            bindingWechat: false,
            unbindingWechat: false
        },
        practice: { msg: '' },
        theme: { msg: '' },
        font: { msg: '' },
        // 字体样式相关
        fontStyle: 'system',
        fontStyleClass: '',
        fontStyleName: '系统默认',
        fontStyleList: Object.values(font_1.FONT_STYLE_CONFIG),
        about: {
            errorMsg: '',
            contactOpen: false,
            currentUsername: '—',
            adminUsername: '',
            adminEmail: '',
            adminWechat: '',
            chatDisabled: true,
            chatDisabledReason: ''
        }
    },
    onLoad: function (options) {
        var navKey = normalizeNavKey((options === null || options === void 0 ? void 0 : options.navKey) || (options === null || options === void 0 ? void 0 : options.nav) || (options === null || options === void 0 ? void 0 : options.tab));
        var accTab = normalizeAccTab((options === null || options === void 0 ? void 0 : options.accTab) || (options === null || options === void 0 ? void 0 : options.acc) || (options === null || options === void 0 ? void 0 : options.sub));
        var aboutTab = normalizeAboutTab((options === null || options === void 0 ? void 0 : options.aboutTab) || (options === null || options === void 0 ? void 0 : options.about));
        var patch = { navKey: navKey, accTab: accTab, aboutTab: aboutTab };
        if (navKey === 'practice')
            patch.practiceMounted = true;
        if (navKey === 'theme')
            patch.themeMounted = true;
        if (navKey === 'about')
            patch.aboutMounted = true;
        if (navKey === 'account') {
            if (accTab === 'profile')
                patch.profileMounted = true;
            if (accTab === 'security')
                patch.securityMounted = true;
            if (accTab === 'bindings')
                patch.bindingsMounted = true;
        }
        (0, typed_set_data_1.typedSetData)(this, patch);
        try {
            var edit = String((options === null || options === void 0 ? void 0 : options.edit) || '');
            if (edit === '1' && navKey === 'account' && accTab === 'profile') {
                (0, typed_set_data_1.typedSetData)(this, { 'profile.editing': true });
            }
        }
        catch (e) { }
    },
    onShow: function () {
        if (!(0, auth_1.checkLogin)()) {
            wx.redirectTo({ url: '/pages/login/login' });
            return;
        }
        try {
            (0, typed_set_data_1.typedSetData)(this, theme_1.themeManager.getPageData());
            (0, typed_set_data_1.typedSetData)(this, font_1.fontManager.getPageData());
        }
        catch (e) { }
        this.ensureTabLoaded(false);
    },
    onUnload: function () {
        this.clearCountdown();
    },
    onPullDownRefresh: function () {
        var _this = this;
        Promise.resolve()
            .then(function () { return __awaiter(_this, void 0, void 0, function () {
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0: return [4 /*yield*/, this.ensureTabLoaded(true)];
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
    ensureTabLoaded: function (force) {
        if (force === void 0) { force = false; }
        var navKey = this.data.navKey;
        if (navKey === 'account')
            return this.loadAccountSummary(force);
        if (navKey === 'about')
            return this.loadAboutInfo(force);
        if (navKey === 'theme' && !this.data.themeMounted)
            (0, typed_set_data_1.typedSetData)(this, { themeMounted: true });
        if (navKey === 'practice' && !this.data.practiceMounted)
            (0, typed_set_data_1.typedSetData)(this, { practiceMounted: true });
        return Promise.resolve();
    },
    resetScroll: function () {
        (0, typed_set_data_1.typedSetData)(this, { scrollTop: bumpScrollTop(this.data.scrollTop) });
    },
    onToggleDarkTap: function () {
        theme_1.themeManager.toggleDark();
        (0, typed_set_data_1.typedSetData)(this, theme_1.themeManager.getPageData());
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
        var key = normalizeNavKey((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.key);
        if (!key || key === this.data.navKey)
            return;
        var patch = { navKey: key };
        if (key === 'practice')
            patch.practiceMounted = true;
        if (key === 'theme')
            patch.themeMounted = true;
        if (key === 'about')
            patch.aboutMounted = true;
        if (key === 'account') {
            var acc = this.data.accTab;
            if (acc === 'profile')
                patch.profileMounted = true;
            if (acc === 'security')
                patch.securityMounted = true;
            if (acc === 'bindings')
                patch.bindingsMounted = true;
        }
        (0, typed_set_data_1.typedSetData)(this, patch);
        this.resetScroll();
        this.ensureTabLoaded(false);
    },
    onAccountSubTap: function (e) {
        var _a, _b;
        var key = normalizeAccTab((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.key);
        if (!key)
            return;
        if (this.data.navKey !== 'account')
            (0, typed_set_data_1.typedSetData)(this, { navKey: 'account' });
        if (key === this.data.accTab)
            return;
        var patch = { accTab: key };
        if (key === 'profile')
            patch.profileMounted = true;
        if (key === 'security')
            patch.securityMounted = true;
        if (key === 'bindings')
            patch.bindingsMounted = true;
        (0, typed_set_data_1.typedSetData)(this, patch);
        this.resetScroll();
        this.loadAccountSummary(false);
    },
    // ========== 账号：资料 ==========
    onEdit: function () {
        (0, typed_set_data_1.typedSetData)(this, { 'profile.editing': true, 'profile.msg': '', 'profile.errorMsg': '' });
    },
    onCancel: function () {
        var original = _p(this).originalProfile || {};
        var signature = String(original.signature || '');
        (0, typed_set_data_1.typedSetData)(this, {
            'profile.editing': false,
            'profile.msg': '',
            'profile.errorMsg': '',
            'profile.college': String(original.college || ''),
            'profile.contact': String(original.contact || ''),
            'profile.signature': signature,
            'profile.signatureCount': signature.length
        });
    },
    onCollegeInput: function (e) {
        var _a;
        var v = clampLen((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.value, 40);
        (0, typed_set_data_1.typedSetData)(this, { 'profile.college': v });
    },
    onContactInput: function (e) {
        var _a;
        var v = clampLen((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.value, 60);
        (0, typed_set_data_1.typedSetData)(this, { 'profile.contact': v });
    },
    onSignatureInput: function (e) {
        var _a;
        var v = clampLen((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.value, 80);
        (0, typed_set_data_1.typedSetData)(this, { 'profile.signature': v, 'profile.signatureCount': v.length });
    },
    onSave: function () {
        return __awaiter(this, void 0, void 0, function () {
            var saving, e_1;
            var _a, _b, _c, _d;
            return __generator(this, function (_e) {
                switch (_e.label) {
                    case 0:
                        saving = !!((_a = this.data.profile) === null || _a === void 0 ? void 0 : _a.saving);
                        if (saving)
                            return [2 /*return*/];
                        (0, typed_set_data_1.typedSetData)(this, { 'profile.saving': true, 'profile.msg': '', 'profile.errorMsg': '' });
                        _e.label = 1;
                    case 1:
                        _e.trys.push([1, 4, 5, 6]);
                        return [4 /*yield*/, api_1.api.updateProfile({
                                college: String(((_b = this.data.profile) === null || _b === void 0 ? void 0 : _b.college) || '').trim(),
                                contact: String(((_c = this.data.profile) === null || _c === void 0 ? void 0 : _c.contact) || '').trim(),
                                signature: String(((_d = this.data.profile) === null || _d === void 0 ? void 0 : _d.signature) || '').trim()
                            })];
                    case 2:
                        _e.sent();
                        (0, typed_set_data_1.typedSetData)(this, { 'profile.editing': false, 'profile.msg': '已保存' });
                        return [4 /*yield*/, this.loadAccountSummary(true)];
                    case 3:
                        _e.sent();
                        return [3 /*break*/, 6];
                    case 4:
                        e_1 = _e.sent();
                        (0, typed_set_data_1.typedSetData)(this, { 'profile.errorMsg': (e_1 === null || e_1 === void 0 ? void 0 : e_1.message) || '保存失败，请稍后重试' });
                        return [3 /*break*/, 6];
                    case 5:
                        (0, typed_set_data_1.typedSetData)(this, { 'profile.saving': false });
                        return [7 /*endfinally*/];
                    case 6: return [2 /*return*/];
                }
            });
        });
    },
    onAvatarTap: function () {
        return __awaiter(this, void 0, void 0, function () {
            var p, currentUrl, idx, filePath, res, url, e_2;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        p = this.data.profile || {};
                        if (p.loading || p.saving)
                            return [2 /*return*/];
                        currentUrl = String(p.avatarUrl || '').trim();
                        if (!currentUrl) return [3 /*break*/, 2];
                        return [4 /*yield*/, new Promise(function (resolve) {
                                wx.showActionSheet({
                                    itemList: ['预览头像', '更换头像'],
                                    success: function (res) { return resolve(Number(res.tapIndex)); },
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
                            if (wx.chooseMedia) {
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
                                success: function (res) { var _a; return resolve(String(((_a = res.tempFilePaths) === null || _a === void 0 ? void 0 : _a[0]) || '')); },
                                fail: function () { return resolve(''); }
                            });
                        })];
                    case 3:
                        filePath = _a.sent();
                        if (!filePath)
                            return [2 /*return*/];
                        (0, typed_set_data_1.typedSetData)(this, { 'profile.msg': '', 'profile.errorMsg': '' });
                        wx.showLoading({ title: '上传中…', mask: true });
                        _a.label = 4;
                    case 4:
                        _a.trys.push([4, 7, 8, 9]);
                        return [4 /*yield*/, api_1.api.uploadProfileAvatar(filePath)];
                    case 5:
                        res = _a.sent();
                        (0, avatar_1.bumpAvatarRev)();
                        url = (0, avatar_1.decorateAvatarUrl)((0, api_1.resolveUploadUrl)(res === null || res === void 0 ? void 0 : res.avatar_url));
                        (0, typed_set_data_1.typedSetData)(this, { 'profile.avatarUrl': url, 'profile.msg': '头像已更新' });
                        return [4 /*yield*/, this.loadAccountSummary(true)];
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
        var _this = this;
        var _a;
        var url = String(((_a = this.data.profile) === null || _a === void 0 ? void 0 : _a.avatarUrl) || '').trim();
        if (!url || !/^https?:\/\//i.test(url)) {
            (0, typed_set_data_1.typedSetData)(this, { 'profile.avatarUrl': '' });
            return;
        }
        var priv = _p(this);
        if (priv.avatarDlTried) {
            (0, typed_set_data_1.typedSetData)(this, { 'profile.avatarUrl': '' });
            return;
        }
        priv.avatarDlTried = true;
        wx.downloadFile({
            url: url,
            timeout: 15000,
            success: function (res) {
                var tempFilePath = String((res && res.tempFilePath) || '').trim();
                (0, typed_set_data_1.typedSetData)(_this, { 'profile.avatarUrl': tempFilePath || '' });
            },
            fail: function () {
                (0, typed_set_data_1.typedSetData)(_this, { 'profile.avatarUrl': '' });
            }
        });
    },
    // ========== 账号：安全 ==========
    onToggleShow: function (e) {
        var _a, _b;
        var target = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.target) || '');
        var sec = this.data.security || {};
        if (target === 'current')
            (0, typed_set_data_1.typedSetData)(this, { 'security.showCurrent': !sec.showCurrent });
        if (target === 'new')
            (0, typed_set_data_1.typedSetData)(this, { 'security.showNew': !sec.showNew });
        if (target === 'confirm')
            (0, typed_set_data_1.typedSetData)(this, { 'security.showConfirm': !sec.showConfirm });
    },
    onCurrentInput: function (e) {
        var _a;
        (0, typed_set_data_1.typedSetData)(this, { 'security.currentPassword': String(((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.value) || '') });
    },
    onNewInput: function (e) {
        var _a;
        (0, typed_set_data_1.typedSetData)(this, { 'security.newPassword': String(((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.value) || '') });
    },
    onConfirmInput: function (e) {
        var _a;
        (0, typed_set_data_1.typedSetData)(this, { 'security.confirmPassword': String(((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.value) || '') });
    },
    onReset: function () {
        var _a;
        var submitting = !!((_a = this.data.security) === null || _a === void 0 ? void 0 : _a.submitting);
        if (submitting)
            return;
        (0, typed_set_data_1.typedSetData)(this, {
            'security.msg': '',
            'security.errorMsg': '',
            'security.currentPassword': '',
            'security.newPassword': '',
            'security.confirmPassword': ''
        });
    },
    onSubmit: function () {
        return __awaiter(this, void 0, void 0, function () {
            var sec, isSetPassword, cur, nw, c, res, e_3;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        sec = this.data.security || {};
                        if (sec.submitting)
                            return [2 /*return*/];
                        (0, typed_set_data_1.typedSetData)(this, { 'security.submitting': true, 'security.msg': '', 'security.errorMsg': '' });
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 6, 7, 8]);
                        isSetPassword = !sec.hasPasswordSet;
                        cur = String(sec.currentPassword || '');
                        nw = String(sec.newPassword || '');
                        c = String(sec.confirmPassword || '');
                        if (!nw || !c)
                            throw new Error('请填写新密码');
                        if (nw !== c)
                            throw new Error('两次输入的密码不一致');
                        if (!isStrongPassword(nw))
                            throw new Error('密码至少 8 位且包含字母和数字');
                        if (isSetPassword && cur)
                            throw new Error('设置密码不需要输入当前密码');
                        if (!isSetPassword && !cur)
                            throw new Error('修改密码需要输入当前密码');
                        return [4 /*yield*/, api_1.api.updateProfilePassword({
                                current_password: cur,
                                new_password: nw,
                                is_set_password: isSetPassword
                            })];
                    case 2:
                        res = _a.sent();
                        if (!isSetPassword) return [3 /*break*/, 4];
                        wx.showToast({ title: res.message || '密码设置成功', icon: 'none' });
                        (0, typed_set_data_1.typedSetData)(this, {
                            'security.currentPassword': '',
                            'security.newPassword': '',
                            'security.confirmPassword': '',
                            'security.msg': res.message || '密码设置成功'
                        });
                        return [4 /*yield*/, this.loadAccountSummary(true)];
                    case 3:
                        _a.sent();
                        return [2 /*return*/];
                    case 4: return [4 /*yield*/, new Promise(function (resolve) {
                            wx.showModal({
                                title: '修改成功',
                                content: '为保证安全，需要重新登录。',
                                showCancel: false,
                                confirmText: '去登录',
                                success: function () { return resolve(); }
                            });
                        })];
                    case 5:
                        _a.sent();
                        (0, auth_1.logout)();
                        wx.redirectTo({ url: '/pages/login/login' });
                        return [3 /*break*/, 8];
                    case 6:
                        e_3 = _a.sent();
                        (0, typed_set_data_1.typedSetData)(this, { 'security.errorMsg': (e_3 === null || e_3 === void 0 ? void 0 : e_3.message) || '操作失败，请稍后重试' });
                        return [3 /*break*/, 8];
                    case 7:
                        (0, typed_set_data_1.typedSetData)(this, { 'security.submitting': false });
                        return [7 /*endfinally*/];
                    case 8: return [2 /*return*/];
                }
            });
        });
    },
    // ========== 账号：绑定 ==========
    onEmailActionTap: function () {
        var _a;
        if ((_a = this.data.bindings) === null || _a === void 0 ? void 0 : _a.loading)
            return;
        (0, typed_set_data_1.typedSetData)(this, { 'bindings.msg': '', 'bindings.errorMsg': '', 'bindings.emailFormOpen': true });
    },
    onCloseEmailFormTap: function () {
        var _a;
        if ((_a = this.data.bindings) === null || _a === void 0 ? void 0 : _a.bindingEmail)
            return;
        this.clearCountdown();
        (0, typed_set_data_1.typedSetData)(this, { 'bindings.emailFormOpen': false, 'bindings.bindEmail': '', 'bindings.bindCode': '' });
    },
    onBindEmailInput: function (e) {
        var _a;
        (0, typed_set_data_1.typedSetData)(this, { 'bindings.bindEmail': String(((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.value) || '') });
    },
    onBindCodeInput: function (e) {
        var _a;
        (0, typed_set_data_1.typedSetData)(this, { 'bindings.bindCode': String(((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.value) || '') });
    },
    getSendCodeText: function () {
        var b = this.data.bindings || {};
        if (b.sendingCode)
            return '发送中…';
        if (b.countdown > 0)
            return "\u91CD\u53D1(".concat(b.countdown, "s)");
        return '发送验证码';
    },
    refreshSendCodeUi: function () {
        var b = this.data.bindings || {};
        (0, typed_set_data_1.typedSetData)(this, {
            'bindings.sendCodeText': this.getSendCodeText(),
            'bindings.sendCodeDisabled': !!b.sendingCode || Number(b.countdown || 0) > 0
        });
    },
    clearCountdown: function () {
        var priv = _p(this);
        if (priv.countdownTimer) {
            clearTimeout(priv.countdownTimer);
            priv.countdownTimer = null;
        }
        (0, typed_set_data_1.typedSetData)(this, { 'bindings.countdown': 0, 'bindings.sendingCode': false });
        this.refreshSendCodeUi();
    },
    tickCountdown: function () {
        var _this = this;
        var _a;
        var priv = _p(this);
        var next = Math.max(0, Number(((_a = this.data.bindings) === null || _a === void 0 ? void 0 : _a.countdown) || 0) - 1);
        (0, typed_set_data_1.typedSetData)(this, { 'bindings.countdown': next });
        this.refreshSendCodeUi();
        if (next <= 0) {
            priv.countdownTimer = null;
            return;
        }
        priv.countdownTimer = setTimeout(function () { return _this.tickCountdown(); }, 1000);
    },
    onSendCodeTap: function () {
        return __awaiter(this, void 0, void 0, function () {
            var b, v, res, tip, e_4;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        b = this.data.bindings || {};
                        if (b.sendingCode || b.countdown > 0)
                            return [2 /*return*/];
                        v = validateEmail(b.bindEmail);
                        if (!v.ok) {
                            (0, typed_set_data_1.typedSetData)(this, { 'bindings.errorMsg': v.msg || '邮箱格式不正确' });
                            return [2 /*return*/];
                        }
                        (0, typed_set_data_1.typedSetData)(this, { 'bindings.sendingCode': true, 'bindings.msg': '', 'bindings.errorMsg': '' });
                        this.refreshSendCodeUi();
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, 4, 5]);
                        return [4 /*yield*/, api_1.api.sendEmailBindCode(v.value)];
                    case 2:
                        res = _a.sent();
                        tip = String((res === null || res === void 0 ? void 0 : res.message) || '验证码已发送');
                        wx.showToast({ title: tip, icon: 'none' });
                        (0, typed_set_data_1.typedSetData)(this, { 'bindings.msg': tip, 'bindings.countdown': 60 });
                        this.refreshSendCodeUi();
                        this.tickCountdown();
                        return [3 /*break*/, 5];
                    case 3:
                        e_4 = _a.sent();
                        (0, typed_set_data_1.typedSetData)(this, { 'bindings.errorMsg': (e_4 === null || e_4 === void 0 ? void 0 : e_4.message) || '发送失败，请稍后重试' });
                        this.clearCountdown();
                        return [3 /*break*/, 5];
                    case 4:
                        (0, typed_set_data_1.typedSetData)(this, { 'bindings.sendingCode': false });
                        this.refreshSendCodeUi();
                        return [7 /*endfinally*/];
                    case 5: return [2 /*return*/];
                }
            });
        });
    },
    onBindEmailTap: function () {
        return __awaiter(this, void 0, void 0, function () {
            var b, v, code, e_5;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        b = this.data.bindings || {};
                        if (b.bindingEmail)
                            return [2 /*return*/];
                        v = validateEmail(b.bindEmail);
                        if (!v.ok) {
                            (0, typed_set_data_1.typedSetData)(this, { 'bindings.errorMsg': v.msg || '邮箱格式不正确' });
                            return [2 /*return*/];
                        }
                        code = String(b.bindCode || '').trim();
                        if (!code || code.length !== 6) {
                            (0, typed_set_data_1.typedSetData)(this, { 'bindings.errorMsg': '请输入 6 位验证码' });
                            return [2 /*return*/];
                        }
                        (0, typed_set_data_1.typedSetData)(this, { 'bindings.bindingEmail': true, 'bindings.msg': '', 'bindings.errorMsg': '' });
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 4, 5, 6]);
                        return [4 /*yield*/, api_1.api.bindEmail(v.value, code)];
                    case 2:
                        _a.sent();
                        wx.showToast({ title: '邮箱绑定成功', icon: 'none' });
                        this.clearCountdown();
                        (0, typed_set_data_1.typedSetData)(this, { 'bindings.emailFormOpen': false, 'bindings.bindEmail': '', 'bindings.bindCode': '', 'bindings.msg': '邮箱绑定成功' });
                        return [4 /*yield*/, this.loadAccountSummary(true)];
                    case 3:
                        _a.sent();
                        return [3 /*break*/, 6];
                    case 4:
                        e_5 = _a.sent();
                        (0, typed_set_data_1.typedSetData)(this, { 'bindings.errorMsg': (e_5 === null || e_5 === void 0 ? void 0 : e_5.message) || '绑定失败，请稍后重试' });
                        return [3 /*break*/, 6];
                    case 5:
                        (0, typed_set_data_1.typedSetData)(this, { 'bindings.bindingEmail': false });
                        return [7 /*endfinally*/];
                    case 6: return [2 /*return*/];
                }
            });
        });
    },
    onWechatBindTap: function () {
        return __awaiter(this, void 0, void 0, function () {
            var b, code, res, e_6;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        b = this.data.bindings || {};
                        if (b.bindingWechat)
                            return [2 /*return*/];
                        (0, typed_set_data_1.typedSetData)(this, { 'bindings.bindingWechat': true, 'bindings.msg': '', 'bindings.errorMsg': '' });
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 5, 6, 7]);
                        return [4 /*yield*/, new Promise(function (resolve) {
                                wx.login({
                                    success: function (res) { return resolve(String(res.code || '')); },
                                    fail: function () { return resolve(''); }
                                });
                            })];
                    case 2:
                        code = _a.sent();
                        if (!code)
                            throw new Error('获取微信登录 code 失败');
                        return [4 /*yield*/, api_1.api.miniWechatBind(code)];
                    case 3:
                        res = _a.sent();
                        if (res && res.token)
                            wx.setStorageSync('token', res.token);
                        if (res && res.user_info)
                            wx.setStorageSync('userInfo', res.user_info);
                        wx.showToast({ title: '绑定成功', icon: 'none' });
                        (0, typed_set_data_1.typedSetData)(this, { 'bindings.msg': '绑定成功' });
                        return [4 /*yield*/, this.loadAccountSummary(true)];
                    case 4:
                        _a.sent();
                        return [3 /*break*/, 7];
                    case 5:
                        e_6 = _a.sent();
                        (0, typed_set_data_1.typedSetData)(this, { 'bindings.errorMsg': (e_6 === null || e_6 === void 0 ? void 0 : e_6.message) || '绑定失败，请稍后重试' });
                        return [3 /*break*/, 7];
                    case 6:
                        (0, typed_set_data_1.typedSetData)(this, { 'bindings.bindingWechat': false });
                        return [7 /*endfinally*/];
                    case 7: return [2 /*return*/];
                }
            });
        });
    },
    onWechatUnbindTap: function () {
        return __awaiter(this, void 0, void 0, function () {
            var b, ok, e_7;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        b = this.data.bindings || {};
                        if (b.unbindingWechat)
                            return [2 /*return*/];
                        return [4 /*yield*/, new Promise(function (resolve) {
                                wx.showModal({
                                    title: '确认解绑微信',
                                    content: '解绑后将无法使用微信一键登录。为保证安全，需要重新登录。',
                                    confirmText: '解绑',
                                    cancelText: '取消',
                                    success: function (res) { return resolve(!!res.confirm); },
                                    fail: function () { return resolve(false); }
                                });
                            })];
                    case 1:
                        ok = _a.sent();
                        if (!ok)
                            return [2 /*return*/];
                        (0, typed_set_data_1.typedSetData)(this, { 'bindings.unbindingWechat': true, 'bindings.msg': '', 'bindings.errorMsg': '' });
                        _a.label = 2;
                    case 2:
                        _a.trys.push([2, 5, 6, 7]);
                        return [4 /*yield*/, api_1.api.wechatUnbind()];
                    case 3:
                        _a.sent();
                        return [4 /*yield*/, new Promise(function (resolve) {
                                wx.showModal({
                                    title: '解绑成功',
                                    content: '需要重新登录。',
                                    showCancel: false,
                                    confirmText: '去登录',
                                    success: function () { return resolve(); }
                                });
                            })];
                    case 4:
                        _a.sent();
                        (0, auth_1.logout)();
                        wx.redirectTo({ url: '/pages/login/login' });
                        return [3 /*break*/, 7];
                    case 5:
                        e_7 = _a.sent();
                        (0, typed_set_data_1.typedSetData)(this, { 'bindings.errorMsg': (e_7 === null || e_7 === void 0 ? void 0 : e_7.message) || '解绑失败，请稍后重试' });
                        return [3 /*break*/, 7];
                    case 6:
                        (0, typed_set_data_1.typedSetData)(this, { 'bindings.unbindingWechat': false });
                        return [7 /*endfinally*/];
                    case 7: return [2 /*return*/];
                }
            });
        });
    },
    // ========== 主题 ==========
    onStyleTap: function (e) {
        return __awaiter(this, void 0, void 0, function () {
            var style;
            var _a, _b;
            return __generator(this, function (_c) {
                switch (_c.label) {
                    case 0:
                        style = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.style) || 'default');
                        theme_1.themeManager.setStyle(style);
                        (0, typed_set_data_1.typedSetData)(this, theme_1.themeManager.getPageData());
                        return [4 /*yield*/, (0, user_settings_1.syncUserSettingsToServer)()];
                    case 1:
                        _c.sent();
                        (0, typed_set_data_1.typedSetData)(this, { 'theme.msg': '已应用并尝试同步到云端' });
                        return [2 /*return*/];
                }
            });
        });
    },
    // ========== 字体 ==========
    onFontStyleTap: function (e) {
        var _a, _b;
        var style = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.style) || 'system');
        font_1.fontManager.setStyle(style);
        (0, typed_set_data_1.typedSetData)(this, font_1.fontManager.getPageData());
        var config = font_1.FONT_STYLE_CONFIG[style];
        (0, typed_set_data_1.typedSetData)(this, { 'font.msg': "\u5DF2\u5207\u6362\u5230\u300C".concat(config.name, "\u300D\u5B57\u4F53") });
    },
    // ========== 关于 ==========
    onAboutTabTap: function (e) {
        var _a, _b;
        var tab = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.tab) || '').toLowerCase();
        var next = tab === 'legal' ? 'legal' : 'app';
        if (next === this.data.aboutTab)
            return;
        (0, typed_set_data_1.typedSetData)(this, { aboutTab: next });
        this.resetScroll();
    },
    onToggleContact: function () {
        var _a;
        var open = !!((_a = this.data.about) === null || _a === void 0 ? void 0 : _a.contactOpen);
        (0, typed_set_data_1.typedSetData)(this, { 'about.contactOpen': !open });
    },
    onGoProfile: function () {
        (0, typed_set_data_1.typedSetData)(this, { navKey: 'account', accTab: 'profile', profileMounted: true });
        this.resetScroll();
        this.loadAccountSummary(false);
    },
    onContactChat: function () {
        var a = this.data.about || {};
        if (a.chatDisabled) {
            wx.showToast({ title: a.chatDisabledReason || '暂不可用', icon: 'none' });
            return;
        }
        wx.showToast({ title: '小程序暂不支持站内聊天，请在 Web 端打开 /contact_admin', icon: 'none' });
    },
    onCopy: function (e) {
        var _a, _b;
        var v = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.value) || '').trim();
        if (!v)
            return;
        wx.setClipboardData({
            data: v,
            success: function () { return wx.showToast({ title: '已复制', icon: 'none' }); },
            fail: function () { return wx.showToast({ title: '复制失败', icon: 'none' }); }
        });
    },
    onOpenTerms: function () {
        wx.showToast({ title: '协议页待复刻，可先在 Web 端查看 /terms', icon: 'none' });
    },
    onOpenPrivacy: function () {
        wx.showToast({ title: '协议页待复刻，可先在 Web 端查看 /privacy', icon: 'none' });
    },
    loadAboutInfo: function () {
        return __awaiter(this, arguments, void 0, function (force) {
            var priv, now, lastAt, res, e_8;
            if (force === void 0) { force = false; }
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        priv = _p(this);
                        now = Date.now();
                        lastAt = Number(priv.aboutLastLoadedAt || 0) || 0;
                        if (!force && lastAt && now - lastAt < 8000) {
                            (0, typed_set_data_1.typedSetData)(this, { 'about.currentUsername': summarizeUsername() });
                            return [2 /*return*/];
                        }
                        priv.aboutLastLoadedAt = now;
                        (0, typed_set_data_1.typedSetData)(this, { 'about.errorMsg': '', 'about.currentUsername': summarizeUsername() });
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, , 4]);
                        return [4 /*yield*/, api_1.api.getSettingsAbout()];
                    case 2:
                        res = _a.sent();
                        (0, typed_set_data_1.typedSetData)(this, {
                            'about.adminUsername': String((res === null || res === void 0 ? void 0 : res.admin_username) || ''),
                            'about.adminEmail': String((res === null || res === void 0 ? void 0 : res.admin_email) || ''),
                            'about.adminWechat': String((res === null || res === void 0 ? void 0 : res.admin_wechat) || ''),
                            'about.chatDisabled': !!(res === null || res === void 0 ? void 0 : res.chat_disabled),
                            'about.chatDisabledReason': String((res === null || res === void 0 ? void 0 : res.chat_disabled_reason) || '')
                        });
                        return [3 /*break*/, 4];
                    case 3:
                        e_8 = _a.sent();
                        (0, typed_set_data_1.typedSetData)(this, { 'about.errorMsg': (e_8 === null || e_8 === void 0 ? void 0 : e_8.message) || '加载失败，请稍后重试' });
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        });
    },
    buildSecurityMode: function (hasPasswordSet) {
        var isSetPassword = !hasPasswordSet;
        return {
            hasPasswordSet: hasPasswordSet,
            pwdChip: hasPasswordSet ? '已设置密码' : '未设置密码',
            pwdSub: hasPasswordSet ? '修改登录密码。修改成功后需要重新登录。' : '为账号设置登录密码（首次设置无需填写当前密码）。',
            submitText: isSetPassword ? '设置密码' : '修改密码'
        };
    },
    buildBindingsProfile: function (p) {
        var email = String((p === null || p === void 0 ? void 0 : p.email) || '').trim();
        var verified = !!(p === null || p === void 0 ? void 0 : p.email_verified);
        var emailChip = email ? (verified ? '已绑定' : '已绑定(未验证)') : '未绑定';
        var emailDesc = email ? "\u5F53\u524D\u90AE\u7BB1\uFF1A".concat(email).concat(verified ? '' : '（未验证）') : '绑定邮箱用于接收验证码与找回账号。';
        var emailActionText = email ? '更换' : '绑定';
        var wechatBound = !!(p === null || p === void 0 ? void 0 : p.wechat_bound);
        var wechatChip = wechatBound ? '已绑定' : '未绑定';
        var wechatDesc = wechatBound ? '已绑定微信，可使用微信一键登录。' : '绑定微信后可使用微信一键登录。';
        return { wechatBound: wechatBound, emailChip: emailChip, emailDesc: emailDesc, emailActionText: emailActionText, wechatChip: wechatChip, wechatDesc: wechatDesc };
    },
    loadAccountSummary: function () {
        return __awaiter(this, arguments, void 0, function (force) {
            var priv, now, lastAt, p, username, avatar, isAdmin, createdAtText, college, contact, signature, emailMasked, emailVerified, hasPasswordSet, wechatBound, emailBadge, passwordBadge, wechatBadge, e_9, err;
            if (force === void 0) { force = false; }
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        priv = _p(this);
                        now = Date.now();
                        lastAt = Number(priv.accountLastLoadedAt || 0) || 0;
                        if (!force && lastAt && now - lastAt < 8000)
                            return [2 /*return*/];
                        priv.accountLastLoadedAt = now;
                        if (!this.data.profileMounted)
                            (0, typed_set_data_1.typedSetData)(this, { profileMounted: true });
                        if (this.data.navKey === 'account') {
                            if (this.data.accTab === 'security' && !this.data.securityMounted)
                                (0, typed_set_data_1.typedSetData)(this, { securityMounted: true });
                            if (this.data.accTab === 'bindings' && !this.data.bindingsMounted)
                                (0, typed_set_data_1.typedSetData)(this, { bindingsMounted: true });
                        }
                        (0, typed_set_data_1.typedSetData)(this, {
                            'profile.loading': true,
                            'security.loading': true,
                            'bindings.loading': true,
                            'profile.errorMsg': '',
                            'security.errorMsg': '',
                            'bindings.errorMsg': ''
                        });
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
                        (0, typed_set_data_1.typedSetData)(this, {
                            profile: __assign(__assign({}, this.data.profile), { username: username, avatarUrl: avatar || '/images/default-avatar.png', avatarInitial: (username || 'U').charAt(0).toUpperCase(), roleText: isAdmin ? '管理员' : '普通用户', createdAtText: createdAtText, college: college, contact: contact, signature: signature, signatureCount: signature.length, emailMasked: emailMasked || '未绑定', emailBadge: emailBadge, passwordBadge: passwordBadge, wechatBadge: wechatBadge }),
                            security: __assign(__assign({}, this.data.security), this.buildSecurityMode(hasPasswordSet)),
                            bindings: __assign(__assign({}, this.data.bindings), this.buildBindingsProfile(p))
                        });
                        priv.originalProfile = { college: college, contact: contact, signature: signature };
                        this.refreshSendCodeUi();
                        return [3 /*break*/, 5];
                    case 3:
                        e_9 = _a.sent();
                        err = (e_9 === null || e_9 === void 0 ? void 0 : e_9.message) || '加载失败，请稍后重试';
                        (0, typed_set_data_1.typedSetData)(this, {
                            'profile.errorMsg': err,
                            'security.errorMsg': err,
                            'bindings.errorMsg': err,
                            security: __assign(__assign({}, this.data.security), this.buildSecurityMode(false)),
                            bindings: __assign(__assign({}, this.data.bindings), this.buildBindingsProfile({}))
                        });
                        this.refreshSendCodeUi();
                        return [3 /*break*/, 5];
                    case 4:
                        (0, typed_set_data_1.typedSetData)(this, { 'profile.loading': false, 'security.loading': false, 'bindings.loading': false });
                        return [7 /*endfinally*/];
                    case 5: return [2 /*return*/];
                }
            });
        });
    }
});
