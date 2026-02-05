"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.buildDataCenterChartOption = exports.buildDataCenterCompatPayload = exports.getDataCenterThemeTokens = void 0;

// 为了保持小程序原生渲染与 Web 数据中心一致，这里复用 Web 端 data_center.js 的图表 option 生成逻辑（去掉 DOM 依赖）。

function clamp01(n) {
  var v = Number(n || 0);
  if (!isFinite(v)) v = 0;
  return Math.max(0, Math.min(1, v));
}

function clamp100(n) {
  var v = Number(n || 0);
  if (!isFinite(v)) v = 0;
  return Math.max(0, Math.min(100, v));
}

function fmtDay(iso) {
  var s = String(iso || '');
  if (/^\\d{4}-\\d{2}-\\d{2}/.test(s)) return s.slice(5, 10);
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
  if (h.indexOf('rgb') === 0) return h;
  if (h[0] !== '#') return h;
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

function applyBaseOption(opt, t) {
  if (!opt || typeof opt !== 'object') return opt;
  t = t || getDataCenterThemeTokens(false, 'default');

  opt.textStyle = opt.textStyle || {};
  if (!opt.textStyle.fontFamily) opt.textStyle.fontFamily = t.fontBody;

  if (opt.tooltip) {
    opt.tooltip.backgroundColor = opt.tooltip.backgroundColor || t.surface;
    opt.tooltip.borderColor = opt.tooltip.borderColor || t.border;
    opt.tooltip.textStyle = opt.tooltip.textStyle || {};
    if (!opt.tooltip.textStyle.color) opt.tooltip.textStyle.color = t.text;
    if (!opt.tooltip.textStyle.fontFamily) opt.tooltip.textStyle.fontFamily = t.fontBody;
    if (opt.tooltip.confine == null) opt.tooltip.confine = true;
  }

  if (opt.legend && opt.legend.textStyle) {
    if (!opt.legend.textStyle.fontFamily) opt.legend.textStyle.fontFamily = t.fontBody;
  }

  if (opt.title && opt.title.textStyle) {
    if (!opt.title.textStyle.fontFamily) opt.title.textStyle.fontFamily = t.fontHeading;
  }

  return opt;
}

function emptyOption(titleText, subtitleText, t) {
  return applyBaseOption(
    {
      title: {
        text: String(titleText || ''),
        subtext: subtitleText ? String(subtitleText) : '',
        left: 12,
        top: 10,
        textStyle: { color: t.text, fontWeight: 900, fontSize: 12 },
        subtextStyle: { color: t.muted, fontSize: 11 },
      },
      grid: { left: 12, right: 12, top: 44, bottom: 12 },
      xAxis: { show: false },
      yAxis: { show: false },
      series: [],
      graphic: [
        {
          type: 'text',
          left: 'center',
          top: 'middle',
          style: { text: '暂无数据', fill: t.muted, fontSize: 12, fontWeight: 800 },
        },
      ],
    },
    t,
  );
}

function mapByDay(list) {
  var m = {};
  (Array.isArray(list) ? list : []).forEach(function (d) {
    if (!d || !d.day) return;
    m[String(d.day)] = d;
  });
  return m;
}

function getDayKeys(ctx) {
  if (ctx.allDaily && ctx.allDaily.length) return ctx.allDaily.map(function (d) { return String(d.day); });
  if (ctx.dailyPublic && ctx.dailyPublic.length) return ctx.dailyPublic.map(function (d) { return String(d.day); });
  if (ctx.dailyBanks && ctx.dailyBanks.length) return ctx.dailyBanks.map(function (d) { return String(d.day); });
  return [];
}

function getWidthSafe(chart) {
  try {
    if (chart && typeof chart.getWidth === 'function') return chart.getWidth() || 0;
  } catch (e) {}
  return 0;
}

function createChartCtx(payload) {
  var p = payload || {};
  var dailyPublic = Array.isArray(p.daily) ? p.daily : [];
  var dailyBanks = Array.isArray(p.bank_daily) ? p.bank_daily : [];
  var allDaily = Array.isArray(p.all_daily) ? p.all_daily : [];
  var subjects = Array.isArray(p.subjects) ? p.subjects : Array.isArray(p.subject_rows) ? p.subject_rows : [];
  var banks = Array.isArray(p.banks) ? p.banks : Array.isArray(p.bank_rows) ? p.bank_rows : [];
  var bankCategories = Array.isArray(p.bank_categories) ? p.bank_categories : Array.isArray(p.bank_category_rows) ? p.bank_category_rows : [];
  var ability = Array.isArray(p.ability_radar) ? p.ability_radar : [];
  var weakness = Array.isArray(p.weakness) ? p.weakness : Array.isArray(p.weakness_rows) ? p.weakness_rows : [];
  var hourly = p.activity_hourly || { max: 0, public: [], banks: [], all: [] };
  var heatmap = p.activity_heatmap || { max: 0, public: [], banks: [], all: [] };

  return {
    payload: p,
    dailyPublic: dailyPublic,
    dailyBanks: dailyBanks,
    allDaily: allDaily,
    subjects: subjects,
    banks: banks,
    bankCategories: bankCategories,
    ability: ability,
    weakness: weakness,
    hourly: hourly,
    heatmap: heatmap,
  };
}

function optionTrendDetail(ctx, t) {
  var keys = getDayKeys(ctx);
  if (!keys.length) {
    return emptyOption('趋势（公共 + 个人）', '近 ' + (ctx.payload.window_days || 30) + ' 天', t);
  }

  var pubMap = mapByDay(ctx.dailyPublic);
  var bankMap = mapByDay(ctx.dailyBanks);
  var allMap = mapByDay(ctx.allDaily);
  var x = keys.map(function (k) { return fmtDay(k); });

  var pubTotals = keys.map(function (k) { return toInt((pubMap[k] || {}).total); });
  var bankTotals = keys.map(function (k) { return toInt((bankMap[k] || {}).total); });
  var allTotals = keys.map(function (k) { return toInt((allMap[k] || {}).total); });
  var accAll = keys.map(function (k) { return clamp100((allMap[k] || {}).accuracy); });

  return applyBaseOption(
    {
      tooltip: { trigger: 'axis' },
      legend: { data: ['公共', '个人', '合计', '正确率'], top: 8, textStyle: { color: t.muted, fontWeight: 800 } },
      grid: { left: 12, right: 12, top: 44, bottom: 30, containLabel: true },
      xAxis: {
        type: 'category',
        data: x,
        axisLine: { lineStyle: { color: t.border } },
        axisLabel: { color: t.muted },
      },
      yAxis: [
        {
          type: 'value',
          axisLine: { show: false },
          axisTick: { show: false },
          axisLabel: { color: t.muted },
          splitLine: { lineStyle: { color: t.border, type: 'dashed', opacity: 0.6 } },
        },
        {
          type: 'value',
          min: 0,
          max: 100,
          axisLine: { show: false },
          axisTick: { show: false },
          axisLabel: { color: t.muted, formatter: '{value}%' },
          splitLine: { show: false },
        },
      ],
      dataZoom: [
        { type: 'inside', start: 0, end: 100 },
        { type: 'slider', height: 14, bottom: 8, borderColor: 'transparent', backgroundColor: pickColor(t.border, 0.25) },
      ],
      series: [
        { name: '公共', type: 'line', smooth: true, data: pubTotals, lineStyle: { width: 2, color: t.primary }, itemStyle: { color: t.primary }, areaStyle: { color: pickColor(t.primary, 0.08) } },
        { name: '个人', type: 'line', smooth: true, data: bankTotals, lineStyle: { width: 2, color: t.cta }, itemStyle: { color: t.cta }, areaStyle: { color: pickColor(t.cta, 0.06) } },
        { name: '合计', type: 'bar', data: allTotals, barWidth: 10, itemStyle: { color: pickColor(t.primary, 0.18), borderRadius: [6, 6, 6, 6] } },
        { name: '正确率', type: 'line', yAxisIndex: 1, smooth: true, data: accAll, symbolSize: 5, lineStyle: { width: 2, color: pickColor(t.cta, 0.9) }, itemStyle: { color: pickColor(t.cta, 0.9) } },
      ],
    },
    t,
  );
}

function optionCalendar(ctx, t, chart) {
  if (!ctx.allDaily.length) {
    return emptyOption('日历热力图', '按“每日已做题”', t);
  }

  var compact = false;
  try {
    var w = getWidthSafe(chart);
    compact = w > 0 ? w < 520 : false;
  } catch (e) {
    compact = false;
  }
  var labelFs = compact ? 10 : 11;
  var labelMargin = compact ? 10 : 12;
  var leftPad = compact ? 30 : 40;

  var data = ctx.allDaily.map(function (d) { return [String(d.day), toInt(d.total)]; });
  var max = 0;
  data.forEach(function (it) { max = Math.max(max, toInt(it[1])); });
  var start = data[0][0];
  var end = data[data.length - 1][0];

  return applyBaseOption(
    {
      tooltip: {
        formatter: function (p) {
          var v = p && p.value ? p.value : null;
          if (!v) return '';
          return v[0] + '<br/>已做：' + v[1];
        },
      },
      visualMap: {
        min: 0,
        max: max || 1,
        orient: 'horizontal',
        left: 'center',
        top: 10,
        textStyle: { color: t.muted, fontWeight: 800 },
        inRange: { color: [pickColor(t.primary, 0.05), pickColor(t.primary, 0.14), pickColor(t.cta, 0.22), pickColor(t.cta, 0.46)] },
      },
      calendar: {
        top: 54,
        bottom: 16,
        left: leftPad,
        right: 18,
        cellSize: ['auto', 'auto'],
        range: [start, end],
        yearLabel: { show: false },
        dayLabel: {
          show: true,
          position: 'start',
          margin: labelMargin,
          nameMap: ['周日', '周一', '周二', '周三', '周四', '周五', '周六'],
          color: t.muted,
          fontWeight: 800,
          fontSize: labelFs,
        },
        monthLabel: { color: t.muted, fontWeight: 800, fontSize: labelFs },
        splitLine: { show: true, lineStyle: { color: pickColor(t.border, 0.65), width: 1 } },
        itemStyle: { borderWidth: 0, borderColor: 'transparent', borderRadius: 4 },
      },
      series: [{ type: 'heatmap', coordinateSystem: 'calendar', data: data }],
    },
    t,
  );
}

function optionHeatmap(ctx, t) {
  var heatmap = ctx.heatmap || {};
  var src = heatmap && heatmap.all ? heatmap.all : [];
  var max = toInt((heatmap && heatmap.max) || 0);
  if (!src.length || max <= 0) {
    return emptyOption('活跃热力图', '周 × 小时（近 ' + (ctx.payload.window_days || 30) + ' 天）', t);
  }

  var days = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
  var hours = [];
  for (var i = 0; i < 24; i++) hours.push(i < 10 ? '0' + i : '' + i);

  var data = src.map(function (it) {
    return [toInt(it[1]), toInt(it[0]), toInt(it[2])];
  });

  return applyBaseOption(
    {
      tooltip: {
        position: 'top',
        formatter: function (p) {
          var v = p && p.value ? p.value : null;
          if (!v) return '';
          var h = hours[v[0]];
          var d = days[v[1]];
          return d + ' ' + h + ':00<br/>答题：' + v[2];
        },
      },
      grid: { left: 44, right: 12, top: 18, bottom: 40, containLabel: false },
      xAxis: {
        type: 'category',
        data: hours,
        splitArea: { show: true, areaStyle: { color: [pickColor(t.surface, 0.0), pickColor(t.surface, 0.0)] } },
        axisLine: { lineStyle: { color: t.border } },
        axisLabel: { color: t.muted, interval: 3 },
      },
      yAxis: {
        type: 'category',
        data: days,
        splitArea: { show: true, areaStyle: { color: [pickColor(t.surface, 0.0), pickColor(t.surface, 0.0)] } },
        axisLine: { lineStyle: { color: t.border } },
        axisLabel: { color: t.muted },
      },
      visualMap: {
        min: 0,
        max: max,
        calculable: false,
        orient: 'horizontal',
        left: 'center',
        bottom: 6,
        textStyle: { color: t.muted, fontWeight: 800 },
        inRange: {
          color: [pickColor(t.primary, 0.06), pickColor(t.primary, 0.18), pickColor(t.cta, 0.26), pickColor(t.cta, 0.48)],
        },
      },
      series: [
        {
          type: 'heatmap',
          data: data,
          label: { show: false },
          itemStyle: { borderColor: pickColor(t.border, 0.65), borderWidth: 1 },
          emphasis: { itemStyle: { shadowBlur: 10, shadowColor: pickColor(t.cta, 0.25) } },
        },
      ],
    },
    t,
  );
}

function optionHourly(ctx, t) {
  var rows = ctx.hourly && ctx.hourly.all && ctx.hourly.all.length ? ctx.hourly.all : [];
  if (!rows.length) {
    return emptyOption('按小时分布', '统计近 ' + (ctx.payload.window_days || 30) + ' 天', t);
  }

  var x = rows.map(function (r) { var h = toInt(r.hour); return (h < 10 ? '0' + h : '' + h) + ':00'; });
  var y = rows.map(function (r) { return toInt(r.total); });
  var max = toInt((ctx.hourly && ctx.hourly.max) || 0) || 1;

  return applyBaseOption(
    {
      tooltip: { trigger: 'axis' },
      grid: { left: 12, right: 12, top: 18, bottom: 24, containLabel: true },
      xAxis: { type: 'category', data: x, axisLine: { lineStyle: { color: t.border } }, axisLabel: { color: t.muted, interval: 3 } },
      yAxis: { type: 'value', max: max, axisLabel: { color: t.muted }, splitLine: { lineStyle: { color: t.border, type: 'dashed', opacity: 0.6 } } },
      series: [
        {
          type: 'bar',
          data: y,
          barWidth: 10,
          itemStyle: { color: pickColor(t.cta, 0.38), borderRadius: [6, 6, 6, 6] },
        },
      ],
    },
    t,
  );
}

function optionWeekday(ctx, t) {
  var src = ctx.heatmap && ctx.heatmap.all ? ctx.heatmap.all : [];
  if (!src.length) {
    return emptyOption('周内分布', '周一到周日', t);
  }

  var days = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
  var sums = [0, 0, 0, 0, 0, 0, 0];
  src.forEach(function (it) {
    var d = toInt(it[0]);
    if (d >= 0 && d < 7) sums[d] += toInt(it[2]);
  });
  var max = 0;
  sums.forEach(function (v) { max = Math.max(max, v); });

  return applyBaseOption(
    {
      tooltip: { trigger: 'axis' },
      grid: { left: 12, right: 12, top: 18, bottom: 12, containLabel: true },
      xAxis: { type: 'category', data: days, axisLine: { lineStyle: { color: t.border } }, axisLabel: { color: t.muted } },
      yAxis: { type: 'value', max: max || 1, axisLabel: { color: t.muted }, splitLine: { lineStyle: { color: t.border, type: 'dashed', opacity: 0.6 } } },
      series: [{ type: 'bar', data: sums, barWidth: 14, itemStyle: { color: pickColor(t.primary, 0.38), borderRadius: [8, 8, 8, 8] } }],
    },
    t,
  );
}

function optionHealthGauge(ctx, t) {
  var score = clamp100(ctx.payload.health_score);
  return applyBaseOption(
    {
      title: {
        text: '学习健康分',
        subtext: '覆盖×正确×连续×错题治理',
        left: 12,
        top: 10,
        textStyle: { color: t.text, fontWeight: 950, fontSize: 12 },
        subtextStyle: { color: t.muted, fontSize: 11 },
      },
      series: [
        {
          type: 'gauge',
          startAngle: 210,
          endAngle: -30,
          center: ['50%', '56%'],
          radius: '82%',
          min: 0,
          max: 100,
          splitNumber: 5,
          axisLine: {
            lineStyle: {
              width: 14,
              color: [[1, pickColor(t.border, 0.35)]],
            },
          },
          progress: {
            show: true,
            width: 14,
            roundCap: true,
            itemStyle: {
              color: {
                type: 'linear',
                x: 0,
                y: 0,
                x2: 1,
                y2: 0,
                colorStops: [
                  { offset: 0, color: pickColor(t.primary, 0.92) },
                  { offset: 1, color: pickColor(t.cta, 0.92) },
                ],
              },
            },
          },
          pointer: { show: false },
          axisTick: { show: false },
          splitLine: { show: false },
          axisLabel: { show: false },
          anchor: { show: false },
          detail: {
            valueAnimation: true,
            offsetCenter: [0, '8%'],
            formatter: function (v) {
              var n = Math.round(Number(v || 0));
              return String(n);
            },
            color: t.text,
            fontSize: 44,
            fontWeight: 980,
          },
          data: [{ value: score }],
        },
      ],
    },
    t,
  );
}

function optionAssetTrend(ctx, t) {
  var mis = Array.isArray(ctx.payload.mistakes_daily) ? ctx.payload.mistakes_daily : [];
  var fav = Array.isArray(ctx.payload.favorites_daily) ? ctx.payload.favorites_daily : [];
  if (!mis.length && !fav.length) {
    return emptyOption('资产新增趋势', '错题 vs 收藏（近 ' + (ctx.payload.window_days || 30) + ' 天）', t);
  }

  var keys = (mis.length ? mis : fav).map(function (d) { return String(d.day); });
  var misMap = {};
  var favMap = {};
  mis.forEach(function (d) { if (d && d.day) misMap[String(d.day)] = d; });
  fav.forEach(function (d) { if (d && d.day) favMap[String(d.day)] = d; });

  var x = keys.map(function (k) { return fmtDay(k); });
  var m = keys.map(function (k) { return toInt((misMap[k] || {}).all); });
  var f = keys.map(function (k) { return toInt((favMap[k] || {}).all); });

  return applyBaseOption(
    {
      tooltip: { trigger: 'axis' },
      legend: { top: 8, textStyle: { color: t.muted, fontWeight: 800 } },
      grid: { left: 12, right: 12, top: 44, bottom: 18, containLabel: true },
      xAxis: { type: 'category', data: x, axisLine: { lineStyle: { color: t.border } }, axisLabel: { color: t.muted } },
      yAxis: { type: 'value', axisLabel: { color: t.muted }, splitLine: { lineStyle: { color: t.border, type: 'dashed', opacity: 0.6 } } },
      series: [
        {
          name: '错题新增',
          type: 'line',
          smooth: true,
          symbol: 'circle',
          symbolSize: 6,
          data: m,
          lineStyle: { width: 2, color: t.cta },
          itemStyle: { color: t.cta },
          areaStyle: { color: pickColor(t.cta, 0.1) },
        },
        {
          name: '收藏新增',
          type: 'line',
          smooth: true,
          symbol: 'circle',
          symbolSize: 6,
          data: f,
          lineStyle: { width: 2, color: t.primary },
          itemStyle: { color: t.primary },
          areaStyle: { color: pickColor(t.primary, 0.08) },
        },
      ],
    },
    t,
  );
}

function optionRadar(ctx, t) {
  var rows = Array.isArray(ctx.ability) ? ctx.ability : [];
  if (!rows.length) {
    return emptyOption('能力画像', '覆盖 × 正确 × 连续 × 错题治理', t);
  }

  var indicators = rows.map(function (r) {
    return { name: String(r.name || ''), max: 100 };
  });
  var vals = rows.map(function (r) {
    return clamp100(r.value);
  });

  return applyBaseOption(
    {
      tooltip: {},
      radar: {
        indicator: indicators,
        radius: '62%',
        splitNumber: 4,
        axisName: { color: t.muted, fontWeight: 800, fontSize: 11 },
        splitLine: { lineStyle: { color: pickColor(t.border, 0.9) } },
        splitArea: { areaStyle: { color: [pickColor(t.primary, 0.03), pickColor(t.primary, 0.01)] } },
        axisLine: { lineStyle: { color: pickColor(t.border, 0.8) } },
      },
      series: [
        {
          type: 'radar',
          data: [
            {
              value: vals,
              name: '能力',
              lineStyle: { color: t.cta, width: 2 },
              itemStyle: { color: t.cta },
              areaStyle: { color: pickColor(t.cta, 0.12) },
            },
          ],
        },
      ],
    },
    t,
  );
}

function optionTopMix(ctx, t) {
  var items = [];
  (Array.isArray(ctx.subjects) ? ctx.subjects : []).forEach(function (s) {
    var name = s && s.subject ? String(s.subject) : '公共题库';
    items.push({ name: '公·' + name, answered: toInt(s.answered), accuracy: toNum(s.accuracy) });
  });
  (Array.isArray(ctx.banks) ? ctx.banks : []).forEach(function (b) {
    var name = b && b.name ? String(b.name) : '个人题库';
    items.push({ name: '个·' + name, answered: toInt(b.answered), accuracy: toNum(b.accuracy) });
  });

  items.sort(function (a, b) { return (b.answered || 0) - (a.answered || 0); });
  var top = items.slice(0, 10);

  if (!top.length) {
    return emptyOption('Top 题库/科目', '按“已做题”排序', t);
  }

  return applyBaseOption(
    {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        formatter: function (params) {
          var p = params && params[0] ? params[0] : null;
          if (!p) return '';
          var it = top[p.dataIndex] || {};
          return it.name + '<br/>已做：' + (it.answered || 0) + ' · 正确率：' + (it.accuracy || 0) + '%';
        },
      },
      grid: { left: 12, right: 12, top: 18, bottom: 12, containLabel: true },
      xAxis: {
        type: 'value',
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: t.muted },
        splitLine: { lineStyle: { color: t.border, type: 'dashed', opacity: 0.6 } },
      },
      yAxis: {
        type: 'category',
        data: top.map(function (it) { return it.name; }),
        inverse: true,
        axisLine: { lineStyle: { color: t.border } },
        axisLabel: { color: t.muted, width: 140, overflow: 'truncate' },
      },
      series: [
        {
          name: '已做题',
          type: 'bar',
          data: top.map(function (it) { return it.answered; }),
          barWidth: 12,
          itemStyle: { color: pickColor(t.primary, 0.52), borderRadius: [8, 8, 8, 8] },
        },
      ],
    },
    t,
  );
}

