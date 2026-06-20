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
var api_endpoints_1 = require("../../utils/api-endpoints");
var auth_1 = require("../../utils/auth");
var nav_1 = require("../../utils/nav");
var theme_1 = require("../../utils/theme");
function formatDateLabel(input) {
    var raw = String(input || '').trim();
    if (!raw)
        return '-';
    // iOS 对 YYYY-MM-DD HH:mm:ss 兼容较差，统一替换为 YYYY/MM/DD
    var normalized = raw.replace(/-/g, '/');
    var d = new Date(normalized);
    if (Number.isFinite(d.getTime())) {
        var y = d.getFullYear();
        var m_1 = String(d.getMonth() + 1).padStart(2, '0');
        var day = String(d.getDate()).padStart(2, '0');
        return "".concat(y, "-").concat(m_1, "-").concat(day);
    }
    var m = normalized.match(/^(\d{4})[\/-](\d{2})[\/-](\d{2})/);
    if (m)
        return "".concat(m[1], "-").concat(m[2], "-").concat(m[3]);
    return raw;
}
Page({
    data: {
        loading: false,
        inited: false,
        banks: [],
        keyword: '',
        typeFilter: '', // ''=全部
        sortIndex: 0,
        sortLabels: ['最新发布', '最受欢迎', '题目最多'],
        sortValues: ['newest', 'popular', 'questions'],
        page: 1,
        perPage: 20,
        total: 0,
        shownTotal: 0,
        hasMore: true
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
        if (!this.data.inited && !this.data.loading) {
            this.loadBanks(true);
        }
    },
    loadBanks: function () {
        return __awaiter(this, arguments, void 0, function (reset) {
            var that, reqSeq, nextPage, sortValues, sort, params, keyword, res, rawBanks, total, mapped, merged, existing, seen_1, shownTotal, hasMore, e_1;
            if (reset === void 0) { reset = false; }
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        // reset（筛选/搜索/排序）时允许并发请求：用序号丢弃旧响应，避免“闪烁/回跳”。
                        if (this.data.loading && !reset)
                            return [2 /*return*/];
                        if (!reset && !this.data.hasMore)
                            return [2 /*return*/];
                        that = this;
                        that._bankReqSeq = Number(that._bankReqSeq || 0) + 1;
                        reqSeq = that._bankReqSeq;
                        nextPage = reset ? 1 : Number(this.data.page || 1) || 1;
                        this.setData({ loading: true });
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, 4, 5]);
                        sortValues = this.data.sortValues || ['newest', 'popular', 'questions'];
                        sort = (sortValues[this.data.sortIndex] || 'newest');
                        params = {
                            page: nextPage,
                            per_page: this.data.perPage || 20,
                            sort: sort,
                            type: this.data.typeFilter || ''
                        };
                        keyword = String(this.data.keyword || '').trim();
                        if (keyword)
                            params.keyword = keyword;
                        return [4 /*yield*/, api_1.api.getPublicBanks(params)];
                    case 2:
                        res = _a.sent();
                        if (reqSeq !== that._bankReqSeq)
                            return [2 /*return*/];
                        rawBanks = Array.isArray(res === null || res === void 0 ? void 0 : res.banks) ? res.banks : [];
                        total = Number((res === null || res === void 0 ? void 0 : res.total) || 0) || 0;
                        mapped = (rawBanks || [])
                            .map(function (b) {
                            var bankType = (b === null || b === void 0 ? void 0 : b.bank_type) === 'system' ? 'system' : 'user';
                            var id = Number((b === null || b === void 0 ? void 0 : b.id) || 0) || 0;
                            var name = String((b === null || b === void 0 ? void 0 : b.name) || '').trim();
                            var description = String((b === null || b === void 0 ? void 0 : b.description) || '').trim();
                            var questionCount = Number((b === null || b === void 0 ? void 0 : b.question_count) || 0) || 0;
                            var useCount = Number((b === null || b === void 0 ? void 0 : b.use_count) || 0) || 0;
                            var allowCopy = !!(b === null || b === void 0 ? void 0 : b.allow_copy);
                            var isShared = !!(b === null || b === void 0 ? void 0 : b.is_shared);
                            var coverUrl = (0, api_endpoints_1.resolveUploadUrl)(b === null || b === void 0 ? void 0 : b.cover_image);
                            var isJoined = !!(b && b.relation && b.relation.is_joined);
                            var ownerLabel = String((b === null || b === void 0 ? void 0 : b.owner_nickname) || (bankType === 'system' ? '系统管理员' : '匿名')).trim();
                            var createdLabel = formatDateLabel((b === null || b === void 0 ? void 0 : b.created_at) || (b === null || b === void 0 ? void 0 : b.public_at));
                            return {
                                key: "".concat(bankType, "_").concat(id),
                                id: id,
                                name: name,
                                description: description,
                                question_count: questionCount,
                                use_count: useCount,
                                allow_copy: allowCopy,
                                cover_url: coverUrl,
                                has_cover: !!coverUrl,
                                owner_label: ownerLabel,
                                created_label: createdLabel,
                                bank_type: bankType,
                                type_label: bankType === 'system' ? '系统题库' : '用户',
                                is_shared: isShared,
                                is_joined: isJoined
                            };
                        })
                            .filter(function (b) { return b.id > 0 && !!b.name; });
                        merged = [];
                        if (reset) {
                            merged = mapped;
                        }
                        else {
                            existing = (this.data.banks || []);
                            seen_1 = new Set(existing.map(function (x) { return x.key; }));
                            merged = existing.concat(mapped.filter(function (x) { return !seen_1.has(x.key); }));
                        }
                        shownTotal = merged.length;
                        hasMore = shownTotal < total;
                        this.setData({
                            inited: true,
                            banks: merged,
                            total: total,
                            shownTotal: shownTotal,
                            hasMore: hasMore,
                            page: nextPage + 1
                        });
                        return [3 /*break*/, 5];
                    case 3:
                        e_1 = _a.sent();
                        if (reqSeq !== that._bankReqSeq)
                            return [2 /*return*/];
                        if (reset) {
                            this.setData({ banks: [], total: 0, shownTotal: 0, hasMore: false, page: 1 });
                        }
                        wx.showToast({ title: (e_1 && e_1.message) || '加载失败', icon: 'none' });
                        return [3 /*break*/, 5];
                    case 4:
                        if (reqSeq !== that._bankReqSeq)
                            return [2 /*return*/];
                        this.setData({ loading: false });
                        return [7 /*endfinally*/];
                    case 5: return [2 /*return*/];
                }
            });
        });
    },
    scheduleReload: function () {
        var that = this;
        try {
            if (that._kwTimer)
                clearTimeout(that._kwTimer);
        }
        catch (e) { }
        that._kwTimer = setTimeout(function () {
            that._kwTimer = null;
            that.setData({ page: 1, hasMore: true }, function () { return that.loadBanks(true); });
        }, 250);
    },
    onKeywordInput: function (e) {
        var _this = this;
        var keyword = (e && e.detail && e.detail.value) ? String(e.detail.value) : '';
        this.setData({ keyword: keyword }, function () { return _this.scheduleReload(); });
    },
    onClearKeyword: function () {
        var _this = this;
        this.setData({ keyword: '' }, function () { return _this.loadBanks(true); });
    },
    onTypeTap: function (e) {
        var _this = this;
        var _a, _b, _c;
        var next = String((_c = (_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.type) !== null && _c !== void 0 ? _c : '').trim();
        var typeFilter = next === 'system' ? 'system' : next === 'user' ? 'user' : '';
        this.setData({ typeFilter: typeFilter, page: 1, hasMore: true }, function () { return _this.loadBanks(true); });
    },
    onSortChange: function (e) {
        var _this = this;
        var _a, _b;
        var idx = Number((_b = (_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.value) !== null && _b !== void 0 ? _b : 0) || 0;
        var max = (this.data.sortLabels || []).length - 1;
        var sortIndex = Math.max(0, Math.min(idx, max));
        this.setData({ sortIndex: sortIndex, page: 1, hasMore: true }, function () { return _this.loadBanks(true); });
    },
    onScrollToLower: function () {
        if (this.data.loading)
            return;
        if (!this.data.hasMore)
            return;
        this.loadBanks(false);
    },
    onBankTap: function (e) {
        var _a, _b, _c, _d, _e, _f;
        var id = Number(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.id) || 0);
        var bankType = String(((_d = (_c = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _c === void 0 ? void 0 : _c.dataset) === null || _d === void 0 ? void 0 : _d.bankType) || '').trim();
        var name = (_f = (_e = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _e === void 0 ? void 0 : _e.dataset) === null || _f === void 0 ? void 0 : _f.name;
        if (!Number.isFinite(id) || id <= 0)
            return;
        if (bankType === 'system') {
            var params = [];
            params.push("id=".concat(id));
            if (name)
                params.push("subject=".concat(encodeURIComponent(String(name))));
            (0, nav_1.safeNavigate)("/pages/subject-detail-v2/subject-detail-v2?".concat(params.join('&')), 'navigateTo');
            return;
        }
        (0, nav_1.safeNavigate)("/pages/bank-join/bank-join?source_type=user&bank_id=".concat(encodeURIComponent(String(id))), 'navigateTo');
    },
    onCycleThemeModeTap: function () {
        var mode = theme_1.themeManager.cycleMode();
        this.setData(__assign(__assign({}, theme_1.themeManager.getPageData()), { themeMode: mode }));
    }
});
