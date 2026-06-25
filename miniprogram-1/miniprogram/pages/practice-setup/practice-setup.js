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
// practice-setup.ts - 练习设置页面（入口页）
var api_1 = require("../../utils/api");
var auth_1 = require("../../utils/auth");
Page({
    data: {
        sourceType: 'public', // 数据源类型：public 科目题库 / bank 个人题库
        bankId: 0, // 个人题库ID（sourceType=bank）
        subject: '', // 科目名称
        selectedSource: 'all', // 选中的刷题范围（all/favorites/mistakes）
        selectedType: 'all', // 选中的题型（all/选择题/多选题/判断题/填空题）
        selectedTag: 'all', // 选中的标签（all/自定义标签名）
        // 该科目实际拥有的题型（不含 all）
        availableTypes: [],
        // 可选标签列表（来自 /quiz/tags）
        availableTags: [],
        // 统计信息
        stats: {
            total: 0, // 总题数（当前范围和题型）
            favorites: 0, // 收藏数（当前题型）
            mistakes: 0 // 错题数（当前题型）
        },
        // 设置选项
        settings: {
            shuffleQuestions: false, // 打乱题目
            shuffleOptions: false // 打乱选项
        },
        canShuffleOptions: true,
        loading: false, // 加载状态
        debounceTimer: null
    },
    getSettingsStorageKey: function () {
        if (this.data.sourceType === 'bank' && this.data.bankId) {
            return "practice_settings_bank_".concat(this.data.bankId);
        }
        return "practice_settings_".concat(this.data.subject);
    },
    onLoad: function (options) {
        console.log('练习设置页面 onLoad，参数:', options);
        var bankId = Number(options.bank_id || options.bankId || 0);
        var isBank = isFinite(bankId) && bankId > 0;
        var subject = options.subject || '';
        if (!isBank) {
            if (!subject) {
                console.error('科目参数缺失');
                wx.showToast({ title: '科目参数缺失', icon: 'none' });
                setTimeout(function () {
                    wx.navigateBack();
                }, 1500);
                return;
            }
            // 显式解码URL参数
            try {
                subject = decodeURIComponent(subject);
            }
            catch (e) {
                console.warn('URL参数解码失败，使用原始值:', e);
            }
            console.log('科目名称:', subject);
        }
        else {
            subject = '题库';
            console.log('个人题库ID:', bankId);
        }
        var settingsKey = isBank ? "practice_settings_bank_".concat(bankId) : "practice_settings_".concat(subject);
        var savedSettings = wx.getStorageSync(settingsKey) || {};
        var selectedType = options.type || 'all';
        var selectedTag = options.tag || 'all';
        try {
            selectedType = decodeURIComponent(selectedType);
        }
        catch (e) {
            console.warn('题型参数解码失败，使用原始值:', e);
        }
        try {
            selectedTag = decodeURIComponent(selectedTag);
        }
        catch (e) {
            console.warn('标签参数解码失败，使用原始值:', e);
        }
        this.setData({
            sourceType: isBank ? 'bank' : 'public',
            bankId: isBank ? bankId : 0,
            subject: subject,
            selectedSource: options.source || 'all',
            selectedType: selectedType,
            selectedTag: selectedTag || 'all',
            settings: {
                shuffleQuestions: savedSettings.shuffleQuestions || false,
                shuffleOptions: savedSettings.shuffleOptions || false
            }
        });
        this.syncShuffleOptionAvailability(selectedType);
        this.loadAvailableTypesAndStats();
    },
    loadTags: function () {
        return __awaiter(this, void 0, void 0, function () {
            var res, _a, tags, list, map, _i, list_1, t, prev, availableTags, err_1;
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0:
                        _b.trys.push([0, 5, , 6]);
                        if (!(this.data.sourceType === 'bank' && this.data.bankId)) return [3 /*break*/, 2];
                        return [4 /*yield*/, api_1.api.getBankTags(this.data.bankId)];
                    case 1:
                        _a = _b.sent();
                        return [3 /*break*/, 4];
                    case 2: return [4 /*yield*/, api_1.api.getTags({ subject: this.data.subject })];
                    case 3:
                        _a = _b.sent();
                        _b.label = 4;
                    case 4:
                        res = _a;
                        tags = res.tags || res || [];
                        list = (Array.isArray(tags) ? tags : [])
                            .map(function (t) { return ({
                            name: (t && (t.name || t)) ? String(t.name || t).trim() : '',
                            count: Number((t && t.count) || 0) || 0
                        }); })
                            .filter(function (t) { return t.name; });
                        map = new Map();
                        for (_i = 0, list_1 = list; _i < list_1.length; _i++) {
                            t = list_1[_i];
                            prev = map.get(t.name) || 0;
                            if (t.count > prev)
                                map.set(t.name, t.count);
                        }
                        availableTags = Array.from(map.entries())
                            .map(function (entry) { return ({ name: entry[0], count: entry[1] }); })
                            .sort(function (a, b) {
                            if (b.count !== a.count)
                                return b.count - a.count;
                            return a.name.localeCompare(b.name, 'zh-Hans-CN');
                        });
                        this.setData({ availableTags: availableTags });
                        return [3 /*break*/, 6];
                    case 5:
                        err_1 = _b.sent();
                        console.error('加载标签列表失败:', err_1);
                        this.setData({ availableTags: [] });
                        return [3 /*break*/, 6];
                    case 6: return [2 /*return*/];
                }
            });
        });
    },
    loadAvailableTypesAndStats: function () {
        return __awaiter(this, void 0, void 0, function () {
            var info, res, name, res, types, availableTypes, preferredOrder_1, selectedType, nextSelectedType, err_2;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (!(0, auth_1.checkLogin)()) {
                            wx.redirectTo({ url: '/pages/login/login' });
                            return [2 /*return*/];
                        }
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 6, , 7]);
                        info = {};
                        if (!(this.data.sourceType === 'bank' && this.data.bankId)) return [3 /*break*/, 3];
                        return [4 /*yield*/, api_1.api.getBankDetail(this.data.bankId)];
                    case 2:
                        res = _a.sent();
                        info = ((res === null || res === void 0 ? void 0 : res.data) || res || {});
                        name = info.name || "\u9898\u5E93".concat(this.data.bankId);
                        if (name && name !== this.data.subject) {
                            this.setData({ subject: name });
                        }
                        return [3 /*break*/, 5];
                    case 3: return [4 /*yield*/, api_1.api.getSubjectInfo(this.data.subject)];
                    case 4:
                        res = _a.sent();
                        info = ((res === null || res === void 0 ? void 0 : res.data) || res || {});
                        _a.label = 5;
                    case 5:
                        types = Array.isArray(info.available_types) ? info.available_types : [];
                        availableTypes = (types || [])
                            .filter(function (t) { return typeof t === 'string' && t.trim(); })
                            .map(function (t) { return t.trim(); });
                        preferredOrder_1 = ['选择题', '多选题', '判断题', '填空题', '简答题', '计算题'];
                        availableTypes.sort(function (a, b) {
                            var ia = preferredOrder_1.indexOf(a);
                            var ib = preferredOrder_1.indexOf(b);
                            if (ia === -1 && ib === -1)
                                return a.localeCompare(b, 'zh-Hans-CN');
                            if (ia === -1)
                                return 1;
                            if (ib === -1)
                                return -1;
                            return ia - ib;
                        });
                        selectedType = this.data.selectedType;
                        nextSelectedType = selectedType !== 'all' && availableTypes.length > 0 && !availableTypes.includes(selectedType)
                            ? 'all'
                            : selectedType;
                        this.setData({ availableTypes: availableTypes, selectedType: nextSelectedType });
                        this.syncShuffleOptionAvailability(nextSelectedType);
                        return [3 /*break*/, 7];
                    case 6:
                        err_2 = _a.sent();
                        console.error('加载题型失败:', err_2);
                        // 题型加载失败不阻断刷题：回退为空列表（只显示“全部”）
                        this.setData({ availableTypes: [] });
                        return [3 /*break*/, 7];
                    case 7: return [4 /*yield*/, this.loadTags()];
                    case 8:
                        _a.sent();
                        return [4 /*yield*/, this.loadStats()];
                    case 9:
                        _a.sent();
                        return [2 /*return*/];
                }
            });
        });
    },
    // 清除当前筛选的刷题进度（云端 + 本地），不影响其它组合
    onClearProgressTap: function () {
        var _this = this;
        if (!(0, auth_1.checkLogin)()) {
            wx.redirectTo({ url: '/pages/login/login' });
            return;
        }
        if (this.data.loading) {
            wx.showToast({ title: '加载中，请稍候', icon: 'none' });
            return;
        }
        wx.showActionSheet({
            itemList: ['清除刷题进度', '清除背题进度'],
            success: function (res) {
                var mode = res.tapIndex === 1 ? 'memo' : 'quiz';
                _this.confirmAndClearProgress(mode);
            }
        });
    },
    confirmAndClearProgress: function (mode) {
        var _this = this;
        var key = this.buildProgressKey(mode);
        var _a = this.data, subject = _a.subject, selectedSource = _a.selectedSource, selectedType = _a.selectedType, selectedTag = _a.selectedTag, settings = _a.settings;
        var sourceLabel = selectedSource === 'favorites' ? '收藏' : selectedSource === 'mistakes' ? '错题' : '全部';
        var typeLabel = selectedType === 'all' ? '全部题型' : selectedType;
        var tagLabel = selectedTag && selectedTag !== 'all' ? selectedTag : '全部标签';
        var modeLabel = mode === 'memo' ? '背题' : '刷题';
        var shuffleQ = settings.shuffleQuestions ? '开' : '关';
        var shuffleO = settings.shuffleOptions ? '开' : '关';
        wx.showModal({
            title: '确认清除',
            content: "\u5C06\u6E05\u9664\u4EE5\u4E0B\u7EC4\u5408\u7684\u8FDB\u5EA6\uFF1A\n\u79D1\u76EE\uFF1A".concat(subject, "\n\u8303\u56F4\uFF1A").concat(sourceLabel, "\n\u9898\u578B\uFF1A").concat(typeLabel, "\n\u6807\u7B7E\uFF1A").concat(tagLabel, "\n\u6A21\u5F0F\uFF1A").concat(modeLabel, "\n\u6253\u4E71\u9898\u76EE\uFF1A").concat(shuffleQ, "  \u6253\u4E71\u9009\u9879\uFF1A").concat(shuffleO),
            confirmText: '清除',
            confirmColor: '#FF3B30',
            success: function (r) { return __awaiter(_this, void 0, void 0, function () {
                var e_1;
                return __generator(this, function (_a) {
                    switch (_a.label) {
                        case 0:
                            if (!r.confirm)
                                return [2 /*return*/];
                            wx.showLoading({ title: '清除中...' });
                            _a.label = 1;
                        case 1:
                            _a.trys.push([1, 3, , 4]);
                            return [4 /*yield*/, api_1.api.deleteProgress(key)];
                        case 2:
                            _a.sent();
                            return [3 /*break*/, 4];
                        case 3:
                            e_1 = _a.sent();
                            // 云端清除失败时也会清掉本地，避免“看起来没清除”
                            console.error('清除云端进度失败:', e_1);
                            return [3 /*break*/, 4];
                        case 4:
                            try {
                                wx.removeStorageSync(key);
                            }
                            catch (e) { }
                            wx.hideLoading();
                            wx.showToast({ title: '已清除', icon: 'success' });
                            return [2 /*return*/];
                    }
                });
            }); }
        });
    },
    buildProgressKey: function (mode) {
        var userInfo = wx.getStorageSync('userInfo') || {};
        var uid = (userInfo && (userInfo.id || userInfo.user_id)) ? String(userInfo.id || userInfo.user_id) : 'guest';
        var type = (this.data.selectedType || 'all').toString();
        var source = (this.data.selectedSource || '').toString();
        var dataScope = source === 'favorites' || source === 'mistakes' ? source : 'all';
        var tag = (this.data.selectedTag || '').toString();
        var tagPart = tag && tag.toLowerCase() !== 'all' ? "_tag".concat(tag) : '';
        var shuffleQ = this.data.settings.shuffleQuestions ? '1' : '0';
        var shuffleO = (this.data.settings.shuffleOptions && this.isOptionShuffleAllowed(type)) ? '1' : '0';
        if (this.data.sourceType === 'bank' && this.data.bankId) {
            var bankId = this.data.bankId || 0;
            return "bank_quiz_progress_".concat(uid, "_").concat(mode, "_").concat(bankId, "_").concat(type, "_").concat(dataScope).concat(tagPart, "_q").concat(shuffleQ, "_o").concat(shuffleO);
        }
        var subject = (this.data.subject || 'all').toString();
        return "quiz_progress_".concat(uid, "_").concat(mode, "_").concat(subject, "_").concat(type, "_").concat(dataScope).concat(tagPart, "_q").concat(shuffleQ, "_o").concat(shuffleO);
    },
    // 加载统计信息
    loadStats: function () {
        return __awaiter(this, void 0, void 0, function () {
            var _a, bankId, selectedSource_1, selectedType_1, selectedTag_1, params, res, data, _b, subject, selectedSource, selectedType, selectedTag, countParams, totalCount, userCounts, err_3, errorMsg;
            return __generator(this, function (_c) {
                switch (_c.label) {
                    case 0:
                        if (!(0, auth_1.checkLogin)()) {
                            wx.redirectTo({ url: '/pages/login/login' });
                            return [2 /*return*/];
                        }
                        this.setData({ loading: true });
                        _c.label = 1;
                    case 1:
                        _c.trys.push([1, 6, , 7]);
                        if (!(this.data.sourceType === 'bank' && this.data.bankId)) return [3 /*break*/, 3];
                        _a = this.data, bankId = _a.bankId, selectedSource_1 = _a.selectedSource, selectedType_1 = _a.selectedType, selectedTag_1 = _a.selectedTag;
                        params = {};
                        if (selectedType_1 !== 'all')
                            params.q_type = selectedType_1;
                        if (selectedSource_1 !== 'all')
                            params.source = selectedSource_1;
                        if (selectedTag_1 && selectedTag_1 !== 'all')
                            params.tag = selectedTag_1;
                        return [4 /*yield*/, api_1.api.getBankUserCounts(bankId, params)];
                    case 2:
                        res = _c.sent();
                        data = ((res === null || res === void 0 ? void 0 : res.data) || res || {});
                        this.setData({
                            stats: {
                                total: data.total || 0,
                                favorites: data.favorites || 0,
                                mistakes: data.mistakes || 0
                            },
                            loading: false
                        });
                        return [2 /*return*/];
                    case 3:
                        _b = this.data, subject = _b.subject, selectedSource = _b.selectedSource, selectedType = _b.selectedType, selectedTag = _b.selectedTag;
                        countParams = { subject: subject };
                        if (selectedType !== 'all') {
                            countParams.type = selectedType;
                        }
                        if (selectedSource !== 'all') {
                            countParams.source = selectedSource;
                        }
                        if (selectedTag && selectedTag !== 'all') {
                            countParams.tag = selectedTag;
                        }
                        return [4 /*yield*/, api_1.api.getQuestionsCount(countParams)];
                    case 4:
                        totalCount = _c.sent();
                        return [4 /*yield*/, api_1.api.getUserCounts({
                                subject: subject,
                                type: selectedType !== 'all' ? selectedType : undefined,
                                tag: selectedTag && selectedTag !== 'all' ? selectedTag : undefined
                            })];
                    case 5:
                        userCounts = _c.sent();
                        this.setData({
                            stats: {
                                total: totalCount.count || 0,
                                favorites: userCounts.favorites || 0,
                                mistakes: userCounts.mistakes || 0
                            },
                            loading: false
                        });
                        return [3 /*break*/, 7];
                    case 6:
                        err_3 = _c.sent();
                        console.error('加载统计信息失败:', err_3);
                        errorMsg = (err_3 && err_3.message) || '加载失败';
                        if (errorMsg.includes('401') || errorMsg.includes('登录') || errorMsg.includes('过期')) {
                            wx.removeStorageSync('token');
                            wx.removeStorageSync('userInfo');
                            wx.reLaunch({ url: '/pages/login/login' });
                            return [2 /*return*/];
                        }
                        wx.showToast({ title: errorMsg, icon: 'none' });
                        this.setData({ loading: false });
                        return [3 /*break*/, 7];
                    case 7: return [2 /*return*/];
                }
            });
        });
    },
    // 防抖加载统计信息
    debouncedLoadStats: function () {
        var _this = this;
        if (this.data.debounceTimer) {
            clearTimeout(this.data.debounceTimer);
        }
        this.data.debounceTimer = setTimeout(function () {
            _this.loadStats();
        }, 300);
    },
    // 选择刷题范围
    onSourceTap: function (e) {
        var source = e.currentTarget.dataset.source;
        this.setData({ selectedSource: source });
        this.debouncedLoadStats();
    },
    // 选择题型
    onTypeTap: function (e) {
        var type = e.currentTarget.dataset.type;
        this.setData({ selectedType: type });
        this.syncShuffleOptionAvailability(type);
        this.debouncedLoadStats();
    },
    // 选择标签
    onTagTap: function (e) {
        var tag = e.currentTarget.dataset.tag;
        this.setData({ selectedTag: tag || 'all' });
        this.debouncedLoadStats();
    },
    // 切换设置选项
    onSettingChange: function (e) {
        var setting = e.currentTarget.dataset.setting;
        var value = e.detail.value;
        if (setting === 'shuffleOptions' && !this.isOptionShuffleAllowed(this.data.selectedType)) {
            this.setData({ settings: __assign(__assign({}, this.data.settings), { shuffleOptions: false }) });
            return;
        }
        var newSettings = Object.assign({}, this.data.settings);
        newSettings[setting] = value;
        this.setData({ settings: newSettings });
        // 保存用户偏好到本地存储
        this.saveSettings(newSettings);
    },
    // 操作按钮点击（刷题/背题）
    onActionButtonTap: function (e) {
        console.log('操作按钮点击，event:', e);
        var mode = e.currentTarget.dataset.mode; // quiz/memo
        console.log('模式:', mode);
        var _a = this.data, subject = _a.subject, selectedSource = _a.selectedSource, selectedType = _a.selectedType, selectedTag = _a.selectedTag, settings = _a.settings;
        console.log('当前数据:', { subject: subject, selectedSource: selectedSource, selectedType: selectedType, selectedTag: selectedTag, settings: settings });
        if (!subject) {
            wx.showToast({ title: '科目信息缺失', icon: 'none' });
            return;
        }
        if (this.data.loading) {
            wx.showToast({ title: '加载中，请稍候', icon: 'none' });
            return;
        }
        var total = (this.data.stats && this.data.stats.total) || 0;
        if (total <= 0) {
            wx.showToast({ title: '当前筛选暂无题目', icon: 'none' });
            return;
        }
        // 构建参数
        var params = [];
        if (this.data.sourceType === 'bank' && this.data.bankId) {
            params.push("bank_id=".concat(this.data.bankId));
        }
        else {
            params.push("subject=".concat(encodeURIComponent(subject)));
        }
        // 题型参数
        if (selectedType !== 'all') {
            params.push("type=".concat(encodeURIComponent(selectedType)));
        }
        // 标签参数
        if (selectedTag && selectedTag !== 'all') {
            params.push("tag=".concat(encodeURIComponent(selectedTag)));
        }
        // 模式参数
        params.push("mode=".concat(mode));
        // 来源参数
        if (selectedSource !== 'all') {
            params.push("source=".concat(selectedSource));
        }
        // 设置参数
        if (settings.shuffleQuestions) {
            params.push('shuffle_questions=1');
        }
        if (settings.shuffleOptions && this.isOptionShuffleAllowed(selectedType)) {
            params.push('shuffle_options=1');
        }
        var url = "/pages/quiz/quiz?".concat(params.join('&'));
        console.log('跳转URL:', url);
        wx.navigateTo({
            url: url,
            success: function () {
                console.log('跳转到刷题页面成功');
            },
            fail: function (err) {
                console.error('跳转失败:', err);
                wx.showToast({ title: '跳转失败: ' + (err.errMsg || '未知错误'), icon: 'none', duration: 3000 });
            }
        });
    },
    isOptionShuffleAllowed: function (type) {
        if (!type || type === 'all')
            return true;
        return type === '选择题' || type === '多选题';
    },
    syncShuffleOptionAvailability: function (type) {
        var targetType = (type !== undefined ? type : this.data.selectedType) || 'all';
        var canShuffleOptions = this.isOptionShuffleAllowed(targetType);
        var settings = __assign({}, this.data.settings);
        if (!canShuffleOptions && settings.shuffleOptions) {
            settings.shuffleOptions = false;
            this.saveSettings(settings);
        }
        this.setData({
            canShuffleOptions: canShuffleOptions,
            settings: settings
        });
    },
    saveSettings: function (settings) {
        try {
            wx.setStorageSync(this.getSettingsStorageKey(), settings);
        }
        catch (e) {
            console.warn('保存设置失败:', e);
        }
    },
    onUnload: function () {
        // 清除防抖定时器
        if (this.data.debounceTimer) {
            clearTimeout(this.data.debounceTimer);
        }
    }
});