function optionStackedCategory(ctx, t, list, titleText, subtitleText, useTimes) {
  var rows = (Array.isArray(list) ? list : []).slice();

  rows = rows
    .map(function (r) {
      var name = r && (r.label || r.q_type) ? String(r.label || r.q_type) : '未知';
      var pub = toInt(useTimes ? r.times_public : r.public);
      var bank = toInt(useTimes ? r.times_banks : r.banks);
      var order = r && r.difficulty != null ? toInt(r.difficulty) : null;
      return { name: name, public: pub, banks: bank, all: pub + bank, order: order };
    })
    .filter(function (r) { return r.all > 0; });

  var hasOrder = rows.some(function (r) { return r.order != null; });
  rows.sort(function (a, b) {
    if (hasOrder) return (a.order || 0) - (b.order || 0);
    return (b.all || 0) - (a.all || 0);
  });
  if (!hasOrder) rows = rows.slice(0, 12);

  if (!rows.length) {
    return emptyOption(titleText, subtitleText, t);
  }

  return applyBaseOption(
    {
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      legend: { top: 8, textStyle: { color: t.muted, fontWeight: 800 } },
      grid: { left: 12, right: 12, top: 44, bottom: 18, containLabel: true },
      xAxis: {
        type: 'category',
        data: rows.map(function (r) { return r.name; }),
        axisLine: { lineStyle: { color: t.border } },
        axisLabel: { color: t.muted, interval: 0, rotate: 18 },
      },
      yAxis: { type: 'value', axisLabel: { color: t.muted }, splitLine: { lineStyle: { color: t.border, type: 'dashed', opacity: 0.6 } } },
      series: [
        { name: '公共', type: 'bar', stack: 't', data: rows.map(function (r) { return r.public; }), barWidth: 12, itemStyle: { color: pickColor(t.primary, 0.28), borderRadius: [8, 8, 8, 8] } },
        { name: '个人', type: 'bar', stack: 't', data: rows.map(function (r) { return r.banks; }), barWidth: 12, itemStyle: { color: pickColor(t.cta, 0.22), borderRadius: [8, 8, 8, 8] } },
        { name: '合计', type: 'line', smooth: true, data: rows.map(function (r) { return r.all; }), symbol: 'circle', symbolSize: 5, lineStyle: { width: 2, color: t.cta }, itemStyle: { color: t.cta } },
      ],
    },
    t,
  );
}

