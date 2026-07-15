"use strict";

function clamp(val, min, max) {
  var n = Number(val);
  if (!isFinite(n)) return min;
  return Math.max(min, Math.min(max, n));
}

function toNum(v) {
  var n = Number(v || 0);
  return isFinite(n) ? n : 0;
}

function pickColor(hex, alpha) {
  var a = clamp(alpha == null ? 1 : alpha, 0, 1);
  if (!hex) return "rgba(17,24,39," + a + ")";
  var h = String(hex).trim();
  if (h.indexOf("rgb") === 0) return h;
  if (h[0] !== "#") return h;
  var v = h.slice(1);
  if (v.length === 3) v = v[0] + v[0] + v[1] + v[1] + v[2] + v[2];
  if (v.length !== 6) return h;
  var r = parseInt(v.slice(0, 2), 16);
  var g = parseInt(v.slice(2, 4), 16);
  var b = parseInt(v.slice(4, 6), 16);
  return "rgba(" + r + "," + g + "," + b + "," + a + ")";
}

function fmtCount(v) {
  var n = Math.max(0, Math.floor(toNum(v)));
  try {
    return n.toLocaleString("zh-CN");
  } catch (e) {
    return String(n);
  }
}

function fmtPercent(v) {
  return toNum(v).toFixed(1) + "%";
}

function fmtDay(iso) {
  var s = String(iso || "");
  if (/^\\d{4}-\\d{2}-\\d{2}/.test(s)) return s.slice(5, 10);
  return s;
}

function fmtDayLabel(v) {
  var s = String(v || "");
  if (/^\\d{4}-\\d{2}-\\d{2}/.test(s)) return s.slice(5, 10);
  return s;
}

function shortText(value, maxLen) {
  var s = String(value == null ? "" : value);
  var n = maxLen == null ? 10 : Number(maxLen);
  if (!isFinite(n)) n = 10;
  n = Math.max(0, Math.floor(n));
  if (n <= 0) return "";
  return s.length > n ? s.slice(0, n) + "…" : s;
}

function parseLooseDate(raw) {
  if (!raw) return null;
  try {
    var str = String(raw);
    var iso = str.indexOf("T") >= 0 ? str : str.replace(" ", "T");
    var d = new Date(iso);
    if (isNaN(d.getTime())) return null;
    return d;
  } catch (e) {
    return null;
  }
}

function daysSince(raw) {
  var d = parseLooseDate(raw);
  if (!d) return null;
  var diff = Date.now() - d.getTime();
  if (!isFinite(diff)) return null;
  return Math.max(0, Math.floor(diff / 86400000));
}

function isCompact() {
  try {
    var info = wx.getSystemInfoSync();
    var w = Number(info && info.windowWidth) || 0;
    return w > 0 && w < 520;
  } catch (e) {
    return true;
  }
}

function emptyOption(text, t) {
  return {
    title: {
      text: text || "暂无数据",
      left: "center",
      top: "middle",
      textStyle: { color: t.muted, fontSize: 12, fontWeight: 700 },
    },
  };
}

function getUbdv2ThemeTokens(isDark, style) {
  var s = String(style || "default").trim().toLowerCase();
  var d = !!isDark;

  var base = {
    bg: d ? "#000000" : "#F2F2F7",
    surface: d ? "rgba(28, 28, 30, 0.86)" : "rgba(255, 255, 255, 0.86)",
    border: d ? "rgba(255, 255, 255, 0.08)" : "rgba(0, 0, 0, 0.06)",
    text: d ? "#FFFFFF" : "#111111",
    muted: d ? "rgba(235, 235, 245, 0.6)" : "rgba(60, 60, 67, 0.6)",
    primary: d ? "#FFFFFF" : "#111111",
    cta: "#007AFF",
  };

  if (s === "mist") {
    base.bg = d ? "#0C111A" : "#EEF2FF";
    base.surface = d ? "rgba(20, 27, 39, 0.86)" : "rgba(255, 255, 255, 0.86)";
    base.border = d ? "rgba(199, 210, 254, 0.16)" : "#C7D2FE";
    base.primary = d ? "#818CF8" : "#4F46E5";
    base.cta = "#F97316";
  } else if (s === "dune") {
    base.bg = d ? "#15110D" : "#FDFBF7";
    base.surface = d ? "rgba(29, 24, 19, 0.86)" : "rgba(255, 253, 249, 0.86)";
    base.border = d ? "rgba(224, 194, 162, 0.16)" : "#E8E0D3";
    base.primary = d ? "#E7A46A" : "#E07A2C";
    base.cta = d ? "#E7A46A" : "#EA580C";
  } else if (s === "pine") {
    base.bg = d ? "#0E1411" : "#F3F7F4";
    base.surface = d ? "rgba(18, 28, 23, 0.86)" : "rgba(255, 255, 255, 0.86)";
    base.border = d ? "rgba(170, 210, 190, 0.16)" : "#D8E4DD";
    base.primary = d ? "#63D29C" : "#2DBA7D";
    base.cta = base.primary;
  } else if (s === "celadon") {
    base.bg = d ? "#0D1314" : "#F0FDFA";
    base.surface = d ? "rgba(18, 26, 27, 0.86)" : "rgba(255, 255, 255, 0.86)";
    base.border = d ? "rgba(94, 234, 212, 0.18)" : "#5EEAD4";
    base.primary = d ? "#2DD4BF" : "#0D9488";
    base.cta = "#EA580C";
  }

  return base;
}

