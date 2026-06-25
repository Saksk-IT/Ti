import { api } from '../../utils/api';
import { checkLogin } from '../../utils/auth';
import { safeNavigate } from '../../utils/nav';
import { themeManager, ThemeMode } from '../../utils/theme';
import {
  buildCampusTerms,
  campusFriendlyError,
  CampusMode,
  CampusSemesterValue,
  normalizeGradeSnapshots,
  normalizeScheduleSnapshots,
  normalizeTermResults,
} from './campus-content';

const SEMESTER_LABELS = ['第一学期', '第二学期'];
const SEMESTER_VALUES: CampusSemesterValue[] = ['3', '12'];
const ACADEMIC_YEAR_PAST_COUNT = 6;
const ACADEMIC_YEAR_FUTURE_COUNT = 2;
const ACTIVE_TASK_STATUSES = ['pending', 'running', 'retrying', 'webvpn_refresh_required'];
const POLL_INTERVAL_MS = 2000;
const WEEK_COUNT = 25;
const SCHEDULE_VIEW_STORAGE_KEY = 'campus_schedule_view_mode_v1';
const SCHEDULE_START_DATE_STORAGE_KEY = 'campus_schedule_start_date_v1';
const SCHEDULE_VIEW_MODES = {
  list: '列表',
  table: '课程表',
};

interface AcademicYearOption {
  label: string;
  value: string;
}

interface SnapshotOption {
  label: string;
  value: string;
  count: number;
  active: boolean;
}

interface CampusProgressData {
  queryProgressVisible: boolean;
  queryProgressStatus: string;
  queryProgressPercent: number;
  queryProgressDetail: string;
  queryProgressMeta: string;
}

interface CampusQueryPageConfig {
  mode: CampusMode;
  pageTitle: string;
}

interface ScheduleTableCell {
  key: string;
  day: string;
  courses: any[];
  hasCourses: boolean;
}

interface ScheduleTableRow {
  key: string;
  section: string;
  cells: ScheduleTableCell[];
}

function defaultAcademicYear(): number {
  const now = new Date();
  const month = now.getMonth() + 1;
  return month >= 9 ? now.getFullYear() : now.getFullYear() - 1;
}

function defaultSemesterIndex(): number {
  const month = new Date().getMonth() + 1;
  return month >= 2 && month <= 8 ? 1 : 0;
}

function formatAcademicYearLabel(year: number): string {
  return `${year}~${year + 1}`;
}

function buildAcademicYearOptions(defaultYear: number): AcademicYearOption[] {
  const options: AcademicYearOption[] = [];
  for (let year = defaultYear - ACADEMIC_YEAR_PAST_COUNT; year <= defaultYear + ACADEMIC_YEAR_FUTURE_COUNT; year += 1) {
    options.push({ label: formatAcademicYearLabel(year), value: String(year) });
  }
  return options;
}

function clampAcademicYearIndex(value: unknown, fallback: number): number {
  const index = Number(value);
  if (!Number.isInteger(index)) return fallback;
  return Math.max(0, Math.min(index, ACADEMIC_YEAR_OPTIONS.length - 1));
}

function academicYearValueAt(index: number): string {
  return ACADEMIC_YEAR_OPTIONS[index]?.value || String(defaultYear);
}

function academicYearIndexForValue(value: unknown): number {
  const year = String(value || '').trim();
  const index = ACADEMIC_YEAR_OPTIONS.findIndex((item) => item.value === year);
  return index >= 0 ? index : DEFAULT_ACADEMIC_YEAR_INDEX;
}

function semesterIndexForValue(value: unknown): number {
  const semester = String(value || '').trim();
  const index = SEMESTER_VALUES.findIndex((item) => item === semester);
  return index >= 0 ? index : defaultSemesterIndex();
}

function selectedSemesterValue(index: number): CampusSemesterValue {
  return SEMESTER_VALUES[Math.max(0, Math.min(index, SEMESTER_VALUES.length - 1))] || '3';
}

function normalizeCredential(credential: any): { has_credentials: boolean; username_hint: string } {
  return {
    has_credentials: !!credential?.has_credentials,
    username_hint: String(credential?.username_hint || '').trim(),
  };
}

function ensureRuntimeState(self: any): any {
  if (!self.__campusTaskTimers) self.__campusTaskTimers = { schedule: null, grades: null };
  if (!self.__activeCampusTasks) self.__activeCampusTasks = { schedule: null, grades: null };
  if (!self.__lastCampusProgress) self.__lastCampusProgress = { schedule: null, grades: null };
  return self;
}

function isActiveTask(task: any): boolean {
  return !!task?.task_id && ACTIVE_TASK_STATUSES.indexOf(String(task.status || '')) !== -1;
}

function taskStatusLabel(status: string): string {
  if (status === 'pending') return '排队中';
  if (status === 'running') return '查询中';
  if (status === 'retrying') return '自动重试中';
  if (status === 'webvpn_refresh_required') return '等待验证码';
  if (status === 'succeeded') return '已完成';
  if (status === 'cancelled') return '已停止';
  if (status === 'failed') return '查询失败';
  return '查询中';
}