function optionBankSplit(ctx, t) {
  var pub = toInt(((ctx.payload.public_summary || {}).answered || 0));
  var per = toInt(((ctx.payload.bank_summary || {}).answered || 0));
  var total = pub + per;
  if (total <= 0) {
    return emptyOption('公共/个人分布', '按“已做题”', t);
  }

  return applyBaseOption(
    {
      tooltip: { trigger: 'item' },
      legend: { top: 12, left: 12, textStyle: { color: t.muted, fontWeight: 800 } },
      series: [
        {
          type: 'pie',
          radius: ['50%', '68%'],
          center: ['50%', '52%'],
          avoidLabelOverlap: true,
          itemStyle: { borderColor: t.surface, borderWidth: 2 },
          label: { color: t.muted, fontWeight: 800, formatter: '{b} {d}%' },
          labelLine: { length: 12, length2: 10 },
          labelLayout: { hideOverlap: true },
          data: [
            { name: '公共题库', value: pub, itemStyle: { color: pickColor(t.primary, 0.55) } },
            { name: '个人题库', value: per, itemStyle: { color: pickColor(t.cta, 0.5) } },
          ],
        },
      ],
      graphic: [
        {
          type: 'text',
          left: 'center',
          top: '42%',
          style: { text: '已做题\\n' + total, fill: t.text, fontSize: 12, fontWeight: 900, align: 'center' },
        },
      ],
    },
    t,
  );
}

