"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.normalizeAnswerCardKey = normalizeAnswerCardKey;
exports.getAnswerCardHidden = getAnswerCardHidden;
exports.toggleAnswerCardHidden = toggleAnswerCardHidden;
exports.resetAnswerCardHidden = resetAnswerCardHidden;
function normalizeAnswerCardKey(questionKey) {
    if (questionKey == null)
        return '';
    return String(questionKey).trim();
}
function cloneAnswerCardHiddenMap(hiddenMap) {
    var current = hiddenMap || {};
    return Object.keys(current).reduce(function (next, key) {
        next[key] = current[key];
        return next;
    }, {});
}
function getAnswerCardHidden(hiddenMap, questionKey) {
    var key = normalizeAnswerCardKey(questionKey);
    if (!key || !hiddenMap)
        return false;
    return hiddenMap[key] === true;
}
function toggleAnswerCardHidden(hiddenMap, questionKey) {
    var key = normalizeAnswerCardKey(questionKey);
    var current = hiddenMap || {};
    var next = cloneAnswerCardHiddenMap(current);
    if (!key)
        return next;
    next[key] = !getAnswerCardHidden(current, key);
    return next;
}
function resetAnswerCardHidden(hiddenMap, questionKey) {
    var current = hiddenMap || {};
    if (questionKey == null)
        return {};
    var key = normalizeAnswerCardKey(questionKey);
    if (!key)
        return cloneAnswerCardHiddenMap(current);
    return Object.keys(current).reduce(function (next, itemKey) {
        if (itemKey !== key) {
            next[itemKey] = current[itemKey];
        }
        return next;
    }, {});
}
