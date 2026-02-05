"use strict";
function buildLayout(compact) {
    var rectLeft = 0;
    try {
        var rect = wx.getMenuButtonBoundingClientRect();
        rectLeft = Number(rect === null || rect === void 0 ? void 0 : rect.left) || 0;
    }
    catch (e) { }
    // wx.getSystemInfo 已废弃：优先使用 getDeviceInfo/getWindowInfo
    var platform = '';
    try {
        var di = wx.getDeviceInfo ? wx.getDeviceInfo() : null;
        if (di && di.platform)
            platform = String(di.platform);
    }
    catch (e) { }
    var windowWidth = 0;
    var safeAreaTop = 0;
    try {
        var wi = wx.getWindowInfo ? wx.getWindowInfo() : null;
        var ww = wi && wi.windowWidth;
        var st = wi && wi.safeArea && wi.safeArea.top;
        windowWidth = Number(ww);
        safeAreaTop = Number(st);
    }
    catch (e) { }
    // 兼容旧基础库：兜底使用 getSystemInfoSync（旧版不算废弃）
    if (!Number.isFinite(windowWidth) || windowWidth <= 0) {
        try {
            var si = wx.getSystemInfoSync();
            windowWidth = Number(si.windowWidth);
            safeAreaTop = Number(si.safeArea && si.safeArea.top);
            if (!platform)
                platform = String(si.platform || '');
        }
        catch (e) { }
    }
    var isAndroid = platform === 'android';
    var isDevtools = platform === 'devtools';
    var padRight = Math.max(0, (Number.isFinite(windowWidth) ? windowWidth : 0) - rectLeft);
    var top = Number.isFinite(safeAreaTop) && safeAreaTop > 0 ? safeAreaTop : 0;
    var styleVars = "--nb-pad-right: ".concat(padRight, "px;").concat(top > 0 ? "--nb-safe-top: ".concat(top, "px;") : "");
    return {
        ios: !isAndroid,
        innerPaddingRight: "".concat(styleVars, "padding-right: ").concat(padRight, "px"),
        leftWidth: compact ? '' : "width: ".concat(padRight, "px"),
        safeAreaTop: isDevtools || isAndroid ? "height: calc(var(--height) + ".concat(top, "px); padding-top: ").concat(top, "px") : ""
    };
}
var DEFAULT_LAYOUT = buildLayout(false);
Component({
    options: {
        multipleSlots: true // 在组件定义时的选项中启用多slot支持
    },
    /**
     * 组件的属性列表
     */
    properties: {
        extClass: {
            type: String,
            value: ''
        },
        compact: {
            type: Boolean,
            value: false
        },
        title: {
            type: String,
            value: ''
        },
        background: {
            type: String,
            value: ''
        },
        color: {
            type: String,
            value: ''
        },
        back: {
            type: Boolean,
            value: true
        },
        loading: {
            type: Boolean,
            value: false
        },
        homeButton: {
            type: Boolean,
            value: false,
        },
        animated: {
            // 显示隐藏的时候opacity动画效果
            type: Boolean,
            value: true
        },
        show: {
            // 显示隐藏导航，隐藏的时候navigation-bar的高度占位还在
            type: Boolean,
            value: true,
            observer: '_showChange'
        },
        // back为true的时候，返回的页面深度
        delta: {
            type: Number,
            value: 1
        },
    },
    /**
     * 组件的初始数据
     */
    data: {
        displayStyle: '',
        ios: DEFAULT_LAYOUT.ios,
        innerPaddingRight: DEFAULT_LAYOUT.innerPaddingRight,
        leftWidth: DEFAULT_LAYOUT.leftWidth,
        safeAreaTop: DEFAULT_LAYOUT.safeAreaTop
    },
    lifetimes: {
        attached: function () {
            var next = buildLayout(!!this.properties.compact);
            var cur = this.data || {};
            if (cur.ios === next.ios &&
                cur.innerPaddingRight === next.innerPaddingRight &&
                cur.leftWidth === next.leftWidth &&
                cur.safeAreaTop === next.safeAreaTop)
                return;
            this.setData(next);
        },
    },
    /**
     * 组件的方法列表
     */
    methods: {
        _showChange: function (show) {
            var animated = this.data.animated;
            var displayStyle = '';
            if (animated) {
                displayStyle = "opacity: ".concat(show ? '1' : '0', ";transition:opacity 0.5s;");
            }
            else {
                displayStyle = "display: ".concat(show ? '' : 'none');
            }
            this.setData({
                displayStyle: displayStyle
            });
        },
        back: function () {
            var data = this.data;
            if (data.delta) {
                wx.navigateBack({
                    delta: data.delta
                });
            }
            this.triggerEvent('back', { delta: data.delta }, {});
        }
    },
});