function buildCalendarOption(trend, t) {
  var list = Array.isArray(trend) ? trend : [];
  if (!list.length) return emptyOption("暂无作答记录", t);

  var compact = isCompact();
  var side = compact ? 10 : 16;
  var topPad = compact ? 22 : 16;
  var bottomPad = compact ? 10 : 12;
  var labelFs = compact ? 10 : 11;
  var leftPad = compact ? 52 : 68;

  var data = list.map(function (d) {
    return [String((d && d.day) || ""), toNum(d && d.answered)];
  });
  var maxVal = Math.max.apply(
    null,
    data.map(function (d) {
      return d[1];
    }),
  );

  return {
    tooltip: {
      trigger: "item",
      confine: true,
      backgroundColor: pickColor(t.surface, 0.96),
      borderColor: pickColor(t.border, 0.9),
      textStyle: { color: t.text, fontSize: 12 },
      formatter: function (p) {
        var v = p && p.value ? p.value : [];
        var day = v[0] || "";
        var cnt = v[1] || 0;
        return String(day) + "\\n作答：" + fmtCount(cnt);
      },
    },
    visualMap: {
      min: 0,
      max: maxVal > 0 ? maxVal : 10,
      show: false,
      inRange: { color: [pickColor(t.primary, 0.08), pickColor(t.primary, 0.55)] },
    },
    calendar: {
      top: topPad,
      left: leftPad,
      right: side,
      bottom: bottomPad,
      cellSize: ["auto", "auto"],
      range: [data[0][0], data[data.length - 1][0]],
      itemStyle: {
        borderWidth: 1,
        borderColor: pickColor(t.border, 0.9),
        color: pickColor(t.surface, 0.45),
      },
      splitLine: { lineStyle: { color: pickColor(t.border, 0.9) } },
      yearLabel: { show: false },
      monthLabel: { color: t.muted, fontSize: labelFs },
      dayLabel: {
        show: true,
        position: "start",
        margin: compact ? 10 : 14,
        nameMap: ["周日", "周一", "周二", "周三", "周四", "周五", "周六"],
        color: t.muted,
        fontSize: labelFs,
      },
    },
    series: [
      {
        type: "heatmap",
        coordinateSystem: "calendar",
        data: data,
        emphasis: { itemStyle: { shadowBlur: 10, shadowColor: pickColor(t.primary, 0.25) } },
      },
    ],
  };
}

function buildGaugeOption(stats, t) {
  var compact = isCompact();
  var accuracy = toNum(stats && stats.accuracy);
  var completion = toNum(stats && stats.completion);
  var score = clamp(accuracy * 0.65 + completion * 0.35, 0, 100);

  var axisFs = compact ? 9 : 10;
  var titleFs = compact ? 11 : 12;
  var detailFs = compact ? 20 : 22;
  var metaFs = compact ? 11 : 12;

  return {
    series: [
      {
        type: "gauge",
        startAngle: 220,
        endAngle: -40,
        min: 0,
        max: 100,
        radius: "96%",
        pointer: { show: true, length: "64%", width: 4 },
        progress: { show: true, width: 10, roundCap: true, itemStyle: { color: t.cta } },
        axisLine: { lineStyle: { width: 10, color: [[1, pickColor(t.primary, 0.12)]] } },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: { color: t.muted, fontSize: axisFs, distance: 18 },
        anchor: { show: false },
        title: { show: true, offsetCenter: [0, "56%"], color: t.muted, fontSize: titleFs, fontWeight: 800 },
        detail: {
          valueAnimation: true,
          formatter: function (v) {
            return toNum(v).toFixed(1) + "%";
          },
          offsetCenter: [0, "30%"],
          color: t.text,
          fontSize: detailFs,
          fontWeight: 950,
        },
        data: [{ value: score, name: "掌握指数" }],
      },
    ],
    graphic: [
      {
        type: "text",
        left: "center",
        top: "84%",
        style: {
          text: "正确率" + fmtPercent(accuracy) + "  |  覆盖率" + fmtPercent(completion),
          fill: t.muted,
          fontSize: metaFs,
          fontWeight: 700,
        },
      },
    ],
  };
}

