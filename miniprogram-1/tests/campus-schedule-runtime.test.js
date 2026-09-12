const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
const test = require('node:test');
const ts = require(process.env.TYPESCRIPT_PATH || 'typescript');

// Exercise TypeScript as well as checked-in JavaScript: WeChat compiles the TS source.
function loadTypeScript(filename) {
  const compiled = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES5 },
  });
  const loaded = new Module(filename, module);
  loaded.filename = filename;
  loaded.paths = module.paths;
  const localRequire = Module.createRequire(filename);
  loaded.require = (id) => id === './campus-content'
    ? loadTypeScript(path.join(path.dirname(filename), 'campus-content.ts'))
    : localRequire(id);
  loaded._compile(compiled.outputText, filename);
  return loaded.exports;
}

const corePath = path.resolve(__dirname, '../miniprogram/pages/campus/campus-query-core');
const runtimes = {
  TypeScript: loadTypeScript(`${corePath}.ts`),
  JavaScript: require(corePath),
};

if (process.env.SCHEDULE_LIVE_USER_ID) {
  test('live upstream terms render distinct course content in the TypeScript page', () => {
    const { execFileSync } = require('node:child_process');
    const raw = execFileSync('docker', ['exec', '-e', 'PYTHONPATH=/app', 'ti-local-demo-web-1',
      'python', 'scripts/diagnose_schedule_query.py', '--user-id', process.env.SCHEDULE_LIVE_USER_ID,
      '--frontend-payload'], { encoding: 'utf8', timeout: 120000 });
    const liveSnapshots = JSON.parse(raw);
    const definition = runtimes.TypeScript.createCampusQueryPage({ mode: 'schedule', pageTitle: 'Schedule' });
    const page = { ...definition, data: { ...definition.data }, setData(patch, callback) {
      Object.assign(this.data, patch);
      if (callback) callback.call(this);
    } };
    page.applyEduStatus({ credential: { has_credentials: true }, snapshots: liveSnapshots });
    for (const { payload } of liveSnapshots) {
      const termKey = `${payload.term.xnm}-${payload.term.xqm}`;
      page.onSnapshotTermTap({ currentTarget: { dataset: { value: termKey } } });
      const expected = Object.values(payload.week_table).flatMap((day) => Object.values(day).flat()).map((course) => course.course_name).sort();
      const rendered = page.data.scheduleTableRows.flatMap((row) => row.cells.flatMap((cell) => cell.courses)).map((course) => course.course_name).sort();
      assert.deepEqual([...new Set(rendered)], [...new Set(expected)], termKey);
      const listCourses = page.data.visibleScheduleResults[0].weekRows.flatMap((day) => day.sections.flatMap((section) => section.courses)).map((course) => course.course_name).sort();
      assert.deepEqual(listCourses, expected, termKey);
      assert.deepEqual(page.data.visibleScheduleResults[0].practice_courses.map((course) => course.course_name), payload.practice_courses.map((course) => course.course_name));
      console.log(`${termKey}: rendered ${rendered.length} course rows`);
    }
  });
}

const snapshots = [
  { payload: { term: { xnm: '2026', xqm: '3' },
    week_table: { 星期日: { '5-8节': [{ course_name: 'Current course' }] } },
    practice_courses: [{ course_name: 'Current practice' }] } },
  { payload: { term: { xnm: '2025', xqm: '12' },
    week_table: {
      星期一: { '1-2节': [{ course_name: 'Historical A' }], '9-10节': [{ course_name: 'Historical B' }] },
      星期二: { '5-6节': [{ course_name: 'Historical C' }], '3-4节': [{ course_name: 'Historical D' }], '7-8节': [{ course_name: 'Historical E' }] },
    }, practice_courses: [{ course_name: 'Historical practice' }] } },
  { payload: { term: { xnm: '2026', xqm: '12' }, week_table: {}, practice_courses: [] } },
];

for (const [runtime, { createCampusQueryPage }] of Object.entries(runtimes)) {
  test(`${runtime}: overlapping sections share chronological two-period rows without losing courses`, () => {
    const definition = createCampusQueryPage({ mode: 'schedule', pageTitle: 'Schedule' });
    const page = { ...definition, data: { ...definition.data }, setData(patch, callback) {
      Object.assign(this.data, patch);
      if (callback) callback.call(this);
    } };
    const course = (course_name, section, weeks = '1-16周') => ({ course_name, section, weeks });
    page.applyEduStatus({ credential: { has_credentials: true }, snapshots: [{ payload: {
      term: { xnm: '2024', xqm: '3' }, week_table: {
        星期一: {
          '9-10节': [course('Last', '9-10节')],
          '1-4节': [course('Long morning', '1-4节', '2-16周')],
          '1-2节': [course('Short morning', '1-2节')],
        },
        星期二: { '5-8节': [course('Long afternoon', '5-8节')], '3-4节': [course('Second', '3-4节')] },
      },
    } }] });
    const rows = page.data.scheduleTableRows;
    assert.deepEqual(rows.map((row) => row.section), ['1-2节', '3-4节', '5-6节', '7-8节', '9-10节']);
    assert.deepEqual(rows[0].cells[0].courses.map((c) => c.course_name).sort(), ['Long morning', 'Short morning']);
    assert.equal(rows[1].cells[0].courses[0].course_name, 'Long morning');
    assert.equal(rows[0].cells[0].courses.find((c) => c.course_name === 'Long morning').isCurrentWeek, false);
    assert.equal(rows[1].cells[0].courses[0].tableSection, '1-4节');
    assert.equal(rows[2].cells[1].courses[0].course_name, 'Long afternoon');
    assert.equal(rows[3].cells[1].courses[0].course_name, 'Long afternoon');
    const listCourses = page.data.visibleScheduleResults[0].weekRows.flatMap((day) => day.sections.flatMap((section) => section.courses));
    assert.equal(listCourses.filter((c) => c.course_name === 'Long morning').length, 1);
    assert.equal(listCourses.find((c) => c.course_name === 'Long morning').section, '1-4节');
  });

  test(`${runtime}: switching from a single-section term refreshes all historical sections and practice`, () => {
    const definition = createCampusQueryPage({ mode: 'schedule', pageTitle: 'Schedule' });
    const page = { ...definition, data: { ...definition.data }, setData(patch, callback) {
      Object.assign(this.data, patch);
      if (callback) callback.call(this);
    } };
    page.applyEduStatus({ credential: { has_credentials: true }, snapshots });
    assert.equal(page.data.snapshotTerms.length, 2);
    assert.equal(page.data.scheduleTableRows[0].cells[0].courses[0].course_name, 'Current course');
    page.onSnapshotTermTap({ currentTarget: { dataset: { value: '2025-12' } } });
    assert.deepEqual(page.data.scheduleTableRows.map((row) => row.section), ['1-2节', '3-4节', '5-6节', '7-8节', '9-10节']);
    assert.equal(page.data.visibleScheduleResults[0].practice_courses[0].course_name, 'Historical practice');
    assert.equal(page.data.visibleScheduleResults[0].termKey, '2025-12');
    page.onSnapshotTermTap({ currentTarget: { dataset: { value: '2026-3' } } });
    assert.equal(page.data.scheduleTableRows[0].cells[0].courses[0].course_name, 'Current course');
    assert.equal(page.data.visibleScheduleResults[0].practice_courses[0].course_name, 'Current practice');
  });
}
