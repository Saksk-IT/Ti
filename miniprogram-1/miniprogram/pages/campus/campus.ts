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

interface AcademicYearOption {
  label: string;
  value: string;
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

const defaultYear = defaultAcademicYear();
const ACADEMIC_YEAR_OPTIONS = buildAcademicYearOptions(defaultYear);
const DEFAULT_ACADEMIC_YEAR_INDEX = ACADEMIC_YEAR_PAST_COUNT;

Page({
  data: {
    mode: 'schedule' as CampusMode,
    modeLabels: ['查询课表', '查询成绩'],
    academicYearLabels: ACADEMIC_YEAR_OPTIONS.map((item) => item.label),
    startYearIndex: DEFAULT_ACADEMIC_YEAR_INDEX,
    endYearIndex: DEFAULT_ACADEMIC_YEAR_INDEX,
    semesterLabels: SEMESTER_LABELS,
    semesterIndex: 0,
    startYear: academicYearValueAt(DEFAULT_ACADEMIC_YEAR_INDEX),
    endYear: academicYearValueAt(DEFAULT_ACADEMIC_YEAR_INDEX),
    loading: false,
    statusLoading: false,
    statusReady: false,
    statusFailed: false,
    errorMsg: '',
    statusMsg: '',
    eduBound: false,
    eduUsernameHint: '',
    scheduleResults: [] as any[],
    gradeResults: [] as any[],
  },

  onShow() {
    if (!checkLogin()) {
      wx.redirectTo({ url: '/pages/login/login' });
      return;
    }
    try {
      this.setData(themeManager.getPageData());
    } catch (e) {}
    this.loadEduStatus(false);
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

  onModeTap(e: any) {
    const mode = String(e?.currentTarget?.dataset?.mode || '') as CampusMode;
    if (mode !== 'schedule' && mode !== 'grades') return;
    this.setData({ mode, errorMsg: '' });
  },

  onStartYearChange(e: any) {
    const startYearIndex = clampAcademicYearIndex(e?.detail?.value, this.data.startYearIndex);
    const startYear = academicYearValueAt(startYearIndex);
    const endYearIndex = Number(this.data.endYear) < Number(startYear) ? startYearIndex : this.data.endYearIndex;
    this.setData({
      startYearIndex,
      startYear,
      endYearIndex,
      endYear: academicYearValueAt(endYearIndex),
    });
  },

  onEndYearChange(e: any) {
    const endYearIndex = clampAcademicYearIndex(e?.detail?.value, this.data.endYearIndex);
    this.setData({
      endYearIndex,
      endYear: academicYearValueAt(endYearIndex),
    });
  },

  onSemesterChange(e: any) {
    const value = Number(e?.detail?.value ?? 0);
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
      scheduleResults: normalizeScheduleSnapshots(data?.snapshots || []),
      gradeResults: normalizeGradeSnapshots(data?.grade_snapshots || []),
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

    let terms;
    try {
      const semester = SEMESTER_VALUES[this.data.semesterIndex] || 'all';
      terms = buildCampusTerms(this.data.startYear, this.data.endYear, semester);
    } catch (e: any) {
      this.setData({ errorMsg: e?.message || '学年或学期不正确' });
      return;
    }

    const mode = this.data.mode as CampusMode;
    this.setData({
      loading: true,
      errorMsg: '',
      statusMsg: mode === 'grades' ? '正在查询成绩...' : '正在查询课表...',
    });
    try {
      const payload = { terms };
      const data: any = mode === 'grades'
        ? await api.queryEduGrades(payload)
        : await api.queryEduSchedule(payload);
      const rows = normalizeTermResults(data || {}, mode);
      if (mode === 'grades') {
        this.setData({ gradeResults: rows, statusMsg: '成绩查询完成' });
      } else {
        this.setData({ scheduleResults: rows, statusMsg: '课表查询完成' });
      }
      if (data?.credential) {
        const credential = normalizeCredential(data.credential);
        this.setData({
          eduBound: credential.has_credentials,
          eduUsernameHint: credential.username_hint,
        });
      }
    } catch (e: any) {
      this.setData({ errorMsg: campusFriendlyError(e, '查询失败，请稍后重试') });
    } finally {
      this.setData({ loading: false });
    }
  },
});