function buildAnsweredTrendOption(trend, t, emptyText) {
  var list = Array.isArray(trend) ? trend : [];
  if (!list.length) return emptyOption(emptyText || "暂无趋势数据", t);

  var compact = isCompact();
  var x = list.map(function (d) {
    return fmtDay(d && d.day);
  });
  var answered = list.map(function (d) {
    return toNum(d && d.answered);
  });
  var acc = list.map(function (d) {
    var a = toNum(d && d.answered);
    var c = toNum(d && d.correct);
    return a > 0 ? (c * 100) / a : 0;
  });

  var labelFs = compact ? 10 : 12;
  var barW = compact ? 10 : 14;
  var sym = compact ? 4 : 6;
  var gridBottom = compact ? 22 : 10;

  return {
    tooltip: {
      trigger: "axis",
      confine: true,
      backgroundColor: pickColor(t.surface, 0.96),
      borderColor: pickColor(t.border, 0.9),
      textStyle: { color: t.text, fontSize: 12 },
    },
    grid: { left: 12, right: 12, top: 18, bottom: gridBottom, containLabel: true },
    xAxis: {
      type: "category",
      data: x,
      axisLine: { lineStyle: { color: pickColor(t.border, 0.9) } },
      axisLabel: { color: t.muted, fontSize: labelFs, hideOverlap: true, formatter: fmtDayLabel },
    },
    yAxis: [
      {
        type: "value",
        min: 0,
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: t.muted, fontSize: labelFs },
        splitLine: { lineStyle: { color: pickColor(t.border, 0.9), type: "dashed", opacity: 0.6 } },
      },
      {
        type: "value",
        min: 0,
        max: 100,
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: t.muted, fontSize: labelFs, formatter: "{value}%" },
        splitLine: { show: false },
      },
    ],
    series: [
      {
        name: "作答量",
        type: "bar",
        data: answered,
        barWidth: barW,
        itemStyle: { color: pickColor(t.primary, 0.55), borderRadius: [8, 8, 0, 0] },
      },
      {
        name: "正确率",
        type: "line",
        yAxisIndex: 1,
        data: acc,
        smooth: true,
        symbol: "circle",
        symbolSize: sym,
        lineStyle: { width: 2, color: t.cta },
        itemStyle: { color: t.cta },
      },
    ],
  };
}

function buildTypeStructureOption(byType, t) {
  var list = Array.isArray(byType) ? byType.slice() : [];
  if (!list.length) return emptyOption("暂无题型数据", t);

  var compact = isCompact();
  list.sort(function (a, b) {
    return toNum(b && b.total) - toNum(a && a.total);
  });

  var top = list.slice(0, 10);
  var x = top.map(function (r) {
    return String((r && r.q_type) || "未知");
  });
  var correct = top.map(function (r) {
    return toNum(r && r.correct);
  });
  var wrong = top.map(function (r) {
    return toNum(r && r.wrong);
  });
  var completion = top.map(function (r) {
    return toNum(r && r.completion);
  });

  var labelFs = compact ? 10 : 12;
  var barW = compact ? 12 : 16;
  var sym = compact ? 4 : 6;
  var maxXLen = compact ? 4 : 6;
  var rotate = compact ? (x.length > 4 ? 30 : 0) : x.length > 6 ? 22 : 0;
  var legend = compact
    ? {
        bottom: 0,
        left: "center",
        type: "scroll",
        orient: "horizontal",
        textStyle: { color: t.muted, fontSize: labelFs },
        itemWidth: 10,
        itemHeight: 10,
      }
    : { top: 6, textStyle: { color: t.muted, fontSize: 12 }, itemWidth: 10, itemHeight: 10 };

  return {
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      confine: true,
      backgroundColor: pickColor(t.surface, 0.96),
      borderColor: pickColor(t.border, 0.9),
      textStyle: { color: t.text, fontSize: 12 },
      formatter: function (params) {
        var p = Array.isArray(params) ? params : [];
        var name = (p[0] && p[0].axisValue) || "";
        var c = (p[0] && toNum(p[0].data)) || 0;
        var w = (p[1] && toNum(p[1].data)) || 0;
        var idx = p[0] ? p[0].dataIndex : 0;
        var comp = completion[idx] || 0;
        return String(name) + "\\n正确：" + fmtCount(c) + "\\n错误：" + fmtCount(w) + "\\n覆盖率：" + fmtPercent(comp);
      },
    },
    legend: legend,
    grid: { left: 12, right: 12, top: compact ? 12 : 40, bottom: compact ? 34 : 10, containLabel: true },
    xAxis: {
      type: "category",
      data: x,
      axisLine: { lineStyle: { color: pickColor(t.border, 0.9) } },
      axisLabel: {
        color: t.muted,
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
        type: "value",
        min: 0,
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: t.muted, fontSize: labelFs },
        splitLine: { lineStyle: { color: pickColor(t.border, 0.9), type: "dashed", opacity: 0.6 } },
      },
      {
        type: "value",
        min: 0,
        max: 100,
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: t.muted, fontSize: labelFs, formatter: "{value}%" },
        splitLine: { show: false },
      },
    ],
    series: [
      {
        name: "正确",
        type: "bar",
        stack: "ans",
        data: correct,
        barWidth: barW,
        itemStyle: { color: pickColor(t.primary, 0.5), borderRadius: [8, 8, 0, 0] },
      },
      {
        name: "错误",
        type: "bar",
        stack: "ans",
        data: wrong,
        itemStyle: { color: pickColor(t.cta, 0.45), borderRadius: [8, 8, 0, 0] },
      },
      {
        name: "覆盖率",
        type: "line",
        yAxisIndex: 1,
        data: completion,
        smooth: true,
        symbol: "circle",
        symbolSize: sym,
        lineStyle: { width: 2, color: pickColor(t.text, 0.65) },
        itemStyle: { color: pickColor(t.text, 0.65) },
      },
    ],
  };
}

