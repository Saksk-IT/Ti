"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
// logs.ts
// const util = require('../../utils/util.js')
var util_1 = require("../../utils/util");
Page({
    data: {
        logs: []
    },
    onLoad: function () {
        this.loadLogs();
    },
    onShow: function () {
        this.loadLogs();
    },
    loadLogs: function () {
        var logs = (wx.getStorageSync('logs') || []).map(function (log) {
            return {
                date: (0, util_1.formatTime)(new Date(log)),
                timeStamp: log
            };
        });
        this.setData({ logs: logs });
    }
});
