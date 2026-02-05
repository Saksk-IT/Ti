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
var theme_1 = require("../../utils/theme");
var TYPE_ORDER = ['announcement', 'reminder', 'warning', 'info'];
var TYPE_LABEL = {
    info: '信息',
    announcement: '公告',
    reminder: '提醒',
    warning: '警告'
};
function toInt(v) {
    var n = Number(v);
    return Number.isFinite(n) ? Math.trunc(n) : 0;
}
function normalizeType(t) {
    var raw = (t || 'info').toString().trim().toLowerCase();
    return TYPE_LABEL[raw] ? raw : 'info';
}
function typeDotColor(type) {
    var t = normalizeType(type);
    if (t === 'announcement')
        return 'var(--noti-announcement)';
    if (t === 'reminder')
        return 'var(--noti-reminder)';
    if (t === 'warning')
        return 'var(--noti-warning)';
    return 'var(--noti-info)';
}
function fmtTime(s) {
    if (!s)
        return '';
    var raw = String(s).replace('T', ' ');
    if (raw.length >= 16)
        return raw.slice(0, 16);
    return raw;
}
function toTimeValue(s) {
    if (!s)
        return 0;
    var raw = String(s);
    var m = raw.match(/^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})(?::(\d{2}))?$/);
    // 统一以北京时间为准：后端返回的 "YYYY-MM-DD HH:mm:ss" 视为本地（北京时间）时间
    if (m)
        return new Date(+m[1], +m[2] - 1, +m[3], +m[4], +m[5], +(m[6] || 0)).getTime();
    try {
        var d = new Date(raw);
        var t = d.getTime();
        return Number.isFinite(t) ? t : 0;
    }
    catch (e) {
        return 0;
    }
}
function snippetText(s, maxLen) {
    var t = (s || '').toString().replace(/\s+/g, ' ').trim();
    if (!t)
        return '';
    if (t.length <= maxLen)
        return t;
    return t.slice(0, maxLen) + '…';
}
function sortTypeKeys(keys) {
    var arr = (keys || []).slice();
    arr.sort(function (a, b) {
        var ia = TYPE_ORDER.indexOf(a);
        var ib = TYPE_ORDER.indexOf(b);
        if (ia === -1 && ib === -1)
            return a.localeCompare(b);
        if (ia === -1)
            return 1;
        if (ib === -1)
            return -1;
        return ia - ib;
    });
    return arr;
}
function getReadFacets(list) {
    var counts = {};
    (list || []).forEach(function (n) {
        var key = normalizeType(n.typeKey);
        counts[key] = (counts[key] || 0) + 1;
    });
    var keys = sortTypeKeys(Object.keys(counts));
    var items = keys.map(function (t) { return ({
        type: t,
        label: TYPE_LABEL[t] || t,
        count: counts[t] || 0,
        color: typeDotColor(t)
    }); });
    return { total: (list || []).length, items: items };
}
function sortReadItems(items, sortKey) {
    var arr = (items || []).slice();
    arr.sort(function (a, b) {
        var pa = toInt(a.priority);
        var pb = toInt(b.priority);
        var ta = toInt(a.timeValue);
        var tb = toInt(b.timeValue);
        if (sortKey === 'priority') {
            if (pb !== pa)
                return pb - pa;
            if (tb !== ta)
                return tb - ta;
        }
        else {
            if (tb !== ta)
                return tb - ta;
            if (pb !== pa)
                return pb - pa;
        }
        return toInt(b.id) - toInt(a.id);
    });
    return arr;
}
function groupByType(items) {
    var groups = {};
    (items || []).forEach(function (n) {
        var k = normalizeType(n.typeKey);
        if (!groups[k])
            groups[k] = [];
        groups[k].push(n);
    });
    var keys = sortTypeKeys(Object.keys(groups));
    return keys.map(function (k) { return ({ type: k, items: groups[k] || [] }); });
}
function resolvePresetTab(raw) {
    var t = String(raw || '').trim().toLowerCase();
    if (t === 'read')
        return 'read';
    if (t === 'unread')
        return 'unread';
    return '';
}
Page({
    data: {
        drawerOpen: false,
        loading: false,
        inited: false,
        errorMsg: '',
        tab: 'unread',
        list: [],
        unreadList: [],
        readAll: [],
        readGroups: [],
        unreadCount: 0,
        readCount: 0,
        unreadSub: '优先处理',
        readSub: '按通知类型归档展示',
        markingId: 0,
        markAllLoading: false,
        readTypeFilter: 'all',
        readTypeFacets: { total: 0, items: [] },
        readFilteredCount: 0
    },
    onLoad: function (options) {
        var preset = resolvePresetTab(options === null || options === void 0 ? void 0 : options.tab);
        this.__presetTab = preset;
        if (preset)
            this.setData({ tab: preset });
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
        this.fetchList(false);
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
    onCycleThemeModeTap: function () {
        var mode = theme_1.themeManager.cycleMode();
        this.setData(__assign(__assign({}, theme_1.themeManager.getPageData()), { themeMode: mode }));
    },
    onTabTap: function (e) {
        var _a, _b;
        var tab = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.tab) || '');
        var next = tab === 'read' ? 'read' : 'unread';
        if (next === this.data.tab)
            return;
        this.setData({ tab: next });
    },
    onRefreshTap: function () {
        this.fetchList(true);
    },
    onPullDownRefresh: function () {
        var _this = this;
        Promise.resolve()
            .then(function () { return __awaiter(_this, void 0, void 0, function () {
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0: return [4 /*yield*/, this.fetchList(true)];
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
    onReadTypeTap: function (e) {
        var _this = this;
        var _a, _b;
        var type = String(((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.type) || 'all');
        if (type === this.data.readTypeFilter)
            return;
        this.setData({ readTypeFilter: type }, function () { return _this.rebuildDerived(); });
    },
    onToggleReadExpand: function (e) {
        var _a, _b;
        var id = toInt((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.id);
        if (!id)
            return;
        var self = this;
        if (!self.__expandedReadIds)
            self.__expandedReadIds = new Set();
        var s = self.__expandedReadIds;
        if (s.has(id))
            s.delete(id);
        else
            s.add(id);
        this.rebuildDerived();
    },
    onMarkRead: function (e) {
        return __awaiter(this, void 0, void 0, function () {
            var id, list, err_1;
            var _this = this;
            var _a, _b;
            return __generator(this, function (_c) {
                switch (_c.label) {
                    case 0:
                        id = toInt((_b = (_a = e === null || e === void 0 ? void 0 : e.currentTarget) === null || _a === void 0 ? void 0 : _a.dataset) === null || _b === void 0 ? void 0 : _b.id);
                        if (!id)
                            return [2 /*return*/];
                        if (this.data.markingId)
                            return [2 /*return*/];
                        this.setData({ markingId: id, errorMsg: '' });
                        _c.label = 1;
                    case 1:
                        _c.trys.push([1, 3, 4, 5]);
                        return [4 /*yield*/, api_1.api.markNotificationRead(id)];
                    case 2:
                        _c.sent();
                        list = (this.data.list || []).map(function (n) { return (n.id === id ? __assign(__assign({}, n), { isRead: true }) : n); });
                        this.setData({ list: list }, function () { return _this.rebuildDerived(); });
                        return [3 /*break*/, 5];
                    case 3:
                        err_1 = _c.sent();
                        wx.showToast({ title: (err_1 === null || err_1 === void 0 ? void 0 : err_1.message) || '操作失败', icon: 'none' });
                        return [3 /*break*/, 5];
                    case 4:
                        this.setData({ markingId: 0 });
                        return [7 /*endfinally*/];
                    case 5: return [2 /*return*/];
                }
            });
        });
    },
    onMarkAllRead: function () {
        return __awaiter(this, void 0, void 0, function () {
            var unread, ok, _loop_1, this_1, _i, unread_1, n, err_2;
            var _this = this;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (this.data.loading || this.data.markAllLoading)
                            return [2 /*return*/];
                        unread = (this.data.list || []).filter(function (n) { return !n.isRead; });
                        if (unread.length === 0)
                            return [2 /*return*/];
                        return [4 /*yield*/, new Promise(function (resolve) {
                                wx.showModal({
                                    title: '批量标记',
                                    content: "\u5C06 ".concat(unread.length, " \u6761\u672A\u8BFB\u901A\u77E5\u5168\u90E8\u6807\u8BB0\u4E3A\u5DF2\u8BFB\uFF1F"),
                                    confirmText: '确定',
                                    cancelText: '取消',
                                    success: function (res) { return resolve(!!res.confirm); },
                                    fail: function () { return resolve(false); }
                                });
                            })];
                    case 1:
                        ok = _a.sent();
                        if (!ok)
                            return [2 /*return*/];
                        this.setData({ markAllLoading: true, errorMsg: '' });
                        _a.label = 2;
                    case 2:
                        _a.trys.push([2, 7, 8, 9]);
                        _loop_1 = function (n) {
                            var list;
                            return __generator(this, function (_b) {
                                switch (_b.label) {
                                    case 0:
                                        if (!(n === null || n === void 0 ? void 0 : n.id))
                                            return [2 /*return*/, "continue"];
                                        return [4 /*yield*/, api_1.api.markNotificationRead(n.id)];
                                    case 1:
                                        _b.sent();
                                        list = (this_1.data.list || []).map(function (x) { return (x.id === n.id ? __assign(__assign({}, x), { isRead: true }) : x); });
                                        this_1.setData({ list: list }, function () { return _this.rebuildDerived(); });
                                        return [2 /*return*/];
                                }
                            });
                        };
                        this_1 = this;
                        _i = 0, unread_1 = unread;
                        _a.label = 3;
                    case 3:
                        if (!(_i < unread_1.length)) return [3 /*break*/, 6];
                        n = unread_1[_i];
                        return [5 /*yield**/, _loop_1(n)];
                    case 4:
                        _a.sent();
                        _a.label = 5;
                    case 5:
                        _i++;
                        return [3 /*break*/, 3];
                    case 6: return [3 /*break*/, 9];
                    case 7:
                        err_2 = _a.sent();
                        wx.showToast({ title: (err_2 === null || err_2 === void 0 ? void 0 : err_2.message) || '部分操作失败', icon: 'none' });
                        return [3 /*break*/, 9];
                    case 8:
                        this.setData({ markAllLoading: false });
                        this.fetchList(true);
                        return [7 /*endfinally*/];
                    case 9: return [2 /*return*/];
                }
            });
        });
    },
    rebuildDerived: function () {
        var list = Array.isArray(this.data.list) ? this.data.list : [];
        var unreadList = list.filter(function (n) { return !n.isRead; });
        var readAll = list.filter(function (n) { return !!n.isRead; });
        var unreadCount = unreadList.length;
        var readCount = readAll.length;
        var unreadSub = unreadCount > 0 ? '优先处理' : '已清空';
        var facets = getReadFacets(readAll);
        var readTypeFilter = (this.data.readTypeFilter || 'all').toString();
        if (readTypeFilter !== 'all' && facets.total > 0 && !facets.items.some(function (i) { return i.type === readTypeFilter; })) {
            readTypeFilter = 'all';
        }
        var readFiltered = readTypeFilter === 'all' ? readAll : readAll.filter(function (n) { return n.typeKey === readTypeFilter; });
        var readFilteredCount = readFiltered.length;
        var self = this;
        if (!self.__expandedReadIds)
            self.__expandedReadIds = new Set();
        var expanded = self.__expandedReadIds;
        var groups = groupByType(readFiltered).map(function (g) {
            var sorted = sortReadItems(g.items, 'time');
            var items = sorted.map(function (n) { return (__assign(__assign({}, n), { expanded: expanded.has(n.id) })); });
            return {
                type: g.type,
                label: TYPE_LABEL[g.type] || g.type,
                count: items.length,
                items: items
            };
        });
        var typeLabel = readTypeFilter === 'all' ? '全部' : (TYPE_LABEL[readTypeFilter] || readTypeFilter);
        var readSub = '按通知类型归档展示';
        if (readAll.length === 0) {
            readSub = '暂无已读通知';
        }
        else {
            readSub = "\u5171 ".concat(readFilteredCount, "/").concat(readAll.length, " \u6761 \u00B7 ").concat(typeLabel);
        }
        this.setData({
            unreadList: unreadList,
            readAll: readAll,
            unreadCount: unreadCount,
            readCount: readCount,
            unreadSub: unreadSub,
            readSub: readSub,
            readTypeFacets: facets,
            readTypeFilter: readTypeFilter,
            readGroups: groups,
            readFilteredCount: readFilteredCount
        });
    },
    fetchList: function () {
        return __awaiter(this, arguments, void 0, function (force) {
            var self, now, lastAt, isFirstLoad, res, rawList, list, tab, preset, err_3;
            var _this = this;
            if (force === void 0) { force = false; }
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (this.data.loading)
                            return [2 /*return*/];
                        self = this;
                        now = Date.now();
                        lastAt = Number(self.__lastLoadedAt || 0) || 0;
                        isFirstLoad = !this.data.inited;
                        if (!force && !isFirstLoad && now - lastAt < 12000)
                            return [2 /*return*/];
                        self.__lastLoadedAt = now;
                        this.setData({ loading: true, errorMsg: '' });
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, 4, 5]);
                        return [4 /*yield*/, api_1.api.getNotifications({ include_dismissed: 1, limit: 200 })];
                    case 2:
                        res = (_a.sent());
                        rawList = Array.isArray(res) ? res : [];
                        list = rawList
                            .map(function (n) {
                            var id = toInt(n === null || n === void 0 ? void 0 : n.id);
                            if (!id)
                                return null;
                            var title = ((n === null || n === void 0 ? void 0 : n.title) || '通知').toString();
                            var content = ((n === null || n === void 0 ? void 0 : n.content) || '').toString();
                            var typeKey = normalizeType(n === null || n === void 0 ? void 0 : n.n_type);
                            var priority = toInt(n === null || n === void 0 ? void 0 : n.priority);
                            var createdAt = ((n === null || n === void 0 ? void 0 : n.created_at) || '').toString();
                            var isRead = !!(n === null || n === void 0 ? void 0 : n.is_read);
                            return {
                                id: id,
                                title: title,
                                content: content,
                                typeKey: typeKey,
                                typeLabel: TYPE_LABEL[typeKey] || '信息',
                                priority: priority,
                                createdAt: createdAt,
                                timeText: fmtTime(createdAt),
                                timeValue: toTimeValue(createdAt),
                                isRead: isRead,
                                snippet: snippetText(content, 70)
                            };
                        })
                            .filter(function (x) { return !!x; });
                        tab = this.data.tab;
                        preset = (self.__presetTab || '');
                        if (isFirstLoad) {
                            if (preset === 'read' || preset === 'unread')
                                tab = preset;
                            else
                                tab = list.some(function (n) { return !n.isRead; }) ? 'unread' : 'read';
                        }
                        this.setData({ list: list, tab: tab, inited: true }, function () { return _this.rebuildDerived(); });
                        return [3 /*break*/, 5];
                    case 3:
                        err_3 = _a.sent();
                        this.setData({ errorMsg: (err_3 === null || err_3 === void 0 ? void 0 : err_3.message) || '网络异常：无法加载通知' });
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