function buildTypePieOption(byType, t, emptyText) {
  var list = Array.isArray(byType) ? byType.slice() : [];
  if (!list.length) return emptyOption(emptyText || "暂无分布数据", t);

  var compact = isCompact();
  list.sort(function (a, b) {
    return toNum(b && b.total) - toNum(a && a.total);
  });

  var top = list.slice(0, 8);
  var rest = list
    .slice(8)
    .reduce(function (sum, r) {
      return sum + toNum(r && r.total);
    }, 0);

  var data = top.map(function (r) {
    return { name: String((r && r.q_type) || "未知"), value: toNum(r && r.total) };
  });
  if (rest > 0) data.push({ name: "其他", value: rest });

  var labelFs = compact ? 10 : 12;
  var legend = compact
    ? {
        bottom: 0,
        left: "center",
        type: "scroll",
        orient: "horizontal",
        textStyle: { color: t.muted, fontSize: labelFs },
        itemWidth: 10,
        itemHeight: 10,
      }
    : {
        top: "middle",
        right: 6,
        type: "scroll",
        orient: "vertical",
        textStyle: { color: t.muted, fontSize: 12 },
        itemWidth: 10,
        itemHeight: 10,
      };

  return {
    tooltip: {
      trigger: "item",
      confine: true,
      backgroundColor: pickColor(t.surface, 0.96),
      borderColor: pickColor(t.border, 0.9),
      textStyle: { color: t.text, fontSize: 12 },
      formatter: function (p) {
        var name = p && p.name ? p.name : "";
        var val = p && p.value != null ? p.value : 0;
        var percent = p && p.percent != null ? p.percent : 0;
        return String(name) + "\\n" + fmtCount(val) + " 题  |  " + percent + "%";
      },
    },
    legend: legend,
    series: [
      {
        type: "pie",
        radius: compact ? ["48%", "76%"] : ["52%", "78%"],
        center: compact ? ["50%", "44%"] : ["34%", "50%"],
        avoidLabelOverlap: true,
        itemStyle: { borderColor: pickColor(t.surface, 0.8), borderWidth: 2 },
        label: { show: false },
        emphasis: { scale: true, scaleSize: 6 },
        data: data,
        color: [
          pickColor(t.primary, 0.65),
          pickColor(t.primary, 0.5),
          pickColor(t.primary, 0.36),
          pickColor(t.cta, 0.55),
          pickColor(t.cta, 0.4),
          pickColor(t.text, 0.45),
          pickColor(t.text, 0.32),
          pickColor(t.primary, 0.26),
          pickColor(t.primary, 0.18),
        ],
      },
    ],
  };
}

