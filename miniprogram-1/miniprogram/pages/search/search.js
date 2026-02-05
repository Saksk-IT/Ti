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
// search.ts - 题目搜索
// 支持公有题库（subject参数）和个人题库（bank_id参数）双数据源
var auth_1 = require("../../utils/auth");
var quiz_source_1 = require("../../utils/quiz-source");
// 数据源实例（页面级别）
var quizSource = null;
var FALLBACK_TYPES = ['选择题', '多选题', '判断题', '填空题', '简答题', '计算题'];
var PREFERRED_TYPE_ORDER = ['选择题', '多选题', '判断题', '填空题', '简答题', '计算题'];
function normalizeTypeList(input) {
    var list = Array.isArray(input) ? input : [];
    var out = list
        .filter(function (t) { return typeof t === 'string' && t.trim(); })
        .map(function (t) { return String(t).trim(); });
    var uniq = Array.from(new Set(out));
    uniq.sort(function (a, b) {
        var ia = PREFERRED_TYPE_ORDER.indexOf(a);
        var ib = PREFERRED_TYPE_ORDER.indexOf(b);
        if (ia === -1 && ib === -1)
            return a.localeCompare(b, 'zh-Hans-CN');
        if (ia === -1)
            return 1;
        if (ib === -1)
            return -1;
        return ia - ib;
    });
    return uniq;
}
function buildTypeChips(types) {
    var list = normalizeTypeList(types);
    var safe = list.length ? list : FALLBACK_TYPES;
    return __spreadArray([{ value: 'all', label: '全部' }], safe.map(function (t) { return ({ value: t, label: t }); }), true);
}
Page({
    data: {
        // 数据源信息
        sourceType: '',
        sourceId: '',
        displayName: '',
        keyword: '',
        selectedType: 'all',
        typeChips: [],
        questions: [],
        page: 1,
        per_page: 20,
        total: 0,
        hasMore: true,
        loading: false,
        searched: false
    },
    onLoad: function (options) {
        if (!(0, auth_1.checkLogin)()) {
            wx.redirectTo({ url: '/pages/login/login' });
            return;
        }
        // 使用工厂函数创建数据源
        quizSource = (0, quiz_source_1.createSourceFromOptions)(options);
        if (!quizSource) {
            console.error('数据源参数缺失（需要 subject 或 bank_id）');
            wx.showToast({ title: '参数缺失', icon: 'none' });
            setTimeout(function () {
                wx.navigateBack();
            }, 1500);
            return;
        }
        console.log('搜索页面数据源类型:', quizSource.sourceType, '标识:', quizSource.sourceId);
        this.setData({
            sourceType: quizSource.sourceType,
            sourceId: quizSource.sourceId,
            displayName: quizSource.displayName || String(quizSource.sourceId)
        });
        this.loadSourceInfo();
    },
    loadSourceInfo: function () {
        return __awaiter(this, void 0, void 0, function () {
            var info, name, types, typeChips, selectedType, allowed, nextSelectedType, err_1;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (!quizSource)
                            return [2 /*return*/];
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, , 4]);
                        return [4 /*yield*/, quizSource.getInfo()];
                    case 2:
                        info = _a.sent();
                        name = (info && info.name) ? String(info.name) : '';
                        types = info === null || info === void 0 ? void 0 : info.available_types;
                        typeChips = buildTypeChips(types);
                        selectedType = this.data.selectedType;
                        allowed = new Set(typeChips.map(function (c) { return c.value; }));
                        nextSelectedType = allowed.has(selectedType) ? selectedType : 'all';
                        this.setData({
                            displayName: name || this.data.displayName,
                            typeChips: typeChips,
                            selectedType: nextSelectedType
                        });
                        return [3 /*break*/, 4];
                    case 3:
                        err_1 = _a.sent();
                        // 题型/名称加载失败不阻断搜索：回退到默认题型列表
                        this.setData({ typeChips: buildTypeChips(FALLBACK_TYPES) });
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        });
    },
    onKeywordInput: function (e) {
        this.setData({ keyword: e.detail.value || '' });
    },
    onClearKeyword: function () {
        this.setData({ keyword: '' });
    },
    onTypeTap: function (e) {
        var _this = this;
        var type = e.currentTarget.dataset.type || 'all';
        if (type === this.data.selectedType)
            return;
        this.setData({ selectedType: type }, function () {
            var kw = (_this.data.keyword || '').trim();
            if (_this.data.searched && kw) {
                _this.loadResults(true);
            }
        });
    },
    onSearch: function () {
        var kw = (this.data.keyword || '').trim();
        if (!kw) {
            wx.showToast({ title: '请输入关键词', icon: 'none' });
            return;
        }
        this.loadResults(true);
    },
    loadResults: function () {
        return __awaiter(this, arguments, void 0, function (reset) {
            var keyword, page, result, list, next, err_2, msg;
            if (reset === void 0) { reset = false; }
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (this.data.loading || !quizSource)
                            return [2 /*return*/];
                        keyword = (this.data.keyword || '').trim();
                        if (!keyword)
                            return [2 /*return*/];
                        page = reset ? 1 : this.data.page;
                        if (reset) {
                            this.setData({ loading: true, questions: [], page: 1, total: 0, hasMore: true });
                        }
                        else {
                            this.setData({ loading: true });
                        }
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, , 4]);
                        return [4 /*yield*/, quizSource.searchQuestions({
                                keyword: keyword,
                                type: this.data.selectedType !== 'all' ? this.data.selectedType : undefined,
                                page: page,
                                per_page: this.data.per_page
                            })];
                    case 2:
                        result = _a.sent();
                        list = (result.questions || []);
                        next = reset ? list : this.data.questions.concat(list);
                        this.setData({
                            questions: next,
                            total: result.total || 0,
                            page: page + 1,
                            hasMore: list.length === this.data.per_page,
                            loading: false,
                            searched: true
                        });
                        return [3 /*break*/, 4];
                    case 3:
                        err_2 = _a.sent();
                        console.error('搜索失败:', err_2);
                        msg = (err_2 && err_2.message) || '搜索失败';
                        wx.showToast({ title: msg, icon: 'none' });
                        this.setData({ loading: false });
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        });
    },
    onPullDownRefresh: function () {
        this.loadResults(true).finally(function () {
            wx.stopPullDownRefresh();
        });
    },
    onReachBottom: function () {
        if (this.data.hasMore && !this.data.loading) {
            this.loadResults(false);
        }
    },
    onResultTap: function (e) {
        var id = Number(e.currentTarget.dataset.id);
        if (!isFinite(id) || id <= 0)
            return;
        var _a = this.data, sourceType = _a.sourceType, sourceId = _a.sourceId;
        var type = this.data.selectedType;
        // 获取保存的设置
        var storageKey = sourceType === 'bank'
            ? "practice_settings_bank_".concat(sourceId)
            : "practice_settings_".concat(sourceId);
        var saved = wx.getStorageSync(storageKey) || {};
        var shuffleQuestions = !!saved.shuffleQuestions;
        var shuffleOptions = !!saved.shuffleOptions;
        // 构建跳转参数
        var params = [];
        // 根据数据源类型添加不同的标识参数
        if (sourceType === 'bank') {
            params.push("bank_id=".concat(sourceId));
        }
        else {
            params.push("subject=".concat(encodeURIComponent(String(sourceId))));
        }
        params.push('mode=quiz');
        if (type && type !== 'all')
            params.push("type=".concat(encodeURIComponent(type)));
        params.push("start_id=".concat(id));
        if (shuffleQuestions)
            params.push('shuffle_questions=1');
        if (shuffleOptions)
            params.push('shuffle_options=1');
        wx.navigateTo({ url: "/pages/quiz/quiz?".concat(params.join('&')) });
    }
});
