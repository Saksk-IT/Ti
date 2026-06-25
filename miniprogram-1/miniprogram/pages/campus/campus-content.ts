export type CampusMode = 'schedule' | 'grades';
export type CampusSemesterValue = 'all' | '3' | '12';
export type CampusActionKey = 'schedule' | 'grades' | 'binding' | 'evaluation' | 'more';

export interface CampusTerm {
  xnm: string;
  xqm: string;
}

export interface CampusTodayCourse {
  key: string;
  section: string;
  course_name: string;
  teacher: string;
  location: string;
  weeks: string;
  detail: string;
}

export interface CampusTodaySummary {
  title: string;
  subtitle: string;
  dayLabel: string;
  termTitle: string;
  emptyText: string;
  courseCount: number;
  hasCourses: boolean;
  courses: CampusTodayCourse[];
}

export interface CampusLatestGradeSummary {
  title: string;
  subtitle: string;
  termTitle: string;
  summaryText: string;
  emptyText: string;
  courseCount: number;
  totalCredits: string;
  gpa: string;
  hasGrades: boolean;
  grades: any[];
}

export interface CampusActionItem {
  key: CampusActionKey;
  title: string;
  subtitle: string;
  icon: string;
  tone: 'primary' | 'normal' | 'muted';
  disabled: boolean;
}

export interface CampusHighlightItem {
  key: string;
  label: string;
  value: string;
  hint: string;
}

const DAY_NAMES = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日'];
const DATE_DAY_NAMES = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六'];
const SECTION_NAMES = ['1-2节', '3-4节', '5-6节', '7-8节', '9-10节', '11-12节'];
const SEMESTER_ORDER: { [key: string]: number } = { '3': 1, '12': 2, '16': 3 };

function toInteger(value: unknown): number {
  const num = Number(value);
  return Number.isInteger(num) ? num : NaN;
}

function cleanText(value: unknown, fallback = ''): string {
  const text = String(value || '').trim();
  return text || fallback;
}

export function campusFriendlyError(error: unknown, fallback: string): string {
  const source = error && typeof error === 'object' && 'message' in error
    ? (error as { message?: unknown }).message
    : error;
  const message = cleanText(source, fallback);
  const lower = message.toLowerCase();
  if (
    lower.includes('requested url was not found')
    || lower.includes('not found on the server')
    || lower.includes('请求失败: 404')
    || lower === '404'
  ) {
    return '教务接口暂不可用，请检查 API 地址或稍后重试';
  }
  return message;
}

function normalizeList(value: unknown): any[] {
  return Array.isArray(value) ? value : [];
}

function unwrapPayload(row: any): any {
  if (row && typeof row === 'object' && row.payload && typeof row.payload === 'object') {
    return row.payload;
  }
  return row && typeof row === 'object' ? row : {};
}

function trimNumberText(value: unknown): string {
  const text = cleanText(value, '0');
  if (!text.includes('.')) return text;
  return text.replace(/\.0+$/, '').replace(/(\.\d*?)0+$/, '$1');
}

function termYearValue(row: any): number {
  const year = Number(row?.xnm || 0);
  return Number.isFinite(year) ? year : 0;
}

function termSemesterRank(row: any): number {
  const xqm = cleanText(row?.xqm);
  return SEMESTER_ORDER[xqm] || Number(xqm) || 0;
}

function compareTermDesc(a: any, b: any): number {
  const yearDiff = termYearValue(b) - termYearValue(a);
  if (yearDiff !== 0) return yearDiff;
  return termSemesterRank(b) - termSemesterRank(a);
}

function firstMeaningfulRow(rows: any[]): any {
  const candidates = normalizeList(rows)
    .filter((row) => row && typeof row === 'object')
    .slice()
    .sort(compareTermDesc);
  return candidates[0] || null;
}

function courseDetail(course: any): string {
  const teacher = cleanText(course?.teacher, '-');
  const location = cleanText(course?.location, '-');
  const weeks = cleanText(course?.weeks, '-');
  return `${teacher} / ${location} / ${weeks}`;
}

