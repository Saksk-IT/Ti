/**
 * data_center.js — 数据中心主入口：AI 聊天、初始化、事件绑定
 * 依赖: data_center_utils.js (window.DCUtils), data_center_charts.js (window.DCCharts)
 */
(function () {
  'use strict';

  var U = window.DCUtils || {};
  var C = window.DCCharts || {};
  var toInt = U.toInt;
  var pickColor = U.pickColor;
  var charts = C.charts || {};
  var theme = C.theme || function () { return { primary: '#111827', cta: '#111827' }; };
  var ensureChart = C.ensureChart;
  var emptyOption = C.emptyOption;
  var noop = function () {};
  var renderHealthGauge = C.renderHealthGauge || noop;
  var renderAssetTrend = C.renderAssetTrend || noop;
  var renderGlobalLoop = C.renderGlobalLoop || noop;
  var renderTrendStack = C.renderTrendStack || noop;
  var renderTrendDetail = C.renderTrendDetail || noop;
  var renderCalendar = C.renderCalendar || noop;
  var renderHeatmap = C.renderHeatmap || noop;
  var renderHourly = C.renderHourly || noop;
  var renderWeekday = C.renderWeekday || noop;
  var renderRadar = C.renderRadar || noop;
  var renderTopMix = C.renderTopMix || noop;
  var renderStackedCategory = C.renderStackedCategory || noop;
  var renderBankSplit = C.renderBankSplit || noop;
  var renderBankCategories = C.renderBankCategories || noop;
  var renderBankBubble = C.renderBankBubble || noop;
  var renderBankRank = C.renderBankRank || noop;
  var renderSubjectProgress = C.renderSubjectProgress || noop;
  var renderSubjectRisk = C.renderSubjectRisk || noop;
  var renderDailySplit = C.renderDailySplit || noop;
  var renderRankBar = C.renderRankBar || noop;
  var renderTagTreemap = C.renderTagTreemap || noop;
  var renderTagGraph = C.renderTagGraph || noop;
  var renderTagTop = C.renderTagTop || noop;
  var renderTagAccuracy = C.renderTagAccuracy || noop;
  var renderAiFocus = C.renderAiFocus || noop;
  var renderChartById;

  var payload = window.__DATA_CENTER__ || {};
  var ability = Array.isArray(payload.ability_radar) ? payload.ability_radar : [];
  var weakness = Array.isArray(payload.weakness) ? payload.weakness : [];

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
