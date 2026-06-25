const assert = require('node:assert/strict');
const test = require('node:test');

const {
  buildCampusSummary,
  buildStudyAdvice,
  buildRecentBanks,
  buildWeaknessEmptyActions,
  normalizeHubStats
} = require('../miniprogram/pages/hub-v2/hub-content');

test('buildStudyAdvice prioritizes continue practice, weakness, and mistakes for logged in users', () => {
  const advice = buildStudyAdvice(
    { answered: 20, accuracy: 70, favorites: 4, mistakes: 8 },
    [{ subject: '数据结构', q_type: '选择题', accuracy: 45 }],
    { has_practice: true, subject_name: 'C语言专项', last_at_display: '2小时前' },
    true
  );

  assert.deepEqual(
    advice.map((item) => item.key),
    ['continue', 'weakness', 'mistakes']
  );
  assert.equal(advice[0].subtitle, 'C语言专项');
  assert.equal(advice[1].subtitle, '数据结构');
  assert.equal(advice[2].target, 'review');
});

test('buildStudyAdvice gives a login action to visitors', () => {
  const advice = buildStudyAdvice(
    { answered: 0, accuracy: 0, favorites: 0, mistakes: 0 },
    [],
    { has_practice: false },
    false
  );

  assert.equal(advice.length, 1);
  assert.equal(advice[0].key, 'login');
  assert.equal(advice[0].target, 'login');
});

test('buildRecentBanks combines last practice and stored rows without duplicates', () => {
  const recent = buildRecentBanks(
    {
      has_practice: true,
      subject_name: '算法基础',
      last_at_display: '刚刚',
      source_type: 'public',
      source_id: 7,
      mode: 'normal'
    },
    [
      { title: '算法基础', source_type: 'public', source_id: 7, meta: '重复项' },
      { title: '我的错题专项', source_type: 'bank', source_id: 12, meta: '昨天' },
      { title: '期末模拟', source_type: 'bank', source_id: 18, meta: '3天前' },
      { title: '超出限制', source_type: 'bank', source_id: 99, meta: '4天前' }
    ]
  );

  assert.deepEqual(
    recent.map((item) => item.title),
    ['算法基础', '我的错题专项', '期末模拟']
  );
  assert.equal(recent[0].target, 'continue');
  assert.equal(recent.length, 3);
});

test('buildWeaknessEmptyActions adapts empty state for login and practice progress', () => {
  assert.equal(buildWeaknessEmptyActions(false, {}).at(0).target, 'login');
  assert.equal(buildWeaknessEmptyActions(true, { answered: 0 }).at(0).target, 'publicBank');
  assert.equal(buildWeaknessEmptyActions(true, { answered: 9 }).at(0).target, 'review');
});

test('normalizeHubStats prefers data center all_summary for public and personal bank totals', () => {
  const stats = normalizeHubStats({
    answered_count: 2,
    accuracy: 50,
    favorites_count: 1,
    mistakes_count: 1,
    all_summary: {
      answered: 18,
      accuracy: 83.3,
      favorites: 6,
      mistakes: 4
    }
  });

  assert.deepEqual(stats, {
    answered: 18,
    accuracy: 83.3,
    favorites: 6,
    mistakes: 4
  });
});