function taskProgressPercent(task: any): number {
  const status = String(task?.status || '');
  if (status === 'succeeded' || status === 'cancelled' || status === 'failed') return 100;
  if (status === 'webvpn_refresh_required') return 72;
  const attempt = Math.max(0, Number(task?.attempt || task?.attempt_count || 0) || 0);
  return Math.max(16, Math.min(92, 24 + attempt * 7));
}

function xqmLabel(value: unknown): string {
  const xqm = String(value || '').trim();
  if (xqm === '3') return '第一学期';
  if (xqm === '12') return '第二学期';
  return xqm ? `第${xqm}学期` : '未知学期';
}

function rowYearValue(row: any): string {
  return String(row?.xnm || '').trim();
}

function rowSemesterValue(row: any): string {
  return String(row?.xqm || '').trim();
}

function rowKey(row: any, index: number): string {
  return String(row?.termKey || [rowYearValue(row), rowSemesterValue(row)].filter(Boolean).join('-') || `${row?.title || 'term'}-${index}`);
}

function compareTermRows(a: any, b: any): number {
  const yearDiff = (Number(rowYearValue(b)) || 0) - (Number(rowYearValue(a)) || 0);
  if (yearDiff !== 0) return yearDiff;
  const order: { [key: string]: number } = { '12': 2, '3': 1 };
  return (order[rowSemesterValue(b)] || 0) - (order[rowSemesterValue(a)] || 0);
}

function mergeCampusRows(existing: any[], incoming: any[]): any[] {
  const byKey: { [key: string]: any } = {};
  (Array.isArray(existing) ? existing : []).forEach((row, index) => {
    byKey[rowKey(row, index)] = { ...row };
  });
  (Array.isArray(incoming) ? incoming : []).forEach((row, index) => {
    const key = rowKey(row, index);
    byKey[key] = byKey[key] ? { ...byKey[key], ...row } : { ...row };
  });
  return Object.keys(byKey).map((key) => byKey[key]).sort(compareTermRows);
}

function rowTermValue(row: any): string {
  const year = rowYearValue(row);
  const semester = rowSemesterValue(row);
  return year && semester ? `${year}-${semester}` : '';
}

function termLabel(year: string, semester: string): string {
  return `${formatAcademicYearLabel(Number(year))} ${xqmLabel(semester)}`;
}

function buildSnapshotTermOptions(rows: any[], selectedTermKey: string): SnapshotOption[] {
  const counts: { [key: string]: number } = {};
  rows.forEach((row) => {
    const value = rowTermValue(row);
    if (!value) return;
    counts[value] = (counts[value] || 0) + 1;
  });
  return Object.keys(counts)
    .sort((a, b) => {
      const [yearA, semesterA] = a.split('-');
      const [yearB, semesterB] = b.split('-');
      const yearDiff = (Number(yearB) || 0) - (Number(yearA) || 0);
      if (yearDiff !== 0) return yearDiff;
      const order: { [key: string]: number } = { '12': 2, '3': 1 };
      return (order[semesterB] || Number(semesterB) || 0) - (order[semesterA] || Number(semesterA) || 0);
    })
    .map((value) => {
      const [year, semester] = value.split('-');
      return {
        value,
        label: termLabel(year, semester),
        count: counts[value],
        active: value === selectedTermKey,
      };
    });
}

function buildSnapshotTermLabels(options: SnapshotOption[]): string[] {
  return options.map((item) => `${item.label}（${item.count}）`);
}

function filterSnapshotRows(rows: any[], selectedTermKey: string): any[] {
  return rows.filter((row) => rowTermValue(row) === selectedTermKey);
}

function formatTaskTerms(terms: any[]): string {
  const normalized = Array.isArray(terms) ? terms : [];
  if (!normalized.length) return '';
  return normalized
    .slice(0, 3)
    .map((term) => `${formatAcademicYearLabel(Number(term?.xnm) || 0)} ${xqmLabel(term?.xqm)}`)
    .join('、') + (normalized.length > 3 ? ` 等 ${normalized.length} 个学期` : '');
}

function formatTaskMeta(mode: CampusMode, terms: any[]): string {
  return formatTaskTerms(terms);
}

function buildSelectedTerm(yearInput: unknown, semesterIndexInput: unknown): Array<{ xnm: string; xqm: string }> {
  const year = Number(yearInput) || defaultYear;
  const xnm = Number.isInteger(year) && year >= 2000 && year <= 2100 ? year : defaultYear;
  const semester = selectedSemesterValue(Number(semesterIndexInput) || 0);
  return buildCampusTerms(String(xnm), String(xnm), semester);
}

function termKeyFromSelection(yearInput: unknown, semesterIndexInput: unknown): string {
  const year = String(yearInput || '').trim();
  const semester = selectedSemesterValue(Number(semesterIndexInput) || 0);
  return year && semester ? `${year}-${semester}` : '';
}

function termLabelFromSelection(yearInput: unknown, semesterIndexInput: unknown): string {
  const year = Number(yearInput) || defaultYear;
  return `${formatAcademicYearLabel(year)} ${xqmLabel(selectedSemesterValue(Number(semesterIndexInput) || 0))}`;
}

