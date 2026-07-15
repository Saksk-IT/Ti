"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
var theme_1 = require("../../utils/theme");
var FEATURE_COPY = {
    evaluation: {
        title: '一键教评',
        subtitle: '教评自动化能力正在接入，后续会在这里完成评价流程。',
        action: '功能建设中',
    },
    more: {
        title: '更多校园',
        subtitle: '考试安排、校历提醒等校园能力会逐步接入这里。',
        action: '等待接入',
    },
};
function featureCopy(key) {
    return FEATURE_COPY[key] || FEATURE_COPY.more;
}
Page({
    data: {
        pageTitle: '校园功能',
        title: '更多校园',
        subtitle: '校园能力正在接入。',
        action: '功能建设中',
    },
    onLoad: function (options) {
        var key = String((options === null || options === void 0 ? void 0 : options.feature) || '').trim();
        var copy = featureCopy(key);
        this.setData(Object.assign({
            pageTitle: copy.title,
            title: copy.title,
            subtitle: copy.subtitle,
            action: copy.action,
        }, theme_1.themeManager.getPageData()));
    },
    onShow: function () {
        try {
            this.setData(Object.assign({}, theme_1.themeManager.getPageData()));
        }
        catch (e) { }
    },
    onCycleThemeModeTap: function () {
        var mode = theme_1.themeManager.cycleMode();
        this.setData(Object.assign(Object.assign({}, theme_1.themeManager.getPageData()), { themeMode: mode }));
    },
});
