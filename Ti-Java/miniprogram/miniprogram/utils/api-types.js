"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.extractData = extractData;
/**
 * 从 wx.request 的 result 中安全提取 data
 */
function extractData(res) {
    var _a, _b, _c, _d, _e;
    var d = res.data;
    if (!d)
        return { success: false, error: '空响应' };
    return {
        success: d.success === true || d.code === 0 || d.status === 'ok',
        data: ((_b = (_a = d.data) !== null && _a !== void 0 ? _a : d.result) !== null && _b !== void 0 ? _b : d),
        error: ((_d = (_c = d.error) !== null && _c !== void 0 ? _c : d.message) !== null && _d !== void 0 ? _d : d.msg),
        message: ((_e = d.message) !== null && _e !== void 0 ? _e : d.msg),
    };
}