function optionGlobalLoop(ctx, t, chart) {
  var compact = false;
  try {
    var w = getWidthSafe(chart);
    compact = w > 0 ? w < 720 : false;
  } catch (e) {
    compact = false;
  }
  var padL = compact ? 14 : 18;
  var padR = compact ? 62 : 86;
  var labelFs = compact ? 11 : 12;
  var padTB = compact ? 10 : 14;
  var nodeGap = compact ? 14 : 18;

  var all = ctx.payload.all_summary || {};
  var totalQuestionsPublic = toInt(ctx.payload.total_questions);
  var totalQuestionsBanks = toInt(((ctx.payload.bank_summary || {}).total_questions || 0));
  var totalQuestionsAll = totalQuestionsPublic + totalQuestionsBanks;

  var answered = toInt(all.answered);
  var correct = toInt(all.correct);
  var favorites = toInt(all.favorites);
  var mistakes = toInt(all.mistakes);

  if (answered <= 0 && totalQuestionsAll <= 0 && favorites <= 0 && mistakes <= 0) {
    return emptyOption('学习闭环地图', '暂无可用数据', t);
  }

  var untouched = Math.max(0, totalQuestionsAll - answered);
  var incorrect = Math.max(0, answered - correct);
  var tagPct = clamp100(((ctx.payload.tags_kpis || {}).tagged_answered_coverage || 0));
  var tagged = Math.max(0, Math.round((answered * tagPct) / 100));

  function link(source, target, value) {
    var v = toInt(value);
    if (v <= 0) return null;
    return { source: source, target: target, value: v };
  }

  var links = [
    link('题库总量', '已做题', answered),
    link('题库总量', '未触达题', untouched),
    link('已做题', '正确题', correct),
    link('已做题', '错误题', incorrect),
    link('错误题', '错题资产', mistakes),
    link('已做题', '收藏资产', favorites),
    link('已做题', '标签覆盖题', tagged),
  ].filter(Boolean);

  if (!links.length) {
    return emptyOption('学习闭环地图', '暂无可用数据', t);
  }

  var nodes = [
    { name: '题库总量', itemStyle: { color: pickColor(t.primary, 0.22), borderColor: pickColor(t.primary, 0.55), borderWidth: 1 } },
    { name: '已做题', itemStyle: { color: pickColor(t.cta, 0.18), borderColor: pickColor(t.cta, 0.52), borderWidth: 1 } },
    { name: '未触达题', itemStyle: { color: pickColor(t.border, 0.18), borderColor: pickColor(t.border, 0.62), borderWidth: 1 } },
    { name: '正确题', itemStyle: { color: pickColor(t.primary, 0.34), borderColor: pickColor(t.primary, 0.75), borderWidth: 1 } },
    { name: '错误题', itemStyle: { color: pickColor(t.cta, 0.28), borderColor: pickColor(t.cta, 0.75), borderWidth: 1 } },
    { name: '错题资产', itemStyle: { color: pickColor(t.cta, 0.42), borderColor: pickColor(t.cta, 0.85), borderWidth: 1 } },
    { name: '收藏资产', itemStyle: { color: pickColor(t.primary, 0.42), borderColor: pickColor(t.primary, 0.85), borderWidth: 1 } },
    { name: '标签覆盖题', itemStyle: { color: pickColor(t.primary, 0.18), borderColor: pickColor(t.primary, 0.6), borderWidth: 1 } },
  ];

  return applyBaseOption(
    {
      tooltip: {
        trigger: 'item',
        formatter: function (p) {
          if (!p) return '';
          if (p.dataType === 'edge') {
            var d = p.data || {};
            var v = toInt(d.value);
            var s = String(d.source || '');
            var tg = String(d.target || '');
            var extra = '';
            if (s === '题库总量' && tg === '已做题' && totalQuestionsAll > 0) extra = '（覆盖 ' + ((v * 100) / totalQuestionsAll).toFixed(1) + '%）';
            if (s === '已做题' && tg === '正确题' && answered > 0) extra = '（正确率 ' + ((v * 100) / answered).toFixed(1) + '%）';
            if (s === '已做题' && tg === '错误题' && answered > 0) extra = '（错误率 ' + ((v * 100) / answered).toFixed(1) + '%）';
            if (s === '已做题' && tg === '标签覆盖题' && answered > 0) extra = '（覆盖 ' + ((v * 100) / answered).toFixed(1) + '%）';
            return s + ' → ' + tg + '<br/>数量：' + v + extra;
          }
          var name = String((p.data || {}).name || p.name || '');
          return name + '<br/>权重：' + toInt(p.value);
        },
      },
      series: [
        {
          type: 'sankey',
          data: nodes,
          links: links,
          left: padL,
          right: padR,
          top: padTB,
          bottom: padTB,
          nodeAlign: 'justify',
          nodeWidth: 14,
          nodeGap: nodeGap,
          draggable: false,
          emphasis: { focus: 'adjacency' },
          label: {
            color: t.text,
            fontFamily: t.fontBody,
            fontWeight: 900,
            fontSize: labelFs,
            lineHeight: compact ? 14 : 16,
            backgroundColor: pickColor(t.surface, 0.88),
            padding: compact ? [2, 6] : [3, 8],
            borderRadius: 10,
            formatter: function (p) {
              var v = toInt(p.value);
              return p.name + (v > 0 ? '\\n' + v : '');
            },
          },
          lineStyle: {
            color: 'gradient',
            curveness: 0.5,
            opacity: 0.42,
          },
        },
      ],
    },
    t,
  );
}

function optionBankCategories(ctx, t) {
  if (!ctx.bankCategories.length) {
    return emptyOption('分类分布', '个人题库（按“已做题”）', t);
  }

  var hasAnswered = ctx.bankCategories.some(function (r) { return toInt(r && r.answered) > 0; });
  var metricKey = hasAnswered ? 'answered' : 'total';
  var metricName = hasAnswered ? '已做题' : '总题';

  var colors = [
    pickColor(t.primary, 0.28),
    pickColor(t.cta, 0.26),
    pickColor(t.primary, 0.18),
    pickColor(t.cta, 0.18),
    pickColor(t.primary, 0.36),
    pickColor(t.cta, 0.36),
  ];

  var data = ctx.bankCategories.map(function (r, idx) {
    return {
      name: String(r.category_name || '未分类'),
      value: toInt(r && r[metricKey]),
      bank_count: toInt(r.bank_count),
      total: toInt(r.total),
      answered: toInt(r.answered),
      accuracy: toNum(r.accuracy),
      completion: toNum(r.completion),
      itemStyle: { color: colors[idx % colors.length] },
    };
  });

  var maxVal = 0;
  data.forEach(function (d) { maxVal = Math.max(maxVal, toInt(d && d.value)); });
  if (maxVal <= 0) {
    return emptyOption('分类分布', '个人题库（按“' + metricName + '”）', t);
  }

  return applyBaseOption(
    {
      tooltip: {
        formatter: function (p) {
          var d = p && p.data ? p.data : {};
          return (
            (d.name || '') +
            '<br/>' +
            metricName +
            '：' +
            (d.value || 0) +
            ' · 题库数：' +
            (d.bank_count || 0) +
            '<br/>总题：' +
            (d.total || 0) +
            ' · 已做：' +
            (d.answered || 0) +
            '<br/>正确率：' +
            (d.accuracy || 0) +
            '% · 完成度：' +
            (d.completion || 0) +
            '%'
          );
        },
      },
      series: [
        {
          type: 'treemap',
          roam: false,
          nodeClick: false,
          breadcrumb: { show: false },
          label: { show: true, color: t.text, fontWeight: 900 },
          upperLabel: { show: false },
          itemStyle: { borderColor: t.border, borderWidth: 1, gapWidth: 2 },
          data: data,
        },
      ],
    },
    t,
  );
}

