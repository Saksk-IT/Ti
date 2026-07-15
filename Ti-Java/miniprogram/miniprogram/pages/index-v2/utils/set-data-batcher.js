"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.createSetDataBatcher = createSetDataBatcher;
function mergePatch(target, incoming) {
    if (!incoming || typeof incoming !== 'object')
        return;
    Object.keys(incoming).forEach(function (key) {
        target[key] = incoming[key];
    });
}
function createSetDataBatcher(setData) {
    var scheduled = false;
    var pending = null;
    var flush = function () {
        scheduled = false;
        var current = pending;
        pending = null;
        if (!current)
            return;
        var callbacks = current.callbacks.slice();
        setData(current.patch, function () {
            callbacks.forEach(function (cb) {
                try {
                    cb();
                }
                catch (e) { }
            });
        });
    };
    var scheduleFlush = function () {
        if (scheduled)
            return;
        scheduled = true;
        Promise.resolve().then(flush);
    };
    return function (patch, callback, options) {
        var immediate = !!(options === null || options === void 0 ? void 0 : options.immediate);
        if (immediate) {
            setData(patch, callback);
            return;
        }
        if (!pending) {
            pending = { patch: {}, callbacks: [] };
        }
        mergePatch(pending.patch, patch || {});
        if (callback)
            pending.callbacks.push(callback);
        scheduleFlush();
    };
}
