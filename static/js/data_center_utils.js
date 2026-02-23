/**
 * data_center_utils.js — 数据中心工具函数
 * 通过 window.DCUtils 命名空间暴露给其他模块
 */
(function () {
  'use strict';

  function clamp01(n) {
    return Math.max(0, Math.min(1, n));
  }

  function clamp100(n) {
    var v = Number(n || 0);
    if (!isFinite(v)) v = 0;
    return Math.max(0, Math.min(100, v));
  }

  function getVar(name) {
    try {
      return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    } catch (e) {
      return '';
    }
  }

  function fmtDay(iso) {
    var s = String(iso || '');
    if (/^\d{4}-\d{2}-\d{2}/.test(s)) return s.slice(5, 10);
    return s;
  }

  function toInt(v) {
    var n = Number(v);
    if (!isFinite(n)) return 0;
    return Math.trunc(n);
  }

  function toNum(v) {
    var n = Number(v);
    return isFinite(n) ? n : 0;
  }

  function pickColor(hex, alpha) {
    var a = clamp01(alpha == null ? 1 : alpha);
    if (!hex) return 'rgba(17,24,39,' + a + ')';
    var h = String(hex).trim();
    if (h.startsWith('rgb')) return h;
    if (!h.startsWith('#')) return h;
    var v = h.slice(1);
    if (v.length === 3) v = v[0] + v[0] + v[1] + v[1] + v[2] + v[2];
    if (v.length !== 6) return h;
    var r = parseInt(v.slice(0, 2), 16);
    var g = parseInt(v.slice(2, 4), 16);
    var b = parseInt(v.slice(4, 6), 16);
    return 'rgba(' + r + ',' + g + ',' + b + ',' + a + ')';
  }

  function parseRgb(input) {
    var s = String(input || '').trim();
    if (!s) return null;
    if (s[0] === '#') {
      var v = s.slice(1);
      if (v.length === 3) v = v[0] + v[0] + v[1] + v[1] + v[2] + v[2];
      if (v.length !== 6) return null;
      var r = parseInt(v.slice(0, 2), 16);
      var g = parseInt(v.slice(2, 4), 16);
      var b = parseInt(v.slice(4, 6), 16);
      if (!isFinite(r) || !isFinite(g) || !isFinite(b)) return null;
      return [r, g, b];
    }
    var m = s.match(/^rgba?\\(\\s*([\\d.]+)\\s*,\\s*([\\d.]+)\\s*,\\s*([\\d.]+)(?:\\s*,\\s*([\\d.]+))?\\s*\\)$/i);
    if (m) {
      var r2 = Math.round(parseFloat(m[1]) || 0);
      var g2 = Math.round(parseFloat(m[2]) || 0);
      var b2 = Math.round(parseFloat(m[3]) || 0);
      return [Math.max(0, Math.min(255, r2)), Math.max(0, Math.min(255, g2)), Math.max(0, Math.min(255, b2))];
    }
    return null;
  }

  function relLuminance(rgb) {
    function chan(c) {
      var v = (c || 0) / 255;
      return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
    }
    return 0.2126 * chan(rgb[0]) + 0.7152 * chan(rgb[1]) + 0.0722 * chan(rgb[2]);
  }

  function contrastRatio(rgb1, rgb2) {
    var l1 = relLuminance(rgb1);
    var l2 = relLuminance(rgb2);
    var hi = Math.max(l1, l2);
    var lo = Math.min(l1, l2);
    return (hi + 0.05) / (lo + 0.05);
  }

  function mixRgb(a, b, t) {
    t = clamp01(t);
    return [
      Math.round(a[0] * (1 - t) + b[0] * t),
      Math.round(a[1] * (1 - t) + b[1] * t),
      Math.round(a[2] * (1 - t) + b[2] * t),
    ];
  }

  function grad(from, to, vertical) {
    if (!window.echarts || !echarts.graphic) return to;
    var v = vertical !== false;
    return new echarts.graphic.LinearGradient(0, 0, v ? 0 : 1, v ? 1 : 0, [
      { offset: 0, color: from },
      { offset: 1, color: to },
    ]);
  }

  // 暴露工具函数到全局命名空间
  window.DCUtils = {
    clamp01: clamp01,
    clamp100: clamp100,
    getVar: getVar,
    fmtDay: fmtDay,
    toInt: toInt,
    toNum: toNum,
    pickColor: pickColor,
    parseRgb: parseRgb,
    relLuminance: relLuminance,
    contrastRatio: contrastRatio,
    mixRgb: mixRgb,
    grad: grad
  };
})();
