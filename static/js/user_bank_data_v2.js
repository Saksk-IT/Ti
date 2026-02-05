(function () {
  'use strict';

  function clamp(val, min, max) {
    return Math.max(min, Math.min(max, val));
  }

  function getVar(name) {
    try {
      return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    } catch (err) {
      return '';
    }
  }

  function pickColor(hex, alpha) {
    var a = clamp(alpha == null ? 1 : alpha, 0, 1);
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

  function toNum(v) {
    var n = Number(v || 0);
    return Number.isFinite(n) ? n : 0;
  }

  function fmtCount(v) {
    var n = toNum(v);
    try {
      return n.toLocaleString('zh-CN');
    } catch (err) {
      return String(n);
    }
  }

  function fmtPercent(v) {
    return toNum(v).toFixed(1) + '%';
  }

  function fmtDay(iso) {
    var s = String(iso || '');
    if (/^\d{4}-\d{2}-\d{2}/.test(s)) return s.slice(5, 10);
    return s;
  }

  function fmtDateTime(iso) {
    var s = String(iso || '');
    if (!s) return '—';
    if (/^\d{4}-\d{2}-\d{2}/.test(s)) return s.slice(0, 16).replace('T', ' ');
    return s;
  }

  function escapeHtml(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/\"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function shortText(value, maxLen) {
    var s = String(value == null ? '' : value);
    var n = maxLen == null ? 10 : Number(maxLen);
    if (!Number.isFinite(n)) n = 10;
    n = Math.max(0, Math.floor(n));
    if (n <= 0) return '';
    return s.length > n ? s.slice(0, n) + '…' : s;
  }

  function isCompactChart(chartId) {
    try {
      var el = document.getElementById(chartId);
      if (el && el.clientWidth && el.clientWidth < 420) return true;
    } catch (err) {}
    try {
      return !!(window.matchMedia && window.matchMedia('(max-width: 520px)').matches);
    } catch (err) {
      return false;
    }
  }

  function fmtDayLabel(v) {
    var s = String(v || '');
    if (/^\d{4}-\d{2}-\d{2}/.test(s)) return s.slice(5, 10);
    return s;
  }

  function parseLooseDate(s) {
    if (!s) return null;
    var str = String(s);
    var iso = str.includes('T') ? str : str.replace(' ', 'T');
    var d = new Date(iso);
    if (Number.isNaN(d.getTime())) return null;
    return d;
  }

  function daysSince(iso) {
    var d = parseLooseDate(iso);
    if (!d) return null;
    var diff = Date.now() - d.getTime();
    if (!Number.isFinite(diff)) return null;
    return Math.max(0, Math.floor(diff / 86400000));
  }

  function calcActiveDays(trend) {
    return (trend || []).filter(function (d) {
      return toNum(d.answered) > 0;
    }).length;
  }

  function calcRecentAnswered(trend, days) {
    var list = Array.isArray(trend) ? trend : [];
    if (!list.length) return 0;
    var slice = list.slice(Math.max(0, list.length - days));
    return slice.reduce(function (sum, item) {
      return sum + toNum(item.answered);
    }, 0);
  }

  function setText(id, value) {
    var el = document.getElementById(id);
    if (el) el.textContent = value == null ? '' : String(value);
  }

  function setBar(id, percent) {
    var el = document.getElementById(id);
    if (!el) return;
    var v = clamp(toNum(percent), 0, 100);
    el.style.width = v.toFixed(1) + '%';
  }

  var api = (function () {
    try {
      if (window.UserBankDataV2 && typeof window.UserBankDataV2 === 'object') return window.UserBankDataV2;
    } catch (err) {}
    return {};
  })();
  try {
    window.UserBankDataV2 = api;
  } catch (err) {}

  var root = null;
  var mode = 'user_bank';
  var bankId = null;
  var subjectName = '';
  var subtab = 'global';
  var windowDays = 30;
  var bankTotal = 0;
  var bankFavorites = 0;
  var bankMistakes = 0;

  var loadedKeyByTab = { global: '', mistakes: '', favorites: '' };
  var pendingCtx = null;
  var inflight = null;
  var themeObserver = null;
  var themeDirty = false;
  var resizeBound = false;

  function resolveRoot() {
    if (root) return root;
    root = document.querySelector('.ubdv2-shell');
    return root;
  }

  function isVisible(el) {
    try {
      return !!(el && el.getClientRects && el.getClientRects().length);
    } catch (err) {
      return false;
    }
  }

  function readContextFromDom() {
    var el = resolveRoot();
    var payload = window.__UBDV2__ || {};
    var modeAttr = null;
    var subj = null;
    try {
      modeAttr = payload.mode || (el ? el.getAttribute('data-ubdv2-mode') || el.getAttribute('data-mode') : null);
      subj = payload.subject_name || payload.subjectName || (el ? el.getAttribute('data-subject-name') : null);
    } catch (err) {
      modeAttr = payload.mode || null;
      subj = payload.subject_name || payload.subjectName || null;
    }
    return {
      mode: modeAttr,
      bank_id: payload.bank_id || (el ? el.getAttribute('data-bank-id') : null),
      subject_name: subj,
      subtab: payload.subtab || (el ? el.getAttribute('data-subtab') : null),
      window_days: payload.window_days || (el ? el.getAttribute('data-days') : null),
      bank_total: payload.bank_total,
      bank_favorites: payload.bank_favorites,
      bank_mistakes: payload.bank_mistakes,
      force: false,
    };
  }

  function normalizeContext(input) {
    input = input || {};

    var rawMode =
      input.mode != null
        ? input.mode
        : input.ubdv2_mode != null
          ? input.ubdv2_mode
          : input.data_mode != null
            ? input.data_mode
            : input.kind;
    var bid = input.bank_id != null ? input.bank_id : input.bankId;
    var subj =
      input.subject_name != null
        ? input.subject_name
        : input.subjectName != null
          ? input.subjectName
          : input.subject != null
            ? input.subject
            : input.subject_name_text;
    var st = input.subtab != null ? input.subtab : input.tab;
    var days = input.window_days != null ? input.window_days : (input.windowDays != null ? input.windowDays : input.days);

    var nextSubjectName = subj != null ? String(subj) : '';
    nextSubjectName = nextSubjectName.trim();

    var nextBankId = bid != null ? String(bid) : '';
    if (!nextBankId) nextBankId = '';

    var nextMode = String(rawMode || '').trim().toLowerCase();
    if (nextMode !== 'subject') nextMode = nextSubjectName ? 'subject' : 'user_bank';
    if (!nextSubjectName) nextMode = 'user_bank';

    var nextTab = String(st || '').trim().toLowerCase();
    if (nextTab !== 'mistakes' && nextTab !== 'favorites') nextTab = 'global';

    var nextDays = toNum(days);
    if (![7, 14, 30, 90].includes(nextDays)) nextDays = nextTab === 'global' ? 90 : 30;

    var ctx = {
      mode: nextMode,
      bank_id: nextBankId,
      subject_name: nextSubjectName,
      subtab: nextTab,
      window_days: nextDays,
      bank_total: input.bank_total != null ? toNum(input.bank_total) : (input.bankTotal != null ? toNum(input.bankTotal) : 0),
      bank_favorites: input.bank_favorites != null ? toNum(input.bank_favorites) : (input.bankFavorites != null ? toNum(input.bankFavorites) : 0),
      bank_mistakes: input.bank_mistakes != null ? toNum(input.bank_mistakes) : (input.bankMistakes != null ? toNum(input.bankMistakes) : 0),
      force: !!input.force,
    };

    return ctx;
  }

  var charts = {};

  function getChart(id) {
    if (!window.echarts) return null;
    var el = document.getElementById(id);
    if (!el) return null;
    if (!charts[id]) charts[id] = echarts.init(el);
    return charts[id];
  }

  function renderEmpty(chart, text) {
    if (!chart) return;
    chart.clear();
    chart.setOption({
      title: {
        text: text || '暂无数据',
        left: 'center',
        top: 'middle',
        textStyle: {
          color: getVar('--app-muted') || '#6b7280',
          fontSize: 12,
          fontWeight: 700,
        },
      },
    });
  }

  async function fetchJson(url) {
    var res = await fetch(url, { credentials: 'same-origin' });
    var js = await res.json().catch(function () {
      return {};
    });
    var ok = res.ok && js && (js.code === 0 || js.status === 'success');
    if (!ok) throw new Error((js && (js.message || js.msg)) || '请求失败');
    return js;
  }

  function renderAdvice(list, wrapId) {
    var wrap = document.getElementById(wrapId);
    if (!wrap) return;
    var items = Array.isArray(list) ? list : [];
    if (!items.length) {
      wrap.innerHTML = '<div class="ubdv2-muted">暂无建议</div>';
      return;
    }
    wrap.innerHTML = items
      .map(function (item) {
        var title = item && item.title ? String(item.title) : '建议';
        var content = item && item.content ? String(item.content) : '';
        return (
          '<div class="ubdv2-advice-item">' +
          '<div class="t">' +
          escapeHtml(title) +
          '</div>' +
          '<div class="c">' +
          escapeHtml(content) +
          '</div>' +
          '</div>'
        );
      })
      .join('');
  }

  function renderCalendarChart(trend, chartId) {
    var chart = getChart(chartId);
    if (!chart) return;
    var list = Array.isArray(trend) ? trend : [];
    if (!list.length) return renderEmpty(chart, '暂无作答记录');

    var isCompact = isCompactChart(chartId);
    var side = isCompact ? 10 : 16;
    var topPad = isCompact ? 22 : 16;
    var bottomPad = isCompact ? 10 : 12;
    var labelFs = isCompact ? 10 : 11;
    var leftPad = isCompact ? 52 : 68;

    var data = list.map(function (d) {
      return [String(d.day || ''), toNum(d.answered)];
    });

    var primary = getVar('--app-primary') || '#111827';
    var border = pickColor(getVar('--app-border') || '#e5e7eb', 0.9);
    var text = getVar('--app-text') || '#111827';
    var muted = getVar('--app-muted') || '#6b7280';

    var maxVal = Math.max.apply(
      null,
      data.map(function (d) {
        return d[1];
      }),
    );

    chart.setOption(
      {
        tooltip: {
          trigger: 'item',
          backgroundColor: pickColor(getVar('--app-surface') || '#ffffff', 0.96),
          borderColor: border,
          textStyle: { color: text, fontSize: 12 },
          formatter: function (p) {
            var v = p && p.value ? p.value : [];
            var day = v[0] || '';
            var cnt = v[1] || 0;
            return escapeHtml(String(day)) + '<br/>作答：' + fmtCount(cnt);
          },
        },
        visualMap: {
          min: 0,
          max: maxVal > 0 ? maxVal : 10,
          show: false,
          inRange: { color: [pickColor(primary, 0.08), pickColor(primary, 0.55)] },
        },
        calendar: {
          top: topPad,
          left: leftPad,
          right: side,
          bottom: bottomPad,
          cellSize: ['auto', 'auto'],
          range: [data[0][0], data[data.length - 1][0]],
          itemStyle: {
            borderWidth: 1,
            borderColor: border,
            color: pickColor(getVar('--app-surface') || '#ffffff', 0.45),
          },
          splitLine: { lineStyle: { color: border } },
          yearLabel: { show: false },
          monthLabel: { color: muted, fontSize: labelFs },
          dayLabel: {
            show: true,
            position: 'start',
            margin: isCompact ? 10 : 14,
            nameMap: ['周日', '周一', '周二', '周三', '周四', '周五', '周六'],
            color: muted,
            fontSize: labelFs,
          },
        },
        series: [
          {
            type: 'heatmap',
            coordinateSystem: 'calendar',
            data: data,
            emphasis: { itemStyle: { shadowBlur: 10, shadowColor: pickColor(primary, 0.25) } },
          },
        ],
      },
      true,
    );
  }

  function renderGaugeChart(stats, chartId) {
    var chart = getChart(chartId);
    if (!chart) return;

    var isCompact = isCompactChart(chartId);
    var accuracy = toNum(stats.accuracy);
    var completion = toNum(stats.completion);
    var score = clamp(accuracy * 0.65 + completion * 0.35, 0, 100);

    var primary = getVar('--app-primary') || '#111827';
    var cta = getVar('--app-cta') || primary;
    var border = pickColor(getVar('--app-border') || '#e5e7eb', 0.9);
    var text = getVar('--app-text') || '#111827';
    var muted = getVar('--app-muted') || '#6b7280';
    var axisFs = isCompact ? 9 : 10;
    var titleFs = isCompact ? 11 : 12;
    var detailFs = isCompact ? 20 : 22;
    var metaFs = isCompact ? 11 : 12;

    chart.setOption(
      {
        series: [
          {
            type: 'gauge',
            startAngle: 220,
            endAngle: -40,
            min: 0,
            max: 100,
            radius: '96%',
            pointer: { show: true, length: '64%', width: 4 },
            progress: { show: true, width: 10, roundCap: true, itemStyle: { color: cta } },
            axisLine: { lineStyle: { width: 10, color: [[1, pickColor(primary, 0.12)]] } },
            axisTick: { show: false },
            splitLine: { show: false },
            axisLabel: { color: muted, fontSize: axisFs, distance: 18 },
            anchor: { show: false },
            title: { show: true, offsetCenter: [0, '56%'], color: muted, fontSize: titleFs, fontWeight: 800 },
            detail: {
              valueAnimation: true,
              formatter: function (v) {
                return v.toFixed(1) + '%';
              },
              offsetCenter: [0, '30%'],
              color: text,
              fontSize: detailFs,
              fontWeight: 950,
            },
            data: [{ value: score, name: '掌握指数' }],
          },
        ],
        graphic: [
          {
            type: 'text',
            left: 'center',
            top: '84%',
            style: {
              text: '正确率 ' + fmtPercent(accuracy) + ' · 覆盖率 ' + fmtPercent(completion),
              fill: muted,
              fontSize: metaFs,
              fontWeight: 700,
            },
          },
        ],
      },
      true,
    );
  }

  function renderAnsweredTrend(trend, chartId) {
    var chart = getChart(chartId);
    if (!chart) return;
    var list = Array.isArray(trend) ? trend : [];
    if (!list.length) return renderEmpty(chart, '暂无趋势数据');

    var isCompact = isCompactChart(chartId);
    var x = list.map(function (d) {
      return fmtDay(d.day);
    });
    var answered = list.map(function (d) {
      return toNum(d.answered);
    });
    var acc = list.map(function (d) {
      var a = toNum(d.answered);
      var c = toNum(d.correct);
      return a > 0 ? (c * 100) / a : 0;
    });

    var primary = getVar('--app-primary') || '#111827';
    var cta = getVar('--app-cta') || primary;
    var border = pickColor(getVar('--app-border') || '#e5e7eb', 0.9);
    var text = getVar('--app-text') || '#111827';
    var muted = getVar('--app-muted') || '#6b7280';
    var labelFs = isCompact ? 10 : 12;
    var barW = isCompact ? 10 : 14;
    var sym = isCompact ? 4 : 6;
    var gridBottom = isCompact ? 22 : 10;
    var xAxisLabel = { color: muted, fontSize: labelFs, hideOverlap: true, formatter: fmtDayLabel };

    chart.setOption(
      {
        tooltip: {
          trigger: 'axis',
          backgroundColor: pickColor(getVar('--app-surface') || '#ffffff', 0.96),
          borderColor: border,
          textStyle: { color: text, fontSize: 12 },
        },
        grid: { left: 12, right: 12, top: 18, bottom: gridBottom, containLabel: true },
        xAxis: {
          type: 'category',
          data: x,
          axisLine: { lineStyle: { color: border } },
          axisLabel: xAxisLabel,
        },
        yAxis: [
          {
            type: 'value',
            min: 0,
            axisLine: { show: false },
            axisTick: { show: false },
            axisLabel: { color: muted, fontSize: labelFs },
            splitLine: { lineStyle: { color: border, type: 'dashed', opacity: 0.6 } },
          },
          {
            type: 'value',
            min: 0,
            max: 100,
            axisLine: { show: false },
            axisTick: { show: false },
            axisLabel: { color: muted, fontSize: labelFs, formatter: '{value}%' },
            splitLine: { show: false },
          },
        ],
        series: [
          {
            name: '作答量',
            type: 'bar',
            data: answered,
            barWidth: barW,
            itemStyle: { color: pickColor(primary, 0.55), borderRadius: [8, 8, 0, 0] },
          },
          {
            name: '正确率',
            type: 'line',
            yAxisIndex: 1,
            data: acc,
            smooth: true,
            symbol: 'circle',
            symbolSize: sym,
            lineStyle: { width: 2, color: cta },
            itemStyle: { color: cta },
          },
        ],
      },
      true,
    );
  }

  function renderTypeStructureChart(byType, chartId) {
    var chart = getChart(chartId);
    if (!chart) return;
    var list = Array.isArray(byType) ? byType.slice() : [];
    if (!list.length) return renderEmpty(chart, '暂无题型数据');

    var isCompact = isCompactChart(chartId);
    list.sort(function (a, b) {
      return toNum(b.total) - toNum(a.total);
    });

    var top = list.slice(0, 10);
    var x = top.map(function (r) {
      return String(r.q_type || '未知');
    });
    var correct = top.map(function (r) {
      return toNum(r.correct);
    });
    var wrong = top.map(function (r) {
      return toNum(r.wrong);
    });
    var completion = top.map(function (r) {
      return toNum(r.completion);
    });

    var primary = getVar('--app-primary') || '#111827';
    var cta = getVar('--app-cta') || primary;
    var border = pickColor(getVar('--app-border') || '#e5e7eb', 0.9);
    var text = getVar('--app-text') || '#111827';
    var muted = getVar('--app-muted') || '#6b7280';
    var labelFs = isCompact ? 10 : 12;
    var barW = isCompact ? 12 : 16;
    var sym = isCompact ? 4 : 6;
    var maxXLen = isCompact ? 4 : 6;
    var legend = isCompact
      ? {
          bottom: 0,
          left: 'center',
          type: 'scroll',
          orient: 'horizontal',
          textStyle: { color: muted, fontSize: labelFs },
          itemWidth: 10,
          itemHeight: 10,
        }
      : { top: 6, textStyle: { color: muted, fontSize: 12 }, itemWidth: 10, itemHeight: 10 };
    var rotate = isCompact ? (x.length > 4 ? 30 : 0) : x.length > 6 ? 22 : 0;

    chart.setOption(
      {
        tooltip: {
          trigger: 'axis',
          axisPointer: { type: 'shadow' },
          backgroundColor: pickColor(getVar('--app-surface') || '#ffffff', 0.96),
          borderColor: border,
          textStyle: { color: text, fontSize: 12 },
          formatter: function (params) {
            var p = Array.isArray(params) ? params : [];
            var name = (p[0] && p[0].axisValue) || '';
            var c = (p[0] && toNum(p[0].data)) || 0;
            var w = (p[1] && toNum(p[1].data)) || 0;
            var idx = p[0] ? p[0].dataIndex : 0;
            var comp = completion[idx] || 0;
            return (
              escapeHtml(String(name)) +
              '<br/>正确：' +
              fmtCount(c) +
              '<br/>错误：' +
              fmtCount(w) +
              '<br/>覆盖率：' +
              fmtPercent(comp)
            );
          },
        },
        legend: legend,
        grid: { left: 12, right: 12, top: isCompact ? 12 : 40, bottom: isCompact ? 34 : 10, containLabel: true },
        xAxis: {
          type: 'category',
          data: x,
          axisLine: { lineStyle: { color: border } },
          axisLabel: {
            color: muted,
            interval: 0,
            rotate: rotate,
            fontSize: labelFs,
            hideOverlap: true,
            formatter: function (v) {
              return shortText(v, maxXLen);
            },
          },
        },
        yAxis: [
          {
            type: 'value',
            min: 0,
            axisLine: { show: false },
            axisTick: { show: false },
            axisLabel: { color: muted, fontSize: labelFs },
            splitLine: { lineStyle: { color: border, type: 'dashed', opacity: 0.6 } },
          },
          {
            type: 'value',
            min: 0,
            max: 100,
            axisLine: { show: false },
            axisTick: { show: false },
            axisLabel: { color: muted, fontSize: labelFs, formatter: '{value}%' },
            splitLine: { show: false },
          },
        ],
        series: [
          {
            name: '正确',
            type: 'bar',
            stack: 'ans',
            data: correct,
            barWidth: barW,
            itemStyle: { color: pickColor(primary, 0.5), borderRadius: [8, 8, 0, 0] },
          },
          {
            name: '错误',
            type: 'bar',
            stack: 'ans',
            data: wrong,
            itemStyle: { color: pickColor(cta, 0.45), borderRadius: [8, 8, 0, 0] },
          },
          {
            name: '覆盖率',
            type: 'line',
            yAxisIndex: 1,
            data: completion,
            smooth: true,
            symbol: 'circle',
            symbolSize: sym,
            lineStyle: { width: 2, color: pickColor(getVar('--app-text') || '#111827', 0.65) },
            itemStyle: { color: pickColor(getVar('--app-text') || '#111827', 0.65) },
          },
        ],
      },
      true,
    );
  }

  function renderTypePie(byType, chartId, emptyText) {
    var chart = getChart(chartId);
    if (!chart) return;
    var list = Array.isArray(byType) ? byType.slice() : [];
    if (!list.length) return renderEmpty(chart, emptyText || '暂无分布数据');

    var isCompact = isCompactChart(chartId);
    list.sort(function (a, b) {
      return toNum(b.total) - toNum(a.total);
    });

    var top = list.slice(0, 8);
    var rest = list.slice(8).reduce(function (sum, r) {
      return sum + toNum(r.total);
    }, 0);

    var data = top.map(function (r) {
      return { name: String(r.q_type || '未知'), value: toNum(r.total) };
    });
    if (rest > 0) data.push({ name: '其他', value: rest });

    var primary = getVar('--app-primary') || '#111827';
    var border = pickColor(getVar('--app-border') || '#e5e7eb', 0.9);
    var text = getVar('--app-text') || '#111827';
    var muted = getVar('--app-muted') || '#6b7280';
    var labelFs = isCompact ? 10 : 12;
    var legend = isCompact
      ? {
          bottom: 0,
          left: 'center',
          type: 'scroll',
          orient: 'horizontal',
          textStyle: { color: muted, fontSize: labelFs },
          itemWidth: 10,
          itemHeight: 10,
        }
      : {
          top: 'middle',
          right: 6,
          type: 'scroll',
          orient: 'vertical',
          textStyle: { color: muted, fontSize: 12 },
          itemWidth: 10,
          itemHeight: 10,
        };

    chart.setOption(
      {
        tooltip: {
          trigger: 'item',
          backgroundColor: pickColor(getVar('--app-surface') || '#ffffff', 0.96),
          borderColor: border,
          textStyle: { color: text, fontSize: 12 },
          formatter: function (p) {
            var name = p && p.name ? p.name : '';
            var val = p && p.value != null ? p.value : 0;
            var percent = p && p.percent != null ? p.percent : 0;
            return escapeHtml(String(name)) + '<br/>' + fmtCount(val) + ' 题 · ' + percent + '%';
          },
        },
        legend: legend,
        series: [
          {
            type: 'pie',
            radius: isCompact ? ['48%', '76%'] : ['52%', '78%'],
            center: isCompact ? ['50%', '44%'] : ['34%', '50%'],
            avoidLabelOverlap: true,
            itemStyle: {
              borderColor: pickColor(getVar('--app-surface') || '#ffffff', 0.8),
              borderWidth: 2,
            },
            label: { show: false },
            emphasis: { scale: true, scaleSize: 6 },
            data: data,
            color: [
              pickColor(primary, 0.65),
              pickColor(primary, 0.5),
              pickColor(primary, 0.36),
              pickColor(getVar('--app-cta') || primary, 0.55),
              pickColor(getVar('--app-cta') || primary, 0.4),
              pickColor(getVar('--app-text') || primary, 0.45),
              pickColor(getVar('--app-text') || primary, 0.32),
              pickColor(primary, 0.26),
              pickColor(primary, 0.18),
            ],
          },
        ],
      },
      true,
    );
  }

  function renderFunnel(stats, chartId) {
    var chart = getChart(chartId);
    if (!chart) return;

    var isCompact = isCompactChart(chartId);
    var total = toNum(stats.total_count);
    var answered = toNum(stats.answered);
    var correct = toNum(stats.correct);
    if (total <= 0) return renderEmpty(chart, '暂无数据');

    var primary = getVar('--app-primary') || '#111827';
    var border = pickColor(getVar('--app-border') || '#e5e7eb', 0.9);
    var text = getVar('--app-text') || '#111827';
    var muted = getVar('--app-muted') || '#6b7280';

    var data = [
      { name: '题库总题', value: total },
      { name: '已覆盖', value: answered },
      { name: '稳定掌握', value: correct },
    ];
    var compactTop = 26;
    if (isCompact) {
      var coverRatio = total > 0 ? answered / total : 0;
      if (coverRatio < 0.15) compactTop = 60;
    }

    chart.setOption(
      {
        tooltip: {
          trigger: 'item',
          backgroundColor: pickColor(getVar('--app-surface') || '#ffffff', 0.96),
          borderColor: border,
          textStyle: { color: text, fontSize: 12 },
          formatter: function (p) {
            return escapeHtml(p.name) + '<br/>' + fmtCount(p.value);
          },
        },
        series: [
          {
            type: 'funnel',
            left: 12,
            right: 12,
            top: isCompact ? compactTop : 12,
            bottom: isCompact ? 22 : 12,
            min: 0,
            max: total,
            minSize: isCompact ? '28%' : '20%',
            maxSize: isCompact ? '88%' : '92%',
            sort: 'descending',
            gap: isCompact ? 8 : 6,
            label: {
              show: true,
              color: text,
              fontSize: isCompact ? 11 : 12,
              fontWeight: 800,
              formatter: function (p) {
                return isCompact ? p.name + '\n' + fmtCount(p.value) : p.name + '  ' + fmtCount(p.value);
              },
              position: isCompact ? 'inside' : 'right',
              align: isCompact ? 'center' : 'left',
              verticalAlign: 'middle',
              lineHeight: isCompact ? 16 : 14,
            },
            labelLine: isCompact ? { show: false } : { length: 8, lineStyle: { color: muted } },
            itemStyle: {
              borderColor: pickColor(getVar('--app-surface') || '#ffffff', 0.85),
              borderWidth: 1,
              shadowBlur: 8,
              shadowColor: pickColor(primary, 0.08),
            },
            emphasis: { itemStyle: { shadowBlur: 16, shadowColor: pickColor(primary, 0.18) } },
            data: data,
            color: [
              pickColor(primary, 0.5),
              pickColor(primary, 0.36),
              pickColor(getVar('--app-cta') || primary, 0.42),
            ],
          },
        ],
      },
      true,
    );
  }

  function renderRiskRadar(byType, chartId) {
    var chart = getChart(chartId);
    if (!chart) return;
    var list = Array.isArray(byType) ? byType.slice() : [];
    if (!list.length) return renderEmpty(chart, '暂无数据');

    var isCompact = isCompactChart(chartId);
    var rows = list
      .map(function (r) {
        var accuracy = toNum(r.accuracy);
        var completion = toNum(r.completion);
        var risk = clamp((100 - accuracy) * 0.65 + (100 - completion) * 0.35, 0, 100);
        return { q_type: String(r.q_type || '未知'), risk: risk };
      })
      .sort(function (a, b) {
        return b.risk - a.risk;
      })
      .slice(0, 6);

    if (!rows.length) return renderEmpty(chart, '暂无数据');

    var indicators = rows.map(function (r) {
      return { name: r.q_type, max: 100 };
    });
    var values = rows.map(function (r) {
      return r.risk;
    });

    var primary = getVar('--app-primary') || '#111827';
    var cta = getVar('--app-cta') || primary;
    var border = pickColor(getVar('--app-border') || '#e5e7eb', 0.9);
    var text = getVar('--app-text') || '#111827';
    var muted = getVar('--app-muted') || '#6b7280';

    chart.setOption(
      {
        tooltip: {
          trigger: 'item',
          backgroundColor: pickColor(getVar('--app-surface') || '#ffffff', 0.96),
          borderColor: border,
          textStyle: { color: text, fontSize: 12 },
          formatter: function () {
            return rows
              .map(function (r) {
                return escapeHtml(r.q_type) + '：风险 ' + fmtPercent(r.risk);
              })
              .join('<br/>');
          },
        },
        radar: {
          indicator: indicators,
          radius: isCompact ? '62%' : '70%',
          splitNumber: 4,
          nameGap: isCompact ? 8 : 14,
          axisName: {
            color: muted,
            fontSize: isCompact ? 10 : 11,
            overflow: 'truncate',
            width: isCompact ? 64 : 88,
            ellipsis: '…',
          },
          splitLine: { lineStyle: { color: border } },
          splitArea: { areaStyle: { color: [pickColor(primary, 0.04), pickColor(primary, 0.02)] } },
          axisLine: { lineStyle: { color: border } },
        },
        series: [
          {
            type: 'radar',
            data: [
              {
                value: values,
                name: '风险',
                areaStyle: { color: pickColor(cta, 0.16) },
                lineStyle: { color: pickColor(cta, 0.7), width: 2 },
                itemStyle: { color: pickColor(cta, 0.85) },
              },
            ],
          },
        ],
      },
      true,
    );
  }

  function renderTypeTable(byType, tbodyId) {
    var body = document.getElementById(tbodyId);
    if (!body) return;
    var list = Array.isArray(byType) ? byType : [];
    if (!list.length) {
      body.innerHTML = '<tr><td colspan="6" class="ubdv2-muted">暂无数据</td></tr>';
      return;
    }

    body.innerHTML = list
      .map(function (row) {
        var total = toNum(row.total);
        var answered = toNum(row.answered);
        var accuracy = toNum(row.accuracy);
        var completion = toNum(row.completion);
        return (
          '<tr>' +
          '<td>' +
          escapeHtml(String(row.q_type || '未知')) +
          '</td>' +
          '<td>' +
          fmtCount(answered) +
          ' / ' +
          fmtCount(total) +
          '</td>' +
          '<td>' +
          fmtPercent(accuracy) +
          '</td>' +
          '<td>' +
          fmtPercent(completion) +
          '</td>' +
          '<td>' +
          fmtCount(row.favorites || 0) +
          '</td>' +
          '<td>' +
          fmtCount(row.mistakes || 0) +
          '</td>' +
          '</tr>'
        );
      })
      .join('');
  }

  function renderDiffChart(byDiff, chartId, cardId) {
    var card = cardId ? document.getElementById(cardId) : null;
    var chart = getChart(chartId);
    if (!chart) return;
    var list = Array.isArray(byDiff) ? byDiff : [];
    if (!list.length) {
      if (card) card.hidden = true;
      return;
    }
    if (card) card.hidden = false;

    var isCompact = isCompactChart(chartId);
    list.sort(function (a, b) {
      return toNum(a.difficulty) - toNum(b.difficulty);
    });

    var x = list.map(function (r) {
      return String(r.difficulty == null ? '—' : r.difficulty);
    });
    var completion = list.map(function (r) {
      return toNum(r.completion);
    });
    var accuracy = list.map(function (r) {
      return toNum(r.accuracy);
    });

    var primary = getVar('--app-primary') || '#111827';
    var cta = getVar('--app-cta') || primary;
    var border = pickColor(getVar('--app-border') || '#e5e7eb', 0.9);
    var text = getVar('--app-text') || '#111827';
    var muted = getVar('--app-muted') || '#6b7280';
    var labelFs = isCompact ? 10 : 12;
    var barW = isCompact ? 10 : 14;
    var sym = isCompact ? 4 : 6;
    var legend = isCompact
      ? {
          bottom: 0,
          left: 'center',
          type: 'scroll',
          orient: 'horizontal',
          textStyle: { color: muted, fontSize: labelFs },
          itemWidth: 10,
          itemHeight: 10,
        }
      : { top: 6, textStyle: { color: muted, fontSize: 12 }, itemWidth: 10, itemHeight: 10 };

    chart.setOption(
      {
        tooltip: {
          trigger: 'axis',
          backgroundColor: pickColor(getVar('--app-surface') || '#ffffff', 0.96),
          borderColor: border,
          textStyle: { color: text, fontSize: 12 },
        },
        legend: legend,
        grid: { left: 12, right: 12, top: isCompact ? 12 : 40, bottom: isCompact ? 34 : 10, containLabel: true },
        xAxis: {
          type: 'category',
          data: x,
          axisLine: { lineStyle: { color: border } },
          axisLabel: { color: muted, fontSize: labelFs },
        },
        yAxis: {
          type: 'value',
          min: 0,
          max: 100,
          axisLine: { show: false },
          axisTick: { show: false },
          axisLabel: { color: muted, fontSize: labelFs, formatter: '{value}%' },
          splitLine: { lineStyle: { color: border, type: 'dashed', opacity: 0.6 } },
        },
        series: [
          {
            name: '覆盖率',
            type: 'bar',
            data: completion,
            barWidth: barW,
            itemStyle: { color: pickColor(primary, 0.6), borderRadius: [8, 8, 0, 0] },
          },
          {
            name: '正确率',
            type: 'line',
            data: accuracy,
            smooth: true,
            symbol: 'circle',
            symbolSize: sym,
            lineStyle: { width: 2, color: cta },
            itemStyle: { color: cta },
          },
        ],
      },
      true,
    );
  }

  function renderMistakeMatrix(items, chartId) {
    var chart = getChart(chartId);
    if (!chart) return;
    var list = Array.isArray(items) ? items : [];
    if (!list.length) return renderEmpty(chart, '暂无错题数据');

    var isCompact = isCompactChart(chartId);
    var data = list.slice(0, 300).map(function (it) {
      var wrongCount = toNum(it.mistake_wrong_count) || 1;
      var ds = daysSince(it.mistake_updated_at || it.mistake_created_at);
      if (ds == null) ds = 0;
      var diff = toNum(it.difficulty) || 1;
      var preview = String(it.content_preview || it.content || '').trim();
      return [wrongCount, ds, diff, preview];
    });

    var primary = getVar('--app-primary') || '#111827';
    var cta = getVar('--app-cta') || primary;
    var border = pickColor(getVar('--app-border') || '#e5e7eb', 0.9);
    var text = getVar('--app-text') || '#111827';
    var muted = getVar('--app-muted') || '#6b7280';
    var labelFs = isCompact ? 10 : 12;

    chart.setOption(
      {
        tooltip: {
          trigger: 'item',
          backgroundColor: pickColor(getVar('--app-surface') || '#ffffff', 0.96),
          borderColor: border,
          textStyle: { color: text, fontSize: 12 },
          formatter: function (p) {
            var v = p && p.value ? p.value : [];
            return (
              '错题次数：' +
              fmtCount(v[0] || 0) +
              '<br/>距上次错题：' +
              fmtCount(v[1] || 0) +
              ' 天<br/>难度：' +
              fmtCount(v[2] || 1) +
              '<br/>' +
              escapeHtml(String(v[3] || '').slice(0, 120))
            );
          },
        },
        grid: { left: 12, right: isCompact ? 12 : 18, top: 12, bottom: isCompact ? 18 : 12, containLabel: true },
        xAxis: {
          type: 'value',
          min: 0,
          axisLine: { lineStyle: { color: border } },
          axisLabel: { color: muted, fontSize: labelFs },
          splitLine: { lineStyle: { color: border, type: 'dashed', opacity: 0.6 } },
          name: isCompact ? '' : '错题次数',
          nameTextStyle: { color: muted, fontSize: labelFs, fontWeight: 800 },
        },
        yAxis: {
          type: 'value',
          min: 0,
          axisLine: { lineStyle: { color: border } },
          axisLabel: { color: muted, fontSize: labelFs },
          splitLine: { lineStyle: { color: border, type: 'dashed', opacity: 0.6 } },
          name: isCompact ? '' : '距上次错题(天)',
          nameTextStyle: { color: muted, fontSize: labelFs, fontWeight: 800 },
        },
        series: [
          {
            type: 'scatter',
            data: data,
            symbolSize: function (val) {
              var wc = toNum(val[0]);
              return isCompact ? clamp(6 + wc * 2, 8, 24) : clamp(8 + wc * 2.2, 10, 28);
            },
            itemStyle: { color: pickColor(cta, 0.55), opacity: 0.9 },
            emphasis: { itemStyle: { color: pickColor(cta, 0.85) } },
          },
        ],
      },
      true,
    );
  }

  function renderMistakeTop(items, chartId) {
    var chart = getChart(chartId);
    if (!chart) return;
    var list = Array.isArray(items) ? items : [];
    if (!list.length) return renderEmpty(chart, '暂无错题数据');

    var isCompact = isCompactChart(chartId);
    var top = list
      .slice()
      .sort(function (a, b) {
        return toNum(b.mistake_wrong_count) - toNum(a.mistake_wrong_count);
      })
      .slice(0, 10);

    var previewLen = isCompact ? 10 : 14;
    var y = top
      .map(function (it) {
        var prev = String(it.content_preview || '').trim();
        if (!prev) return '题目';
        return prev.length > previewLen ? prev.slice(0, previewLen) + '…' : prev;
      })
      .reverse();
    var x = top
      .map(function (it) {
        return toNum(it.mistake_wrong_count);
      })
      .reverse();

    var primary = getVar('--app-primary') || '#111827';
    var border = pickColor(getVar('--app-border') || '#e5e7eb', 0.9);
    var text = getVar('--app-text') || '#111827';
    var muted = getVar('--app-muted') || '#6b7280';
    var labelFs = isCompact ? 10 : 12;

    chart.setOption(
      {
        tooltip: {
          trigger: 'axis',
          axisPointer: { type: 'shadow' },
          backgroundColor: pickColor(getVar('--app-surface') || '#ffffff', 0.96),
          borderColor: border,
          textStyle: { color: text, fontSize: 12 },
          formatter: function (params) {
            var p = Array.isArray(params) ? params[0] : null;
            if (!p) return '';
            var idx = p.dataIndex;
            var original = top[top.length - 1 - idx];
            return escapeHtml(String(original.content_preview || '题目')) + '<br/>错题次数：' + fmtCount(p.data);
          },
        },
        grid: { left: 12, right: 12, top: 10, bottom: 10, containLabel: true },
        xAxis: {
          type: 'value',
          min: 0,
          axisLine: { show: false },
          axisTick: { show: false },
          axisLabel: { color: muted, fontSize: labelFs },
          splitLine: { lineStyle: { color: border, type: 'dashed', opacity: 0.6 } },
        },
        yAxis: {
          type: 'category',
          data: y,
          axisLine: { show: false },
          axisTick: { show: false },
          axisLabel: { color: muted, fontSize: labelFs, width: isCompact ? 110 : 160, overflow: 'truncate', ellipsis: '…' },
        },
        series: [
          {
            type: 'bar',
            data: x,
            barWidth: isCompact ? 10 : 12,
            itemStyle: { color: pickColor(primary, 0.55), borderRadius: [8, 8, 8, 8] },
          },
        ],
      },
      true,
    );
  }

  function renderMistakeDifficulty(items, chartId) {
    var chart = getChart(chartId);
    if (!chart) return;
    var list = Array.isArray(items) ? items : [];
    if (!list.length) return renderEmpty(chart, '暂无难度数据');

    var isCompact = isCompactChart(chartId);
    var buckets = {};
    list.forEach(function (it) {
      var d = toNum(it.difficulty) || 1;
      var key = String(d);
      if (!buckets[key]) buckets[key] = { difficulty: d, count: 0, times: 0 };
      buckets[key].count += 1;
      buckets[key].times += toNum(it.mistake_wrong_count) || 1;
    });

    var rows = Object.keys(buckets)
      .map(function (k) {
        return buckets[k];
      })
      .sort(function (a, b) {
        return a.difficulty - b.difficulty;
      });

    var x = rows.map(function (r) {
      return String(r.difficulty);
    });
    var counts = rows.map(function (r) {
      return r.count;
    });
    var avgTimes = rows.map(function (r) {
      return r.count > 0 ? r.times / r.count : 0;
    });

    var primary = getVar('--app-primary') || '#111827';
    var cta = getVar('--app-cta') || primary;
    var border = pickColor(getVar('--app-border') || '#e5e7eb', 0.9);
    var text = getVar('--app-text') || '#111827';
    var muted = getVar('--app-muted') || '#6b7280';
    var labelFs = isCompact ? 10 : 12;
    var barW = isCompact ? 10 : 14;
    var sym = isCompact ? 4 : 6;
    var legend = isCompact
      ? {
          bottom: 0,
          left: 'center',
          type: 'scroll',
          orient: 'horizontal',
          textStyle: { color: muted, fontSize: labelFs },
          itemWidth: 10,
          itemHeight: 10,
        }
      : { top: 6, textStyle: { color: muted, fontSize: 12 }, itemWidth: 10, itemHeight: 10 };

    chart.setOption(
      {
        tooltip: {
          trigger: 'axis',
          backgroundColor: pickColor(getVar('--app-surface') || '#ffffff', 0.96),
          borderColor: border,
          textStyle: { color: text, fontSize: 12 },
        },
        legend: legend,
        grid: { left: 12, right: 12, top: isCompact ? 12 : 40, bottom: isCompact ? 34 : 10, containLabel: true },
        xAxis: {
          type: 'category',
          data: x,
          axisLine: { lineStyle: { color: border } },
          axisLabel: { color: muted, fontSize: labelFs },
        },
        yAxis: [
          {
            type: 'value',
            min: 0,
            axisLine: { show: false },
            axisTick: { show: false },
            axisLabel: { color: muted, fontSize: labelFs },
            splitLine: { lineStyle: { color: border, type: 'dashed', opacity: 0.6 } },
          },
          {
            type: 'value',
            min: 0,
            axisLine: { show: false },
            axisTick: { show: false },
            axisLabel: { color: muted, fontSize: labelFs },
            splitLine: { show: false },
          },
        ],
        series: [
          {
            name: '错题数',
            type: 'bar',
            data: counts,
            barWidth: barW,
            itemStyle: { color: pickColor(primary, 0.55), borderRadius: [8, 8, 0, 0] },
          },
          {
            name: '平均错题次数',
            type: 'line',
            yAxisIndex: 1,
            data: avgTimes,
            smooth: true,
            symbol: 'circle',
            symbolSize: sym,
            lineStyle: { width: 2, color: cta },
            itemStyle: { color: cta },
          },
        ],
      },
      true,
    );
  }

  function renderMistakeTable(items, tbodyId) {
    var body = document.getElementById(tbodyId);
    if (!body) return;
    var list = Array.isArray(items) ? items : [];
    if (!list.length) {
      body.innerHTML = '<tr><td colspan="7" class="ubdv2-muted">暂无错题</td></tr>';
      return;
    }

    var show = list.slice(0, 50);
    body.innerHTML = show
      .map(function (q) {
        var preview = String(q.content_preview || '').trim() || '—';
        var qType = String(q.q_type || '—');
        var diff = toNum(q.difficulty) || 1;
        var wc = toNum(q.mistake_wrong_count) || 1;
        var lastWrongAt = q.mistake_updated_at || q.mistake_created_at || '';
        var lastAnsAt = q.last_answered_at || '';
        var lastIsCorrect = q.last_is_correct;
        var lastResult = lastIsCorrect == null ? '未作答' : toNum(lastIsCorrect) === 1 ? '正确' : '错误';
        return (
          '<tr>' +
          '<td>' +
          escapeHtml(preview) +
          '</td>' +
          '<td>' +
          escapeHtml(qType) +
          '</td>' +
          '<td>' +
          fmtCount(diff) +
          '</td>' +
          '<td>' +
          fmtCount(wc) +
          '</td>' +
          '<td>' +
          escapeHtml(fmtDateTime(lastWrongAt)) +
          '</td>' +
          '<td>' +
          escapeHtml(fmtDateTime(lastAnsAt)) +
          '</td>' +
          '<td>' +
          escapeHtml(lastResult) +
          '</td>' +
          '</tr>'
        );
      })
      .join('');
  }

  function renderFavAddedTrend(trend, chartId) {
    var chart = getChart(chartId);
    if (!chart) return;
    var list = Array.isArray(trend) ? trend : [];
    if (!list.length) return renderEmpty(chart, '暂无新增数据');

    var isCompact = isCompactChart(chartId);
    var x = list.map(function (d) {
      return fmtDay(d.day);
    });
    var y = list.map(function (d) {
      return toNum(d.added);
    });

    var primary = getVar('--app-primary') || '#111827';
    var border = pickColor(getVar('--app-border') || '#e5e7eb', 0.9);
    var text = getVar('--app-text') || '#111827';
    var muted = getVar('--app-muted') || '#6b7280';
    var labelFs = isCompact ? 10 : 12;
    var sym = isCompact ? 4 : 6;
    var gridBottom = isCompact ? 22 : 10;
    var xAxisLabel = { color: muted, fontSize: labelFs, hideOverlap: true, formatter: fmtDayLabel };

    chart.setOption(
      {
        tooltip: {
          trigger: 'axis',
          backgroundColor: pickColor(getVar('--app-surface') || '#ffffff', 0.96),
          borderColor: border,
          textStyle: { color: text, fontSize: 12 },
        },
        grid: { left: 12, right: 12, top: 18, bottom: gridBottom, containLabel: true },
        xAxis: {
          type: 'category',
          data: x,
          axisLine: { lineStyle: { color: border } },
          axisLabel: xAxisLabel,
        },
        yAxis: {
          type: 'value',
          min: 0,
          axisLine: { show: false },
          axisTick: { show: false },
          axisLabel: { color: muted, fontSize: labelFs },
          splitLine: { lineStyle: { color: border, type: 'dashed', opacity: 0.6 } },
        },
        series: [
          {
            type: 'line',
            data: y,
            smooth: true,
            symbol: 'circle',
            symbolSize: sym,
            lineStyle: { width: 2, color: pickColor(primary, 0.8) },
            itemStyle: { color: pickColor(primary, 0.85) },
            areaStyle: { color: pickColor(primary, 0.14) },
          },
        ],
      },
      true,
    );
  }

  function renderFavTable(items, tbodyId) {
    var body = document.getElementById(tbodyId);
    if (!body) return;
    var list = Array.isArray(items) ? items : [];
    if (!list.length) {
      body.innerHTML = '<tr><td colspan="6" class="ubdv2-muted">暂无收藏</td></tr>';
      return;
    }

    var show = list.slice(0, 50);
    body.innerHTML = show
      .map(function (q) {
        var preview = String(q.content_preview || '').trim() || '—';
        var qType = String(q.q_type || '—');
        var diff = toNum(q.difficulty) || 1;
        var favAt = q.favorite_created_at || '';
        var lastAnsAt = q.last_answered_at || '';
        var lastIsCorrect = q.last_is_correct;
        var lastResult = lastIsCorrect == null ? '未作答' : toNum(lastIsCorrect) === 1 ? '正确' : '错误';
        return (
          '<tr>' +
          '<td>' +
          escapeHtml(preview) +
          '</td>' +
          '<td>' +
          escapeHtml(qType) +
          '</td>' +
          '<td>' +
          fmtCount(diff) +
          '</td>' +
          '<td>' +
          escapeHtml(fmtDateTime(favAt)) +
          '</td>' +
          '<td>' +
          escapeHtml(fmtDateTime(lastAnsAt)) +
          '</td>' +
          '<td>' +
          escapeHtml(lastResult) +
          '</td>' +
          '</tr>'
        );
      })
      .join('');
  }

  function updateGlobalKpis(stats) {
    var totalCount = toNum(stats.total_count);
    var answered = toNum(stats.answered);
    var correct = toNum(stats.correct);
    var wrong = toNum(stats.wrong);
    var favorites = toNum(stats.favorites);
    var mistakes = toNum(stats.mistakes);
    var mistakesTimes = toNum(stats.mistakes_times);
    var accuracy = toNum(stats.accuracy);
    var completion = toNum(stats.completion);
    var streak = toNum(stats.streak_days);
    var trend = Array.isArray(stats.trend) ? stats.trend : [];
    var activeDays = calcActiveDays(trend);
    var recentAnswered = calcRecentAnswered(trend, Math.min(7, windowDays));
    var mistakeRate = answered > 0 ? (wrong * 100) / answered : 0;

    setText(
      'ubdHeadline',
      '全局：覆盖率 ' + fmtPercent(completion) + ' · 正确率 ' + fmtPercent(accuracy) + ' · 近' + windowDays + '天活跃' + activeDays + '天',
    );
    setText('ubdUpdatedAt', '最近活跃：' + fmtDateTime(stats.last_activity));

    setText('kpiTotal', fmtCount(totalCount));
    setText('kpiTotalMeta', '题库规模基座');

    setText('kpiAnswered', fmtCount(answered));
    setText('kpiAnsweredMeta', '近7天作答 ' + fmtCount(recentAnswered));

    setText('kpiAccuracy', fmtPercent(accuracy));
    setText('kpiAccuracyMeta', '正确 ' + fmtCount(correct) + ' / 已做 ' + fmtCount(answered));

    setText('kpiCompletion', fmtPercent(completion));
    setText('kpiCompletionMeta', '未覆盖 ' + fmtPercent(100 - completion));

    setText('kpiMistakeTimes', fmtCount(mistakesTimes));
    setText('kpiMistakeTimesMeta', '错题率 ' + fmtPercent(mistakeRate) + ' · 错题池 ' + fmtCount(mistakes) + ' 题');

    setText('kpiFav', fmtCount(favorites));
    setText('kpiFavMeta', '收藏池题数');

    setText('kpiMis', fmtCount(mistakes));
    setText('kpiMisMeta', '当前错题池');

    setText('kpiStreak', fmtCount(streak));
    setText('kpiStreakMeta', '近似连续活跃');

    setBar('metricStability', accuracy);
    setText('metricStabilityText', fmtPercent(accuracy));

    var avgPerActiveDay = activeDays > 0 ? recentAnswered / activeDays : 0;
    var pacePercent = clamp((avgPerActiveDay / 20) * 100, 0, 100);
    setBar('metricPace', pacePercent);
    setText('metricPaceText', avgPerActiveDay.toFixed(1) + '/天');
  }

  function updateMistakeKpis(stats, items) {
    var mistakesCount = toNum(stats.total_count);
    var mistakesTimes = toNum(stats.mistakes_times);
    var accuracy = toNum(stats.accuracy);
    var completion = toNum(stats.completion);
    var trend = Array.isArray(stats.trend) ? stats.trend : [];
    var activeDays = calcActiveDays(trend);
    var recentAnswered = calcRecentAnswered(trend, Math.min(7, windowDays));

    var highRisk = 0;
    var aging = 0;
    (items || []).forEach(function (q) {
      var wc = toNum(q.mistake_wrong_count) || 1;
      if (wc >= 3) highRisk += 1;
      var ds = daysSince(q.mistake_updated_at || q.mistake_created_at);
      if (ds != null && ds >= 14) aging += 1;
    });

    var denom = bankTotal > 0 ? bankTotal : 0;
    var ratio = denom > 0 ? (mistakesCount * 100) / denom : 0;
    var avgTimes = mistakesCount > 0 ? mistakesTimes / mistakesCount : 0;

    setText(
      'ubdMisHeadline',
      '错题池 ' + fmtCount(mistakesCount) + ' 题 · 错题次数 ' + fmtCount(mistakesTimes) + ' · 近' + windowDays + '天活跃' + activeDays + '天',
    );
    setText('ubdMisUpdatedAt', '最近活跃：' + fmtDateTime(stats.last_activity));

    setText('kpiMisTotal', fmtCount(mistakesCount));
    setText('kpiMisTotalMeta', denom > 0 ? '占题库 ' + fmtPercent(ratio) : '—');

    setText('kpiMisTimes', fmtCount(mistakesTimes));
    setText('kpiMisTimesMeta', '平均 ' + avgTimes.toFixed(1) + ' 次/题');

    setText('kpiMisHighRisk', fmtCount(highRisk));
    setText('kpiMisAging', fmtCount(aging));

    setText('kpiMisAccuracy', fmtPercent(accuracy));
    setText('kpiMisAccuracyMeta', '近7天复习 ' + fmtCount(recentAnswered) + ' 题');

    setText('kpiMisCompletion', fmtPercent(completion));
    setText('kpiMisCompletionMeta', '（错题集内）');

    setText('kpiMisRecent', fmtCount(recentAnswered));
  }

  function updateFavoriteKpis(stats, favTrend) {
    var total = toNum(stats.total_count);
    var answered = toNum(stats.answered);
    var correct = toNum(stats.correct);
    var accuracy = toNum(stats.accuracy);
    var completion = toNum(stats.completion);
    var trend = Array.isArray(stats.trend) ? stats.trend : [];
    var activeDays = calcActiveDays(trend);
    var recentAnswered = calcRecentAnswered(trend, Math.min(7, windowDays));

    var todo = Math.max(0, total - answered);

    setText(
      'ubdFavHeadline',
      '收藏池 ' + fmtCount(total) + ' 题 · 未做 ' + fmtCount(todo) + ' 题 · 近' + windowDays + '天活跃' + activeDays + '天',
    );
    setText('ubdFavUpdatedAt', '最近活跃：' + fmtDateTime(stats.last_activity));

    setText('kpiFavTotal', fmtCount(total));
    setText('kpiFavAnswered', fmtCount(answered));
    setText('kpiFavAnsweredMeta', '未做 ' + fmtCount(todo));

    setText('kpiFavAccuracy', fmtPercent(accuracy));
    setText('kpiFavAccuracyMeta', '正确 ' + fmtCount(correct) + ' / 已做 ' + fmtCount(answered));

    setText('kpiFavCompletion', fmtPercent(completion));
    setText('kpiFavCompletionMeta', '未覆盖 ' + fmtPercent(100 - completion));

    setText('kpiFavTodo', fmtCount(todo));
    setText('kpiFavRecent', fmtCount(recentAnswered));

    var added = favTrend && favTrend.total_added != null ? toNum(favTrend.total_added) : 0;
    setText('kpiFavAdded', fmtCount(added));
  }

  async function loadGlobal() {
    var statsUrl = '';
    if (mode === 'subject') {
      statsUrl =
        '/api/quiz/subjects/' +
        encodeURIComponent(String(subjectName)) +
        '/stats?days=' +
        encodeURIComponent(String(windowDays)) +
        '&source=all';
    } else {
      statsUrl =
        '/user/banks/api/' +
        encodeURIComponent(String(bankId)) +
        '/stats?days=' +
        encodeURIComponent(String(windowDays)) +
        '&source=all';
    }
    var js = await fetchJson(statsUrl);
    var stats = js.data || {};

    updateGlobalKpis(stats);
    renderCalendarChart(stats.trend || [], 'ubdCalendarChart');
    renderGaugeChart(stats, 'ubdGaugeChart');
    renderAnsweredTrend(stats.trend || [], 'ubdTrendChart');
    renderTypeStructureChart(stats.by_type || [], 'ubdTypeChart');
    renderFunnel(stats, 'ubdFunnelChart');
    renderRiskRadar(stats.by_type || [], 'ubdRiskRadarChart');
    renderTypeTable(stats.by_type || [], 'ubdTypeTbody');
    renderDiffChart(stats.by_difficulty || [], 'ubdDiffChart', 'ubdDiffCard');
    renderAdvice(stats.advice || [], 'ubdAdvice');
  }

  async function loadMistakes() {
    var statsUrl = '';
    var listUrl = '';
    if (mode === 'subject') {
      statsUrl =
        '/api/quiz/subjects/' +
        encodeURIComponent(String(subjectName)) +
        '/stats?days=' +
        encodeURIComponent(String(windowDays)) +
        '&source=mistakes';
      listUrl =
        '/api/quiz/subjects/' +
        encodeURIComponent(String(subjectName)) +
        '/questions?source=mistakes&per_page=300&page=1';
    } else {
      statsUrl =
        '/user/banks/api/' +
        encodeURIComponent(String(bankId)) +
        '/stats?days=' +
        encodeURIComponent(String(windowDays)) +
        '&source=mistakes';
      listUrl =
        '/user/banks/api/' +
        encodeURIComponent(String(bankId)) +
        '/questions?source=mistakes&per_page=300&page=1';
    }

    var results = await Promise.all([fetchJson(statsUrl), fetchJson(listUrl)]);
    var stats = (results[0] && results[0].data) || {};
    var list = ((results[1] && results[1].data && results[1].data.questions) || []).slice();

    updateMistakeKpis(stats, list);
    renderMistakeMatrix(list, 'ubdMistakeMatrixChart');
    renderMistakeTop(list, 'ubdMistakeTopChart');
    renderAnsweredTrend(stats.trend || [], 'ubdMisTrendChart');
    renderTypePie(stats.by_type || [], 'ubdMisTypePieChart', '暂无错题题型分布');
    renderMistakeDifficulty(list, 'ubdMisDiffChart');
    renderMistakeTable(list, 'ubdMisTbody');
    renderAdvice(stats.advice || [], 'ubdMisAdvice');
  }

  async function loadFavorites() {
    var statsUrl = '';
    var listUrl = '';
    var trendUrl = '';
    if (mode === 'subject') {
      statsUrl =
        '/api/quiz/subjects/' +
        encodeURIComponent(String(subjectName)) +
        '/stats?days=' +
        encodeURIComponent(String(windowDays)) +
        '&source=favorites';
      listUrl =
        '/api/quiz/subjects/' +
        encodeURIComponent(String(subjectName)) +
        '/questions?source=favorites&per_page=200&page=1';
      trendUrl =
        '/api/quiz/subjects/' +
        encodeURIComponent(String(subjectName)) +
        '/favorites/trend?days=' +
        encodeURIComponent(String(windowDays));
    } else {
      statsUrl =
        '/user/banks/api/' +
        encodeURIComponent(String(bankId)) +
        '/stats?days=' +
        encodeURIComponent(String(windowDays)) +
        '&source=favorites';
      listUrl =
        '/user/banks/api/' +
        encodeURIComponent(String(bankId)) +
        '/questions?source=favorites&per_page=200&page=1';
      trendUrl =
        '/user/banks/api/' +
        encodeURIComponent(String(bankId)) +
        '/favorites/trend?days=' +
        encodeURIComponent(String(windowDays));
    }

    var results = await Promise.all([fetchJson(statsUrl), fetchJson(listUrl), fetchJson(trendUrl)]);
    var stats = (results[0] && results[0].data) || {};
    var list = ((results[1] && results[1].data && results[1].data.questions) || []).slice();
    var favTrend = (results[2] && results[2].data) || {};

    updateFavoriteKpis(stats, favTrend);
    renderFavAddedTrend(favTrend.trend || [], 'ubdFavAddedChart');
    renderTypePie(stats.by_type || [], 'ubdFavTypePieChart', '暂无收藏题型分布');
    renderDiffChart(stats.by_difficulty || [], 'ubdFavDiffChart');
    renderAnsweredTrend(stats.trend || [], 'ubdFavReviewTrendChart');
    renderFavTable(list, 'ubdFavTbody');
    renderAdvice(stats.advice || [], 'ubdFavAdvice');
  }

  function resizeAll() {
    Object.keys(charts).forEach(function (k) {
      try {
        charts[k] && charts[k].resize();
      } catch (err) {}
    });
  }

  function bindResizeOnce() {
    if (resizeBound) return;
    resizeBound = true;
    window.addEventListener('resize', function () {
      resizeAll();
    });
  }

  function canAutostart(el) {
    try {
      var v = String(el && el.getAttribute ? el.getAttribute('data-ubdv2-autostart') : '').trim().toLowerCase();
      return !(v === '0' || v === 'false' || v === 'no');
    } catch (err) {
      return true;
    }
  }

  function headlineIdForTab(tab) {
    if (tab === 'mistakes') return 'ubdMisHeadline';
    if (tab === 'favorites') return 'ubdFavHeadline';
    return 'ubdHeadline';
  }

  function chartIdsForTab(tab) {
    if (tab === 'mistakes') {
      return ['ubdMistakeMatrixChart', 'ubdMistakeTopChart', 'ubdMisTrendChart', 'ubdMisTypePieChart', 'ubdMisDiffChart'];
    }
    if (tab === 'favorites') {
      return ['ubdFavAddedChart', 'ubdFavTypePieChart', 'ubdFavDiffChart', 'ubdFavReviewTrendChart'];
    }
    return ['ubdCalendarChart', 'ubdGaugeChart', 'ubdTrendChart', 'ubdTypeChart', 'ubdFunnelChart', 'ubdRiskRadarChart', 'ubdDiffChart'];
  }

  function setFailure(tab) {
    var hid = headlineIdForTab(tab);
    var el = document.getElementById(hid);
    if (el) el.textContent = '数据加载失败，请稍后重试。';

    chartIdsForTab(tab).forEach(function (id) {
      var c = charts[id];
      if (c) renderEmpty(c, '加载失败');
    });
  }

  function bindThemeObserverOnce() {
    if (themeObserver) return;
    try {
      themeObserver = new MutationObserver(function () {
        var el = resolveRoot();
        if (!el) return;
        if (!isVisible(el)) {
          themeDirty = true;
          return;
        }
        api.load({
          mode: mode,
          bank_id: bankId,
          subject_name: subjectName,
          subtab: subtab,
          window_days: windowDays,
          bank_total: bankTotal,
          bank_favorites: bankFavorites,
          bank_mistakes: bankMistakes,
          force: true,
        });
      });
      themeObserver.observe(document.documentElement, {
        attributes: true,
        attributeFilter: ['data-theme', 'data-theme-style'],
      });
    } catch (err) {
      themeObserver = null;
    }
  }

  async function doLoad(ctx) {
    var el = resolveRoot();
    var force = !!ctx.force || !!themeDirty;

    mode = String((ctx && ctx.mode) || '').trim().toLowerCase();
    if (mode !== 'subject') mode = 'user_bank';

    subjectName = ctx && ctx.subject_name != null ? String(ctx.subject_name) : '';
    subjectName = subjectName.trim();

    bankId = ctx.bank_id ? String(ctx.bank_id) : '';
    subtab = String(ctx.subtab || 'global').trim().toLowerCase();
    if (subtab !== 'mistakes' && subtab !== 'favorites') subtab = 'global';
    windowDays = toNum(ctx.window_days);
    if (![7, 14, 30, 90].includes(windowDays)) windowDays = subtab === 'global' ? 90 : 30;

    bankTotal = toNum(ctx.bank_total);
    bankFavorites = toNum(ctx.bank_favorites);
    bankMistakes = toNum(ctx.bank_mistakes);

    if (mode === 'subject' && !subjectName) mode = 'user_bank';

    if (el) {
      try {
        el.setAttribute('data-ubdv2-mode', String(mode));
        el.setAttribute('data-bank-id', String(bankId));
        el.setAttribute('data-subject-name', String(subjectName));
        el.setAttribute('data-subtab', String(subtab));
        el.setAttribute('data-days', String(windowDays));
      } catch (err) {}
    }

    if (themeDirty && el && isVisible(el)) themeDirty = false;

    if (mode === 'subject') {
      if (!subjectName) return;
    } else {
      if (!bankId) return;
    }
    if (!window.echarts) throw new Error('ECharts 未加载');

    var scopeKey = mode === 'subject' ? String(subjectName) : String(bankId);
    var key = String(mode) + ':' + String(scopeKey) + ':' + String(windowDays);
    if (!force && loadedKeyByTab[subtab] === key) {
      resizeAll();
      return;
    }

    if (subtab === 'mistakes') await loadMistakes();
    else if (subtab === 'favorites') await loadFavorites();
    else await loadGlobal();

    loadedKeyByTab[subtab] = key;
    resizeAll();

    bindResizeOnce();
    bindThemeObserverOnce();
  }

  function load(ctxInput) {
    pendingCtx = normalizeContext(ctxInput || readContextFromDom());
    if (inflight) return inflight;

    inflight = (async function () {
      while (pendingCtx) {
        var ctx = pendingCtx;
        pendingCtx = null;
        try {
          await doLoad(ctx);
        } catch (err) {
          setFailure(String(ctx && ctx.subtab ? ctx.subtab : 'global'));
        }
      }
    })();

    inflight.then(
      function () {
        inflight = null;
      },
      function () {
        inflight = null;
      },
    );

    return inflight;
  }

  api.load = load;
  api.resize = resizeAll;

  function tryAutostart() {
    var el = resolveRoot();
    if (!el || !isVisible(el) || !canAutostart(el)) return;
    api.load(readContextFromDom());
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', tryAutostart);
  else tryAutostart();
})();
