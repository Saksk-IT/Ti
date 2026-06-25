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
// practice.ts - 练习页面（入口页）
var api_1 = require("../../utils/api");
var auth_1 = require("../../utils/auth");
Page({
    data: {
        subject: '', // 科目名称
        selectedSource: 'all', // 选中的刷题范围（all/favorites/mistakes）
        selectedType: 'all', // 选中的题型（all/选择题/多选题/判断题/填空题）
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
        debounceTimer: null // 防抖定时器
    },
    onLoad: function (options) {
        console.log('练习页面 onLoad，参数:', options);
        var subject = options.subject || '';
        if (!subject) {
            // 作为 tabBar 页面进入时没有 subject 参数，给出引导
            wx.showToast({ title: '请先选择科目', icon: 'none' });
            setTimeout(function () {
                wx.switchTab({ url: '/pages/hub-v2/hub-v2' });
            }, 800);
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
        // 从路由参数或本地存储获取设置
        var savedSettings = wx.getStorageSync("practice_settings_".concat(subject)) || {};
        var selectedType = options.type || 'all';
        try {
            selectedType = decodeURIComponent(selectedType);
        }
        catch (e) {
            console.warn('题型参数解码失败，使用原始值:', e);
        }
        this.setData({
            subject: subject,
            selectedSource: options.source || 'all',
            selectedType: selectedType,
            settings: {
                shuffleQuestions: savedSettings.shuffleQuestions || false,
                shuffleOptions: savedSettings.shuffleOptions || false
            }
        });
        this.syncShuffleOptionAvailability(selectedType);
        this.loadStats();
    },
    // 加载统计信息
    loadStats: function () {
        return __awaiter(this, void 0, void 0, function () {
            var _a, subject, selectedSource, selectedType, countParams, totalCount, userCounts, err_1, errorMsg;
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0:
                        if (!(0, auth_1.checkLogin)()) {
                            wx.redirectTo({ url: '/pages/login/login' });
                            return [2 /*return*/];
                        }
                        this.setData({ loading: true });
                        _b.label = 1;
                    case 1:
                        _b.trys.push([1, 4, , 5]);
                        _a = this.data, subject = _a.subject, selectedSource = _a.selectedSource, selectedType = _a.selectedType;
                        countParams = { subject: subject };
                        if (selectedType !== 'all') {
                            countParams.type = selectedType;
                        }
                        if (selectedSource !== 'all') {
                            countParams.source = selectedSource;
                        }
                        return [4 /*yield*/, api_1.api.getQuestionsCount(countParams)];
                    case 2:
                        totalCount = _b.sent();
                        return [4 /*yield*/, api_1.api.getUserCounts({
                                subject: subject,
                                type: selectedType !== 'all' ? selectedType : undefined
                            })];
                    case 3:
                        userCounts = _b.sent();
                        this.setData({
                            stats: {
                                total: totalCount.count || 0,
                                favorites: userCounts.favorites || 0,
                                mistakes: userCounts.mistakes || 0
                            },
                            loading: false
                        });
                        return [3 /*break*/, 5];
                    case 4:
                        err_1 = _b.sent();
                        console.error('加载统计信息失败:', err_1);
                        errorMsg = (err_1 && err_1.message) || '加载失败';
                        if (errorMsg.includes('401') || errorMsg.includes('登录') || errorMsg.includes('过期')) {
                            wx.removeStorageSync('token');
                            wx.removeStorageSync('userInfo');
                            wx.reLaunch({ url: '/pages/login/login' });
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
        var _a = this.data, subject = _a.subject, selectedSource = _a.selectedSource, selectedType = _a.selectedType, settings = _a.settings;
        console.log('当前数据:', { subject: subject, selectedSource: selectedSource, selectedType: selectedType, settings: settings });
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
        params.push("subject=".concat(encodeURIComponent(subject)));
        // 题型参数
        if (selectedType !== 'all') {
            params.push("type=".concat(encodeURIComponent(selectedType)));
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
        // 直接进入答题页（支持题型/来源筛选与打乱选项/题目）
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
            wx.setStorageSync("practice_settings_".concat(this.data.subject), settings);
        }
        catch (e) {
            console.warn('保存设置失败:', e);
        }
    },
    buildProgressKey: function (mode) {
        var userInfo = wx.getStorageSync('userInfo') || {};
        var uid = (userInfo && (userInfo.id || userInfo.user_id)) ? String(userInfo.id || userInfo.user_id) : 'guest';
        var subject = (this.data.subject || 'all').toString();
        var type = (this.data.selectedType || 'all').toString();
        var sourceParam = (this.data.selectedSource || '').toString();
        var dataScope = (sourceParam === 'favorites' || sourceParam === 'mistakes') ? sourceParam : 'all';
        var shuffleQ = this.data.settings.shuffleQuestions ? '1' : '0';
        var shuffleO = (this.data.settings.shuffleOptions && this.isOptionShuffleAllowed(type)) ? '1' : '0';
        return "quiz_progress_".concat(uid, "_").concat(mode, "_").concat(subject, "_").concat(type, "_").concat(dataScope, "_q").concat(shuffleQ, "_o").concat(shuffleO);
    },
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
                var modeText = mode === 'quiz' ? '刷题' : '背题';
                var sourceMap = {
                    all: '全部',
                    favorites: '收藏',
                    mistakes: '错题'
                };
                var sourceText = sourceMap[_this.data.selectedSource] || '全部';
                var typeText = _this.data.selectedType === 'all' ? '全部题型' : _this.data.selectedType;
                var key = _this.buildProgressKey(mode);
                wx.showModal({
                    title: '确认清除',
                    content: "\u5C06\u6E05\u9664\u3010".concat(_this.data.subject, "\u3011").concat(modeText, "\uFF08").concat(sourceText, " / ").concat(typeText, "\uFF09\u7684\u8FDB\u5EA6\u8BB0\u5F55\uFF0C\u4E0D\u5F71\u54CD\u5176\u4ED6\u7B5B\u9009\u3002\u662F\u5426\u7EE7\u7EED\uFF1F"),
                    confirmText: '清除',
                    confirmColor: '#FF3B30',
                    success: function (r) { return __awaiter(_this, void 0, void 0, function () {
                        var err_2;
                        return __generator(this, function (_a) {
                            switch (_a.label) {
                                case 0:
                                    if (!r.confirm)
                                        return [2 /*return*/];
                                    _a.label = 1;
                                case 1:
                                    _a.trys.push([1, 3, , 4]);
                                    return [4 /*yield*/, api_1.api.deleteProgress(key)];
                                case 2:
                                    _a.sent();
                                    return [3 /*break*/, 4];
                                case 3:
                                    err_2 = _a.sent();
                                    console.warn('删除云端进度失败（将继续清除本地）:', err_2);
                                    return [3 /*break*/, 4];
                                case 4:
                                    try {
                                        wx.removeStorageSync(key);
                                    }
                                    catch (e) { }
                                    wx.showToast({ title: '已清除', icon: 'none' });
                                    return [2 /*return*/];
                            }
                        });
                    }); }
                });
            }
        });
    },
    onUnload: function () {
        // 清除防抖定时器
        if (this.data.debounceTimer) {
            clearTimeout(this.data.debounceTimer);
        }
    }
});