function buildFunnelOption(stats, t) {
  var compact = isCompact();
  var total = toNum(stats && stats.total_count);
  var answered = toNum(stats && stats.answered);
  var correct = toNum(stats && stats.correct);
  if (total <= 0) return emptyOption("暂无数据", t);

  var data = [
    { name: "题库总题", value: total },
    { name: "已覆盖", value: answered },
    { name: "稳定掌握", value: correct },
  ];

  var compactTop = 26;
  if (compact) {
    var coverRatio = total > 0 ? answered / total : 0;
    if (coverRatio < 0.15) compactTop = 60;
  }

  return {
    tooltip: {
      trigger: "item",
      confine: true,
      backgroundColor: pickColor(t.surface, 0.96),
      borderColor: pickColor(t.border, 0.9),
      textStyle: { color: t.text, fontSize: 12 },
      formatter: function (p) {
        return String(p && p.name ? p.name : "") + "\\n" + fmtCount(p && p.value != null ? p.value : 0);
      },
    },
    series: [
      {
        type: "funnel",
        left: 12,
        right: 12,
        top: compact ? compactTop : 12,
        bottom: compact ? 22 : 12,
        min: 0,
        max: total,
        minSize: compact ? "28%" : "20%",
        maxSize: compact ? "88%" : "92%",
        sort: "descending",
        gap: compact ? 8 : 6,
        label: {
          show: true,
          color: t.text,
          fontSize: compact ? 11 : 12,
          fontWeight: 800,
          formatter: function (p) {
            return compact ? p.name + "\\n" + fmtCount(p.value) : p.name + "  " + fmtCount(p.value);
          },
          position: compact ? "inside" : "right",
          align: compact ? "center" : "left",
          verticalAlign: "middle",
          lineHeight: compact ? 16 : 14,
        },
        labelLine: compact ? { show: false } : { length: 8, lineStyle: { color: t.muted } },
        itemStyle: {
          borderColor: pickColor(t.surface, 0.85),
          borderWidth: 1,
          shadowBlur: 8,
          shadowColor: pickColor(t.primary, 0.08),
        },
        emphasis: { itemStyle: { shadowBlur: 16, shadowColor: pickColor(t.primary, 0.18) } },
        data: data,
        color: [pickColor(t.primary, 0.5), pickColor(t.primary, 0.36), pickColor(t.cta, 0.42)],
      },
    ],
  };
}

function buildRiskRadarOption(byType, t) {
  var list = Array.isArray(byType) ? byType.slice() : [];
  if (!list.length) return emptyOption("暂无数据", t);

  var compact = isCompact();
  var rows = list
    .map(function (r) {
      var accuracy = toNum(r && r.accuracy);
      var completion = toNum(r && r.completion);
      var risk = clamp((100 - accuracy) * 0.65 + (100 - completion) * 0.35, 0, 100);
      return { q_type: String((r && r.q_type) || "未知"), risk: risk };
    })
    .sort(function (a, b) {
      return b.risk - a.risk;
    })
    .slice(0, 6);

  if (!rows.length) return emptyOption("暂无数据", t);

  var indicators = rows.map(function (r) {
    return { name: r.q_type, max: 100 };
  });
  var values = rows.map(function (r) {
    return r.risk;
  });

  return {
    tooltip: {
      trigger: "item",
      confine: true,
      backgroundColor: pickColor(t.surface, 0.96),
      borderColor: pickColor(t.border, 0.9),
      textStyle: { color: t.text, fontSize: 12 },
      formatter: function () {
        return rows
          .map(function (r) {
            return r.q_type + "：风险" + fmtPercent(r.risk);
          })
          .join("\\n");
      },
    },
    radar: {
      indicator: indicators,
      radius: compact ? "62%" : "70%",
      splitNumber: 4,
      nameGap: compact ? 8 : 14,
      axisName: {
        color: t.muted,
        fontSize: compact ? 10 : 11,
        overflow: "truncate",
        width: compact ? 64 : 88,
        ellipsis: "…",
      },
      splitLine: { lineStyle: { color: pickColor(t.border, 0.9) } },
      splitArea: { areaStyle: { color: [pickColor(t.primary, 0.04), pickColor(t.primary, 0.02)] } },
      axisLine: { lineStyle: { color: pickColor(t.border, 0.9) } },
    },
    series: [
      {
        type: "radar",
        data: [
          {
            value: values,
            name: "风险",
            areaStyle: { color: pickColor(t.cta, 0.16) },
            lineStyle: { color: pickColor(t.cta, 0.7), width: 2 },
            itemStyle: { color: pickColor(t.cta, 0.85) },
          },
        ],
      },
    ],
  };
}