function optionBankBubble(ctx, t) {
  if (!ctx.banks.length) {
    return emptyOption('题库规模与质量', '完成度 × 正确率（个人题库）', t);
  }

  var pts = [];
  var sumAnswered = 0;
  var sumTotal = 0;
  ctx.banks.forEach(function (b) {
    var answered = toInt(b.answered);
    var total = toInt(b.total);
    sumAnswered += answered;
    sumTotal += total;
    if (total <= 0 && answered <= 0) return;
    pts.push({
      name: String(b.name || ''),
      completion: clamp100(b.completion),
      accuracy: clamp100(b.accuracy),
      answered: answered,
      total: total,
    });
  });
  if (!pts.length) {
    return emptyOption('题库规模与质量', '完成度 × 正确率（个人题库）', t);
  }

  var groupCount = {};
  pts.forEach(function (p) {
    var k = String(p.completion) + '|' + String(p.accuracy);
    groupCount[k] = (groupCount[k] || 0) + 1;
  });
  var groupUsed = {};

  var data = pts.map(function (p) {
    var k = String(p.completion) + '|' + String(p.accuracy);
    var idx = groupUsed[k] || 0;
    groupUsed[k] = idx + 1;

    var x = p.completion;
    var y = p.accuracy;
    if ((groupCount[k] || 0) > 1) {
      var eps = 3.2;
      var ix = idx % 3;
      var iy = Math.floor(idx / 3);

      var dx = (ix - 1) * eps;
      var dy = (iy - 1) * eps;

      if (x <= eps) dx = ix * eps;
      if (x >= 100 - eps) dx = -ix * eps;
      if (y <= eps) dy = iy * eps;
      if (y >= 100 - eps) dy = -iy * eps;

      x = clamp100(x + dx);
      y = clamp100(y + dy);
    }

    return {
      name: p.name,
      value: [x, y, p.answered, p.total],
    };
  });

  var showHint = sumTotal > 0 && sumAnswered <= 0;

  return applyBaseOption(
    {
      tooltip: {
        formatter: function (p) {
          var v = p && p.value ? p.value : [];
          return (
            (p.name || '') +
            '<br/>完成度：' +
            (v[0] || 0) +
            '% · 正确率：' +
            (v[1] || 0) +
            '%<br/>已做：' +
            (v[2] || 0) +
            ' · 总题：' +
            (v[3] || 0)
          );
        },
      },
      grid: { left: 12, right: 44, top: showHint ? 56 : 30, bottom: 24, containLabel: true },
      xAxis: {
        type: 'value',
        min: 0,
        max: 100,
        axisLabel: { color: t.muted, formatter: '{value}%' },
        axisLine: { lineStyle: { color: t.border } },
        splitLine: { lineStyle: { color: t.border, type: 'dashed', opacity: 0.5 } },
      },
      yAxis: {
        type: 'value',
        min: 0,
        max: 100,
        axisLabel: { color: t.muted, formatter: '{value}%' },
        axisLine: { lineStyle: { color: t.border } },
        splitLine: { lineStyle: { color: t.border, type: 'dashed', opacity: 0.5 } },
        name: '正确率',
        nameTextStyle: { color: t.muted, fontWeight: 800 },
      },
      graphic: showHint
        ? [
            {
              type: 'text',
              left: 12,
              top: 10,
              style: {
                text: '提示：个人题库暂无练习记录（先做几题，图表会自动有分布）',
                fill: t.muted,
                fontSize: 11,
                fontWeight: 800,
                fontFamily: t.fontBody,
              },
            },
          ]
        : [],
      series: [
        {
          type: 'scatter',
          data: data,
          clip: false,
          symbolSize: function (val) {
            var total = (val && val[3]) || 0;
            return Math.max(10, Math.min(42, Math.sqrt(Math.max(0, total)) * 2 + 8));
          },
          itemStyle: { color: pickColor(t.cta, 0.38), borderColor: pickColor(t.cta, 0.65), borderWidth: 1 },
          emphasis: { itemStyle: { shadowBlur: 10, shadowColor: pickColor(t.cta, 0.25) } },
        },
      ],
    },
    t,
  );
}

function optionBankRank(ctx, t) {
  if (!ctx.banks.length) {
    return emptyOption('题库排行', '按“已做题”排序（个人题库）', t);
  }

  var list = ctx.banks.map(function (b) {
    return {
      name: String(b.name || ''),
      total: toInt(b.total),
      answered: toInt(b.answered),
      accuracy: toNum(b.accuracy),
      mistakes_times: toInt(b.mistakes_times),
    };
  });

  var hasAnswered = list.some(function (it) { return (it.answered || 0) > 0; });
  var metricKey = hasAnswered ? 'answered' : 'total';
  var metricName = hasAnswered ? '已做' : '总题';

  list = list.sort(function (a, b) { return (b[metricKey] || 0) - (a[metricKey] || 0); }).slice(0, 12);

  if (!list.length) {
    return emptyOption('题库排行', '按“已做题”排序（个人题库）', t);
  }

  var maxVal = 0;
  list.forEach(function (it) { maxVal = Math.max(maxVal, toInt(it && it[metricKey])); });
  if (maxVal <= 0) {
    return emptyOption('题库排行', '暂无个人题库练习数据', t);
  }

  return applyBaseOption(
    {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        formatter: function (params) {
          var p = params && params[0] ? params[0] : null;
          if (!p) return '';
          var it = list[p.dataIndex] || {};
          var head = it.name + '<br/>' + metricName + '：' + (it[metricKey] || 0);
          var extra = ' · 总题：' + (it.total || 0) + ' · 正确率：' + it.accuracy + '% · 错题次数：' + it.mistakes_times;
          return head + extra;
        },
      },
      grid: { left: 12, right: 44, top: 26, bottom: 12, containLabel: true },
      xAxis: {
        type: 'value',
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: t.muted },
        splitLine: { lineStyle: { color: t.border, type: 'dashed', opacity: 0.6 } },
      },
      yAxis: {
        type: 'category',
        data: list.map(function (it) { return it.name; }),
        inverse: true,
        axisLine: { lineStyle: { color: t.border } },
        axisLabel: { color: t.muted, width: 140, overflow: 'truncate' },
      },
      series: [
        {
          name: metricName,
          type: 'bar',
          data: list.map(function (it) { return toInt(it && it[metricKey]); }),
          barWidth: 12,
          itemStyle: { color: pickColor(t.primary, 0.5), borderRadius: [8, 8, 8, 8] },
        },
      ],
    },
    t,
  );
}

