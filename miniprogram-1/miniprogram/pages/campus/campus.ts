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

const SEMESTER_LABELS = ['第一、二学期', '第一学期', '第二学期'];
const SEMESTER_VALUES: CampusSemesterValue[] = ['all', '3', '12'];
const ACADEMIC_YEAR_PAST_COUNT = 6;
const ACADEMIC_YEAR_FUTURE_COUNT = 2;
const ACTIVE_TASK_STATUSES = ['pending', 'running', 'retrying', 'webvpn_refresh_required'];
const POLL_INTERVAL_MS = 2000;
const CAMPUS_PREFERRED_MODE_KEY = 'campus_preferred_mode_v1';

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

function defaultAcademicYear(): number {
  const now = new Date();
  const month = now.getMonth() + 1;
  return month >= 9 ? now.getFullYear() : now.getFullYear() - 1;
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
  const next = (Array.isArray(existing) ? existing : []).slice();
  (Array.isArray(incoming) ? incoming : []).forEach((row, index) => {
    const key = rowKey(row, index);
    const found = next.findIndex((item, itemIndex) => rowKey(item, itemIndex) === key);
    if (found >= 0) {
      next.splice(found, 1, { ...next[found], ...row });
    } else {
      next.push({ ...row });
    }
  });
  return next.sort(compareTermRows);
}

function buildSnapshotYearOptions(rows: any[], selectedYear: string): SnapshotOption[] {
  const counts: { [key: string]: number } = {};
  rows.forEach((row) => {
    const year = rowYearValue(row);
    if (!year) return;
    counts[year] = (counts[year] || 0) + 1;
  });
  return Object.keys(counts)
    .sort((a, b) => (Number(b) || 0) - (Number(a) || 0))
    .map((year) => ({
      value: year,
      label: formatAcademicYearLabel(Number(year)),
      count: counts[year],
      active: year === selectedYear,
    }));
}

function buildSnapshotOptionLabels(options: SnapshotOption[]): string[] {
  return options.map((item) => `${item.label}（${item.count}）`);
}

function buildSnapshotTermOptions(rows: any[], selectedYear: string, selectedSemester: string): SnapshotOption[] {
  const counts: { [key: string]: number } = {};
  rows.forEach((row) => {
    if (rowYearValue(row) !== selectedYear) return;
    const semester = rowSemesterValue(row);
    if (!semester) return;
    counts[semester] = (counts[semester] || 0) + 1;
  });
  const terms = Object.keys(counts).sort((a, b) => {
    const order: { [key: string]: number } = { '12': 2, '3': 1 };
    return (order[b] || Number(b) || 0) - (order[a] || Number(a) || 0);
  });
  const total = terms.reduce((sum, semester) => sum + counts[semester], 0);
  return [
    { value: 'all', label: '全部学期', count: total, active: selectedSemester === 'all' },
    ...terms.map((semester) => ({
      value: semester,
      label: xqmLabel(semester),
      count: counts[semester],
      active: semester === selectedSemester,
    })),
  ];
}

function filterSnapshotRows(rows: any[], selectedYear: string, selectedSemester: string): any[] {
  return rows.filter((row) => {
    if (selectedYear && rowYearValue(row) !== selectedYear) return false;
    if (selectedSemester !== 'all' && rowSemesterValue(row) !== selectedSemester) return false;
    return true;
  });
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
  if (mode === 'grades') return '全部成绩';
  return formatTaskTerms(terms);
}

