(function () {
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

  var payload = window.__DATA_CENTER__ || {};
  var dailyPublic = Array.isArray(payload.daily) ? payload.daily : [];
  var dailyBanks = Array.isArray(payload.bank_daily) ? payload.bank_daily : [];
  var allDaily = Array.isArray(payload.all_daily) ? payload.all_daily : [];
  var subjects = Array.isArray(payload.subjects) ? payload.subjects : [];
  var banks = Array.isArray(payload.bank_rows) ? payload.bank_rows : Array.isArray(payload.banks) ? payload.banks : [];
  var bankCategories = Array.isArray(payload.bank_category_rows)
    ? payload.bank_category_rows
    : Array.isArray(payload.bank_categories)
      ? payload.bank_categories
      : [];
  var ability = Array.isArray(payload.ability_radar) ? payload.ability_radar : [];
  var weakness = Array.isArray(payload.weakness) ? payload.weakness : [];
  var hourly = payload.activity_hourly || { max: 0, public: [], banks: [], all: [] };
  var heatmap = payload.activity_heatmap || { max: 0, public: [], banks: [], all: [] };

  var charts = {};

  function applyBaseOption(opt, t) {
    if (!opt || typeof opt !== 'object') return opt;
    t = t || theme();

    opt.textStyle = opt.textStyle || {};
    if (!opt.textStyle.fontFamily) opt.textStyle.fontFamily = t.fontBody;

    if (opt.tooltip) {
      opt.tooltip.backgroundColor = opt.tooltip.backgroundColor || t.surface;
      opt.tooltip.borderColor = opt.tooltip.borderColor || t.border;
      opt.tooltip.textStyle = opt.tooltip.textStyle || {};
      if (!opt.tooltip.textStyle.color) opt.tooltip.textStyle.color = t.text;
      if (!opt.tooltip.textStyle.fontFamily) opt.tooltip.textStyle.fontFamily = t.fontBody;
      if (opt.tooltip.confine == null) opt.tooltip.confine = true;
      opt.tooltip.extraCssText =
        opt.tooltip.extraCssText ||
        'border-radius:12px;box-shadow:0 18px 50px rgba(2,6,23,0.14);backdrop-filter:blur(10px);';
    }

    if (opt.legend && opt.legend.textStyle) {
      if (!opt.legend.textStyle.fontFamily) opt.legend.textStyle.fontFamily = t.fontBody;
    }

    if (opt.title && opt.title.textStyle) {
      if (!opt.title.textStyle.fontFamily) opt.title.textStyle.fontFamily = t.fontHeading;
    }

    return opt;
  }

  function theme() {
    var bg = getVar('--app-bg') || '#f6f7f8';
    var primary = getVar('--app-primary') || '#111827';
    var cta = getVar('--app-cta') || primary;
    var muted = getVar('--app-muted') || '#6b7280';
    var text = getVar('--app-text') || '#111827';
    var border = getVar('--app-border') || 'rgba(148,163,184,0.24)';
    var surface = getVar('--app-surface') || '#ffffff';
    var surface2 = getVar('--app-surface-2') || surface;
    var fontBody = getVar('--app-font-body') || 'system-ui, -apple-system, Segoe UI, sans-serif';
    var fontHeading = getVar('--app-font-heading') || fontBody;

    try {
      var ts = (document.documentElement.getAttribute('data-theme-style') || 'default').toLowerCase();
      var pRgb = parseRgb(primary);
      var cRgb = parseRgb(cta);
      var bRgb = parseRgb(bg);
      var needFix = false;

      if (cRgb && bRgb && contrastRatio(cRgb, bRgb) < 2.0) needFix = true;
      if (!needFix && ts === 'default' && String(cta || '').trim().toLowerCase() === String(primary || '').trim().toLowerCase()) needFix = true;

      if (needFix && pRgb) {
        var accent = parseRgb('#f97316');
        if (accent) {
          var m = mixRgb(pRgb, accent, 0.42);
          cta = 'rgb(' + m[0] + ',' + m[1] + ',' + m[2] + ')';
        } else {
          cta = primary;
        }
      }
    } catch (e) {}

    return {
      bg: bg,
      primary: primary,
      cta: cta,
      muted: muted,
      text: text,
      border: border,
      surface: surface,
      surface2: surface2,
      fontBody: fontBody,
      fontHeading: fontHeading,
    };
  }

  function ensureChart(id) {
    if (!window.echarts) return null;
    var el = document.getElementById(id);
    if (!el) return null;
    var inst = charts[id] || echarts.getInstanceByDom(el);
    if (!inst) inst = echarts.init(el);
    if (inst && !inst.__dcWrapped) {
      try {
        var rawSet = inst.setOption.bind(inst);
        inst.setOption = function (opt, notMerge, lazyUpdate) {
          try {
            opt = applyBaseOption(opt, theme());
          } catch (e) {}
          return rawSet(opt, notMerge, lazyUpdate);
        };
        inst.__dcWrapped = true;
      } catch (e) {}
    }
    charts[id] = inst;
    return inst;
  }

  function emptyOption(titleText, subtitleText) {
    var t = theme();
    return {
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
    };
  }

  function mapByDay(list) {
    var m = {};
    (Array.isArray(list) ? list : []).forEach(function (d) {
      if (!d || !d.day) return;
      m[String(d.day)] = d;
    });
    return m;
  }

  function getDayKeys() {
    if (allDaily && allDaily.length) return allDaily.map(function (d) { return String(d.day); });
    if (dailyPublic && dailyPublic.length) return dailyPublic.map(function (d) { return String(d.day); });
    if (dailyBanks && dailyBanks.length) return dailyBanks.map(function (d) { return String(d.day); });
    return [];
  }

  function renderTrendStack(id) {
    var c = ensureChart(id);
    if (!c) return;

    var t = theme();
    var keys = getDayKeys();
    if (!keys.length) {
      c.setOption(emptyOption('学习趋势', '近 ' + (payload.window_days || 30) + ' 天（公共 + 个人）'), true);
      return;
    }

    var pubMap = mapByDay(dailyPublic);
    var bankMap = mapByDay(dailyBanks);
    var allMap = mapByDay(allDaily);

    var x = keys.map(function (k) { return fmtDay(k); });
    var pubTotals = keys.map(function (k) { return toInt((pubMap[k] || {}).total); });
    var bankTotals = keys.map(function (k) { return toInt((bankMap[k] || {}).total); });
    var accAll = keys.map(function (k) { return clamp100((allMap[k] || {}).accuracy); });

    c.setOption(
      {
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
        legend: {
          data: ['公共', '个人', '正确率'],
          top: 8,
          textStyle: { color: t.muted, fontWeight: 800 },
        },
        grid: { left: 12, right: 12, top: 44, bottom: 18, containLabel: true },
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
        series: [
          {
            name: '公共',
            type: 'bar',
            stack: 'total',
            data: pubTotals,
            barWidth: 12,
            itemStyle: { color: pickColor(t.primary, 0.26), borderRadius: [8, 8, 8, 8] },
          },
          {
            name: '个人',
            type: 'bar',
            stack: 'total',
            data: bankTotals,
            barWidth: 12,
            itemStyle: { color: pickColor(t.cta, 0.22), borderRadius: [8, 8, 8, 8] },
          },
          {
            name: '正确率',
            type: 'line',
            yAxisIndex: 1,
            smooth: true,
            data: accAll,
            symbol: 'circle',
            symbolSize: 6,
            lineStyle: { width: 2, color: t.cta },
            itemStyle: { color: t.cta },
            areaStyle: { color: pickColor(t.cta, 0.08) },
          },
        ],
      },
      true,
    );
  }

  function renderHeatmap(id) {
    var c = ensureChart(id);
    if (!c) return;

    var t = theme();
    var src = heatmap && heatmap.all ? heatmap.all : [];
    var max = toInt((heatmap && heatmap.max) || 0);
    if (!src.length || max <= 0) {
      c.setOption(emptyOption('活跃热力图', '周 × 小时（近 ' + (payload.window_days || 30) + ' 天）'), true);
      return;
    }

    var days = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
    var hours = [];
    for (var i = 0; i < 24; i++) hours.push(i < 10 ? '0' + i : '' + i);

    var data = src.map(function (it) {
      return [toInt(it[1]), toInt(it[0]), toInt(it[2])];
    });

    c.setOption(
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
      true,
    );
  }

  function renderRadar(id, radarData) {
    var c = ensureChart(id);
    if (!c) return;
    var t = theme();
    var rows = Array.isArray(radarData) ? radarData : [];
    if (!rows.length) {
      c.setOption(emptyOption('能力画像', '覆盖 × 正确 × 连续 × 错题治理'), true);
      return;
    }

    var indicators = rows.map(function (r) {
      return { name: String(r.name || ''), max: 100 };
    });
    var vals = rows.map(function (r) {
      return clamp100(r.value);
    });

    c.setOption(
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
      true,
    );
  }

  function renderTopMix(id) {
    var c = ensureChart(id);
    if (!c) return;
    var t = theme();

    var items = [];
    subjects.forEach(function (s) {
      var name = s && s.subject ? String(s.subject) : '公共题库';
      items.push({ name: '公·' + name, answered: toInt(s.answered), accuracy: toNum(s.accuracy) });
    });
    banks.forEach(function (b) {
      var name = b && b.name ? String(b.name) : '个人题库';
      items.push({ name: '个·' + name, answered: toInt(b.answered), accuracy: toNum(b.accuracy) });
    });
    items.sort(function (a, b) { return (b.answered || 0) - (a.answered || 0); });
    var top = items.slice(0, 10);

    if (!top.length) {
      c.setOption(emptyOption('Top 题库/科目', '按“已做题”排序'), true);
      return;
    }

    c.setOption(
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
      true,
    );
  }

  function renderBankSplit(id) {
    var c = ensureChart(id);
    if (!c) return;
    var t = theme();
    var pub = toInt(((payload.public_summary || {}).answered || 0));
    var per = toInt(((payload.bank_summary || {}).answered || 0));
    var total = pub + per;
    if (total <= 0) {
      c.setOption(emptyOption('公共/个人分布', '按“已做题”'), true);
      return;
    }

    c.setOption(
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
            style: { text: '已做题\n' + total, fill: t.text, fontSize: 12, fontWeight: 900, align: 'center' },
          },
        ],
      },
      true,
    );
  }

  function renderGlobalLoop(id) {
    var c = ensureChart(id);
    if (!c) return;
    var t = theme();

    var compact = false;
    try {
      compact = (c.getWidth && c.getWidth() > 0) ? c.getWidth() < 720 : false;
    } catch (e) {
      compact = false;
    }
    var padL = compact ? 14 : 18;
    var padR = compact ? 62 : 86;
    var labelFs = compact ? 11 : 12;
    var padTB = compact ? 10 : 14;
    var nodeGap = compact ? 14 : 18;

    var all = payload.all_summary || {};
    var totalQuestionsPublic = toInt(payload.total_questions);
    var totalQuestionsBanks = toInt(((payload.bank_summary || {}).total_questions || 0));
    var totalQuestionsAll = totalQuestionsPublic + totalQuestionsBanks;

    var answered = toInt(all.answered);
    var correct = toInt(all.correct);
    var favorites = toInt(all.favorites);
    var mistakes = toInt(all.mistakes);

    if (answered <= 0 && totalQuestionsAll <= 0 && favorites <= 0 && mistakes <= 0) {
      c.setOption(emptyOption('学习闭环地图', '暂无可用数据'), true);
      return;
    }

    var untouched = Math.max(0, totalQuestionsAll - answered);
    var incorrect = Math.max(0, answered - correct);
    var tagPct = clamp100(((payload.tags_kpis || {}).tagged_answered_coverage || 0));
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
      c.setOption(emptyOption('学习闭环地图', '暂无可用数据'), true);
      return;
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

    c.setOption(
      {
        tooltip: {
          trigger: 'item',
          backgroundColor: t.surface,
          borderColor: t.border,
          textStyle: { color: t.text, fontFamily: t.fontBody, fontSize: 12 },
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
                return p.name + (v > 0 ? '\n' + v : '');
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
      true,
    );
  }

  function renderBankCategories(id) {
    var c = ensureChart(id);
    if (!c) return;
    var t = theme();
    if (!bankCategories.length) {
      c.setOption(emptyOption('分类分布', '个人题库（按“已做题”）'), true);
      return;
    }

    var hasAnswered = bankCategories.some(function (r) { return toInt(r && r.answered) > 0; });
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

    var data = bankCategories.map(function (r, idx) {
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
      c.setOption(emptyOption('分类分布', '个人题库（按“' + metricName + '”）'), true);
      return;
    }

    c.setOption(
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
      true,
    );
  }

  function renderBankBubble(id) {
    var c = ensureChart(id);
    if (!c) return;
    var t = theme();
    if (!banks.length) {
      c.setOption(emptyOption('题库规模与质量', '完成度 × 正确率（个人题库）'), true);
      return;
    }

    var pts = [];
    var sumAnswered = 0;
    var sumTotal = 0;
    banks.forEach(function (b) {
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
      c.setOption(emptyOption('题库规模与质量', '完成度 × 正确率（个人题库）'), true);
      return;
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
        // 单位：百分比点；用于把重叠点错开（尤其在 0%/100% 边界附近也能展开）
        var eps = 3.2;
        var ix = idx % 3;
        var iy = Math.floor(idx / 3);

        var dx = (ix - 1) * eps;
        var dy = (iy - 1) * eps;

        if (x <= eps) dx = ix * eps;
        if (x >= (100 - eps)) dx = -ix * eps;
        if (y <= eps) dy = iy * eps;
        if (y >= (100 - eps)) dy = -iy * eps;

        x = clamp100(x + dx);
        y = clamp100(y + dy);
      }

      return {
        name: p.name,
        value: [x, y, p.answered, p.total],
      };
    });

    var showHint = sumTotal > 0 && sumAnswered <= 0;
    c.setOption(
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
      true,
    );
  }

  function renderBankRank(id) {
    var c = ensureChart(id);
    if (!c) return;
    var t = theme();
    if (!banks.length) {
      c.setOption(emptyOption('题库排行', '按“已做题”排序（个人题库）'), true);
      return;
    }

    var list = banks
      .map(function (b) {
        return {
          name: String(b.name || ''),
          total: toInt(b.total),
          answered: toInt(b.answered),
          accuracy: toNum(b.accuracy),
          mistakes_times: toInt(b.mistakes_times),
        };
      })

    var hasAnswered = list.some(function (it) { return (it.answered || 0) > 0; });
    var metricKey = hasAnswered ? 'answered' : 'total';
    var metricName = hasAnswered ? '已做' : '总题';

    list = list
      .sort(function (a, b) { return (b[metricKey] || 0) - (a[metricKey] || 0); })
      .slice(0, 12);

    if (!list.length) {
      c.setOption(emptyOption('题库排行', '按“已做题”排序（个人题库）'), true);
      return;
    }

    var maxVal = 0;
    list.forEach(function (it) { maxVal = Math.max(maxVal, toInt(it && it[metricKey])); });
    if (maxVal <= 0) {
      c.setOption(emptyOption('题库排行', '暂无个人题库练习数据'), true);
      return;
    }

    c.setOption(
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
      true,
    );
  }

  function renderTrendDetail(id) {
    var c = ensureChart(id);
    if (!c) return;

    var t = theme();
    var keys = getDayKeys();
    if (!keys.length) {
      c.setOption(emptyOption('趋势（公共 + 个人）', '近 ' + (payload.window_days || 30) + ' 天'), true);
      return;
    }

    var pubMap = mapByDay(dailyPublic);
    var bankMap = mapByDay(dailyBanks);
    var allMap = mapByDay(allDaily);
    var x = keys.map(function (k) { return fmtDay(k); });

    var pubTotals = keys.map(function (k) { return toInt((pubMap[k] || {}).total); });
    var bankTotals = keys.map(function (k) { return toInt((bankMap[k] || {}).total); });
    var allTotals = keys.map(function (k) { return toInt((allMap[k] || {}).total); });
    var accAll = keys.map(function (k) { return clamp100((allMap[k] || {}).accuracy); });

    c.setOption(
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
      true,
    );
  }

  function renderCalendar(id) {
    var c = ensureChart(id);
    if (!c) return;
    var t = theme();
    if (!allDaily.length) {
      c.setOption(emptyOption('日历热力图', '按“每日已做题”'), true);
      return;
    }

    var compact = false;
    try {
      compact = (c.getWidth && c.getWidth() > 0) ? c.getWidth() < 520 : false;
    } catch (e) {
      compact = false;
    }
    var labelFs = compact ? 10 : 11;
    var labelMargin = compact ? 10 : 12;
    var leftPad = compact ? 30 : 40;

    var data = allDaily.map(function (d) { return [String(d.day), toInt(d.total)]; });
    var max = 0;
    data.forEach(function (it) { max = Math.max(max, toInt(it[1])); });
    var start = data[0][0];
    var end = data[data.length - 1][0];

    c.setOption(
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
      true,
    );
  }

  function renderHourly(id) {
    var c = ensureChart(id);
    if (!c) return;
    var t = theme();
    var rows = (hourly && hourly.all && hourly.all.length) ? hourly.all : [];
    if (!rows.length) {
      c.setOption(emptyOption('按小时分布', '统计近 ' + (payload.window_days || 30) + ' 天'), true);
      return;
    }

    var x = rows.map(function (r) { var h = toInt(r.hour); return (h < 10 ? '0' + h : '' + h) + ':00'; });
    var y = rows.map(function (r) { return toInt(r.total); });
    var max = toInt((hourly && hourly.max) || 0) || 1;

    c.setOption(
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
      true,
    );
  }

  function renderWeekday(id) {
    var c = ensureChart(id);
    if (!c) return;
    var t = theme();
    var src = heatmap && heatmap.all ? heatmap.all : [];
    if (!src.length) {
      c.setOption(emptyOption('周内分布', '周一到周日'), true);
      return;
    }

    var days = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
    var sums = [0, 0, 0, 0, 0, 0, 0];
    src.forEach(function (it) {
      var d = toInt(it[0]);
      if (d >= 0 && d < 7) sums[d] += toInt(it[2]);
    });
    var max = 0;
    sums.forEach(function (v) { max = Math.max(max, v); });

    c.setOption(
      {
        tooltip: { trigger: 'axis' },
        grid: { left: 12, right: 12, top: 18, bottom: 12, containLabel: true },
        xAxis: { type: 'category', data: days, axisLine: { lineStyle: { color: t.border } }, axisLabel: { color: t.muted } },
        yAxis: { type: 'value', max: max || 1, axisLabel: { color: t.muted }, splitLine: { lineStyle: { color: t.border, type: 'dashed', opacity: 0.6 } } },
        series: [{ type: 'bar', data: sums, barWidth: 14, itemStyle: { color: pickColor(t.primary, 0.38), borderRadius: [8, 8, 8, 8] } }],
      },
      true,
    );
  }

  function renderAiFocus(id) {
    var c = ensureChart(id);
    if (!c) return;
    var t = theme();

    var list = (Array.isArray(weakness) ? weakness : [])
      .map(function (w) {
        var acc = clamp100(w.accuracy);
        return {
          name: String((w.subject || '未分类') + ' · ' + (w.q_type || '未知')),
          gap: clamp100(100 - acc),
          answered: toInt(w.answered),
          accuracy: acc,
        };
      })
      .sort(function (a, b) { return (b.gap || 0) - (a.gap || 0); })
      .slice(0, 8);

    if (!list.length) {
      c.setOption(emptyOption('优先级建议', '薄弱点（提升空间）'), true);
      return;
    }

    c.setOption(
      {
        tooltip: {
          trigger: 'axis',
          axisPointer: { type: 'shadow' },
          formatter: function (params) {
            var p = params && params[0] ? params[0] : null;
            if (!p) return '';
            var it = list[p.dataIndex] || {};
            return it.name + '<br/>正确率：' + it.accuracy + '% · 已做：' + it.answered + '<br/>提升空间：' + it.gap;
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
          data: list.map(function (it) { return it.name; }),
          inverse: true,
          axisLine: { lineStyle: { color: t.border } },
          axisLabel: { color: t.muted, width: 160, overflow: 'truncate' },
        },
        series: [{ type: 'bar', data: list.map(function (it) { return it.gap; }), barWidth: 12, itemStyle: { color: pickColor(t.cta, 0.5), borderRadius: [8, 8, 8, 8] } }],
      },
      true,
    );
  }

  // =============================
  // Data v2 charts (Global/Banks/Mistakes/Favorites/Tags)
  // =============================

  function renderHealthGauge(id) {
    var c = ensureChart(id);
    if (!c) return;
    var t = theme();
    var score = clamp100(payload.health_score);

    c.setOption(
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
      true,
    );
  }

  function renderAssetTrend(id) {
    var c = ensureChart(id);
    if (!c) return;
    var t = theme();

    var mis = Array.isArray(payload.mistakes_daily) ? payload.mistakes_daily : [];
    var fav = Array.isArray(payload.favorites_daily) ? payload.favorites_daily : [];
    if (!mis.length && !fav.length) {
      c.setOption(emptyOption('资产新增趋势', '错题 vs 收藏（近 ' + (payload.window_days || 30) + ' 天）'), true);
      return;
    }

    var keys = (mis.length ? mis : fav).map(function (d) { return String(d.day); });
    var misMap = {};
    var favMap = {};
    mis.forEach(function (d) { if (d && d.day) misMap[String(d.day)] = d; });
    fav.forEach(function (d) { if (d && d.day) favMap[String(d.day)] = d; });

    var x = keys.map(function (k) { return fmtDay(k); });
    var m = keys.map(function (k) { return toInt((misMap[k] || {}).all); });
    var f = keys.map(function (k) { return toInt((favMap[k] || {}).all); });

    c.setOption(
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
            areaStyle: { color: pickColor(t.cta, 0.10) },
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
      true,
    );
  }

  function renderDailySplit(id, list, titleText, subtitleText, colorA, colorB) {
    var c = ensureChart(id);
    if (!c) return;
    var t = theme();
    var src = Array.isArray(list) ? list : [];
    if (!src.length) {
      c.setOption(emptyOption(titleText, subtitleText), true);
      return;
    }

    var x = src.map(function (d) { return fmtDay(d.day); });
    var a = src.map(function (d) { return toInt(d.public); });
    var b = src.map(function (d) { return toInt(d.banks); });
    var all = src.map(function (d) { return toInt(d.all); });

    c.setOption(
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
      true,
    );
  }

  function renderRankBar(id, rows, titleText, subtitleText, color) {
    var c = ensureChart(id);
    if (!c) return;
    var t = theme();

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
      c.setOption(emptyOption(titleText, subtitleText), true);
      return;
    }

    c.setOption(
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
      true,
    );
  }

  function renderStackedCategory(id, list, titleText, subtitleText, useTimes) {
    var c = ensureChart(id);
    if (!c) return;
    var t = theme();
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
      c.setOption(emptyOption(titleText, subtitleText), true);
      return;
    }

    c.setOption(
      {
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
        legend: { top: 8, textStyle: { color: t.muted, fontWeight: 800 } },
        grid: { left: 12, right: 12, top: 44, bottom: 18, containLabel: true },
        xAxis: { type: 'category', data: rows.map(function (r) { return r.name; }), axisLine: { lineStyle: { color: t.border } }, axisLabel: { color: t.muted, interval: 0, rotate: 18 } },
        yAxis: { type: 'value', axisLabel: { color: t.muted }, splitLine: { lineStyle: { color: t.border, type: 'dashed', opacity: 0.6 } } },
        series: [
          { name: '公共', type: 'bar', stack: 't', data: rows.map(function (r) { return r.public; }), barWidth: 12, itemStyle: { color: pickColor(t.primary, 0.28), borderRadius: [8, 8, 8, 8] } },
          { name: '个人', type: 'bar', stack: 't', data: rows.map(function (r) { return r.banks; }), barWidth: 12, itemStyle: { color: pickColor(t.cta, 0.22), borderRadius: [8, 8, 8, 8] } },
          { name: '合计', type: 'line', smooth: true, data: rows.map(function (r) { return r.all; }), symbol: 'circle', symbolSize: 5, lineStyle: { width: 2, color: t.cta }, itemStyle: { color: t.cta } },
        ],
      },
      true,
    );
  }

  function renderSubjectProgress(id) {
    var c = ensureChart(id);
    if (!c) return;
    var t = theme();
    var list = (Array.isArray(subjects) ? subjects : []).slice();
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
      c.setOption(emptyOption('科目进度与正确率', 'Top 科目（按已做题）'), true);
      return;
    }

    c.setOption(
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
      true,
    );
  }

  function renderSubjectRisk(id) {
    var c = ensureChart(id);
    if (!c) return;
    var t = theme();
    var list = (Array.isArray(subjects) ? subjects : []).slice();
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
      c.setOption(emptyOption('科目风险分布', '完成度 × 正确率'), true);
      return;
    }

    var data = list.map(function (it) {
      return {
        name: it.name,
        value: [it.completion, it.accuracy, it.mistakes, it.answered, it.favorites],
      };
    });

    c.setOption(
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
      true,
    );
  }

  function renderTagTreemap(id) {
    var c = ensureChart(id);
    if (!c) return;
    var t = theme();

    var tags = Array.isArray(payload.tags_all) ? payload.tags_all : [];
    var data = tags
      .map(function (it) {
        return { name: String(it && it.tag ? it.tag : '—'), value: toInt(it && it.count) };
      })
      .filter(function (it) { return it.value > 0 && it.name; })
      .sort(function (a, b) { return (b.value || 0) - (a.value || 0); })
      .slice(0, 60);

    if (!data.length) {
      c.setOption(emptyOption('标签结构', '暂无可用标签数据'), true);
      return;
    }

    c.setOption(
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
      true,
    );
  }

  function renderTagGraph(id) {
    var c = ensureChart(id);
    if (!c) return;
    var t = theme();

    var g = payload.tags_graph || {};
    var nodesRaw = Array.isArray(g.nodes) ? g.nodes : [];
    var linksRaw = Array.isArray(g.links) ? g.links : [];
    if (!nodesRaw.length || !linksRaw.length) {
      c.setOption(emptyOption('标签共现网络', '暂无可用共现数据'), true);
      return;
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

    c.setOption(
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
      true,
    );
  }

  function renderTagTop(id) {
    var c = ensureChart(id);
    if (!c) return;
    var t = theme();

    var tags = Array.isArray(payload.tags_all) ? payload.tags_all : [];
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
      c.setOption(emptyOption('标签 Top', '按题目数排序'), true);
      return;
    }

    c.setOption(
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
      true,
    );
  }

  function renderTagAccuracy(id) {
    var c = ensureChart(id);
    if (!c) return;
    var t = theme();

    var tags = Array.isArray(payload.tags_all) ? payload.tags_all : [];
    var data = tags
      .map(function (it) {
        return {
          name: String(it && it.tag ? it.tag : '—'),
          value: [toInt(it && it.count), clamp100(it && it.accuracy), toInt(it && it.answered), toInt(it && it.mistakes_times), toInt(it && it.favorites)],
        };
      })
      .filter(function (it) { return (it.value[0] || 0) > 0; });

    if (!data.length) {
      c.setOption(emptyOption('标签质量', '题目数 × 正确率'), true);
      return;
    }

    c.setOption(
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
      true,
    );
  }

  function addMsg(role, text) {
    var root = document.getElementById('dcAiMessages');
    if (!root) return;
    var wrap = document.createElement('div');
    wrap.className = 'dc-ai-msg ' + (role === 'user' ? 'user' : 'bot');
    var bubble = document.createElement('div');
    bubble.className = 'bubble';
    bubble.textContent = String(text || '');
    wrap.appendChild(bubble);
    root.appendChild(wrap);
    try {
      root.scrollTop = root.scrollHeight;
    } catch (e) {}
  }

  async function askAI(prompt) {
    var p = String(prompt || '').trim();
    if (!p) return;
    addMsg('user', p);
    addMsg('bot', '正在分析你的数据…');

    var providerEl = document.getElementById('dcAiProvider');
    var sendBtn = document.getElementById('dcAiSend');
    if (sendBtn) sendBtn.disabled = true;

    try {
      var res = await fetch('/api/data/ai-advice', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: p, days: payload.window_days || 30 }),
      });
      var js = await res.json();
      var ok = js && (js.status === 'success' || js.code === 0);
      var reply = ok
        ? (js.data && js.data.reply) || (js.data && js.data.explain) || js.reply || ''
        : (js && js.message) || 'AI返回异常，请稍后重试。';
      var provider = js && js.data && js.data.provider ? js.data.provider : ok ? 'unknown' : 'error';

      var root = document.getElementById('dcAiMessages');
      if (root) {
        var nodes = root.querySelectorAll('.dc-ai-msg.bot .bubble');
        if (nodes && nodes.length) nodes[nodes.length - 1].textContent = String(reply || '');
      }
      if (providerEl) providerEl.textContent = 'provider：' + provider;
    } catch (e) {
      var root2 = document.getElementById('dcAiMessages');
      if (root2) {
        var nodes2 = root2.querySelectorAll('.dc-ai-msg.bot .bubble');
        if (nodes2 && nodes2.length) nodes2[nodes2.length - 1].textContent = '请求失败，请检查网络或稍后再试。';
      }
      if (providerEl) providerEl.textContent = 'provider：error';
    } finally {
      if (sendBtn) sendBtn.disabled = false;
    }
  }

  function bindAI() {
    var form = document.getElementById('dcAiForm');
    var input = document.getElementById('dcAiInput');
    if (form && input) {
      form.addEventListener('submit', function (e) {
        e.preventDefault();
        var p = String(input.value || '').trim();
        if (!p) return;
        input.value = '';
        askAI(p);
      });
    }
    document.querySelectorAll('.dc-chip[data-prompt]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        askAI(btn.getAttribute('data-prompt') || '');
      });
    });
  }

  function bindThemeObserver() {
    try {
      var mo = new MutationObserver(function () {
        rerenderRenderedCharts();
      });
      mo.observe(document.documentElement, {
        attributes: true,
        attributeFilter: ['data-theme', 'data-theme-style'],
      });
    } catch (e) {}
  }

  function chartRenderers() {
    return [
      ['dcHealthGaugeChart', function () { renderHealthGauge('dcHealthGaugeChart'); }],
      ['dcAssetTrendChart', function () { renderAssetTrend('dcAssetTrendChart'); }],
      ['dcGlobalLoopChart', function () { renderGlobalLoop('dcGlobalLoopChart'); }],

      ['dcTrendChart', function () { renderTrendStack('dcTrendChart'); }],
      ['dcTrendDetailChart', function () { renderTrendDetail('dcTrendDetailChart'); }],
      ['dcCalendarChart', function () { renderCalendar('dcCalendarChart'); }],
      ['dcHeatmapChart', function () { renderHeatmap('dcHeatmapChart'); }],
      ['dcHourlyChart', function () { renderHourly('dcHourlyChart'); }],
      ['dcWeekdayChart', function () { renderWeekday('dcWeekdayChart'); }],

      ['dcRadarChart', function () { renderRadar('dcRadarChart', ability); }],
      ['dcTopMixChart', function () { renderTopMix('dcTopMixChart'); }],
      ['dcTypeDistChart', function () { renderStackedCategory('dcTypeDistChart', payload.mistakes_by_type, '错题题型结构', '公共 + 个人', true); }],
      ['dcDifficultyDistChart', function () { renderStackedCategory('dcDifficultyDistChart', payload.mistakes_by_difficulty, '错题难度结构', '公共 + 个人', true); }],

      ['dcBankSplitChart', function () { renderBankSplit('dcBankSplitChart'); }],
      ['dcBankCategoryChart', function () { renderBankCategories('dcBankCategoryChart'); }],
      ['dcBankBubbleChart', function () { renderBankBubble('dcBankBubbleChart'); }],
      ['dcBankRankChart', function () { renderBankRank('dcBankRankChart'); }],
      ['dcSubjectProgressChart', function () { renderSubjectProgress('dcSubjectProgressChart'); }],
      ['dcSubjectRiskChart', function () { renderSubjectRisk('dcSubjectRiskChart'); }],

      [
        'dcMistakeTrendChart',
        function () {
          var t = theme();
          renderDailySplit('dcMistakeTrendChart', payload.mistakes_daily, '错题新增趋势', '公共 + 个人（近 ' + (payload.window_days || 30) + ' 天）', t.primary, t.cta);
        },
      ],
      [
        'dcMistakeTopChart',
        function () {
          var t = theme();
          renderRankBar('dcMistakeTopChart', payload.mistakes_top_items, '错题次数', '公共按科目 / 个人按题库', t.cta);
        },
      ],
      ['dcMistakeDifficultyChart', function () { renderStackedCategory('dcMistakeDifficultyChart', payload.mistakes_by_difficulty, '错题难度分布', '次数（公共 + 个人）', true); }],
      ['dcMistakeTypeChart', function () { renderStackedCategory('dcMistakeTypeChart', payload.mistakes_by_type, '错题题型分布', '次数（公共 + 个人）', true); }],

      [
        'dcFavoriteTrendChart',
        function () {
          var t = theme();
          renderDailySplit('dcFavoriteTrendChart', payload.favorites_daily, '收藏新增趋势', '公共 + 个人（近 ' + (payload.window_days || 30) + ' 天）', t.primary, t.cta);
        },
      ],
      [
        'dcFavoriteTopChart',
        function () {
          var t = theme();
          renderRankBar('dcFavoriteTopChart', payload.favorites_top_items, '收藏数量', '公共按科目 / 个人按题库', t.primary);
        },
      ],
      ['dcFavoriteDifficultyChart', function () { renderStackedCategory('dcFavoriteDifficultyChart', payload.favorites_by_difficulty, '收藏难度分布', '数量（公共 + 个人）', false); }],
      ['dcFavoriteTypeChart', function () { renderStackedCategory('dcFavoriteTypeChart', payload.favorites_by_type, '收藏题型分布', '数量（公共 + 个人）', false); }],

      ['dcTagTreemapChart', function () { renderTagTreemap('dcTagTreemapChart'); }],
      ['dcTagGraphChart', function () { renderTagGraph('dcTagGraphChart'); }],
      ['dcTagTopChart', function () { renderTagTop('dcTagTopChart'); }],
      ['dcTagAccuracyChart', function () { renderTagAccuracy('dcTagAccuracyChart'); }],

      ['dcAiRadarChart', function () { renderRadar('dcAiRadarChart', ability); }],
      ['dcAiFocusChart', function () { renderAiFocus('dcAiFocusChart'); }],
    ];
  }

  var _rendered = {};
  var _rendererMap = {};
  var _rendererList = chartRenderers();
  _rendererList.forEach(function (pair) {
    _rendererMap[pair[0]] = pair[1];
  });

  function renderChartById(id) {
    if (!window.echarts) return;
    var fn = _rendererMap[id];
    if (!fn) return;
    var el = document.getElementById(id);
    if (!el) return;
    try {
      fn();
      _rendered[id] = true;
    } catch (e) {}
  }

  function initChartsLazy() {
    if (!window.echarts) return;

    if (!('IntersectionObserver' in window)) {
      _rendererList.forEach(function (pair) {
        renderChartById(pair[0]);
      });
      return;
    }

    var io = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (!entry || !entry.isIntersecting) return;
          var el = entry.target;
          if (!el || !el.id) return;
          try {
            io.unobserve(el);
          } catch (e) {}
          renderChartById(el.id);
        });
      },
      { rootMargin: '160px 0px' },
    );

    _rendererList.forEach(function (pair) {
      var id = pair[0];
      var el = document.getElementById(id);
      if (el) io.observe(el);
    });
  }

  function rerenderRenderedCharts() {
    if (!window.echarts) return;
    Object.keys(_rendered).forEach(function (id) {
      renderChartById(id);
    });
  }

  function bindExport() {
    var btn = document.getElementById('dcExportBtn');
    if (!btn) return;
    btn.addEventListener('click', function () {
      try {
        var p = String(location.pathname || '').toLowerCase();
        var tab = 'global';
        if (p.indexOf('/data/banks') === 0) tab = 'banks';
        else if (p.indexOf('/data/mistakes') === 0) tab = 'mistakes';
        else if (p.indexOf('/data/favorites') === 0) tab = 'favorites';
        else if (p.indexOf('/data/tags') === 0) tab = 'tags';

        var days = toInt(payload.window_days) || toInt(new URLSearchParams(location.search || '').get('days')) || 30;
        var stamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-');
        var name = 'data-' + tab + '-' + days + 'd-' + stamp + '.json';

        var out = {
          meta: { exported_at: new Date().toISOString(), path: location.pathname, search: location.search },
          data: payload,
        };
        var blob = new Blob([JSON.stringify(out, null, 2)], { type: 'application/json;charset=utf-8' });
        var url = URL.createObjectURL(blob);
        var a = document.createElement('a');
        a.href = url;
        a.download = name;
        document.body.appendChild(a);
        a.click();
        setTimeout(function () {
          try {
            URL.revokeObjectURL(url);
          } catch (e) {}
          try {
            a.remove();
          } catch (e) {}
        }, 0);
      } catch (e) {}
    });
  }

  initChartsLazy();
  bindAI();
  bindExport();
  bindThemeObserver();

  window.addEventListener('resize', function () {
    Object.keys(charts).forEach(function (k) {
      try {
        charts[k] && charts[k].resize();
      } catch (e) {}
    });
  });
})();