function buildDiffOption(byDiff, t) {
  var list = Array.isArray(byDiff) ? byDiff.slice() : [];
  if (!list.length) return null;

  var compact = isCompact();
  list.sort(function (a, b) {
    return toNum(a && a.difficulty) - toNum(b && b.difficulty);
  });

  var x = list.map(function (r) {
    return String(r && r.difficulty != null ? r.difficulty : "—");
  });
  var completion = list.map(function (r) {
    return toNum(r && r.completion);
  });
  var accuracy = list.map(function (r) {
    return toNum(r && r.accuracy);
  });

  var labelFs = compact ? 10 : 12;
  var barW = compact ? 10 : 14;
  var sym = compact ? 4 : 6;
  var legend = compact
    ? {
        bottom: 0,
        left: "center",
        type: "scroll",
        orient: "horizontal",
        textStyle: { color: t.muted, fontSize: labelFs },
        itemWidth: 10,
        itemHeight: 10,
      }
    : { top: 6, textStyle: { color: t.muted, fontSize: 12 }, itemWidth: 10, itemHeight: 10 };

  return {
    tooltip: {
      trigger: "axis",
      confine: true,
      backgroundColor: pickColor(t.surface, 0.96),
      borderColor: pickColor(t.border, 0.9),
      textStyle: { color: t.text, fontSize: 12 },
    },
    legend: legend,
    grid: { left: 12, right: 12, top: compact ? 12 : 40, bottom: compact ? 34 : 10, containLabel: true },
    xAxis: {
      type: "category",
      data: x,
      axisLine: { lineStyle: { color: pickColor(t.border, 0.9) } },
      axisLabel: { color: t.muted, fontSize: labelFs },
    },
    yAxis: {
      type: "value",
      min: 0,
      max: 100,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: t.muted, fontSize: labelFs, formatter: "{value}%" },
      splitLine: { lineStyle: { color: pickColor(t.border, 0.9), type: "dashed", opacity: 0.6 } },
    },
    series: [
      {
        name: "覆盖率",
        type: "bar",
        data: completion,
        barWidth: barW,
        itemStyle: { color: pickColor(t.primary, 0.6), borderRadius: [8, 8, 0, 0] },
      },
      {
        name: "正确率",
        type: "line",
        data: accuracy,
        smooth: true,
        symbol: "circle",
        symbolSize: sym,
        lineStyle: { width: 2, color: t.cta },
        itemStyle: { color: t.cta },
      },
    ],
  };
}

function buildMistakeMatrixOption(items, t) {
  var list = Array.isArray(items) ? items : [];
  if (!list.length) return emptyOption("暂无错题数据", t);

  var compact = isCompact();
  var data = list.slice(0, 300).map(function (it) {
    var wrongCount = toNum(it && it.mistake_wrong_count) || 1;
    var ds = daysSince((it && (it.mistake_updated_at || it.mistake_created_at)) || "");
    if (ds == null) ds = 0;
    var diff = toNum(it && it.difficulty) || 1;
    var preview = String((it && (it.content_preview || it.content)) || "").trim();
    return [wrongCount, ds, diff, preview];
  });

  var labelFs = compact ? 10 : 12;

  return {
    tooltip: {
      trigger: "item",
      confine: true,
      backgroundColor: pickColor(t.surface, 0.96),
      borderColor: pickColor(t.border, 0.9),
      textStyle: { color: t.text, fontSize: 12 },
      formatter: function (p) {
        var v = p && p.value ? p.value : [];
        return (
          "错题次数：" +
          fmtCount(v[0] || 0) +
          "\\n距上次错题：" +
          fmtCount(v[1] || 0) +
          " 天\\n难度：" +
          fmtCount(v[2] || 1) +
          "\\n" +
          String(v[3] || "").slice(0, 120)
        );
      },
    },
    grid: { left: 12, right: compact ? 12 : 18, top: 12, bottom: compact ? 18 : 12, containLabel: true },
    xAxis: {
      type: "value",
      min: 0,
      axisLine: { lineStyle: { color: pickColor(t.border, 0.9) } },
      axisLabel: { color: t.muted, fontSize: labelFs },
      splitLine: { lineStyle: { color: pickColor(t.border, 0.9), type: "dashed", opacity: 0.6 } },
      name: compact ? "" : "错题次数",
      nameTextStyle: { color: t.muted, fontSize: labelFs, fontWeight: 800 },
    },
    yAxis: {
      type: "value",
      min: 0,
      axisLine: { lineStyle: { color: pickColor(t.border, 0.9) } },
      axisLabel: { color: t.muted, fontSize: labelFs },
      splitLine: { lineStyle: { color: pickColor(t.border, 0.9), type: "dashed", opacity: 0.6 } },
      name: compact ? "" : "距上次错题天数",
      nameTextStyle: { color: t.muted, fontSize: labelFs, fontWeight: 800 },
    },
    series: [
      {
        type: "scatter",
        data: data,
        symbolSize: function (val) {
          var wc = toNum(val && val[0]);
          return compact ? clamp(6 + wc * 2, 8, 24) : clamp(8 + wc * 2.2, 10, 28);
        },
        itemStyle: { color: pickColor(t.cta, 0.55), opacity: 0.9 },
        emphasis: { itemStyle: { color: pickColor(t.cta, 0.85) } },
      },
    ],
  };
}