function optionSubjectProgress(ctx, t) {
  var list = (Array.isArray(ctx.subjects) ? ctx.subjects : []).slice();
  list = list
    .map(function (s) {
      return {
        name: s && s.subject ? String(s.subject) : '未分类',
        total: toInt(s.total),
        answered: toInt(s.answered),
        completion: clamp100(s.completion),
        accuracy: clamp100(s.accuracy),
        mistakes: toInt(s.mistakes),
        favorites: toInt(s.favorites),
      };
    })
    .sort(function (a, b) { return (b.answered || 0) - (a.answered || 0); })
    .slice(0, 12);

  if (!list.length) {
    return emptyOption('科目进度与正确率', 'Top 科目（按已做题）', t);
  }

  return applyBaseOption(
    {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        formatter: function (params) {
          var idx = params && params[0] ? params[0].dataIndex : 0;
          var it = list[idx] || {};
          return (
            it.name +
            '<br/>完成度：' +
            it.completion +
            '% · 正确率：' +
            it.accuracy +
            '%<br/>已做：' +
            it.answered +
            ' / ' +
            it.total +
            ' · 错题：' +
            it.mistakes +
            ' · 收藏：' +
            it.favorites
          );
        },
      },
      grid: { left: 12, right: 12, top: 26, bottom: 12, containLabel: true },
      xAxis: { type: 'value', min: 0, max: 100, axisLabel: { color: t.muted, formatter: '{value}%' }, splitLine: { lineStyle: { color: t.border, type: 'dashed', opacity: 0.6 } } },
      yAxis: { type: 'category', data: list.map(function (it) { return it.name; }), inverse: true, axisLine: { lineStyle: { color: t.border } }, axisLabel: { color: t.muted, width: 160, overflow: 'truncate' } },
      series: [
        { name: '完成度', type: 'bar', data: list.map(function (it) { return it.completion; }), barWidth: 12, itemStyle: { color: pickColor(t.primary, 0.42), borderRadius: [8, 8, 8, 8] } },
        { name: '正确率', type: 'scatter', data: list.map(function (it) { return it.accuracy; }), symbolSize: 9, itemStyle: { color: t.cta } },
      ],
    },
    t,
  );
}

function optionSubjectRisk(ctx, t) {
  var list = (Array.isArray(ctx.subjects) ? ctx.subjects : []).slice();
  list = list
    .map(function (s) {
      return {
        name: s && s.subject ? String(s.subject) : '未分类',
        completion: clamp100(s.completion),
        accuracy: clamp100(s.accuracy),
        answered: toInt(s.answered),
        mistakes: toInt(s.mistakes),
        favorites: toInt(s.favorites),
      };
    })
    .filter(function (s) { return s.answered > 0 || s.mistakes > 0 || s.favorites > 0; });

  if (!list.length) {
    return emptyOption('科目风险分布', '完成度 × 正确率', t);
  }

  var data = list.map(function (it) {
    return { name: it.name, value: [it.completion, it.accuracy, it.mistakes, it.answered, it.favorites] };
  });

  return applyBaseOption(
    {
      tooltip: {
        trigger: 'item',
        formatter: function (p) {
          var v = p && p.value ? p.value : [];
          return (
            (p.name || '') +
            '<br/>完成度：' +
            (v[0] || 0) +
            '% · 正确率：' +
            (v[1] || 0) +
            '%<br/>已做：' +
            (v[3] || 0) +
            ' · 错题：' +
            (v[2] || 0) +
            ' · 收藏：' +
            (v[4] || 0)
          );
        },
      },
      grid: { left: 12, right: 44, top: 32, bottom: 18, containLabel: true },
      xAxis: { type: 'value', min: 0, max: 100, axisLabel: { color: t.muted }, splitLine: { lineStyle: { color: t.border, type: 'dashed', opacity: 0.6 } } },
      yAxis: { type: 'value', min: 0, max: 100, name: '正确率%', nameTextStyle: { color: t.muted }, axisLabel: { color: t.muted }, splitLine: { lineStyle: { color: t.border, type: 'dashed', opacity: 0.6 } } },
      series: [
        {
          type: 'scatter',
          data: data,
          clip: false,
          symbolSize: function (v) {
            var m = toInt(v[2]);
            return Math.max(10, Math.min(34, 10 + Math.sqrt(m) * 6));
          },
          itemStyle: { color: pickColor(t.cta, 0.5), borderColor: pickColor(t.cta, 0.7), borderWidth: 1 },
          emphasis: { focus: 'series' },
        },
      ],
    },
    t,
  );
}

function optionDailySplit(ctx, t, list, titleText, subtitleText, colorA, colorB) {
  var src = Array.isArray(list) ? list : [];
  if (!src.length) {
    return emptyOption(titleText, subtitleText, t);
  }

  var x = src.map(function (d) { return fmtDay(d.day); });
  var a = src.map(function (d) { return toInt(d.public); });
  var b = src.map(function (d) { return toInt(d.banks); });
  var all = src.map(function (d) { return toInt(d.all); });

  return applyBaseOption(
    {
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      legend: { top: 8, textStyle: { color: t.muted, fontWeight: 800 } },
      grid: { left: 12, right: 12, top: 44, bottom: 18, containLabel: true },
      xAxis: { type: 'category', data: x, axisLine: { lineStyle: { color: t.border } }, axisLabel: { color: t.muted } },
      yAxis: { type: 'value', axisLabel: { color: t.muted }, splitLine: { lineStyle: { color: t.border, type: 'dashed', opacity: 0.6 } } },
      series: [
        { name: '公共', type: 'bar', stack: 't', data: a, barWidth: 12, itemStyle: { color: pickColor(colorA, 0.26), borderRadius: [8, 8, 8, 8] } },
        { name: '个人', type: 'bar', stack: 't', data: b, barWidth: 12, itemStyle: { color: pickColor(colorB, 0.22), borderRadius: [8, 8, 8, 8] } },
        { name: '合计', type: 'line', smooth: true, data: all, symbol: 'circle', symbolSize: 5, lineStyle: { width: 2, color: colorB }, itemStyle: { color: colorB } },
      ],
    },
    t,
  );
}

function optionRankBar(ctx, t, rows, titleText, subtitleText, color) {
  var list = Array.isArray(rows) ? rows : [];
  list = list
    .map(function (it) {
      var name = (it && it.name ? String(it.name) : '') || '—';
      var src = it && it.source === 'banks' ? '个·' : it && it.source === 'public' ? '公·' : '';
      var v = toInt(it && (it.times != null ? it.times : it.count));
      return { name: src + name, value: v };
    })
    .filter(function (it) { return it.value > 0; })
    .sort(function (a, b) { return (b.value || 0) - (a.value || 0); })
    .slice(0, 12);

  if (!list.length) {
    return emptyOption(titleText, subtitleText, t);
  }

  return applyBaseOption(
    {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        formatter: function (params) {
          var p = params && params[0] ? params[0] : null;
          if (!p) return '';
          var it = list[p.dataIndex] || {};
          return it.name + '<br/>' + (titleText || '数量') + '：' + (it.value || 0);
        },
      },
      grid: { left: 12, right: 12, top: 18, bottom: 12, containLabel: true },
      xAxis: { type: 'value', axisLabel: { color: t.muted }, splitLine: { lineStyle: { color: t.border, type: 'dashed', opacity: 0.6 } } },
      yAxis: { type: 'category', data: list.map(function (it) { return it.name; }), inverse: true, axisLine: { lineStyle: { color: t.border } }, axisLabel: { color: t.muted, width: 160, overflow: 'truncate' } },
      series: [{ type: 'bar', data: list.map(function (it) { return it.value; }), barWidth: 12, itemStyle: { color: pickColor(color, 0.52), borderRadius: [8, 8, 8, 8] } }],
    },
    t,
  );
}

function optionTagTreemap(ctx, t) {
  var tags = Array.isArray(ctx.payload.tags_all) ? ctx.payload.tags_all : [];
  var data = tags
    .map(function (it) {
      return { name: String(it && it.tag ? it.tag : '—'), value: toInt(it && it.count) };
    })
    .filter(function (it) { return it.value > 0 && it.name; })
    .sort(function (a, b) { return (b.value || 0) - (a.value || 0); })
    .slice(0, 60);

  if (!data.length) {
    return emptyOption('标签结构', '暂无可用标签数据', t);
  }

  return applyBaseOption(
    {
      tooltip: { trigger: 'item' },
      series: [
        {
          type: 'treemap',
          roam: false,
          nodeClick: false,
          breadcrumb: { show: false },
          data: data,
          label: { show: true, color: t.text, fontSize: 11, overflow: 'truncate' },
          upperLabel: { show: false },
          itemStyle: { borderColor: pickColor(t.border, 0.8), borderWidth: 1, gapWidth: 1 },
          emphasis: { itemStyle: { borderColor: pickColor(t.cta, 0.7), borderWidth: 1 } },
          levels: [
            {
              itemStyle: { borderColor: pickColor(t.border, 0.8), borderWidth: 1, gapWidth: 1 },
            },
          ],
        },
      ],
    },
    t,
  );
}