function buildGradeQueryTerms(yearInput: unknown): Array<{ xnm: string; xqm: string }> {
  const year = Number(yearInput) || defaultYear;
  const xnm = Number.isInteger(year) && year >= 2000 && year <= 2100 ? year : defaultYear;
  return [{ xnm: String(xnm), xqm: '3' }];
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

Page({
  data: {
    mode: 'schedule' as CampusMode,
    modeLabels: ['查询课表', '查询成绩'],
    academicYearLabels: ACADEMIC_YEAR_OPTIONS.map((item) => item.label),
    academicYearIndex: DEFAULT_ACADEMIC_YEAR_INDEX,
    semesterLabels: SEMESTER_LABELS,
    semesterIndex: 0,
    academicYear: academicYearValueAt(DEFAULT_ACADEMIC_YEAR_INDEX),
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
    snapshotYears: [] as SnapshotOption[],
    snapshotYearLabels: [] as string[],
    snapshotYearIndex: 0,
    snapshotTerms: [] as SnapshotOption[],
    snapshotSemesterLabels: [] as string[],
    snapshotSemesterIndex: 0,
    snapshotSelectedYear: '',
    snapshotSelectedSemester: 'all',
    snapshotDrawerOpen: false,
    snapshotDrawerTitle: '',
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

  onShow() {
    if (!checkLogin()) {
      wx.redirectTo({ url: '/pages/login/login' });
      return;
    }
    const preferredMode = this.consumePreferredMode();
    try {
      this.setData({
        ...themeManager.getPageData(),
        ...(preferredMode ? { mode: preferredMode, errorMsg: '', snapshotDrawerOpen: false } : {}),
      }, () => {
        if (preferredMode) {
          this.syncSnapshotBrowserForMode(preferredMode);
          this.refreshProgressForMode(preferredMode);
        }
      });
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

  consumePreferredMode(): CampusMode | '' {
    try {
      const mode = String(wx.getStorageSync(CAMPUS_PREFERRED_MODE_KEY) || '').trim();
      wx.removeStorageSync(CAMPUS_PREFERRED_MODE_KEY);
      if (mode === 'schedule' || mode === 'grades') return mode;
    } catch (e) {}
    return '';
  },

  onModeTap(e: any) {
    const mode = String(e?.currentTarget?.dataset?.mode || '') as CampusMode;
    if (mode !== 'schedule' && mode !== 'grades') return;
    this.setData({ mode, errorMsg: '', snapshotDrawerOpen: false }, () => {
      this.syncSnapshotBrowserForMode(mode);
      this.refreshProgressForMode(mode);
    });
  },

  onAcademicYearTap(e: any) {
    const academicYearIndex = clampAcademicYearIndex(e?.currentTarget?.dataset?.index, this.data.academicYearIndex);
    this.setData({
      academicYearIndex,
      academicYear: academicYearValueAt(academicYearIndex),
    });
  },

  onSemesterTap(e: any) {
    const value = Number(e?.currentTarget?.dataset?.index ?? 0);
    const max = SEMESTER_LABELS.length - 1;
    const semesterIndex = Math.max(0, Math.min(value, max));
    this.setData({ semesterIndex });
  },

  onGoEduBindingTap() {
    safeNavigate('/pages/settings-account-bindings-v2/settings-account-bindings-v2', 'navigateTo');
  },

  onHeroActionTap() {
    if (this.data.statusFailed) {
      this.loadEduStatus(true);
      return;
    }
    this.onGoEduBindingTap();
  },

  applyEduStatus(data: any) {
    const credential = normalizeCredential(data?.credential);
    this.setData({
      statusReady: true,
      statusFailed: false,
      eduBound: credential.has_credentials,
      eduUsernameHint: credential.username_hint,
      statusMsg: credential.has_credentials ? `已绑定教务系统账号：${credential.username_hint || '已保存'}` : '未绑定教务系统账号',
      allScheduleResults: normalizeScheduleSnapshots(data?.snapshots || []),
      allGradeResults: normalizeGradeSnapshots(data?.grade_snapshots || []),
    }, () => {
      this.syncSnapshotBrowserForMode(this.data.mode as CampusMode);
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
    const mode = modeInput || this.data.mode as CampusMode;
    const rows = mode === 'grades' ? this.data.allGradeResults : this.data.allScheduleResults;
    const years = buildSnapshotYearOptions(rows, this.data.snapshotSelectedYear);
    const selectedYear = years.some((item) => item.value === this.data.snapshotSelectedYear)
      ? this.data.snapshotSelectedYear
      : (years[0]?.value || '');
    const terms = selectedYear ? buildSnapshotTermOptions(rows, selectedYear, this.data.snapshotSelectedSemester) : [];
    const selectedSemester = terms.some((item) => item.value === this.data.snapshotSelectedSemester)
      ? this.data.snapshotSelectedSemester
      : 'all';
    const selectedYears = buildSnapshotYearOptions(rows, selectedYear);
    const selectedYearIndex = Math.max(0, selectedYears.findIndex((item) => item.value === selectedYear));
    const selectedTerms = selectedYear ? buildSnapshotTermOptions(rows, selectedYear, selectedSemester) : [];
    const selectedSemesterIndex = Math.max(0, selectedTerms.findIndex((item) => item.value === selectedSemester));
    const patch: any = {
      snapshotSelectedYear: selectedYear,
      snapshotSelectedSemester: selectedSemester,
      snapshotYears: selectedYears,
      snapshotYearLabels: buildSnapshotOptionLabels(selectedYears),
      snapshotYearIndex: selectedYearIndex,
      snapshotTerms: selectedTerms,
      snapshotSemesterLabels: buildSnapshotOptionLabels(selectedTerms),
      snapshotSemesterIndex: selectedSemesterIndex,
      snapshotDrawerTitle: selectedYear ? `${formatAcademicYearLabel(Number(selectedYear))} 学期` : '',
      snapshotDrawerOpen: false,
    };
    patch[mode === 'grades' ? 'gradeResults' : 'scheduleResults'] = selectedYear
      ? filterSnapshotRows(rows, selectedYear, selectedSemester)
      : [];
    this.setData(patch);
  },

  onSnapshotYearTap(e: any) {
    const options = this.data.snapshotYears || [];
    const value = String(e?.currentTarget?.dataset?.value || '').trim();
    const index = options.findIndex((item) => item.value === value);
    const year = String(options[index]?.value || '').trim();
    if (!year) return;
    this.setData({
      snapshotSelectedYear: year,
      snapshotSelectedSemester: 'all',
      snapshotDrawerOpen: false,
      snapshotYearIndex: index,
      snapshotSemesterIndex: 0,
    }, () => this.syncSnapshotBrowserForMode(this.data.mode as CampusMode));
  },

  onSnapshotTermTap(e: any) {
    const options = this.data.snapshotTerms || [];
    const value = String(e?.currentTarget?.dataset?.value || '').trim();
    const index = options.findIndex((item) => item.value === value);
    const semester = String(options[index]?.value || 'all').trim() || 'all';
    this.setData({
      snapshotSelectedSemester: semester,
      snapshotSemesterIndex: index,
      snapshotDrawerOpen: false,
    }, () => this.syncSnapshotBrowserForMode(this.data.mode as CampusMode));
  },

  applyQueryRows(data: any, mode: CampusMode, statusMsg = '') {
    const rows = normalizeTermResults(data || {}, mode);
    const sourceKey = mode === 'grades' ? 'allGradeResults' : 'allScheduleResults';
    const patch: any = {};
    patch[sourceKey] = mergeCampusRows(this.data[sourceKey] || [], rows);
    if (statusMsg) patch.statusMsg = statusMsg;
    this.setData(patch, () => {
      if (this.data.mode === mode) this.syncSnapshotBrowserForMode(mode);
    });
    if (data?.credential) {
      const credential = normalizeCredential(data.credential);
      this.setData({
        eduBound: credential.has_credentials,
        eduUsernameHint: credential.username_hint,
      });
    }
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
    const pairs: Array<{ mode: CampusMode; task: any }> = [
      { mode: 'schedule', task: recentTasks?.schedule },
      { mode: 'grades', task: recentTasks?.grades },
    ];
    let restoredCurrent = false;
    pairs.forEach(({ mode, task }) => {
      if (!isActiveTask(task)) return;
      const payload = { terms: Array.isArray(task.terms) ? task.terms : [] };
      const finished = this.handleTaskState(task, payload, mode, { task });
      if (!finished) this.startTaskPolling(String(task.task_id), mode, payload);
      if (mode === this.data.mode) restoredCurrent = true;
    });
    if (!restoredCurrent) this.refreshProgressForMode(this.data.mode as CampusMode);
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

  async onQueryTap() {
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

    const mode = this.data.mode as CampusMode;
    let terms;
    try {
      if (mode === 'grades') {
        terms = buildGradeQueryTerms(this.data.academicYear);
      } else {
        const semester = SEMESTER_VALUES[this.data.semesterIndex] || 'all';
        terms = buildCampusTerms(this.data.academicYear, this.data.academicYear, semester);
      }
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
});