function buildMistakeTopOption(items, t) {
  var list = Array.isArray(items) ? items : [];
  if (!list.length) return emptyOption("暂无错题数据", t);

  var compact = isCompact();
  var top = list
    .slice()
    .sort(function (a, b) {
      return toNum(b && b.mistake_wrong_count) - toNum(a && a.mistake_wrong_count);
    })
    .slice(0, 10);

  var previewLen = compact ? 10 : 14;
  var y = top
    .map(function (it) {
      var prev = String((it && it.content_preview) || "").trim();
      if (!prev) return "题目";
      return prev.length > previewLen ? prev.slice(0, previewLen) + "…" : prev;
    })
    .reverse();
  var x = top
    .map(function (it) {
      return toNum(it && it.mistake_wrong_count);
    })
    .reverse();

  var labelFs = compact ? 10 : 12;

  return {
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      confine: true,
      backgroundColor: pickColor(t.surface, 0.96),
      borderColor: pickColor(t.border, 0.9),
      textStyle: { color: t.text, fontSize: 12 },
      formatter: function (params) {
        var p = Array.isArray(params) ? params[0] : null;
        if (!p) return "";
        var idx = p.dataIndex;
        var original = top[top.length - 1 - idx];
        return String((original && original.content_preview) || "题目") + "\\n错题次数：" + fmtCount(p.data);
      },
    },
    grid: { left: 12, right: 12, top: 10, bottom: 10, containLabel: true },
    xAxis: {
      type: "value",
      min: 0,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: t.muted, fontSize: labelFs },
      splitLine: { lineStyle: { color: pickColor(t.border, 0.9), type: "dashed", opacity: 0.6 } },
    },
    yAxis: {
      type: "category",
      data: y,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: t.muted, fontSize: labelFs, width: compact ? 110 : 160, overflow: "truncate", ellipsis: "…" },
    },
    series: [
      {
        type: "bar",
        data: x,
        barWidth: compact ? 10 : 12,
        itemStyle: { color: pickColor(t.primary, 0.55), borderRadius: [8, 8, 8, 8] },
      },
    ],
  };
}

function buildMistakeDifficultyOption(items, t) {
  var list = Array.isArray(items) ? items : [];
  if (!list.length) return emptyOption("暂无难度数据", t);

  var compact = isCompact();
  var buckets = {};
  list.forEach(function (it) {
    var d = toNum(it && it.difficulty) || 1;
    var key = String(d);
    if (!buckets[key]) buckets[key] = { difficulty: d, count: 0, times: 0 };
    buckets[key].count += 1;
    buckets[key].times += toNum(it && it.mistake_wrong_count) || 1;
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

  var labelFs = compact ? 10 : 12;
  var barW = compact ? 10 : 14;
  var sym = compact ? 4 : 6;
  var legend = compact
    ? {
        bottom: 0,
        left: "center",
        type: "scroll",
        orient: "horizontal",
        textStyle: { color: t.muted, fontSize: labelFs },
        itemWidth: 10,
        itemHeight: 10,
      }
    : { top: 6, textStyle: { color: t.muted, fontSize: 12 }, itemWidth: 10, itemHeight: 10 };

  return {
    tooltip: {
      trigger: "axis",
      confine: true,
      backgroundColor: pickColor(t.surface, 0.96),
      borderColor: pickColor(t.border, 0.9),
      textStyle: { color: t.text, fontSize: 12 },
    },
    legend: legend,
    grid: { left: 12, right: 12, top: compact ? 12 : 40, bottom: compact ? 34 : 10, containLabel: true },
    xAxis: {
      type: "category",
      data: x,
      axisLine: { lineStyle: { color: pickColor(t.border, 0.9) } },
      axisLabel: { color: t.muted, fontSize: labelFs },
    },
    yAxis: [
      {
        type: "value",
        min: 0,
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: t.muted, fontSize: labelFs },
        splitLine: { lineStyle: { color: pickColor(t.border, 0.9), type: "dashed", opacity: 0.6 } },
      },
      {
        type: "value",
        min: 0,
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: t.muted, fontSize: labelFs },
        splitLine: { show: false },
      },
    ],
    series: [
      {
        name: "错题数",
        type: "bar",
        data: counts,
        barWidth: barW,
        itemStyle: { color: pickColor(t.primary, 0.55), borderRadius: [8, 8, 0, 0] },
      },
      {
        name: "平均错题次数",
        type: "line",
        yAxisIndex: 1,
        data: avgTimes,
        smooth: true,
        symbol: "circle",
        symbolSize: sym,
        lineStyle: { width: 2, color: t.cta },
        itemStyle: { color: t.cta },
      },
    ],
  };
}

