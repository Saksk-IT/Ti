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
var __spreadArray = (this && this.__spreadArray) || function (to, from, pack) {
    if (pack || arguments.length === 2) for (var i = 0, l = from.length, ar; i < l; i++) {
        if (ar || !(i in from)) {
            if (!ar) ar = Array.prototype.slice.call(from, 0, i);
            ar[i] = from[i];
        }
    }
    return to.concat(ar || Array.prototype.slice.call(from));
};
Object.defineProperty(exports, "__esModule", { value: true });
var api_1 = require("../../utils/api");
var api_endpoints_1 = require("../../utils/api-endpoints");
var auth_1 = require("../../utils/auth");
var nav_1 = require("../../utils/nav");
var theme_1 = require("../../utils/theme");
function formatDate(dateStr) {
    var raw = String(dateStr || '').trim();
    if (!raw)
        return '-';
    var normalized = raw.replace(/-/g, '/');
    var d = new Date(normalized);
    if (Number.isFinite(d.getTime())) {
        var y = d.getFullYear();
        var m_1 = String(d.getMonth() + 1).padStart(2, '0');
        return "".concat(y, "-").concat(m_1);
    }
    var m = normalized.match(/^(\d{4})[\/-](\d{2})[\/-](\d{2})/);
    if (m)
        return "".concat(m[1], "-").concat(m[2]);
    return raw;
}
function fetchAllOverviewItems() {
    return __awaiter(this, void 0, void 0, function () {
        var perPage, page, total, items, keepGoing, res, pageItems;
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0:
                    perPage = 50;
                    page = 1;
                    total = 0;
                    items = [];
                    keepGoing = true;
                    _a.label = 1;
                case 1:
                    if (!keepGoing) return [3 /*break*/, 3];
                    return [4 /*yield*/, api_1.api.getMyBankOverview({ scope: 'all', page: page, per_page: perPage })];
                case 2:
                    res = _a.sent();
                    pageItems = Array.isArray(res === null || res === void 0 ? void 0 : res.items) ? res.items : [];
                    total = Number((res === null || res === void 0 ? void 0 : res.total) || pageItems.length || 0) || 0;
                    items = __spreadArray(__spreadArray([], items, true), pageItems, true);
                    page += 1;
                    keepGoing = pageItems.length > 0 && items.length < total;
                    return [3 /*break*/, 1];
                case 3: return [2 /*return*/, items];
            }
        });
    });
}
function normalizeSource(item) {
    if (String((item === null || item === void 0 ? void 0 : item.kind) || '') === 'created')
        return 'created';
    var relation = String((item === null || item === void 0 ? void 0 : item.relation) || '').toLowerCase();
    if (relation === 'shared')
        return 'shared';
    if (relation === 'both')
        return 'shared';
    return 'public';
}
function normalizeRelation(item) {
    if (String((item === null || item === void 0 ? void 0 : item.kind) || '') === 'created')
        return 'created';
    var relation = String((item === null || item === void 0 ? void 0 : item.relation) || '').toLowerCase();
    if (relation === 'shared' || relation === 'both')
        return relation;
    return 'public';
}
function sourceLabelFor(item, source, relation) {
    if (source === 'created') {
        var visibility = String((item === null || item === void 0 ? void 0 : item.visibility_label) || '').trim();
        return visibility || ((item === null || item === void 0 ? void 0 : item.is_public) ? '公开' : '私密');
    }
    if (relation === 'both')
        return '公开+分享';
    return source === 'shared' ? '分享加入' : '公开加入';
}
function detailPathFor(id, source, relation, sourceType) {
    if (sourceType === 'system') {
        var params_1 = ["id=".concat(encodeURIComponent(String(id)))];
        if (source !== 'created') {
            params_1.push("source_type=".concat(encodeURIComponent('system')));
            params_1.push("source=".concat(encodeURIComponent(source)));
            params_1.push("relation=".concat(encodeURIComponent(relation)));
        }
        return "/pages/subject-detail-v2/subject-detail-v2?".concat(params_1.join('&'));
    }
    var params = ["id=".concat(encodeURIComponent(String(id)))];
    if (source !== 'created') {
        params.push("source_type=".concat(encodeURIComponent(sourceType)));
        params.push("source=".concat(encodeURIComponent(source)));
        params.push("relation=".concat(encodeURIComponent(relation)));
    }
    return "/pages/bank-detail/bank-detail?".concat(params.join('&'));
}
function overviewItemToBank(item) {
    var id = Number((item === null || item === void 0 ? void 0 : item.id) || 0);
    if (!Number.isFinite(id) || id <= 0)
        return null;
    var source = normalizeSource(item);
    var relation = normalizeRelation(item);
    var sourceType = String((item === null || item === void 0 ? void 0 : item.source_type) || 'user').toLowerCase() === 'system' ? 'system' : 'user';
    var coverUrl = (0, api_endpoints_1.resolveUploadUrl)(item === null || item === void 0 ? void 0 : item.cover_image);
    var ownerLabel = String((item === null || item === void 0 ? void 0 : item.owner_label) || (source === 'created' ? '我创建的题库' : '匿名用户')).trim();
    var ownerAvatarUrl = (0, api_endpoints_1.resolveUploadUrl)(item === null || item === void 0 ? void 0 : item.owner_avatar) || '/images/default-avatar.png';
    var timeValue = (item === null || item === void 0 ? void 0 : item.updated_at) || (item === null || item === void 0 ? void 0 : item.last_joined_at) || (item === null || item === void 0 ? void 0 : item.last_activity_at);
    var isPublic = source === 'created' && String((item === null || item === void 0 ? void 0 : item.visibility_label) || '') === '公开';
    return {
        key: "".concat(sourceType, "-").concat(source, "-").concat(id),
        id: id,
        name: String((item === null || item === void 0 ? void 0 : item.name) || '未命名题库'),
        description: (item === null || item === void 0 ? void 0 : item.description) ? String(item.description) : '',
        question_count: Number((item === null || item === void 0 ? void 0 : item.question_count) || 0) || 0,
        is_public: isPublic,
        created_at: timeValue,
        created_at_fmt: formatDate(timeValue),
        updated_at: timeValue,
        updated_at_fmt: formatDate(timeValue),
        popularity_count: Number((item === null || item === void 0 ? void 0 : item.participants_total) || (item === null || item === void 0 ? void 0 : item.answer_users_7d) || 0) || 0,
        source: source,
        relation: relation,
        source_type: sourceType,
        source_label: sourceLabelFor(item, source, relation),
        owner_name: ownerLabel,
        owner_label: ownerLabel,
        owner_avatar_url: ownerAvatarUrl,
        cover_url: coverUrl,
        has_cover: !!coverUrl,
        detail_path: detailPathFor(id, source, relation, sourceType)
    };
}
Page({
    data: {
        loading: false,
        inited: false,
        keyword: '',
        sourceIndex: 0,
        sourceLabels: ['全部', '我创建的', '公开加入', '分享加入'],
        sourceValues: ['all', 'created', 'public', 'shared'],
        banks: [],
        filteredBanks: [],
        createOpen: false,
        createName: '',
        createDesc: '',
        createError: '',
        creating: false
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
        this.loadBanks();
    },
    loadBanks: function () {
        return __awaiter(this, void 0, void 0, function () {
            var overviewItems, banks, e_1;
            var _this = this;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (this.data.loading)
                            return [2 /*return*/];
                        this.setData({ loading: true });
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, 4, 5]);
                        return [4 /*yield*/, fetchAllOverviewItems()];
                    case 2:
                        overviewItems = _a.sent();
                        banks = overviewItems
                            .map(function (item) { return overviewItemToBank(item); })
                            .filter(function (bank) { return !!bank; });
                        this.setData({ banks: banks, inited: true }, function () { return _this.applyFilter(); });
                        return [3 /*break*/, 5];
                    case 3:
                        e_1 = _a.sent();
                        wx.showToast({ title: (e_1 && e_1.message) || '加载失败', icon: 'none' });
                        return [3 /*break*/, 5];
                    case 4:
                        this.setData({ loading: false });
                        return [7 /*endfinally*/];
                    case 5: return [2 /*return*/];
                }
            });
        });
    },
    onKeywordInput: function (e) {
        var _this = this;
        var keyword = (e && e.detail && e.detail.value) ? String(e.detail.value) : '';
        this.setData({ keyword: keyword }, function () { return _this.applyFilter(); });
    },
    onClearKeyword: function () {
        var _this = this;
        this.setData({ keyword: '' }, function () { return _this.applyFilter(); });
    },
    onSourceChange: function (e) {
        var _this = this;
        var _a, _b;
        var idx = Number((_b = (_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.value) !== null && _b !== void 0 ? _b : 0) || 0;
        var max = (this.data.sourceLabels || []).length - 1;
        var sourceIndex = Math.max(0, Math.min(idx, max));
        if (sourceIndex === this.data.sourceIndex)
            return;
        this.setData({ sourceIndex: sourceIndex }, function () { return _this.applyFilter(); });
    },
    applyFilter: function () {
        var kw = (this.data.keyword || '').trim().toLowerCase();
        var out = (this.data.banks || []).slice();
        var sourceValues = this.data.sourceValues || ['all', 'created', 'public', 'shared'];
        var source = sourceValues[this.data.sourceIndex] || 'all';
        if (source === 'created') {
            out = out.filter(function (b) { return b.source === 'created'; });
        }
        else if (source === 'public') {
            out = out.filter(function (b) { return b.source === 'public' || b.relation === 'both'; });
        }
        else if (source === 'shared') {
            out = out.filter(function (b) { return b.source === 'shared' || b.relation === 'both'; });
        }
        if (kw) {
            out = out.filter(function (b) {
                var name = String(b.name || '').toLowerCase();
                var desc = String(b.description || '').toLowerCase();
                var owner = String(b.owner_name || '').toLowerCase();
                return name.includes(kw) || desc.includes(kw) || owner.includes(kw);
            });
        }
        out.sort(function (a, b) {
            return String(b.updated_at || '').localeCompare(String(a.updated_at || '')) || (b.id - a.id);
        });
        this.setData({ filteredBanks: out });
    },
    onBankTap: function (e) {
        var _a, _b, _c, _d;
        var id = Number(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.id) || 0);
        var key = String(((_d = (_c = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _c === void 0 ? void 0 : _c.dataset) === null || _d === void 0 ? void 0 : _d.key) || '');
        var bank = (this.data.banks || []).find(function (item) { return (key && item.key === key) || item.id === id; });
        if (!bank && (!Number.isFinite(id) || id <= 0))
            return;
        (0, nav_1.safeNavigate)((bank === null || bank === void 0 ? void 0 : bank.detail_path) || "/pages/bank-detail/bank-detail?id=".concat(id), 'navigateTo');
    },
    onGoPublicBank: function () {
        (0, nav_1.safeNavigate)('/pages/public-bank-v2/public-bank-v2', 'redirectTo');
    },
    onGoCreateBank: function () {
        if (this.data.createOpen)
            return;
        this.setData({
            createOpen: true,
            createName: '',
            createDesc: '',
            createError: '',
            creating: false
        });
    },
    onCreateClose: function () {
        if (this.data.creating)
            return;
        this.setData({ createOpen: false });
    },
    onCreateSheetTap: function () { },
    onCreateNameInput: function (e) {
        var _a;
        var value = String(((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.value) || '');
        this.setData({ createName: value, createError: '' });
    },
    onCreateDescInput: function (e) {
        var _a;
        var value = String(((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.value) || '');
        this.setData({ createDesc: value, createError: '' });
    },
    onCreateSubmit: function () {
        return __awaiter(this, void 0, void 0, function () {
            var name, description, msg, msg, msg, e_2, msg;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (this.data.creating)
                            return [2 /*return*/];
                        name = String(this.data.createName || '').trim();
                        description = String(this.data.createDesc || '').trim();
                        if (!name) {
                            msg = '题库名称不能为空';
                            this.setData({ createError: msg });
                            wx.showToast({ title: msg, icon: 'none' });
                            return [2 /*return*/];
                        }
                        if (name.length < 2 || name.length > 50) {
                            msg = '题库名称需要 2-50 个字符';
                            this.setData({ createError: msg });
                            wx.showToast({ title: msg, icon: 'none' });
                            return [2 /*return*/];
                        }
                        if (description.length > 200) {
                            msg = '描述不能超过 200 个字符';
                            this.setData({ createError: msg });
                            wx.showToast({ title: msg, icon: 'none' });
                            return [2 /*return*/];
                        }
                        this.setData({ creating: true, createError: '' });
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, , 4]);
                        return [4 /*yield*/, api_1.api.createBank({ name: name, description: description })];
                    case 2:
                        _a.sent();
                        wx.showToast({ title: '创建成功', icon: 'success' });
                        this.setData({
                            createOpen: false,
                            createName: '',
                            createDesc: '',
                            createError: '',
                            creating: false
                        });
                        this.loadBanks();
                        return [3 /*break*/, 4];
                    case 3:
                        e_2 = _a.sent();
                        msg = (e_2 && e_2.message) ? String(e_2.message) : '创建失败';
                        this.setData({ creating: false, createError: msg });
                        wx.showToast({ title: msg, icon: 'none' });
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        });
    },
    onCycleThemeModeTap: function () {
        var mode = theme_1.themeManager.cycleMode();
        this.setData(__assign(__assign({}, (theme_1.themeManager.getPageData())), { themeMode: mode }));
    }
});
