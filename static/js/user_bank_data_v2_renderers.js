(function () {
  'use strict';
  var ns = window.UserBankDataV2NS;
  if (!ns) return;
  var h = ns.helpers || {};
  var clamp = h.clamp;
  var getVar = h.getVar;
  var pickColor = h.pickColor;
  var toNum = h.toNum;
  var fmtCount = h.fmtCount;
  var fmtPercent = h.fmtPercent;
  var fmtDay = h.fmtDay;
  var fmtDateTime = h.fmtDateTime;
  var escapeHtml = h.escapeHtml;
  var shortText = h.shortText;
  var isCompactChart = h.isCompactChart;
  var fmtDayLabel = h.fmtDayLabel;
  var parseLooseDate = h.parseLooseDate;
  var daysSince = h.daysSince;
  var calcActiveDays = h.calcActiveDays;
  var calcRecentAnswered = h.calcRecentAnswered;
  var setText = h.setText;
  var setBar = h.setBar;
  var getChart = ns.getChart;
  var renderEmpty = ns.renderEmpty;

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
  ns.renderers = {
    renderCalendarChart: renderCalendarChart,
    renderGaugeChart: renderGaugeChart,
    renderAnsweredTrend: renderAnsweredTrend,
    renderTypeStructureChart: renderTypeStructureChart,
    renderTypePie: renderTypePie,
    renderFunnel: renderFunnel,
    renderRiskRadar: renderRiskRadar,
    renderTypeTable: renderTypeTable,
    renderDiffChart: renderDiffChart,
    renderMistakeMatrix: renderMistakeMatrix,
    renderMistakeTop: renderMistakeTop,
    renderMistakeDifficulty: renderMistakeDifficulty,
    renderMistakeTable: renderMistakeTable,
    renderFavAddedTrend: renderFavAddedTrend,
    renderFavTable: renderFavTable
  };
})();

