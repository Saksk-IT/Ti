const assert = require('node:assert/strict');
const test = require('node:test');

const {
  buildCampusActions,
  buildCampusHighlights,
  buildCampusTerms,
  buildGradeMetrics,
  buildLatestGradeSummary,
  buildTodayScheduleSummary,
  campusFriendlyError,
  normalizeGradeSnapshots,
  normalizeScheduleSnapshots,
  normalizeTermResults,
} = require('../miniprogram/pages/campus/campus-content');
const {
  createCampusQueryPage,
  filterScheduleRowsByWeek,
  getScheduleStartDateStorageKey,
} = require('../miniprogram/pages/campus/campus-query-core');

function createPageHarness(config) {
  const definition = createCampusQueryPage(config);
  return {
    ...definition,
    data: { ...definition.data },
    setData(patch, callback) {
      this.data = { ...this.data, ...patch };
      if (callback) callback.call(this);
    },
  };
}

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

test('campusFriendlyError hides raw backend 404 text', () => {
  const message = campusFriendlyError(
    new Error('The requested URL was not found on the server. If you entered the URL manually please check your spelling and try again.'),
    '教务账号状态加载失败'
  );

  assert.equal(message, '教务接口暂不可用，请检查 API 地址或稍后重试');
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

test('buildGradeMetrics combines semester, cumulative and matching academic year values', () => {
  const rows = normalizeGradeSnapshots([
    {
      payload: {
        term: { xnm: '2025', xqm: '3', label: '2025-2026 第一学期' },
        summary: { course_count: 2, total_credits: 6, gpa: 3.67 },
        grades: [
          { course_name: '数据结构', score: '92', credits: '4.0', grade_point: '4.00' },
        ],
      },
    },
  ]);

  const metrics = buildGradeMetrics(
    rows,
    { display_gpa: 3.42 },
    [
      { xnm: '2024', weighted_average: 86.54 },
      { xnm: '2025', weighted_average: 88.16 },
    ]
  );

  assert.deepEqual(metrics, {
    semesterGpa: '3.67',
    allCoursesGpa: '3.42',
    academicYearWeightedAverage: '88.16',
    academicYear: '2025',
  });
});

test('buildGradeMetrics keeps zero values and falls back safely for old snapshots', () => {
  const currentRows = normalizeGradeSnapshots([
    {
      payload: {
        term: { xnm: '2025', xqm: '12', label: '2025-2026 第二学期' },
        summary: { course_count: 1, total_credits: 2, gpa: 0 },
        grades: [{ course_name: '待重修课程', score: '0', credits: '2', grade_point: '0' }],
      },
    },
  ]);

  assert.deepEqual(
    buildGradeMetrics(currentRows, { display_gpa: 0 }, [{ xnm: '2025', weighted_average: 0 }]),
    {
      semesterGpa: '0',
      allCoursesGpa: '0',
      academicYearWeightedAverage: '0',
      academicYear: '2025',
    }
  );
  assert.deepEqual(
    buildGradeMetrics(currentRows, null, [{ xnm: '2024', weighted_average: 91.25 }]),
    {
      semesterGpa: '0',
      allCoursesGpa: '-',
      academicYearWeightedAverage: '-',
      academicYear: '2025',
    }
  );
  const oldRows = normalizeGradeSnapshots([
    {
      payload: {
        term: { xnm: '2025', xqm: '3', label: '2025-2026 第一学期' },
        summary: { course_count: 1, total_credits: 2 },
        grades: [{ course_name: '旧快照课程', score: '80', credits: '2' }],
      },
    },
  ]);
  assert.equal(buildGradeMetrics(oldRows, null, []).semesterGpa, '-');
});

test('grade query page updates metrics from status and completed task payloads', () => {
  const page = createPageHarness({ mode: 'grades', pageTitle: '成绩查询' });
  page.applyEduStatus({
    credential: { has_credentials: true, username_hint: '20***01' },
    grade_snapshots: [
      {
        payload: {
          term: { xnm: '2024', xqm: '12', label: '2024-2025 第二学期' },
          summary: { course_count: 1, total_credits: 2, gpa: 3.25 },
          grades: [{ course_name: '数据库原理', score: '85', credits: '2', grade_point: '3.25' }],
        },
      },
    ],
    grade_overview: { display_gpa: 3.18 },
    academic_year_averages: [{ xnm: '2024', weighted_average: 84.5 }],
    recent_tasks: {},
  });

  assert.equal(page.data.gradeMetrics.semesterGpa, '3.25');
  assert.equal(page.data.gradeMetrics.allCoursesGpa, '3.18');
  assert.equal(page.data.gradeMetrics.academicYearWeightedAverage, '84.5');

  page.setData({ snapshotSelectedTermKey: '2025-3' });
  page.handleTaskState({
    task_id: 'grade-task-1',
    status: 'succeeded',
    message: '全部成绩已同步',
    results: [
      {
        term: { xnm: '2025', xqm: '3', label: '2025-2026 第一学期' },
        summary: { course_count: 1, total_credits: 3, gpa: 3.8 },
        grades: [{ course_name: '操作系统', score: '90', credits: '3', grade_point: '3.8' }],
      },
    ],
    grade_overview: { display_gpa: 3.44 },
    academic_year_averages: [{ xnm: '2025', weighted_average: 89.6 }],
    terms: [{ xnm: '2025', xqm: '3' }],
  }, { terms: [{ xnm: '2025', xqm: '3' }] }, 'grades', {});

  assert.equal(page.data.gradeMetrics.semesterGpa, '3.8');
  assert.equal(page.data.gradeMetrics.allCoursesGpa, '3.44');
  assert.equal(page.data.gradeMetrics.academicYearWeightedAverage, '89.6');
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

test('normalizeScheduleSnapshots keeps weekend courses with nonstandard sections', () => {
  const rows = normalizeScheduleSnapshots([
    {
      payload: {
        term: { xnm: '2023', xqm: '3', label: '2023-2024 第一学期' },
        week_table: {
          星期六: {
            '1-4节': [
              { course_name: '工程实训', teacher: '周老师', location: '实训楼', weeks: '1-8周', section: '1-4节' },
            ],
          },
          星期日: {
            '13-14节': [
              { course_name: '创新创业实践', teacher: '赵老师', location: '双创中心', weeks: '9-12周', section: '13-14节' },
            ],
          },
        },
      },
    },
  ]);

  assert.equal(rows.length, 1);
  assert.deepEqual(
    rows[0].weekRows.map((dayRow) => dayRow.day),
    ['星期六', '星期日']
  );
  assert.equal(rows[0].weekRows[0].sections[0].section, '1-4节');
  assert.equal(rows[0].weekRows[0].sections[0].courses[0].course_name, '工程实训');
  assert.equal(rows[0].weekRows[1].sections[0].section, '13-14节');
  assert.equal(rows[0].weekRows[1].sections[0].courses[0].course_name, '创新创业实践');
});

test('filterScheduleRowsByWeek keeps practice courses visible with the selected term', () => {
  const rows = [
    {
      title: '2023-2024 第一学期',
      weekRows: [
        {
          day: '星期一',
          sections: [
            {
              section: '1-2节',
              courses: [
                { course_name: '数据结构', weeks: '1-8周' },
              ],
            },
          ],
        },
      ],
      practice_courses: [
        { course_name: '专业技术综合实践', weeks: '16-18周' },
      ],
    },
  ];

  const filtered = filterScheduleRowsByWeek(rows, 1);

  assert.equal(filtered.length, 1);
  assert.equal(filtered[0].weekRows[0].sections[0].courses[0].course_name, '数据结构');
  assert.equal(filtered[0].practice_courses[0].course_name, '专业技术综合实践');
});

test('filterScheduleRowsByWeek keeps out-of-week courses and marks them inactive', () => {
  const rows = [
    {
      title: '2026-2027 第一学期',
      weekRows: [
        {
          day: '星期日',
          sections: [
            {
              section: '5-8节',
              courses: [
                { course_name: '形势与政策4', weeks: '10-11周' },
              ],
            },
          ],
        },
      ],
      practice_courses: [],
    },
  ];

  const weekOne = filterScheduleRowsByWeek(rows, 1);
  const weekTen = filterScheduleRowsByWeek(rows, 10);

  assert.equal(weekOne.length, 1);
  assert.equal(weekOne[0].weekRows[0].sections[0].courses[0].course_name, '形势与政策4');
  assert.equal(weekOne[0].weekRows[0].sections[0].courses[0].isCurrentWeek, false);
  assert.equal(weekTen[0].weekRows[0].sections[0].courses[0].isCurrentWeek, true);
});

test('schedule start date storage is isolated by academic year and semester', () => {
  assert.equal(
    getScheduleStartDateStorageKey('2023', '3'),
    'campus_schedule_start_date_v1_2023_3'
  );
  assert.equal(
    getScheduleStartDateStorageKey('2023', '12'),
    'campus_schedule_start_date_v1_2023_12'
  );
  assert.notEqual(
    getScheduleStartDateStorageKey('2023', '3'),
    getScheduleStartDateStorageKey('2023', '12')
  );
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

test('buildTodayScheduleSummary extracts courses for the current weekday', () => {
  const rows = normalizeScheduleSnapshots([
    {
      payload: {
        term: { xnm: '2025', xqm: '12', label: '2025-2026 第二学期' },
        week_table: {
          星期一: {
            '1-2节': [
              { course_name: 'WEB程序设计', teacher: '尹老师', location: '软件楼122', weeks: '1-15周' },
            ],
            '3-4节': [
              { course_name: '数据库原理', teacher: '任课教师B', location: '主楼302', weeks: '1-12周' },
            ],
          },
        },
      },
    },
  ]);

  const summary = buildTodayScheduleSummary(rows, new Date(2026, 5, 22));

  assert.equal(summary.title, '今天要上的课');
  assert.equal(summary.dayLabel, '星期一');
  assert.equal(summary.courseCount, 2);
  assert.equal(summary.hasCourses, true);
  assert.deepEqual(
    summary.courses.map((item) => item.course_name),
    ['WEB程序设计', '数据库原理']
  );
  assert.equal(summary.courses[0].detail, '尹老师 / 软件楼122 / 1-15周');
});

test('buildTodayScheduleSummary keeps a non-empty fallback when today has no courses', () => {
  const rows = normalizeScheduleSnapshots([
    {
      payload: {
        term: { xnm: '2025', xqm: '12', label: '2025-2026 第二学期' },
        week_table: {
          星期二: {
            '1-2节': [
              { course_name: '操作系统', teacher: '任课教师C', location: '主楼201', weeks: '1-15周' },
            ],
          },
        },
      },
    },
  ]);

  const summary = buildTodayScheduleSummary(rows, new Date(2026, 5, 22));

  assert.equal(summary.dayLabel, '星期一');
  assert.equal(summary.hasCourses, false);
  assert.equal(summary.courseCount, 0);
  assert.equal(summary.termTitle, '2025-2026 第二学期');
  assert.match(summary.emptyText, /刷新课表/);
});

test('buildLatestGradeSummary highlights latest term grades and GPA', () => {
  const rows = normalizeGradeSnapshots([
    {
      payload: {
        term: { xnm: '2024', xqm: '12', label: '2024-2025 第二学期' },
        summary: { course_count: 1, total_credits: 2, gpa: 3.1 },
        grades: [
          { course_name: '旧学期课程', score: '88', credits: '2.0', grade_point: '3.10' },
        ],
      },
    },
    {
      payload: {
        term: { xnm: '2025', xqm: '3', label: '2025-2026 第一学期' },
        summary: { course_count: 2, total_credits: 6, gpa: 3.67 },
        grades: [
          { course_name: '数据结构', score: '92', credits: '4.0', grade_point: '4.00' },
          { course_name: '创新实践', score: '良好', credits: '2.0', grade_point: '3.00' },
        ],
      },
    },
  ]);

  const summary = buildLatestGradeSummary(rows);

  assert.equal(summary.title, '最近一学期成绩');
  assert.equal(summary.termTitle, '2025-2026 第一学期');
  assert.equal(summary.courseCount, 2);
  assert.equal(summary.totalCredits, '6');
  assert.equal(summary.gpa, '3.67');
  assert.equal(summary.hasGrades, true);
  assert.deepEqual(
    summary.grades.map((item) => item.course_name),
    ['数据结构', '创新实践']
  );
});

test('campus actions and highlights stay useful without data', () => {
  const today = buildTodayScheduleSummary([], new Date(2026, 5, 22));
  const grades = buildLatestGradeSummary([]);
  const actions = buildCampusActions(false, false);
  const highlights = buildCampusHighlights(today, grades, false);

  assert.deepEqual(actions.map((item) => item.key), ['schedule', 'grades', 'binding', 'evaluation', 'more']);
  assert.equal(actions.find((item) => item.key === 'evaluation').disabled, true);
  assert.deepEqual(highlights.map((item) => item.value), ['0', '-', '待绑定']);
});