function gradeTermFallback(row: any): string {
  const title = cleanText(row?.title);
  if (title) return title;
  const xnm = cleanText(row?.xnm);
  const xqm = semesterLabelFromValue(row?.xqm);
  if (xnm && /^\d+$/.test(xnm)) return `${xnm}~${Number(xnm) + 1}${xqm ? ` ${xqm}` : ''}`;
  return xqm || '最近成绩';
}

function semesterLabelFromValue(value: unknown): string {
  const xqm = cleanText(value);
  if (xqm === '3') return '第一学期';
  if (xqm === '12') return '第二学期';
  return xqm ? `第${xqm}学期` : '';
}

function normalizeTermMeta(termInput: any, fallbackTitle: string): any {
  const term = termInput && typeof termInput === 'object' ? termInput : {};
  const xnm = cleanText(term.xnm || term.XNM);
  const xqm = cleanText(term.xqm || term.XQM);
  const yearLabel = xnm && /^\d+$/.test(xnm) ? `${xnm}~${Number(xnm) + 1}` : cleanText(term.year_label);
  const semesterLabel = cleanText(term.semester_label) || semesterLabelFromValue(xqm);
  const title = cleanText(term.label, [yearLabel, semesterLabel].filter(Boolean).join(' ') || fallbackTitle);
  return {
    xnm,
    xqm,
    termKey: [xnm, xqm].filter(Boolean).join('-') || title,
    yearLabel,
    semesterLabel,
    title,
  };
}

function normalizeCourse(row: any): any {
  const item = row && typeof row === 'object' ? row : {};
  return {
    course_name: cleanText(item.course_name, '-'),
    teacher: cleanText(item.teacher, ''),
    location: cleanText(item.location, ''),
    weeks: cleanText(item.weeks, ''),
    assessment: cleanText(item.assessment, ''),
    credits: cleanText(item.credits, ''),
    section: cleanText(item.section, ''),
  };
}

function normalizeGrade(row: any): any {
  const item = row && typeof row === 'object' ? row : {};
  return {
    course_name: cleanText(item.course_name, '-'),
    course_code: cleanText(item.course_code, ''),
    score: cleanText(item.score, '-'),
    credits: cleanText(item.credits, '-'),
    grade_point: cleanText(item.grade_point, '-'),
    credit_grade_point: cleanText(item.credit_grade_point, ''),
    assessment: cleanText(item.assessment, ''),
    exam_type: cleanText(item.exam_type, ''),
    teacher: cleanText(item.teacher, ''),
  };
}

export function buildCampusTerms(
  startYearInput: unknown,
  endYearInput: unknown,
  semesterInput: CampusSemesterValue | string
): CampusTerm[] {
  const startYear = toInteger(startYearInput);
  const endYear = toInteger(endYearInput);
  if (!Number.isInteger(startYear) || !Number.isInteger(endYear)) {
    throw new Error('学年范围不正确');
  }
  if (startYear < 2000 || endYear > 2100 || startYear > endYear) {
    throw new Error('学年范围不正确');
  }

  const semester = String(semesterInput || 'all') as CampusSemesterValue;
  const xqmValues = semester === 'all' ? ['3', '12'] : [semester];
  if (!xqmValues.every((item) => item === '3' || item === '12')) {
    throw new Error('学期参数不正确');
  }

  const terms: CampusTerm[] = [];
  for (let year = startYear; year <= endYear; year += 1) {
    xqmValues.forEach((xqm) => {
      terms.push({ xnm: String(year), xqm });
    });
  }
  if (terms.length > 12) {
    throw new Error('一次最多查询 12 个学期');
  }
  return terms;
}

