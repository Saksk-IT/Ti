export type CampusMode = 'schedule' | 'grades';
export type CampusSemesterValue = 'all' | '3' | '12';

export interface CampusTerm {
  xnm: string;
  xqm: string;
}

const DAY_NAMES = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日'];
const SECTION_NAMES = ['1-2节', '3-4节', '5-6节', '7-8节', '9-10节', '11-12节'];

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