function buildFavAddedTrendOption(trend, t) {
  var list = Array.isArray(trend) ? trend : [];
  if (!list.length) return emptyOption("暂无新增数据", t);

  var compact = isCompact();
  var x = list.map(function (d) {
    return fmtDay(d && d.day);
  });
  var y = list.map(function (d) {
    return toNum(d && d.added);
  });

  var labelFs = compact ? 10 : 12;
  var sym = compact ? 4 : 6;
  var gridBottom = compact ? 22 : 10;

  return {
    tooltip: {
      trigger: "axis",
      confine: true,
      backgroundColor: pickColor(t.surface, 0.96),
      borderColor: pickColor(t.border, 0.9),
      textStyle: { color: t.text, fontSize: 12 },
    },
    grid: { left: 12, right: 12, top: 18, bottom: gridBottom, containLabel: true },
    xAxis: {
      type: "category",
      data: x,
      axisLine: { lineStyle: { color: pickColor(t.border, 0.9) } },
      axisLabel: { color: t.muted, fontSize: labelFs, hideOverlap: true, formatter: fmtDayLabel },
    },
    yAxis: {
      type: "value",
      min: 0,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: t.muted, fontSize: labelFs },
      splitLine: { lineStyle: { color: pickColor(t.border, 0.9), type: "dashed", opacity: 0.6 } },
    },
    series: [
      {
        type: "line",
        data: y,
        smooth: true,
        symbol: "circle",
        symbolSize: sym,
        lineStyle: { width: 2, color: pickColor(t.primary, 0.8) },
        itemStyle: { color: pickColor(t.primary, 0.85) },
        areaStyle: { color: pickColor(t.primary, 0.14) },
      },
    ],
  };
}

function buildUbdv2ChartOption(id, payload, tokens) {
  var cid = String(id || "").trim();
  if (!cid) return null;

  var t = tokens || getUbdv2ThemeTokens(false, "default");
  var p = payload || {};

  if (p.loading) return emptyOption("加载中…", t);
  if (p.error) return emptyOption("加载失败", t);

  var stats = p.stats || {};
  var questions = Array.isArray(p.questions) ? p.questions : [];
  var favTrend = p.favoritesTrend || {};

  if (cid === "ubdCalendarChart") return buildCalendarOption(stats.trend || [], t);
  if (cid === "ubdGaugeChart") return buildGaugeOption(stats, t);
  if (cid === "ubdTrendChart") return buildAnsweredTrendOption(stats.trend || [], t, "暂无趋势数据");
  if (cid === "ubdTypeChart") return buildTypeStructureOption(stats.by_type || [], t);
  if (cid === "ubdFunnelChart") return buildFunnelOption(stats, t);
  if (cid === "ubdRiskRadarChart") return buildRiskRadarOption(stats.by_type || [], t);
  if (cid === "ubdDiffChart") return buildDiffOption(stats.by_difficulty || [], t) || emptyOption("暂无难度数据", t);

  if (cid === "ubdMistakeMatrixChart") return buildMistakeMatrixOption(questions, t);
  if (cid === "ubdMistakeTopChart") return buildMistakeTopOption(questions, t);
  if (cid === "ubdMisTrendChart") return buildAnsweredTrendOption(stats.trend || [], t, "暂无趋势数据");
  if (cid === "ubdMisTypePieChart") return buildTypePieOption(stats.by_type || [], t, "暂无分布数据");
  if (cid === "ubdMisDiffChart") return buildMistakeDifficultyOption(questions, t);

  if (cid === "ubdFavAddedChart") return buildFavAddedTrendOption((favTrend && favTrend.trend) || [], t);
  if (cid === "ubdFavTypePieChart") return buildTypePieOption(stats.by_type || [], t, "暂无分布数据");
  if (cid === "ubdFavDiffChart") return buildDiffOption(stats.by_difficulty || [], t) || emptyOption("暂无难度数据", t);
  if (cid === "ubdFavReviewTrendChart") return buildAnsweredTrendOption(stats.trend || [], t, "暂无趋势数据");

  return null;
}

module.exports = {
  getUbdv2ThemeTokens,
  buildUbdv2ChartOption,
};
