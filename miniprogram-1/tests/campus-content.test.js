const assert = require('node:assert/strict');
const test = require('node:test');

const {
  buildCampusTerms,
  normalizeGradeSnapshots,
  normalizeScheduleSnapshots,
  normalizeTermResults,
} = require('../miniprogram/pages/campus/campus-content');

test('buildCampusTerms builds all semesters for a year range', () => {
  assert.deepEqual(buildCampusTerms(2024, 2025, 'all'), [
    { xnm: '2024', xqm: '3' },
    { xnm: '2024', xqm: '12' },
    { xnm: '2025', xqm: '3' },
    { xnm: '2025', xqm: '12' },
  ]);
});

test('buildCampusTerms rejects ranges with more than 12 terms', () => {
  assert.throws(
    () => buildCampusTerms(2020, 2026, 'all'),
    /一次最多查询 12 个学期/
  );
});

test('normalizeGradeSnapshots maps summary and grade rows for campus cards', () => {
  const rows = normalizeGradeSnapshots([
    {
      payload: {
        term: { label: '2025-2026 第一学期' },
        summary: { course_count: 2, total_credits: 6, gpa: 3.67 },
        grades: [
          { course_name: '数据结构', score: '92', credits: '4.0', grade_point: '4.00', teacher: '任课教师A' },
          { course_name: '创新实践', score: '良好', credits: '2.0', grade_point: '3.00', teacher: '任课教师B' },
        ],
      },
    },
  ]);

  assert.equal(rows.length, 1);
  assert.equal(rows[0].title, '2025-2026 第一学期');
  assert.equal(rows[0].summaryText, '2 门课 / 6 学分 / GPA 3.67');
  assert.deepEqual(
    rows[0].grades.map((item) => item.course_name),
    ['数据结构', '创新实践']
  );
});

test('normalizeScheduleSnapshots maps week table and practice courses', () => {
  const rows = normalizeScheduleSnapshots([
    {
      payload: {
        term: { label: '2025-2026 第二学期' },
        student: { name: '测试学生', class_name: '软件工程26-1班' },
        week_table: {
          星期一: {
            '1-2节': [
              { course_name: 'WEB程序设计', teacher: '尹老师', location: '软件楼122', weeks: '1-15周' },
            ],
          },
        },
        practice_courses: [
          { course_name: '专业技术综合实践', teacher: '刘老师', weeks: '16-18周' },
        ],
      },
    },
  ]);

  assert.equal(rows.length, 1);
  assert.equal(rows[0].title, '2025-2026 第二学期');
  assert.equal(rows[0].studentText, '测试学生 / 软件工程26-1班');
  assert.equal(rows[0].weekRows[0].day, '星期一');
  assert.equal(rows[0].weekRows[0].sections[0].courses[0].course_name, 'WEB程序设计');
  assert.equal(rows[0].practice_courses[0].course_name, '专业技术综合实践');
});

test('normalizeTermResults accepts direct query results', () => {
  const rows = normalizeTermResults({
    results: [
      { term: { label: '2025-2026 第一学期' }, summary: { course_count: 1 }, grades: [] },
    ],
  }, 'grades');

  assert.equal(rows.length, 1);
  assert.equal(rows[0].title, '2025-2026 第一学期');
});