export function normalizeScheduleSnapshots(rows: unknown[]): any[] {
  return normalizeList(rows)
    .map((row) => {
      const payload = unwrapPayload(row);
      const term = payload.term && typeof payload.term === 'object' ? payload.term : {};
      const termMeta = normalizeTermMeta(term, '课表');
      const student = payload.student && typeof payload.student === 'object' ? payload.student : {};
      const weekTable = payload.week_table && typeof payload.week_table === 'object' ? payload.week_table : {};

      const weekRows = DAY_NAMES.map((day) => {
        const dayTable = weekTable[day] && typeof weekTable[day] === 'object' ? weekTable[day] : {};
        const sections = SECTION_NAMES.map((section) => ({
          section,
          courses: normalizeList(dayTable[section]).map(normalizeCourse),
        })).filter((section) => section.courses.length > 0);
        return { day, sections };
      }).filter((dayRow) => dayRow.sections.length > 0);

      return {
        ...termMeta,
        studentText: [student.name, student.class_name, student.major_name].map((item) => cleanText(item)).filter(Boolean).join(' / '),
        weekRows,
        practice_courses: normalizeList(payload.practice_courses).map(normalizeCourse),
      };
    })
    .filter((item) => item.weekRows.length > 0 || item.practice_courses.length > 0 || item.title !== '课表');
}

export function normalizeGradeSnapshots(rows: unknown[]): any[] {
  return normalizeList(rows)
    .map((row) => {
      const payload = unwrapPayload(row);
      const term = payload.term && typeof payload.term === 'object' ? payload.term : {};
      const termMeta = normalizeTermMeta(term, '成绩');
      const summary = payload.summary && typeof payload.summary === 'object' ? payload.summary : {};
      const courseCount = trimNumberText(summary.course_count);
      const credits = trimNumberText(summary.total_credits);
      const gpa = trimNumberText(summary.gpa);
      return {
        ...termMeta,
        summaryText: `${courseCount} 门课 / ${credits} 学分 / GPA ${gpa}`,
        courseCount,
        totalCredits: credits,
        gpa,
        grades: normalizeList(payload.grades).map(normalizeGrade),
      };
    })
    .filter((item) => item.grades.length > 0 || item.title !== '成绩');
}

export function normalizeTermResults(input: any, mode: CampusMode): any[] {
  const payload = input && typeof input === 'object' ? input : {};
  const rows = Array.isArray(payload.results) ? payload.results : normalizeList(input);
  return mode === 'grades' ? normalizeGradeSnapshots(rows) : normalizeScheduleSnapshots(rows);
}

export function buildTodayScheduleSummary(rows: unknown[], dateInput: Date = new Date()): CampusTodaySummary {
  const dayLabel = DATE_DAY_NAMES[dateInput.getDay()] || '今天';
  const scheduleRows = normalizeList(rows)
    .filter((row) => row && typeof row === 'object')
    .slice()
    .sort(compareTermDesc);
  const matched = scheduleRows
    .map((row) => {
      const dayRow = normalizeList(row.weekRows).find((item) => cleanText(item?.day) === dayLabel);
      return dayRow ? { row, dayRow } : null;
    })
    .find(Boolean) as { row: any; dayRow: any } | null;

  const courses: CampusTodayCourse[] = [];
  if (matched) {
    normalizeList(matched.dayRow.sections).forEach((sectionRow) => {
      normalizeList(sectionRow?.courses).forEach((course, index) => {
        const section = cleanText(sectionRow?.section, cleanText(course?.section, '-'));
        const name = cleanText(course?.course_name, '未命名课程');
        courses.push({
          key: `${matched.row.termKey || matched.row.title || 'today'}-${section}-${name}-${index}`,
          section,
          course_name: name,
          teacher: cleanText(course?.teacher, ''),
          location: cleanText(course?.location, ''),
          weeks: cleanText(course?.weeks, ''),
          detail: courseDetail(course),
        });
      });
    });
  }

  const fallbackRow = matched?.row || firstMeaningfulRow(scheduleRows);
  const termTitle = cleanText(fallbackRow?.title, '最近课表');
  return {
    title: '今天要上的课',
    subtitle: courses.length ? `${dayLabel} · ${termTitle}` : `${dayLabel} · 暂无匹配课程`,
    dayLabel,
    termTitle,
    emptyText: '最近课表暂无今天课程，刷新课表后会自动展示。',
    courseCount: courses.length,
    hasCourses: courses.length > 0,
    courses: courses.slice(0, 4),
  };
}