function termSelectionPatchFromKey(termKey: string): any {
  const [year, semester] = String(termKey || '').split('-');
  if (!year || !semester) return {};
  const academicYearIndex = academicYearIndexForValue(year);
  const semesterIndex = semesterIndexForValue(semester);
  const academicYear = academicYearValueAt(academicYearIndex);
  return {
    academicYearIndex,
    academicYear,
    semesterIndex,
    selectedTermLabel: termLabelFromSelection(academicYear, semesterIndex),
  };
}

function pad2(value: number): string {
  return value < 10 ? `0${value}` : String(value);
}

function formatDateValue(date: Date): string {
  return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}`;
}

function parseDateValue(value: unknown): Date {
  const text = String(value || '').trim();
  const matched = /^(\d{4})-(\d{2})-(\d{2})$/.exec(text);
  if (!matched) return new Date(defaultYear, 8, 1);
  const date = new Date(Number(matched[1]), Number(matched[2]) - 1, Number(matched[3]));
  return Number.isNaN(date.getTime()) ? new Date(defaultYear, 8, 1) : date;
}

function addDays(date: Date, days: number): Date {
  const next = new Date(date.getTime());
  next.setDate(next.getDate() + days);
  return next;
}

function displayDate(date: Date): string {
  return `${date.getMonth() + 1}月${date.getDate()}日`;
}

function defaultScheduleStartDate(yearInput: unknown): string {
  const year = Number(yearInput) || defaultYear;
  return formatDateValue(new Date(year, 8, 1));
}

function readStoredScheduleStartDate(yearInput: unknown): string {
  try {
    const stored = String(wx.getStorageSync(SCHEDULE_START_DATE_STORAGE_KEY) || '').trim();
    if (/^\d{4}-\d{2}-\d{2}$/.test(stored)) return stored;
  } catch (e) {}
  return defaultScheduleStartDate(yearInput);
}

function readStoredScheduleViewMode(): 'list' | 'table' {
  try {
    const mode = String(wx.getStorageSync(SCHEDULE_VIEW_STORAGE_KEY) || '').trim();
    if (mode === 'table') return 'table';
  } catch (e) {}
  return 'list';
}

function buildWeekLabels(): string[] {
  const labels: string[] = [];
  for (let week = 1; week <= WEEK_COUNT; week += 1) labels.push(`第 ${week} 周`);
  return labels;
}

function weekDateRangeText(startDateValue: unknown, weekInput: unknown): string {
  const week = Math.max(1, Math.min(Number(weekInput) || 1, WEEK_COUNT));
  const start = addDays(parseDateValue(startDateValue), (week - 1) * 7);
  const end = addDays(start, 6);
  return `${displayDate(start)} - ${displayDate(end)}`;
}

function parseCourseWeeks(value: unknown): { start: number; end: number; oddEven: '' | 'odd' | 'even' }[] {
  const text = String(value || '').trim();
  if (!text) return [];
  const normalized = text
    .replace(/[，、]/g, ',')
    .replace(/第/g, '')
    .replace(/周/g, '');
  const oddEven = /单/.test(text) ? 'odd' : (/双/.test(text) ? 'even' : '');
  const ranges: { start: number; end: number; oddEven: '' | 'odd' | 'even' }[] = [];
  normalized.split(',').forEach((part) => {
    const matched = /(\d+)(?:\s*[-~至]\s*(\d+))?/.exec(part);
    if (!matched) return;
    const start = Number(matched[1]);
    const end = Number(matched[2] || matched[1]);
    if (!Number.isFinite(start) || !Number.isFinite(end)) return;
    ranges.push({ start: Math.min(start, end), end: Math.max(start, end), oddEven });
  });
  return ranges;
}

function courseMatchesWeek(course: any, weekInput: unknown): boolean {
  const week = Math.max(1, Math.min(Number(weekInput) || 1, WEEK_COUNT));
  const ranges = parseCourseWeeks(course?.weeks);
  if (!ranges.length) return true;
  return ranges.some((range) => {
    if (week < range.start || week > range.end) return false;
    if (range.oddEven === 'odd') return week % 2 === 1;
    if (range.oddEven === 'even') return week % 2 === 0;
    return true;
  });
}

export function filterScheduleRowsByWeek(rows: any[], weekInput: unknown): any[] {
  return (Array.isArray(rows) ? rows : []).map((term) => {
    const weekRows = (Array.isArray(term.weekRows) ? term.weekRows : []).map((dayRow: any) => ({
      ...dayRow,
      sections: (Array.isArray(dayRow.sections) ? dayRow.sections : []).map((sectionRow: any) => ({
        ...sectionRow,
        courses: (Array.isArray(sectionRow.courses) ? sectionRow.courses : []).filter((course: any) => courseMatchesWeek(course, weekInput)),
      })).filter((sectionRow: any) => Array.isArray(sectionRow.courses) && sectionRow.courses.length),
    })).filter((dayRow: any) => Array.isArray(dayRow.sections) && dayRow.sections.length);
    const practiceCourses = Array.isArray(term.practice_courses) ? term.practice_courses.slice() : [];
    return { ...term, weekRows, practice_courses: practiceCourses };
  }).filter((term) => (term.weekRows || []).length || (term.practice_courses || []).length);
}

function buildScheduleTable(rows: any[], weekInput: unknown): { days: string[]; tableRows: ScheduleTableRow[] } {
  const firstTerm = (Array.isArray(rows) ? rows : [])[0] || {};
  const days = (Array.isArray(firstTerm.weekRows) ? firstTerm.weekRows : []).map((dayRow: any) => String(dayRow.day || '').trim()).filter(Boolean);
  const sectionMap: { [key: string]: { section: string; dayCourses: { [day: string]: any[] } } } = {};
  (firstTerm.weekRows || []).forEach((dayRow: any) => {
    const day = String(dayRow.day || '').trim();
    (dayRow.sections || []).forEach((sectionRow: any) => {
      const section = String(sectionRow.section || '').trim();
      if (!section) return;
      const current = sectionMap[section] || { section, dayCourses: {} };
      sectionMap[section] = {
        section,
        dayCourses: {
          ...current.dayCourses,
          [day]: (Array.isArray(sectionRow.courses) ? sectionRow.courses : []).filter((course: any) => courseMatchesWeek(course, weekInput)),
        },
      };
    });
  });
  const tableRows = Object.keys(sectionMap).map((section) => ({
    key: section,
    section,
    cells: days.map((day) => {
      const courses = sectionMap[section].dayCourses[day] || [];
      return { key: `${section}-${day}`, day, courses, hasCourses: courses.length > 0 };
    }),
  }));
  return { days, tableRows };
}

function taskRowsSource(task: any, data: any): any {
  const credential = data?.credential || task?.credential || {};
  if (Array.isArray(task?.results) && task.results.length) return { results: task.results, credential };
  if (Array.isArray(task?.snapshots) && task.snapshots.length) return { results: task.snapshots, credential };
  return data || {};
}

function emptyProgress(): CampusProgressData {
  return {
    queryProgressVisible: false,
    queryProgressStatus: '',
    queryProgressPercent: 0,
    queryProgressDetail: '',
    queryProgressMeta: '',
  };
}

const defaultYear = defaultAcademicYear();
const ACADEMIC_YEAR_OPTIONS = buildAcademicYearOptions(defaultYear);
const DEFAULT_ACADEMIC_YEAR_INDEX = ACADEMIC_YEAR_PAST_COUNT;
const DEFAULT_SEMESTER_INDEX = defaultSemesterIndex();
const WEEK_LABELS = buildWeekLabels();

export function createCampusQueryPage(config: CampusQueryPageConfig): any {
  const fixedMode = config.mode;
  const fixedPageTitle = config.pageTitle;
  const defaultAcademicYearValue = academicYearValueAt(DEFAULT_ACADEMIC_YEAR_INDEX);
  const defaultTermLabel = termLabelFromSelection(defaultAcademicYearValue, DEFAULT_SEMESTER_INDEX);

  return {
  data: {
    mode: fixedMode,
    queryPageKind: fixedMode,
    academicYearLabels: ACADEMIC_YEAR_OPTIONS.map((item) => item.label),
    academicYearIndex: DEFAULT_ACADEMIC_YEAR_INDEX,
    semesterLabels: SEMESTER_LABELS,
    semesterIndex: DEFAULT_SEMESTER_INDEX,
    academicYear: defaultAcademicYearValue,
    selectedTermLabel: defaultTermLabel,
    loading: false,
    statusLoading: false,
    statusReady: false,
    statusFailed: false,
    errorMsg: '',
    statusMsg: '',
    eduBound: false,
    eduUsernameHint: '',
    allScheduleResults: [] as any[],
    allGradeResults: [] as any[],
    scheduleResults: [] as any[],
    gradeResults: [] as any[],
    visibleScheduleResults: [] as any[],
    scheduleViewMode: 'list',
    scheduleViewModeLabel: SCHEDULE_VIEW_MODES.list,
    scheduleTableDays: [] as string[],
    scheduleTableRows: [] as ScheduleTableRow[],
    scheduleTermSheetVisible: false,
    scheduleTermSheetMode: 'switch',
    weekLabels: WEEK_LABELS,
    selectedWeekIndex: 0,
    selectedWeek: 1,
    weekStartDate: defaultScheduleStartDate(defaultAcademicYearValue),
    selectedWeekDateRange: weekDateRangeText(defaultScheduleStartDate(defaultAcademicYearValue), 1),
    isQueryPage: true,
    pageTitle: fixedPageTitle,
    snapshotTerms: [] as SnapshotOption[],
    snapshotTermLabels: [] as string[],
    snapshotTermIndex: 0,
    snapshotSelectedTermKey: '',
    snapshotDrawerOpen: false,
    queryProgressVisible: false,
    queryProgressStatus: '',
    queryProgressPercent: 0,
    queryProgressDetail: '',
    queryProgressMeta: '',
    captchaVisible: false,
    captchaMode: 'schedule' as CampusMode,
    captchaChallengeId: '',
    captchaImage: '',
    captchaCode: '',
    captchaMessage: '',
    captchaSubmitting: false,
  },

  onLoad() {
    const weekStartDate = fixedMode === 'schedule'
      ? readStoredScheduleStartDate(this.data.academicYear)
      : this.data.weekStartDate;
    const scheduleViewMode = fixedMode === 'schedule' ? readStoredScheduleViewMode() : 'list';
    this.setData({
      mode: fixedMode,
      queryPageKind: fixedMode,
      pageTitle: fixedPageTitle,
      scheduleViewMode,
      scheduleViewModeLabel: SCHEDULE_VIEW_MODES[scheduleViewMode],
      weekStartDate,
      selectedWeekDateRange: weekDateRangeText(weekStartDate, this.data.selectedWeek),
    }, () => this.rebuildScheduleDisplay());
  },

  onShow() {
    if (!checkLogin()) {
      wx.redirectTo({ url: '/pages/login/login' });
      return;
    }
    try {
      this.setData({ ...themeManager.getPageData() });
    } catch (e) {}
    this.loadEduStatus(false);
  },

  onUnload() {
    this.clearAllTaskPolling();
  },

  onRefresh() {
    Promise.resolve(this.loadEduStatus(true))
      .then(() => wx.stopPullDownRefresh())
      .catch(() => wx.stopPullDownRefresh());
  },

  onCycleThemeModeTap() {
    const mode = themeManager.cycleMode() as ThemeMode;
    this.setData({ ...(themeManager.getPageData()), themeMode: mode });
  },

  onAcademicYearChange(e: any) {
    const academicYearIndex = clampAcademicYearIndex(e?.detail?.value, this.data.academicYearIndex);
    const academicYear = academicYearValueAt(academicYearIndex);
    this.setData({
      academicYearIndex,
      academicYear,
      selectedTermLabel: termLabelFromSelection(academicYear, this.data.semesterIndex),
    });
  },

  onSemesterChange(e: any) {
    const value = Number(e?.detail?.value ?? 0);
    const max = SEMESTER_LABELS.length - 1;
    const semesterIndex = Math.max(0, Math.min(value, max));
    this.setData({
      semesterIndex,
      selectedTermLabel: termLabelFromSelection(this.data.academicYear, semesterIndex),
    });
  },

  onGoEduBindingTap() {
    safeNavigate('/pages/settings-account-bindings-v2/settings-account-bindings-v2', 'navigateTo');
  },

  applyEduStatus(data: any) {
    const credential = normalizeCredential(data?.credential);
    const allScheduleResults = normalizeScheduleSnapshots(data?.snapshots || []);
    const allGradeResults = normalizeGradeSnapshots(data?.grade_snapshots || []);
    this.setData({
      statusReady: true,
      statusFailed: false,
      eduBound: credential.has_credentials,
      eduUsernameHint: credential.username_hint,
      statusMsg: credential.has_credentials ? `已绑定教务系统账号：${credential.username_hint || '已保存'}` : '未绑定教务系统账号',
      allScheduleResults,
      allGradeResults,
    }, () => {
      this.syncSnapshotBrowserForMode(fixedMode);
      this.restoreRecentCampusTasks(data?.recent_tasks || {});
    });
  },

  async loadEduStatus(force = false) {
    const self: any = this as any;
    const now = Date.now();
    const lastAt = Number(self.__lastCampusStatusAt || 0) || 0;
    if (!force && now - lastAt < 8000) return;
    self.__lastCampusStatusAt = now;

    this.setData({ statusLoading: true, statusFailed: false, errorMsg: '' });
    try {
      const data: any = await api.getEduScheduleStatus();
      this.applyEduStatus(data || {});
    } catch (e: any) {
      const message = campusFriendlyError(e, '教务账号状态加载失败');
      this.setData({
        statusReady: true,
        statusFailed: true,
        eduBound: false,
        statusMsg: message,
        errorMsg: message,
      });
    } finally {
      this.setData({ statusLoading: false });
    }
  },

  showBindPrompt() {
    wx.showModal({
      title: '未绑定教务系统账号',
      content: '请先绑定教务系统账号后再查询课表和成绩。',
      confirmText: '去绑定',
      cancelText: '取消',
      success: (res) => {
        if (res.confirm) this.onGoEduBindingTap();
      },
    });
  },

  syncSnapshotBrowserForMode(modeInput?: CampusMode) {
    const mode = modeInput || fixedMode;
    const rows = mode === 'grades' ? this.data.allGradeResults : this.data.allScheduleResults;
    const terms = buildSnapshotTermOptions(rows, this.data.snapshotSelectedTermKey);
    const selectedTermKey = terms.some((item) => item.value === this.data.snapshotSelectedTermKey)
      ? this.data.snapshotSelectedTermKey
      : (terms[0]?.value || '');
    const selectedTerms = buildSnapshotTermOptions(rows, selectedTermKey);
    const selectedTermIndex = Math.max(0, selectedTerms.findIndex((item) => item.value === selectedTermKey));
    const patch: any = {
      snapshotSelectedTermKey: selectedTermKey,
      snapshotTerms: selectedTerms,
      snapshotTermLabels: buildSnapshotTermLabels(selectedTerms),
      snapshotTermIndex: selectedTermIndex,
      snapshotDrawerOpen: false,
    };
    patch[mode === 'grades' ? 'gradeResults' : 'scheduleResults'] = selectedTermKey
      ? filterSnapshotRows(rows, selectedTermKey)
      : [];
    this.setData({
      ...patch,
      ...(selectedTermKey ? termSelectionPatchFromKey(selectedTermKey) : {}),
    }, () => {
      if (mode === 'schedule') this.rebuildScheduleDisplay();
    });
  },

  onSnapshotTermTap(e: any) {
    const options = this.data.snapshotTerms || [];
    const value = String(e?.currentTarget?.dataset?.value || '').trim();
    const index = options.findIndex((item) => item.value === value);
    const selectedTermKey = String(options[index]?.value || '').trim();
    if (!selectedTermKey) return;
    this.setData({
      snapshotSelectedTermKey: selectedTermKey,
      snapshotTermIndex: index,
      snapshotDrawerOpen: false,
      ...termSelectionPatchFromKey(selectedTermKey),
    }, () => this.syncSnapshotBrowserForMode(fixedMode));
  },

  rebuildScheduleDisplay() {
    if (fixedMode !== 'schedule') return;
    const selectedWeek = Math.max(1, Math.min(Number(this.data.selectedWeek) || 1, WEEK_COUNT));
    const visibleScheduleResults = filterScheduleRowsByWeek(this.data.scheduleResults || [], selectedWeek);
    const table = buildScheduleTable(this.data.scheduleResults || [], selectedWeek);
    this.setData({
      visibleScheduleResults,
      scheduleTableDays: table.days,
      scheduleTableRows: table.tableRows,
      selectedWeek,
      selectedWeekDateRange: weekDateRangeText(this.data.weekStartDate, selectedWeek),
    });
  },

  onScheduleViewToggleTap() {
    if (fixedMode !== 'schedule') return;
    const scheduleViewMode = this.data.scheduleViewMode === 'table' ? 'list' : 'table';
    try {
      wx.setStorageSync(SCHEDULE_VIEW_STORAGE_KEY, scheduleViewMode);
    } catch (e) {}
    this.setData({
      scheduleViewMode,
      scheduleViewModeLabel: SCHEDULE_VIEW_MODES[scheduleViewMode],
    }, () => this.rebuildScheduleDisplay());
  },

  onWeekChange(e: any) {
    const value = Number(e?.detail?.value ?? 0);
    const selectedWeekIndex = Math.max(0, Math.min(value, WEEK_COUNT - 1));
    const selectedWeek = selectedWeekIndex + 1;
    this.setData({
      selectedWeekIndex,
      selectedWeek,
      selectedWeekDateRange: weekDateRangeText(this.data.weekStartDate, selectedWeek),
    }, () => this.rebuildScheduleDisplay());
  },

  onWeekStartDateChange(e: any) {
    const weekStartDate = String(e?.detail?.value || '').trim() || defaultScheduleStartDate(this.data.academicYear);
    try {
      wx.setStorageSync(SCHEDULE_START_DATE_STORAGE_KEY, weekStartDate);
    } catch (err) {}
    this.setData({
      weekStartDate,
      selectedWeekDateRange: weekDateRangeText(weekStartDate, this.data.selectedWeek),
    }, () => this.rebuildScheduleDisplay());
  },

  onOpenScheduleTermSheetTap() {
    if (fixedMode !== 'schedule') return;
    this.setData({ scheduleTermSheetVisible: true, scheduleTermSheetMode: 'switch' });
  },

  onOpenScheduleQuerySheetTap() {
    if (fixedMode !== 'schedule') return;
    this.setData({ scheduleTermSheetVisible: true, scheduleTermSheetMode: 'query' });
  },

  onCloseScheduleTermSheetTap() {
    this.setData({ scheduleTermSheetVisible: false });
  },

  onScheduleTermSheetConfirmTap() {
    if (this.data.scheduleTermSheetMode === 'query') {
      this.setData({ scheduleTermSheetVisible: false }, () => this.executeCampusQuery());
      return;
    }
    const selectedTermKey = termKeyFromSelection(this.data.academicYear, this.data.semesterIndex);
    const options = this.data.snapshotTerms || [];
    const index = options.findIndex((item) => item.value === selectedTermKey);
    if (index < 0) {
      wx.showToast({ title: '暂无该学期课表记录', icon: 'none' });
      this.setData({ scheduleTermSheetVisible: false });
      return;
    }
    this.setData({
      scheduleTermSheetVisible: false,
      snapshotSelectedTermKey: selectedTermKey,
      snapshotTermIndex: index,
    }, () => this.syncSnapshotBrowserForMode('schedule'));
  },

  applyQueryRows(data: any, mode: CampusMode, statusMsg = '') {
    const rows = normalizeTermResults(data || {}, mode);
    const sourceKey = mode === 'grades' ? 'allGradeResults' : 'allScheduleResults';
    const patch: any = {};
    const mergedRows = mergeCampusRows(this.data[sourceKey] || [], rows);
    const credential = data?.credential ? normalizeCredential(data.credential) : null;
    patch[sourceKey] = mergedRows;
    if (statusMsg) patch.statusMsg = statusMsg;
    if (credential) {
      patch.eduBound = credential.has_credentials;
      patch.eduUsernameHint = credential.username_hint;
    }
    this.setData(patch, () => {
      if (fixedMode === mode) this.syncSnapshotBrowserForMode(mode);
    });
    return rows;
  },

  getActiveCampusTask(mode: CampusMode) {
    const self = ensureRuntimeState(this as any);
    return self.__activeCampusTasks[mode];
  },

  setActiveCampusTask(mode: CampusMode, task: any) {
    const self = ensureRuntimeState(this as any);
    self.__activeCampusTasks[mode] = task || null;
  },

  setProgressForTask(task: any, mode: CampusMode) {
    const status = String(task?.status || 'running');
    const progress: CampusProgressData = {
      queryProgressVisible: true,
      queryProgressStatus: taskStatusLabel(status),
      queryProgressPercent: taskProgressPercent(task),
      queryProgressDetail: String(task?.message || (mode === 'grades' ? '正在刷新全部成绩' : '正在后台查询课表')),
      queryProgressMeta: formatTaskMeta(mode, Array.isArray(task?.terms) ? task.terms : []),
    };
    const self = ensureRuntimeState(this as any);
    self.__lastCampusProgress[mode] = progress;
    if (this.data.mode === mode) this.setData(progress as any);
  },

  refreshProgressForMode(mode: CampusMode) {
    const self = ensureRuntimeState(this as any);
    const progress = self.__lastCampusProgress[mode] || emptyProgress();
    this.setData(progress as any);
  },

  clearTaskPolling(mode: CampusMode) {
    const self = ensureRuntimeState(this as any);
    const timer = self.__campusTaskTimers[mode];
    if (timer) clearTimeout(timer);
    self.__campusTaskTimers[mode] = null;
  },

  clearAllTaskPolling() {
    this.clearTaskPolling('schedule');
    this.clearTaskPolling('grades');
  },

  startTaskPolling(taskId: string, mode: CampusMode, payload: any) {
    this.clearTaskPolling(mode);
    const poll = async () => {
      try {
        const data: any = await api.getEduQueryTask(taskId);
        const task = data?.task;
        const finished = this.handleTaskState(task, payload, mode, data || {});
        if (!finished) {
          const self = ensureRuntimeState(this as any);
          self.__campusTaskTimers[mode] = setTimeout(poll, POLL_INTERVAL_MS);
        }
      } catch (e: any) {
        this.clearTaskPolling(mode);
        this.setActiveCampusTask(mode, null);
        if (this.data.mode === mode) {
          this.setData({ errorMsg: campusFriendlyError(e, '查询任务状态获取失败') });
        }
      }
    };
    poll();
  },

  handleTaskState(task: any, payload: any, mode: CampusMode, data: any = {}) {
    if (!task) throw new Error('查询任务状态不正确');
    const status = String(task.status || '');
    this.setProgressForTask(task, mode);
    if (isActiveTask(task)) {
      this.setActiveCampusTask(mode, task);
    } else {
      this.setActiveCampusTask(mode, null);
      this.clearTaskPolling(mode);
    }

    const rows = this.applyQueryRows(taskRowsSource(task, data), mode);
    if (status === 'cancelled') {
      if (this.data.mode === mode) this.setData({ statusMsg: task.message || '查询已停止' });
      return true;
    }
    if (status === 'webvpn_refresh_required') {
      this.clearTaskPolling(mode);
      this.showWebvpnCaptcha(task, payload, mode);
      return true;
    }
    if (status === 'succeeded') {
      if (this.data.mode === mode) this.setData({ statusMsg: mode === 'grades' ? '全部成绩已同步' : '课表查询完成' });
      return true;
    }
    if (status === 'failed') {
      const message = task.message || '教务系统繁忙，请稍后重试';
      if (this.data.mode === mode) this.setData({ statusMsg: message, errorMsg: rows.length ? '' : message });
      return true;
    }

    const suffix = rows.length ? '，当前显示上次成功结果' : '';
    if (this.data.mode === mode) this.setData({ statusMsg: `${task.message || '正在后台查询教务系统'}${suffix}` });
    return false;
  },

  restoreRecentCampusTasks(recentTasks: any) {
    const task = recentTasks?.[fixedMode];
    if (isActiveTask(task)) {
      const payload = { terms: Array.isArray(task.terms) ? task.terms : [] };
      const finished = this.handleTaskState(task, payload, fixedMode, { task });
      if (!finished) this.startTaskPolling(String(task.task_id), fixedMode, payload);
      return;
    }
    this.refreshProgressForMode(fixedMode);
  },

  confirmReplacingActiveTask(mode: CampusMode): Promise<boolean> {
    const label = mode === 'grades' ? '成绩' : '课表';
    return new Promise((resolve) => {
      wx.showModal({
        title: '停止上次查询？',
        content: mode === 'grades'
          ? '发起本次刷新会停止上次的成绩刷新，确定继续吗？'
          : `发起本次查询会停止上次的${label}查询，确定继续吗？`,
        confirmText: '继续',
        cancelText: '取消',
        success: (res) => resolve(!!res.confirm),
        fail: () => resolve(false),
      });
    });
  },

  async cancelActiveQueryTask(mode: CampusMode) {
    const task = this.getActiveCampusTask(mode);
    if (!task?.task_id) return;
    this.clearTaskPolling(mode);
    try {
      const data: any = await api.cancelEduQueryTask(String(task.task_id));
      this.handleTaskState(data?.task || { ...task, status: 'cancelled', message: '查询已停止' }, { terms: task.terms || [] }, mode, data || {});
    } catch (e: any) {
      if (this.data.mode === mode) this.setData({ errorMsg: campusFriendlyError(e, '停止上次查询失败') });
    } finally {
      this.setActiveCampusTask(mode, null);
      if (this.data.captchaMode === mode) this.hideWebvpnCaptcha();
    }
  },

  async submitCampusQuery(mode: CampusMode, payload: any) {
    this.setData({
      loading: true,
      errorMsg: '',
      statusMsg: mode === 'grades' ? '全部成绩刷新已提交，正在连接教务系统...' : '课表查询已提交，正在连接教务系统...',
    });
    try {
      const data: any = mode === 'grades'
        ? await api.queryEduGrades(payload)
        : await api.queryEduSchedule(payload);
      const task = data?.task;
      if (task?.task_id) {
        const finished = this.handleTaskState(task, payload, mode, data || {});
        if (!finished) this.startTaskPolling(String(task.task_id), mode, payload);
        return;
      }
      this.applyQueryRows(data || {}, mode, mode === 'grades' ? '全部成绩已同步' : '课表查询完成');
      this.setProgressForTask({ status: 'succeeded', message: mode === 'grades' ? '全部成绩已同步' : '查询完成', terms: payload.terms }, mode);
    } catch (e: any) {
      this.setData({ errorMsg: campusFriendlyError(e, '查询失败，请稍后重试') });
    } finally {
      this.setData({ loading: false });
    }
  },

  showWebvpnCaptcha(task: any, payload: any, mode: CampusMode) {
    const self = ensureRuntimeState(this as any);
    const challenge = task?.challenge || {};
    self.__pendingCampusCaptcha = { payload, mode };
    this.setData({
      captchaVisible: true,
      captchaMode: mode,
      captchaChallengeId: String(challenge.challenge_id || ''),
      captchaImage: String(challenge.captcha_image || ''),
      captchaCode: '',
      captchaMessage: task?.message || 'WebVPN 登录态失效，请输入验证码后继续查询。',
      captchaSubmitting: false,
    });
  },

  hideWebvpnCaptcha() {
    const self = ensureRuntimeState(this as any);
    self.__pendingCampusCaptcha = null;
    this.setData({
      captchaVisible: false,
      captchaChallengeId: '',
      captchaImage: '',
      captchaCode: '',
      captchaMessage: '',
      captchaSubmitting: false,
    });
  },

  onCaptchaInput(e: any) {
    this.setData({ captchaCode: String(e?.detail?.value || '').trim() });
  },

  onCaptchaCancelTap() {
    this.hideWebvpnCaptcha();
  },

  async onCaptchaSubmitTap() {
    const challengeId = String(this.data.captchaChallengeId || '').trim();
    const captchaCode = String(this.data.captchaCode || '').trim();
    if (!challengeId || !captchaCode) {
      this.setData({ captchaMessage: '请输入验证码' });
      return;
    }
    const self = ensureRuntimeState(this as any);
    const pending = self.__pendingCampusCaptcha || { mode: this.data.captchaMode, payload: null };
    this.setData({ captchaSubmitting: true, errorMsg: '' });
    try {
      await api.completeEduWebvpnSession(challengeId, captchaCode);
      this.setActiveCampusTask(pending.mode, null);
      this.hideWebvpnCaptcha();
      if (pending.payload) await this.submitCampusQuery(pending.mode, pending.payload);
    } catch (e: any) {
      this.setData({
        captchaSubmitting: false,
        captchaMessage: campusFriendlyError(e, '刷新 WebVPN 登录态失败，请重新输入验证码'),
      });
    }
  },

  async executeCampusQuery() {
    if (this.data.loading) return;
    if (this.data.statusLoading || !this.data.statusReady) {
      this.setData({ errorMsg: '教务系统账号状态同步中，请稍后再试' });
      return;
    }
    if (this.data.statusFailed) {
      const message = '教务接口暂不可用，请检查 API 地址或稍后重试';
      this.setData({ statusMsg: message, errorMsg: message });
      return;
    }
    if (!this.data.eduBound) {
      this.showBindPrompt();
      return;
    }

    const mode = fixedMode;
    let terms;
    try {
      terms = buildSelectedTerm(this.data.academicYear, this.data.semesterIndex);
    } catch (e: any) {
      this.setData({ errorMsg: e?.message || '学年或学期不正确' });
      return;
    }

    if (isActiveTask(this.getActiveCampusTask(mode))) {
      const confirmed = await this.confirmReplacingActiveTask(mode);
      if (!confirmed) return;
      await this.cancelActiveQueryTask(mode);
    }
    await this.submitCampusQuery(mode, { terms });
  },

  async onQueryTap() {
    if (fixedMode === 'schedule') {
      this.onOpenScheduleQuerySheetTap();
      return;
    }
    await this.executeCampusQuery();
  },
  };
}
