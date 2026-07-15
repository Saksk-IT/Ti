"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.wechatLogin = wechatLogin;
exports.checkLogin = checkLogin;
exports.logout = logout;
var api_1 = require("./api");
// 微信登录
function wechatLogin() {
    return new Promise(function (resolve, reject) {
        wx.login({
            success: function (res) {
                if (res.code) {
                    // 直接使用 code 登录，不强制获取用户信息
                    // 首次未绑定时：由后端返回 need_bind，让用户选择创建/绑定
                    api_1.api.wechatLogin(res.code, undefined, false)
                        .then(function (data) {
                        if (data && data.need_bind && data.wechat_temp_token) {
                            wx.setStorageSync('wechatTempToken', data.wechat_temp_token);
                            resolve('need_bind');
                            return;
                        }
                        if (!data || !data.token) {
                            console.error('登录返回数据无效:', data);
                            reject(new Error('登录失败：服务器返回数据异常'));
                            return;
                        }
                        wx.setStorageSync('token', data.token);
                        if (data.user_info)
                            wx.setStorageSync('userInfo', data.user_info);
                        resolve('success');
                    })
                        .catch(function (err) {
                        console.error('登录API调用失败:', err);
                        reject(err);
                    });
                }
                else {
                    console.error('获取微信登录code失败:', res);
                    reject(new Error('获取微信登录code失败'));
                }
            },
            fail: function (err) {
                console.error('wx.login调用失败:', err);
                reject(new Error('微信登录失败，请稍后重试'));
            }
        });
    });
}
// 检查登录状态
function checkLogin() {
    var token = wx.getStorageSync('token');
    return !!token;
}
// 退出登录
function logout() {
    wx.removeStorageSync('token');
    wx.removeStorageSync('userInfo');
}