export function buildLatestGradeSummary(rows: unknown[]): CampusLatestGradeSummary {
  const gradeRows = normalizeList(rows)
    .filter((row) => row && typeof row === 'object')
    .slice()
    .sort(compareTermDesc);
  const latest = gradeRows.find((row) => normalizeList(row.grades).length > 0) || gradeRows[0] || null;
  if (!latest) {
    return {
      title: '最近一学期成绩',
      subtitle: '暂无成绩快照',
      termTitle: '暂无成绩',
      summaryText: '刷新成绩后展示课程、学分与 GPA',
      emptyText: '还没有成绩记录，点击成绩查询同步最近一学期信息。',
      courseCount: 0,
      totalCredits: '-',
      gpa: '-',
      hasGrades: false,
      grades: [],
    };
  }

  const grades = normalizeList(latest.grades);
  const courseCount = cleanText(latest.courseCount, String(grades.length || 0));
  const totalCredits = cleanText(latest.totalCredits, '-');
  const gpa = cleanText(latest.gpa, '-');
  return {
    title: '最近一学期成绩',
    subtitle: gradeTermFallback(latest),
    termTitle: gradeTermFallback(latest),
    summaryText: cleanText(latest.summaryText, `${courseCount} 门课 / ${totalCredits} 学分 / GPA ${gpa}`),
    emptyText: '该学期暂无成绩明细，刷新成绩后会自动补全。',
    courseCount: Number(courseCount) || grades.length,
    totalCredits,
    gpa,
    hasGrades: grades.length > 0,
    grades: grades.slice(0, 3),
  };
}

export function buildCampusActions(eduBound: boolean, statusFailed: boolean): CampusActionItem[] {
  return [
    {
      key: 'schedule',
      title: '课表查询',
      subtitle: eduBound ? '刷新学期课表' : '绑定后查询课表',
      icon: '/images/icons/book-open.svg',
      tone: 'primary',
      disabled: statusFailed,
    },
    {
      key: 'grades',
      title: '成绩查询',
      subtitle: eduBound ? '同步成绩与 GPA' : '绑定后同步成绩',
      icon: '/images/icons/chart.svg',
      tone: 'normal',
      disabled: statusFailed,
    },
    {
      key: 'binding',
      title: '教务绑定',
      subtitle: eduBound ? '更换或删除账号' : '先绑定教务账号',
      icon: '/images/icons/settings.svg',
      tone: 'normal',
      disabled: false,
    },
    {
      key: 'evaluation',
      title: '一键教评',
      subtitle: '功能建设中',
      icon: '/images/icons/clipboard-check.svg',
      tone: 'muted',
      disabled: true,
    },
    {
      key: 'more',
      title: '更多校园',
      subtitle: '考试安排等后续接入',
      icon: '/images/icons/list.svg',
      tone: 'muted',
      disabled: true,
    },
  ];
}

export function buildCampusHighlights(
  today: CampusTodaySummary,
  latestGrade: CampusLatestGradeSummary,
  eduBound: boolean
): CampusHighlightItem[] {
  return [
    {
      key: 'today',
      label: '今日课程',
      value: String(today.courseCount),
      hint: today.hasCourses ? today.dayLabel : '待刷新',
    },
    {
      key: 'grade',
      label: '最新 GPA',
      value: latestGrade.gpa || '-',
      hint: latestGrade.hasGrades ? latestGrade.termTitle : '待同步',
    },
    {
      key: 'binding',
      label: '教务账号',
      value: eduBound ? '已绑定' : '待绑定',
      hint: eduBound ? '可直接查询' : '先完成绑定',
    },
  ];
}