function optionTagGraph(ctx, t) {
  var g = ctx.payload.tags_graph || {};
  var nodesRaw = Array.isArray(g.nodes) ? g.nodes : [];
  var linksRaw = Array.isArray(g.links) ? g.links : [];
  if (!nodesRaw.length || !linksRaw.length) {
    return emptyOption('标签共现网络', '暂无可用共现数据', t);
  }

  var nodes = nodesRaw.map(function (n) {
    var v = toInt(n && n.value);
    return {
      name: String(n && n.name ? n.name : '—'),
      value: v,
      symbolSize: Math.max(10, Math.min(42, 10 + Math.sqrt(Math.max(1, v)) * 5)),
      itemStyle: { color: pickColor(t.primary, 0.32), borderColor: pickColor(t.primary, 0.52), borderWidth: 1 },
      label: { show: v >= 6, color: t.text, fontSize: 11 },
    };
  });

  var links = linksRaw.map(function (l) {
    return {
      source: String(l && l.source ? l.source : ''),
      target: String(l && l.target ? l.target : ''),
      value: toInt(l && l.value),
    };
  });

  return applyBaseOption(
    {
      tooltip: {
        trigger: 'item',
        formatter: function (p) {
          if (!p) return '';
          if (p.dataType === 'edge') {
            var d = p.data || {};
            return String(d.source) + ' ↔ ' + String(d.target) + '<br/>共现：' + (d.value || 0);
          }
          var d2 = p.data || {};
          return String(d2.name || '') + '<br/>权重：' + (d2.value || 0);
        },
      },
      series: [
        {
          type: 'graph',
          layout: 'force',
          roam: true,
          data: nodes,
          links: links,
          lineStyle: { color: pickColor(t.border, 0.65), width: 1, opacity: 0.75 },
          emphasis: { focus: 'adjacency' },
          force: { repulsion: 120, edgeLength: [40, 120], friction: 0.25 },
        },
      ],
    },
    t,
  );
}

function optionTagTop(ctx, t) {
  var tags = Array.isArray(ctx.payload.tags_all) ? ctx.payload.tags_all : [];
  var list = tags
    .map(function (it) {
      return {
        name: String(it && it.tag ? it.tag : '—'),
        count: toInt(it && it.count),
        answered: toInt(it && it.answered),
        accuracy: clamp100(it && it.accuracy),
        mistakesTimes: toInt(it && it.mistakes_times),
        favorites: toInt(it && it.favorites),
      };
    })
    .filter(function (it) { return it.count > 0; })
    .sort(function (a, b) { return (b.count || 0) - (a.count || 0); })
    .slice(0, 12);

  if (!list.length) {
    return emptyOption('标签 Top', '按题目数排序', t);
  }

  return applyBaseOption(
    {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        formatter: function (params) {
          var p = params && params[0] ? params[0] : null;
          if (!p) return '';
          var it = list[p.dataIndex] || {};
          return (
            it.name +
            '<br/>题目：' +
            it.count +
            ' · 已做：' +
            it.answered +
            ' · 正确率：' +
            it.accuracy +
            '%<br/>错题次数：' +
            it.mistakesTimes +
            ' · 收藏：' +
            it.favorites
          );
        },
      },
      grid: { left: 12, right: 12, top: 18, bottom: 12, containLabel: true },
      xAxis: { type: 'value', axisLabel: { color: t.muted }, splitLine: { lineStyle: { color: t.border, type: 'dashed', opacity: 0.6 } } },
      yAxis: { type: 'category', data: list.map(function (it) { return it.name; }), inverse: true, axisLine: { lineStyle: { color: t.border } }, axisLabel: { color: t.muted, width: 160, overflow: 'truncate' } },
      series: [{ type: 'bar', data: list.map(function (it) { return it.count; }), barWidth: 12, itemStyle: { color: pickColor(t.primary, 0.52), borderRadius: [8, 8, 8, 8] } }],
    },
    t,
  );
}

function optionTagAccuracy(ctx, t) {
  var tags = Array.isArray(ctx.payload.tags_all) ? ctx.payload.tags_all : [];
  var data = tags
    .map(function (it) {
      return {
        name: String(it && it.tag ? it.tag : '—'),
        value: [toInt(it && it.count), clamp100(it && it.accuracy), toInt(it && it.answered), toInt(it && it.mistakes_times), toInt(it && it.favorites)],
      };
    })
    .filter(function (it) { return (it.value[0] || 0) > 0; });

  if (!data.length) {
    return emptyOption('标签质量', '题目数 × 正确率', t);
  }

  return applyBaseOption(
    {
      tooltip: {
        trigger: 'item',
        formatter: function (p) {
          var v = p && p.value ? p.value : [];
          return (
            (p.name || '') +
            '<br/>题目：' +
            (v[0] || 0) +
            ' · 正确率：' +
            (v[1] || 0) +
            '%<br/>已做：' +
            (v[2] || 0) +
            ' · 错题次数：' +
            (v[3] || 0) +
            ' · 收藏：' +
            (v[4] || 0)
          );
        },
      },
      grid: { left: 16, right: 44, top: 44, bottom: 24, containLabel: true },
      xAxis: { type: 'value', axisLabel: { color: t.muted }, splitLine: { lineStyle: { color: t.border, type: 'dashed', opacity: 0.6 } } },
      yAxis: { type: 'value', min: 0, max: 100, name: '正确率%', nameTextStyle: { color: t.muted }, axisLabel: { color: t.muted, formatter: '{value}%' }, splitLine: { lineStyle: { color: t.border, type: 'dashed', opacity: 0.6 } } },
      series: [
        {
          type: 'scatter',
          data: data,
          clip: false,
          symbolSize: function (v) {
            var a = toInt(v[2]);
            return Math.max(10, Math.min(36, 10 + Math.sqrt(Math.max(1, a)) * 4));
          },
          itemStyle: { color: pickColor(t.cta, 0.42), borderColor: pickColor(t.cta, 0.7), borderWidth: 1 },
          emphasis: { focus: 'series' },
        },
      ],
    },
    t,
  );
}

function buildDataCenterOptionById(id, ctx, t, chart) {
  if (id === 'dcTrendDetailChart') return optionTrendDetail(ctx, t);
  if (id === 'dcGlobalLoopChart') return optionGlobalLoop(ctx, t, chart);
  if (id === 'dcHealthGaugeChart') return optionHealthGauge(ctx, t);
  if (id === 'dcCalendarChart') return optionCalendar(ctx, t, chart);
  if (id === 'dcHeatmapChart') return optionHeatmap(ctx, t);
  if (id === 'dcHourlyChart') return optionHourly(ctx, t);
  if (id === 'dcWeekdayChart') return optionWeekday(ctx, t);
  if (id === 'dcAssetTrendChart') return optionAssetTrend(ctx, t);
  if (id === 'dcRadarChart') return optionRadar(ctx, t);
  if (id === 'dcTopMixChart') return optionTopMix(ctx, t);
  if (id === 'dcTypeDistChart') return optionStackedCategory(ctx, t, ctx.payload.mistakes_by_type, '错题题型结构', '公共 + 个人', true);
  if (id === 'dcDifficultyDistChart') return optionStackedCategory(ctx, t, ctx.payload.mistakes_by_difficulty, '错题难度结构', '公共 + 个人', true);

  if (id === 'dcBankSplitChart') return optionBankSplit(ctx, t);
  if (id === 'dcBankCategoryChart') return optionBankCategories(ctx, t);
  if (id === 'dcBankBubbleChart') return optionBankBubble(ctx, t);
  if (id === 'dcBankRankChart') return optionBankRank(ctx, t);
  if (id === 'dcSubjectProgressChart') return optionSubjectProgress(ctx, t);
  if (id === 'dcSubjectRiskChart') return optionSubjectRisk(ctx, t);

  if (id === 'dcMistakeTrendChart') return optionDailySplit(ctx, t, ctx.payload.mistakes_daily, '错题新增趋势', '公共 + 个人（近 ' + (ctx.payload.window_days || 30) + ' 天）', t.primary, t.cta);
  if (id === 'dcMistakeTopChart') return optionRankBar(ctx, t, ctx.payload.mistakes_top_items, '错题次数', '公共按科目 / 个人按题库', t.cta);
  if (id === 'dcMistakeDifficultyChart') return optionStackedCategory(ctx, t, ctx.payload.mistakes_by_difficulty, '错题难度分布', '次数（公共 + 个人）', true);
  if (id === 'dcMistakeTypeChart') return optionStackedCategory(ctx, t, ctx.payload.mistakes_by_type, '错题题型分布', '次数（公共 + 个人）', true);

  if (id === 'dcFavoriteTrendChart') return optionDailySplit(ctx, t, ctx.payload.favorites_daily, '收藏新增趋势', '公共 + 个人（近 ' + (ctx.payload.window_days || 30) + ' 天）', t.primary, t.cta);
  if (id === 'dcFavoriteTopChart') return optionRankBar(ctx, t, ctx.payload.favorites_top_items, '收藏数量', '公共按科目 / 个人按题库', t.primary);
  if (id === 'dcFavoriteDifficultyChart') return optionStackedCategory(ctx, t, ctx.payload.favorites_by_difficulty, '收藏难度分布', '数量（公共 + 个人）', false);
  if (id === 'dcFavoriteTypeChart') return optionStackedCategory(ctx, t, ctx.payload.favorites_by_type, '收藏题型分布', '数量（公共 + 个人）', false);

  if (id === 'dcTagTreemapChart') return optionTagTreemap(ctx, t);
  if (id === 'dcTagGraphChart') return optionTagGraph(ctx, t);
  if (id === 'dcTagTopChart') return optionTagTop(ctx, t);
  if (id === 'dcTagAccuracyChart') return optionTagAccuracy(ctx, t);

  return null;
}

