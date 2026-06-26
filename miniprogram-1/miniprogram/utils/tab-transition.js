"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.restartTabPageTransition = restartTabPageTransition;
var TAB_TRANSITION_CLASS = 'tab-switch-enter';
function restartTabPageTransition(page) {
    if (!page || typeof page.setData !== 'function')
        return;
    page.setData({ tabPageTransitionClass: '' }, function () {
        setTimeout(function () {
            page.setData({ tabPageTransitionClass: TAB_TRANSITION_CLASS });
        }, 16);
    });
}
