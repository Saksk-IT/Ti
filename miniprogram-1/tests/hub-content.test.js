const assert = require('node:assert/strict');
const test = require('node:test');

const {
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
