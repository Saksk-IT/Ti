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
var theme_1 = require("../../utils/theme");
var web_1 = require("../../utils/web");
function buildExternalWebUrl(next) {
    var origin = String((0, api_1.getApiOrigin)() || '').trim().replace(/\/$/, '');
    var path = (0, web_1.normalizeWebNextPath)(next, '/hub');
    if (!origin)
        return path;
    var raw = "".concat(origin).concat(path);
    if (/([?&])from=/.test(raw))
        return raw;
    return "".concat(raw).concat(raw.includes('?') ? '&' : '?', "from=miniapp");
}
Page({
    data: {
        name: '',
        description: '',
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
        var self = this;
        if (!self.__webCreateHintShown) {
            self.__webCreateHintShown = true;
            wx.showToast({ title: '提示：网页端支持更完整的题库导入与管理', icon: 'none' });
        }
    },
    onNameInput: function (e) {
        var _a;
        this.setData({ name: String(((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.value) || '') });
    },
    onDescInput: function (e) {
        var _a;
        this.setData({ description: String(((_a = e === null || e === void 0 ? void 0 : e.detail) === null || _a === void 0 ? void 0 : _a.value) || '') });
    },
    onCycleThemeModeTap: function () {
        var mode = theme_1.themeManager.cycleMode();
        this.setData(__assign(__assign({}, (theme_1.themeManager.getPageData())), { themeMode: mode }));
    },
    onCancel: function () {
        wx.navigateBack();
    },
    onOpenWebCreate: function () {
        var url = buildExternalWebUrl('/user/banks');
        wx.showModal({
            title: '请前往网页端',
            content: '小程序内不再内嵌网页端。点击「复制链接」后在浏览器打开并登录。',
            confirmText: '复制链接',
            cancelText: '关闭',
            success: function (res) {
                if (!res.confirm)
                    return;
                wx.setClipboardData({
                    data: url,
                    success: function () { return wx.showToast({ title: '链接已复制', icon: 'success' }); },
                    fail: function () { return wx.showToast({ title: '复制失败', icon: 'none' }); }
                });
            }
        });
    },
    onSubmit: function () {
        return __awaiter(this, void 0, void 0, function () {
            var name, description, res, id_1, e_1;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (this.data.creating)
                            return [2 /*return*/];
                        name = String(this.data.name || '').trim();
                        description = String(this.data.description || '').trim();
                        if (!name) {
                            wx.showToast({ title: '题库名称不能为空', icon: 'none' });
                            return [2 /*return*/];
                        }
                        if (name.length < 2 || name.length > 50) {
                            wx.showToast({ title: '题库名称需要 2-50 个字符', icon: 'none' });
                            return [2 /*return*/];
                        }
                        if (description.length > 200) {
                            wx.showToast({ title: '描述不能超过 200 个字符', icon: 'none' });
                            return [2 /*return*/];
                        }
                        this.setData({ creating: true });
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, , 4]);
                        return [4 /*yield*/, api_1.api.createBank({ name: name, description: description })];
                    case 2:
                        res = _a.sent();
                        id_1 = Number((res === null || res === void 0 ? void 0 : res.id) || 0);
                        if (!Number.isFinite(id_1) || id_1 <= 0) {
                            wx.showToast({ title: '创建成功，但未返回题库ID', icon: 'none' });
                            this.setData({ creating: false });
                            return [2 /*return*/];
                        }
                        wx.showToast({ title: '创建成功', icon: 'success' });
                        setTimeout(function () {
                            wx.redirectTo({ url: "/pages/bank-detail/bank-detail?id=".concat(id_1) });
                        }, 400);
                        return [3 /*break*/, 4];
                    case 3:
                        e_1 = _a.sent();
                        wx.showToast({ title: (e_1 && e_1.message) || '创建失败', icon: 'none' });
                        this.setData({ creating: false });
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        });
    }
});
