(function () {
  'use strict';

  function clamp(val, min, max) {
    return Math.max(min, Math.min(max, val));
  }

  function escapeHtml(s) {
    var d = document.createElement('div');
    d.textContent = s == null ? '' : String(s);
    return d.innerHTML;
  }

  function getVar(name) {
    try {
      return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    } catch (e) {
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
    } catch (e) {
      return String(n);
    }
  }

  function fmtPercent(v) {
    var n = toNum(v);
    return n.toFixed(1) + '%';
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

  var payload = window.__UBD__ || {};
  var root = document.querySelector('.ubd-shell');
  var bankId = payload.bank_id || (root ? root.getAttribute('data-bank-id') : null);
  var subjectName = payload.subject_name || (root ? root.getAttribute('data-subject-name') : null);
  var subtab = payload.subtab || (root ? root.getAttribute('data-subtab') : 'global');
  var windowDays = toNum(payload.window_days || (root ? root.getAttribute('data-days') : 30)) || 30;

  var charts = {};
  var state = {
    data: null,
    loading: false,
  };

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
          fontWeight: 600,
        },
      },
    });
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

  function buildHeadline(d, trend) {
    var activeDays = calcActiveDays(trend);
    var accuracy = toNum(d.accuracy);
    var completion = toNum(d.completion);
    if (subtab === 'mistakes') {
      return '错题池：' + fmtCount(d.mistakes) + ' 题 · 纠错率 ' + fmtPercent(accuracy) + ' · 近' + windowDays + '天活跃' + activeDays + '天';
    }
    if (subtab === 'favorites') {
      return '收藏池：' + fmtCount(d.total_count) + ' 题 · 覆盖率 ' + fmtPercent(completion) + ' · 近' + windowDays + '天活跃' + activeDays + '天';
    }
    return '全局：覆盖率 ' + fmtPercent(completion) + ' · 正确率 ' + fmtPercent(accuracy) + ' · 近' + windowDays + '天活跃' + activeDays + '天';
  }

  function updateKpis(d) {
    var totalCount = toNum(d.total_count);
    var answered = toNum(d.answered);
    var correct = toNum(d.correct);
    var wrong = toNum(d.wrong);
    var favorites = toNum(d.favorites);
    var mistakes = toNum(d.mistakes);
    var mistakesTimes = toNum(d.mistakes_times);
    var accuracy = toNum(d.accuracy);
    var completion = toNum(d.completion);
    var streak = toNum(d.streak_days);
    var trend = Array.isArray(d.trend) ? d.trend : [];
    var activeDays = calcActiveDays(trend);
    var recentAnswered = calcRecentAnswered(trend, Math.min(7, windowDays));
    var mistakeRate = answered > 0 ? (wrong * 100) / answered : 0;

    setText('ubdHeadline', buildHeadline(d, trend));
    setText('ubdUpdatedAt', '最近活跃：' + fmtDateTime(d.last_activity));

    var totalLabel = '题库总题';
    var favLabel = '收藏题';
    var misLabel = '错题题';
    if (subtab === 'mistakes') {
      totalLabel = '错题总量';
      favLabel = '收藏错题';
      misLabel = '错题题';
    } else if (subtab === 'favorites') {
      totalLabel = '收藏总量';
      favLabel = '收藏题';
      misLabel = '收藏错题';
    }

    setText('kpiTotalLabel', totalLabel);
    setText('kpiFavLabel', favLabel);
    setText('kpiMisLabel', misLabel);

    setText('kpiTotal', fmtCount(totalCount));
    setText('kpiAnswered', fmtCount(answered));
    setText('kpiAccuracy', fmtPercent(accuracy));
    setText('kpiCompletion', fmtPercent(completion));
    setText('kpiMistakeTimes', fmtCount(mistakesTimes));
    setText('kpiFav', fmtCount(favorites));
    setText('kpiMis', fmtCount(mistakes));
    setText('kpiStreak', fmtCount(streak));

    setText('kpiTotalMeta', '覆盖率 ' + fmtPercent(completion));
    setText('kpiAnsweredMeta', '近7天作答 ' + fmtCount(recentAnswered) + ' 题');
    setText('kpiAccuracyMeta', '错误 ' + fmtCount(wrong) + ' 题');
    setText('kpiCompletionMeta', '未做 ' + fmtCount(Math.max(0, totalCount - answered)) + ' 题');
    setText('kpiMistakeTimesMeta', '错题率 ' + fmtPercent(mistakeRate));
    setText('kpiFavMeta', '收藏率 ' + fmtPercent(totalCount ? (favorites * 100) / totalCount : 0));
    setText('kpiMisMeta', '错题占比 ' + fmtPercent(totalCount ? (mistakes * 100) / totalCount : 0));
    setText('kpiStreakMeta', '活跃天数 ' + fmtCount(activeDays) + ' / ' + windowDays);

    setBar('metricStability', accuracy);
    setText('metricStabilityText', fmtPercent(accuracy));

    var activeRate = windowDays ? (activeDays * 100) / windowDays : 0;
    setBar('metricPace', activeRate);
    setText('metricPaceText', fmtPercent(activeRate));
  }

  function renderCalendarChart(trend) {
    var chart = getChart('ubdCalendarChart');
    if (!chart) return;
    var list = Array.isArray(trend) ? trend : [];
    if (!list.length) return renderEmpty(chart, '暂无作答记录');

    var data = list.map(function (d) {
      return [d.day, toNum(d.answered)];
    });

    var maxVal = data.reduce(function (m, it) {
      return Math.max(m, toNum(it[1]));
    }, 0);

    var start = list[0].day;
    var end = list[list.length - 1].day;

    var primary = getVar('--app-primary') || '#2563eb';
    var cta = getVar('--app-cta') || '#f97316';
    var muted = getVar('--app-muted') || '#6b7280';
    var border = getVar('--app-border') || 'rgba(148,163,184,0.24)';

    chart.setOption(
      {
        tooltip: {
          position: 'top',
          formatter: function (p) {
            var v = p && p.value ? p.value : [];
            return String(v[0] || '') + '：' + fmtCount(v[1] || 0) + ' 题';
          },
        },
        visualMap: {
          min: 0,
          max: Math.max(4, maxVal),
          calculable: false,
          orient: 'horizontal',
          left: 'center',
          bottom: 0,
          textStyle: { color: muted },
          inRange: {
            color: [pickColor(primary, 0.15), pickColor(primary, 0.35), pickColor(cta, 0.6)],
          },
        },
        calendar: {
          top: 10,
          left: 12,
          right: 12,
          cellSize: ['auto', 18],
          range: [start, end],
          dayLabel: { color: muted },
          monthLabel: { color: muted },
          yearLabel: { show: false },
          itemStyle: { borderColor: border, borderWidth: 1 },
        },
        series: [
          {
            type: 'heatmap',
            coordinateSystem: 'calendar',
            data: data,
          },
        ],
      },
      true,
    );
  }

  function renderGaugeChart(d) {
    var chart = getChart('ubdGaugeChart');
    if (!chart) return;

    var primary = getVar('--app-primary') || '#2563eb';
    var cta = getVar('--app-cta') || '#f97316';
    var muted = getVar('--app-muted') || '#6b7280';
    var text = getVar('--app-text') || '#111827';
    var border = getVar('--app-border') || 'rgba(148,163,184,0.24)';

    var accuracy = toNum(d.accuracy);
    var completion = toNum(d.completion);
    var mistakeRate = toNum(d.answered) ? (toNum(d.wrong) * 100) / toNum(d.answered) : 0;

    var score = accuracy * 0.6 + completion * 0.4;
    if (subtab === 'mistakes') {
      score = 100 - mistakeRate;
    }
    var label = subtab === 'mistakes' ? '纠错指数' : subtab === 'favorites' ? '收藏掌握度' : '掌握指数';

    chart.setOption(
      {
        series: [
          {
            type: 'gauge',
            startAngle: 220,
            endAngle: -40,
            min: 0,
            max: 100,
            splitNumber: 5,
            axisLine: {
              lineStyle: {
                width: 12,
                color: [
                  [0.3, pickColor(primary, 0.35)],
                  [0.7, pickColor(primary, 0.65)],
                  [1, pickColor(cta, 0.65)],
                ],
              },
            },
            pointer: { show: true, length: '60%', width: 6 },
            axisTick: { show: false },
            splitLine: { length: 10, lineStyle: { color: border } },
            axisLabel: { color: muted, distance: -28, fontSize: 10 },
            title: { offsetCenter: [0, '70%'], color: muted, fontSize: 12 },
            detail: {
              valueAnimation: true,
              formatter: function (v) {
                return Math.round(v) + '分';
              },
              color: text,
              fontSize: 18,
              fontWeight: 900,
              offsetCenter: [0, '32%'],
            },
            data: [{ value: Math.round(clamp(score, 0, 100)), name: label }],
          },
        ],
      },
      true,
    );
  }

  function renderTrendChart(trend) {
    var chart = getChart('ubdTrendChart');
    if (!chart) return;
    var list = Array.isArray(trend) ? trend : [];
    if (!list.length) return renderEmpty(chart, '暂无趋势数据');

    var primary = getVar('--app-primary') || '#2563eb';
    var cta = getVar('--app-cta') || '#f97316';
    var muted = getVar('--app-muted') || '#6b7280';
    var border = getVar('--app-border') || 'rgba(148,163,184,0.24)';

    var x = list.map(function (d) {
      return fmtDay(d.day);
    });
    var answered = list.map(function (d) {
      return toNum(d.answered);
    });
    var accuracy = list.map(function (d) {
      var a = toNum(d.answered);
      var c = toNum(d.correct);
      return a ? Math.round((c * 1000) / a) / 10 : 0;
    });

    chart.setOption(
      {
        tooltip: { trigger: 'axis' },
        legend: {
          data: ['作答量', '正确率'],
          top: 4,
          textStyle: { color: muted, fontWeight: 700 },
        },
        grid: { left: 12, right: 12, top: 36, bottom: 12, containLabel: true },
        xAxis: {
          type: 'category',
          data: x,
          axisLine: { lineStyle: { color: border } },
          axisLabel: { color: muted },
        },
        yAxis: [
          {
            type: 'value',
            name: '题',
            axisLine: { show: false },
            axisTick: { show: false },
            axisLabel: { color: muted },
            splitLine: { lineStyle: { color: border, type: 'dashed', opacity: 0.6 } },
          },
          {
            type: 'value',
            name: '%',
            min: 0,
            max: 100,
            axisLine: { show: false },
            axisTick: { show: false },
            axisLabel: { color: muted },
            splitLine: { show: false },
          },
        ],
        series: [
          {
            name: '作答量',
            type: 'bar',
            data: answered,
            barWidth: 10,
            itemStyle: {
              color: {
                type: 'linear',
                x: 0,
                y: 0,
                x2: 0,
                y2: 1,
                colorStops: [
                  { offset: 0, color: pickColor(primary, 0.8) },
                  { offset: 1, color: pickColor(primary, 0.25) },
                ],
              },
              borderRadius: [8, 8, 0, 0],
            },
          },
          {
            name: '正确率',
            type: 'line',
            yAxisIndex: 1,
            data: accuracy,
            smooth: true,
            symbol: 'circle',
            symbolSize: 6,
            lineStyle: { width: 2, color: cta },
            itemStyle: { color: cta },
            areaStyle: { color: pickColor(cta, 0.12) },
          },
        ],
      },
      true,
    );
  }

  function renderTypeChart(byType) {
    var chart = getChart('ubdTypeChart');
    if (!chart) return;
    var list = Array.isArray(byType) ? byType : [];
    if (!list.length) return renderEmpty(chart, '暂无题型数据');

    var primary = getVar('--app-primary') || '#2563eb';
    var cta = getVar('--app-cta') || '#f97316';
    var muted = getVar('--app-muted') || '#6b7280';
    var border = getVar('--app-border') || 'rgba(148,163,184,0.24)';

    list = list.slice().sort(function (a, b) {
      return toNum(b.answered) - toNum(a.answered);
    }).slice(0, 8);

    var x = list.map(function (d) {
      return String(d.q_type || '未知');
    });
    var correct = list.map(function (d) {
      return toNum(d.correct);
    });
    var wrong = list.map(function (d) {
      return toNum(d.wrong);
    });
    var completion = list.map(function (d) {
      return toNum(d.completion);
    });

    chart.setOption(
      {
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
        legend: {
          data: ['正确', '错误', '覆盖率'],
          top: 4,
          textStyle: { color: muted, fontWeight: 700 },
        },
        grid: { left: 12, right: 12, top: 36, bottom: 18, containLabel: true },
        xAxis: {
          type: 'category',
          data: x,
          axisLine: { lineStyle: { color: border } },
          axisLabel: { color: muted, interval: 0, rotate: 18 },
        },
        yAxis: [
          {
            type: 'value',
            axisLine: { show: false },
            axisTick: { show: false },
            axisLabel: { color: muted },
            splitLine: { lineStyle: { color: border, type: 'dashed', opacity: 0.6 } },
          },
          {
            type: 'value',
            min: 0,
            max: 100,
            axisLine: { show: false },
            axisTick: { show: false },
            axisLabel: { color: muted },
            splitLine: { show: false },
          },
        ],
        series: [
          {
            name: '正确',
            type: 'bar',
            stack: 'ans',
            data: correct,
            barWidth: 10,
            itemStyle: { color: pickColor(primary, 0.75), borderRadius: [8, 8, 0, 0] },
          },
          {
            name: '错误',
            type: 'bar',
            stack: 'ans',
            data: wrong,
            barWidth: 10,
            itemStyle: { color: pickColor(cta, 0.5), borderRadius: [8, 8, 0, 0] },
          },
          {
            name: '覆盖率',
            type: 'line',
            yAxisIndex: 1,
            data: completion,
            smooth: true,
            symbol: 'circle',
            symbolSize: 6,
            lineStyle: { width: 2, color: cta },
            itemStyle: { color: cta },
          },
        ],
      },
      true,
    );
  }

  function renderDiffChart(byDiff) {
    var card = document.getElementById('ubdDiffCard');
    var chart = getChart('ubdDiffChart');
    var list = Array.isArray(byDiff) ? byDiff : [];
    if (!list.length) {
      if (card) card.hidden = true;
      if (chart) chart.clear();
      return;
    }
    if (card) card.hidden = false;

    var primary = getVar('--app-primary') || '#2563eb';
    var cta = getVar('--app-cta') || '#f97316';
    var muted = getVar('--app-muted') || '#6b7280';
    var border = getVar('--app-border') || 'rgba(148,163,184,0.24)';

    var x = list.map(function (d) {
      return String(d.label || d.difficulty || '');
    });
    var completion = list.map(function (d) {
      return toNum(d.completion);
    });
    var accuracy = list.map(function (d) {
      return toNum(d.accuracy);
    });

    if (!chart) return;
    chart.setOption(
      {
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
        legend: {
          data: ['覆盖率', '正确率'],
          top: 4,
          textStyle: { color: muted, fontWeight: 700 },
        },
        grid: { left: 12, right: 12, top: 36, bottom: 12, containLabel: true },
        xAxis: {
          type: 'category',
          data: x,
          axisLine: { lineStyle: { color: border } },
          axisLabel: { color: muted },
        },
        yAxis: {
          type: 'value',
          min: 0,
          max: 100,
          axisLine: { show: false },
          axisTick: { show: false },
          axisLabel: { color: muted },
          splitLine: { lineStyle: { color: border, type: 'dashed', opacity: 0.6 } },
        },
        series: [
          {
            name: '覆盖率',
            type: 'bar',
            data: completion,
            barWidth: 14,
            itemStyle: { color: pickColor(primary, 0.65), borderRadius: [8, 8, 0, 0] },
          },
          {
            name: '正确率',
            type: 'line',
            data: accuracy,
            smooth: true,
            symbol: 'circle',
            symbolSize: 6,
            lineStyle: { width: 2, color: cta },
            itemStyle: { color: cta },
          },
        ],
      },
      true,
    );
  }

  function renderTypeTable(byType) {
    var body = document.getElementById('ubdTypeTbody');
    if (!body) return;
    var list = Array.isArray(byType) ? byType : [];
    if (!list.length) {
      body.innerHTML = '<tr><td colspan="6" class="ubd-muted">暂无数据</td></tr>';
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
          '<td>' + escapeHtml(row.q_type || '未知') + '</td>' +
          '<td>' + fmtCount(answered) + ' / ' + fmtCount(total) + '</td>' +
          '<td>' + fmtPercent(accuracy) + '</td>' +
          '<td>' + fmtPercent(completion) + '</td>' +
          '<td>' + fmtCount(row.favorites || 0) + '</td>' +
          '<td>' + fmtCount(row.mistakes || 0) + '</td>' +
          '</tr>'
        );
      })
      .join('');
  }

  function renderAdvice(list) {
    var wrap = document.getElementById('ubdAdvice');
    if (!wrap) return;
    var items = Array.isArray(list) ? list : [];
    if (!items.length) {
      wrap.innerHTML = '<div class="ubd-muted">暂无建议</div>';
      return;
    }
    wrap.innerHTML = items
      .map(function (item) {
        var title = item && item.title ? String(item.title) : '建议';
        var content = item && item.content ? String(item.content) : '';
        return (
          '<div class="ubd-advice-item">' +
          '<div class="t">' + escapeHtml(title) + '</div>' +
          '<div class="c">' + escapeHtml(content) + '</div>' +
          '</div>'
        );
      })
      .join('');
  }

  function renderAll() {
    if (!state.data) return;
    var d = state.data;
    var trend = Array.isArray(d.trend) ? d.trend : [];

    updateKpis(d);
    renderCalendarChart(trend);
    renderGaugeChart(d);
    renderTrendChart(trend);
    renderTypeChart(d.by_type || []);
    renderDiffChart(d.by_difficulty || []);
    renderTypeTable(d.by_type || []);
    renderAdvice(d.advice || []);
  }

  async function fetchStats() {
    if ((!bankId && !subjectName) || state.loading) return;
    state.loading = true;
    try {
      var source = subtab === 'mistakes' ? 'mistakes' : subtab === 'favorites' ? 'favorites' : 'all';
      var url = bankId
        ? ('/user/banks/api/' + encodeURIComponent(String(bankId)) + '/stats?days=' + encodeURIComponent(String(windowDays)) + '&source=' + encodeURIComponent(source))
        : ('/api/quiz/subjects/' + encodeURIComponent(String(subjectName)) + '/stats?days=' + encodeURIComponent(String(windowDays)) + '&source=' + encodeURIComponent(source));
      var res = await fetch(url, { credentials: 'same-origin' });
      var js = await res.json().catch(function () {
        return {};
      });
      var ok = res.ok && js && (js.code === 0 || js.status === 'success') && js.data;
      if (!ok) throw new Error((js && (js.message || js.msg)) || '数据加载失败');
      state.data = js.data || null;
      renderAll();
    } catch (e) {
      var head = document.getElementById('ubdHeadline');
      if (head) head.textContent = '数据加载失败，请稍后重试。';
      var chartIds = ['ubdCalendarChart', 'ubdGaugeChart', 'ubdTrendChart', 'ubdTypeChart', 'ubdDiffChart'];
      chartIds.forEach(function (id) {
        var c = getChart(id);
        if (c) renderEmpty(c, '加载失败');
      });
    } finally {
      state.loading = false;
    }
  }

  function bindThemeObserver() {
    try {
      var mo = new MutationObserver(function () {
        renderAll();
      });
      mo.observe(document.documentElement, {
        attributes: true,
        attributeFilter: ['data-theme', 'data-theme-style'],
      });
    } catch (e) {}
  }

  function bindResize() {
    window.addEventListener('resize', function () {
      Object.keys(charts).forEach(function (k) {
        try {
          charts[k] && charts[k].resize();
        } catch (e) {}
      });
    });
  }

  fetchStats();
  bindThemeObserver();
  bindResize();
})();
