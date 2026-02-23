(function () {
  'use strict';
  var ns = window.UserBankDataV2NS;
  if (!ns) return;
  var h = ns.helpers || {};
  var toNum = h.toNum;
  var fmtCount = h.fmtCount;
  var fmtPercent = h.fmtPercent;
  var fmtDateTime = h.fmtDateTime;
  var calcActiveDays = h.calcActiveDays;
  var calcRecentAnswered = h.calcRecentAnswered;
  var setText = h.setText;
  var setBar = h.setBar;
  var api = ns.api || {};
  var charts = ns.charts || {};
  var resolveRoot = ns.resolveRoot;
  var isVisible = ns.isVisible;
  var readContextFromDom = ns.readContextFromDom;
  var normalizeContext = ns.normalizeContext;
  var renderAdvice = ns.renderAdvice;
  var fetchJson = ns.fetchJson;
  var r = ns.renderers || {};
  var renderCalendarChart = r.renderCalendarChart;
  var renderGaugeChart = r.renderGaugeChart;
  var renderAnsweredTrend = r.renderAnsweredTrend;
  var renderTypeStructureChart = r.renderTypeStructureChart;
  var renderTypePie = r.renderTypePie;
  var renderFunnel = r.renderFunnel;
  var renderRiskRadar = r.renderRiskRadar;
  var renderTypeTable = r.renderTypeTable;
  var renderDiffChart = r.renderDiffChart;
  var renderMistakeMatrix = r.renderMistakeMatrix;
  var renderMistakeTop = r.renderMistakeTop;
  var renderMistakeDifficulty = r.renderMistakeDifficulty;
  var renderMistakeTable = r.renderMistakeTable;
  var renderFavAddedTrend = r.renderFavAddedTrend;
  var renderFavTable = r.renderFavTable;
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
  var resizeBound = false;  function updateGlobalKpis(stats) {
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