test('buildCampusSummary reuses campus page schedule and grade summaries', () => {
  const summary = buildCampusSummary({
    credential: { has_credentials: true, username_hint: '2024****18' },
    snapshots: [
      { id: 1 },
      {
        payload: {
          term: { xnm: '2025', xqm: '12', label: '2025-2026 第二学期' },
          week_table: {
            星期一: {
              '1-2节': [
                { course_name: 'WEB程序设计', teacher: '尹老师', location: '软件楼122', weeks: '1-15周' },
              ],
            },
          },
        },
      },
    ],
    grade_snapshots: [
      {
        payload: {
          term: { xnm: '2025', xqm: '3', label: '2025-2026 第一学期' },
          summary: { course_count: 1, total_credits: 3, gpa: 3.5 },
          grades: [
            { course_name: '数据结构', score: '90', credits: '3.0', grade_point: '3.50' },
          ],
        },
      },
    ]
  }, true, new Date(2026, 5, 22));

  assert.equal(summary.statusLabel, '已绑定');
  assert.equal(summary.scheduleCount, 1);
  assert.equal(summary.gradeCount, 1);
  assert.equal(summary.hasTodayCourses, true);
  assert.equal(summary.todayCourseCount, 1);
  assert.equal(summary.todayCourseSubtitle, '星期一 · 2025-2026 第二学期');
  assert.deepEqual(summary.todayCourses.map((item) => item.course_name), ['WEB程序设计']);
  assert.equal(summary.hasGradeSummary, true);
  assert.equal(summary.latestGradeTerm, '2025-2026 第一学期');
  assert.equal(summary.latestGradeCourseCount, 1);
  assert.equal(summary.latestGradeCredits, '3');
  assert.equal(summary.latestGradeGpa, '3.5');
});

test('buildCampusSummary highlights the latest grade term, courses, and GPA', () => {
  const summary = buildCampusSummary({
    credential: { has_credentials: true, username_hint: '2024****18' },
    snapshots: [{ id: 1 }],
    grade_snapshots: [
      {
        xnm: '2024',
        xqm: '12',
        payload: {
          term: { label: '2024-2025 第二学期' },
          summary: { course_count: 3, gpa: 3.12 },
          grades: [
            { course_name: '旧学期课程', score: '88' },
          ],
        },
      },
      {
        xnm: '2025',
        xqm: '3',
        term_label: '2025-2026 第一学期',
        payload: {
          term: { xnm: '2025', xqm: '3', label: '2025-2026 第一学期' },
          summary: { course_count: 5, gpa: 3.87 },
          grades: [
            { course_name: '数据结构', score: '95' },
            { course_name: '数据库原理', score: '91' },
          ],
        },
      },
    ],
  }, true, new Date(2026, 5, 22));

  assert.equal(summary.hasGradeSummary, true);
  assert.equal(summary.latestGradeTerm, '2025-2026 第一学期');
  assert.equal(summary.latestGradeCourseCount, 5);
  assert.equal(summary.latestGradeCredits, '0');
  assert.equal(summary.latestGradeGpa, '3.87');
  assert.equal(summary.scheduleCount, 0);
  assert.equal(summary.gradeCount, 2);
});

test('buildCampusSummary falls back to snapshot counts when there are no grades', () => {
  const summary = buildCampusSummary({
    credential: { has_credentials: true, username_hint: '2024****18' },
    snapshots: [{ id: 1 }, { id: 2 }],
    grade_snapshots: [],
  }, true, new Date(2026, 5, 22));

  assert.equal(summary.hasGradeSummary, false);
  assert.equal(summary.latestGradeTerm, '暂无成绩');
  assert.equal(summary.latestGradeCourseCount, 0);
  assert.equal(summary.latestGradeCredits, '-');
  assert.equal(summary.latestGradeGpa, '-');
  assert.equal(summary.hasTodayCourses, false);
  assert.equal(summary.todayCourseCount, 0);
  assert.equal(summary.scheduleCount, 0);
  assert.equal(summary.gradeCount, 0);
});

test('buildCampusSummary prompts visitors and unbound users without leaking errors', () => {
  const visitor = buildCampusSummary(null, false);
  assert.equal(visitor.statusLabel, '登录后使用');
  assert.equal(visitor.primaryAction, '去登录');

  const unbound = buildCampusSummary({ credential: { has_credentials: false } }, true);
  assert.equal(unbound.statusLabel, '待绑定');
  assert.equal(unbound.primaryAction, '去绑定');

  const failed = buildCampusSummary({ error: new Error('raw upstream failed') }, true);
  assert.equal(failed.statusLabel, '同步失败');
  assert.equal(failed.subtitle, '校园状态暂时无法同步，仍可进入校园页查看');
});