function getDataCenterThemeTokens(isDark, style) {
  var isD = Boolean(isDark);
  var st = String(style || 'default').toLowerCase();

  var text = isD ? '#FFFFFF' : '#111111';
  var muted = isD ? 'rgba(235, 235, 245, 0.6)' : 'rgba(60, 60, 67, 0.6)';
  var fontBody = 'system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, \"PingFang SC\", \"Microsoft YaHei\", sans-serif';
  var fontHeading = fontBody;

  var base = {
    bg: isD ? '#000000' : '#F2F2F7',
    surface: isD ? 'rgba(28, 28, 30, 0.86)' : 'rgba(255, 255, 255, 0.86)',
    surface2: isD ? 'rgba(28, 28, 30, 0.72)' : 'rgba(255, 255, 255, 0.72)',
    border: isD ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.06)',
    primary: text,
    cta: '#007AFF',
    muted: muted,
    text: text,
    fontBody: fontBody,
    fontHeading: fontHeading,
  };

  if (st === 'mist') {
    if (isD) {
      base.bg = '#0C111A';
      base.surface = 'rgba(20, 27, 39, 0.86)';
      base.surface2 = 'rgba(20, 27, 39, 0.72)';
      base.border = 'rgba(199, 210, 254, 0.16)';
      base.primary = '#818CF8';
      base.cta = '#F97316';
    } else {
      base.bg = '#EEF2FF';
      base.surface = 'rgba(255, 255, 255, 0.86)';
      base.surface2 = 'rgba(255, 255, 255, 0.72)';
      base.border = '#C7D2FE';
      base.primary = '#4F46E5';
      base.cta = '#F97316';
    }
  } else if (st === 'dune') {
    if (isD) {
      base.bg = '#15110D';
      base.surface = 'rgba(29, 24, 19, 0.86)';
      base.surface2 = 'rgba(29, 24, 19, 0.72)';
      base.border = 'rgba(224, 194, 162, 0.16)';
      base.primary = '#E7A46A';
      base.cta = '#E7A46A';
    } else {
      base.bg = '#FDFBF7';
      base.surface = 'rgba(255, 253, 249, 0.86)';
      base.surface2 = 'rgba(255, 253, 249, 0.72)';
      base.border = '#E8E0D3';
      base.primary = '#E07A2C';
      base.cta = '#EA580C';
    }
  } else if (st === 'pine') {
    if (isD) {
      base.bg = '#0E1411';
      base.surface = 'rgba(18, 28, 23, 0.86)';
      base.surface2 = 'rgba(18, 28, 23, 0.72)';
      base.border = 'rgba(170, 210, 190, 0.16)';
      base.primary = '#63D29C';
      base.cta = '#63D29C';
    } else {
      base.bg = '#F3F7F4';
      base.surface = 'rgba(255, 255, 255, 0.86)';
      base.surface2 = 'rgba(255, 255, 255, 0.72)';
      base.border = '#D8E4DD';
      base.primary = '#2DBA7D';
      base.cta = '#2DBA7D';
    }
  } else if (st === 'celadon') {
    if (isD) {
      base.bg = '#0D1314';
      base.surface = 'rgba(18, 26, 27, 0.86)';
      base.surface2 = 'rgba(18, 26, 27, 0.72)';
      base.border = 'rgba(94, 234, 212, 0.18)';
      base.primary = '#2DD4BF';
      base.cta = '#EA580C';
    } else {
      base.bg = '#F0FDFA';
      base.surface = 'rgba(255, 255, 255, 0.86)';
      base.surface2 = 'rgba(255, 255, 255, 0.72)';
      base.border = '#5EEAD4';
      base.primary = '#0D9488';
      base.cta = '#EA580C';
    }
  }

  try {
    var pRgb = parseRgb(base.primary);
    var cRgb = parseRgb(base.cta);
    var bRgb = parseRgb(base.bg);
    var needFix = false;
    if (cRgb && bRgb && contrastRatio(cRgb, bRgb) < 2.0) needFix = true;
    if (!needFix && st === 'default' && String(base.cta || '').trim().toLowerCase() === String(base.primary || '').trim().toLowerCase()) needFix = true;
    if (needFix && pRgb) {
      var accent = parseRgb('#F97316');
      if (accent) {
        var m = mixRgb(pRgb, accent, 0.42);
        base.cta = 'rgb(' + m[0] + ',' + m[1] + ',' + m[2] + ')';
      } else {
        base.cta = base.primary;
      }
    }
  } catch (e) {}

  return base;
}

function buildDataCenterCompatPayload(ctx, activeTab) {
  var raw = ctx && typeof ctx === 'object' ? ctx : {};
  var tab = String(activeTab || '').trim().toLowerCase() || 'global';

  var payload = {};
  for (var k in raw) {
    if (!Object.prototype.hasOwnProperty.call(raw, k)) continue;
    // 防止 __proto__/constructor/prototype 造成原型污染或异常
    if (k === '__proto__' || k === 'constructor' || k === 'prototype') continue;
    payload[k] = raw[k];
  }
  payload.active_tab = tab;
  payload.subjects = raw.subject_rows || [];
  payload.types = raw.type_rows || [];
  payload.difficulty = raw.difficulty_rows || [];
  payload.weakness = raw.weakness_rows || [];
  payload.banks = raw.bank_rows || [];
  payload.bank_categories = raw.bank_category_rows || [];
  payload.public_summary = {
    total_questions: raw.total_questions || 0,
    answered: raw.answered_count || 0,
    correct: raw.correct_count || 0,
    accuracy: raw.accuracy || 0,
    completion: raw.completion || 0,
    favorites: raw.favorites_count || 0,
    mistakes: raw.mistakes_count || 0,
    mistakes_times: raw.mistakes_times || 0,
    streak_days: raw.streak_days || 0,
    last_activity: raw.last_activity,
    answered_7d: raw.answered_7d || 0,
    correct_7d: raw.correct_7d || 0,
    answered_30d: raw.answered_30d || 0,
    correct_30d: raw.correct_30d || 0,
    window_answered: raw.window_answered || 0,
    window_correct: raw.window_correct || 0,
    window_accuracy: raw.window_accuracy || 0,
  };

  return payload;
}

function buildDataCenterChartOption(id, payload, themeTokens, chart) {
  var cid = String(id || '');
  if (!cid) return null;
  var ctx = createChartCtx(payload);
  var t = themeTokens || getDataCenterThemeTokens(false, 'default');
  return buildDataCenterOptionById(cid, ctx, t, chart);
}

exports.getDataCenterThemeTokens = getDataCenterThemeTokens;
exports.buildDataCenterCompatPayload = buildDataCenterCompatPayload;
exports.buildDataCenterChartOption = buildDataCenterChartOption;
