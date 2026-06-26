"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
var theme_1 = require("../utils/theme");
var SWITCH_DELAY_MS = 90;
Component({
    data: {
        selected: 0,
        switching: false,
        switchingIndex: -1,
        isDarkMode: false,
        themeClass: '',
        themeStyleClass: '',
        list: [
            {
                pagePath: '/pages/hub-v2/hub-v2',
                iconPath: '/images/tabbar/home.png',
                selectedIconPath: '/images/tabbar/home-active.png',
                text: '首页'
            },
            {
                pagePath: '/pages/public-bank-v2/public-bank-v2',
                iconPath: '/images/tabbar/plaza.png',
                selectedIconPath: '/images/tabbar/plaza-active.png',
                text: '题库广场'
            },
            {
                pagePath: '/pages/my-banks-v2/my-banks-v2',
                iconPath: '/images/tabbar/banks.png',
                selectedIconPath: '/images/tabbar/banks-active.png',
                text: '我的题库'
            },
            {
                pagePath: '/pages/campus/campus',
                iconPath: '/images/tabbar/campus.png',
                selectedIconPath: '/images/tabbar/campus-active.png',
                text: '校园'
            },
            {
                pagePath: '/pages/mine/mine',
                iconPath: '/images/tabbar/mine.png',
                selectedIconPath: '/images/tabbar/mine-active.png',
                text: '我的'
            }
        ]
    },
    lifetimes: {
        attached: function () {
            var _this = this;
            this.syncTheme();
            var off = theme_1.themeManager.onThemeChange(function () { return _this.syncTheme(); });
            this.__themeOff = off;
        },
        detached: function () {
            var off = this.__themeOff;
            if (typeof off === 'function')
                off();
        }
    },
    methods: {
        syncTheme: function () {
            try {
                var themeData = theme_1.themeManager.getPageData();
                this.setData({
                    isDarkMode: themeData.isDarkMode,
                    themeClass: themeData.themeClass,
                    themeStyleClass: themeData.themeStyleClass
                });
            }
            catch (e) { }
        },
        onTabTap: function (e) {
            var _this = this;
            if (this.data.switching)
                return;
            var index = Number(e.currentTarget.dataset.index);
            var path = String(e.currentTarget.dataset.path || '');
            if (!Number.isInteger(index) || !path)
                return;
            if (index === this.data.selected)
                return;
            this.setData({
                selected: index,
                switching: true,
                switchingIndex: index
            });
            setTimeout(function () {
                wx.switchTab({
                    url: path,
                    fail: function () {
                        _this.setData({
                            switching: false,
                            switchingIndex: -1
                        });
                    }
                });
            }, SWITCH_DELAY_MS);
        }
    }
});
