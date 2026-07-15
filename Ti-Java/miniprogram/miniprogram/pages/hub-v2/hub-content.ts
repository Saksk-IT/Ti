import {
  buildLatestGradeSummary as buildCampusLatestGradeSummary,
  buildTodayScheduleSummary,
  CampusTodayCourse,
  normalizeGradeSnapshots,
  normalizeScheduleSnapshots,
} from '../campus/campus-content';

export interface HubStats {
  answered: number;
  accuracy: number;
  favorites: number;
  mistakes: number;
}

export interface HubWeaknessItem {
  subject?: string;
  q_type?: string;
  answered?: number;
  accuracy?: number;
}

export interface HubLastPractice {
  has_practice?: boolean;
  subject_id?: number | string | null;
  subject_name?: string | null;
  source_type?: string;
  source_id?: string | number;
  display_name?: string;
  last_at_display?: string;
  mode?: string;
}

export interface StudyAdviceItem {
  key: string;
  title: string;
  subtitle: string;
  action: string;
  target: 'login' | 'continue' | 'weakness' | 'review' | 'favorites' | 'publicBank';
  icon: string;
}

export interface RecentBankItem {
  key: string;
  title: string;
  meta: string;
  source_type: string;
  source_id: string | number;
  target: string;
  mode: string;
}

export interface WeaknessEmptyAction {
  key: string;
  title: string;
  subtitle: string;
  action: string;
  target: 'login' | 'publicBank' | 'review';
}

export type CampusSummaryTone = 'ok' | 'warn' | 'muted';

export interface CampusSummary {
  title: string;
  subtitle: string;
  statusLabel: string;
  statusTone: CampusSummaryTone;
  scheduleCount: number;
  gradeCount: number;
  hasTodayCourses: boolean;
  todayCourseCount: number;
  todayCourseSubtitle: string;
  todayCourseEmptyText: string;
  todayCourses: CampusTodayCourse[];
  hasGradeSummary: boolean;
  latestGradeTerm: string;
  latestGradeCourseCount: number;
  latestGradeCredits: string;
  latestGradeGpa: string;
  primaryAction: string;
  secondaryAction: string;
}

type HubStatsPayload = {
  all_summary?: Record<string, unknown>;
  answered_count?: unknown;
  answered?: unknown;
  accuracy?: unknown;
  favorites_count?: unknown;
  favorites?: unknown;
  mistakes_count?: unknown;
  mistakes?: unknown;
};

const DEFAULT_RECENT_LIMIT = 3;
const DEFAULT_ADVICE_LIMIT = 3;

function toNumber(value: unknown): number {
  const num = Number(value || 0);
  return Number.isFinite(num) ? num : 0;
}

function cleanText(value: unknown, fallback: string): string {
  const text = String(value || '').trim();
  return text || fallback;
}

export function normalizeHubStats(payload: HubStatsPayload | null | undefined): HubStats {
  const data = payload && typeof payload === 'object' ? payload : {};
  const allSummary = data.all_summary && typeof data.all_summary === 'object' ? data.all_summary : null;
  return {
    answered: toNumber(allSummary ? allSummary.answered : (data.answered_count || data.answered)),
    accuracy: toNumber(allSummary ? allSummary.accuracy : data.accuracy),
    favorites: toNumber(allSummary ? allSummary.favorites : (data.favorites_count || data.favorites)),
    mistakes: toNumber(allSummary ? allSummary.mistakes : (data.mistakes_count || data.mistakes)),
  };
}

function buildCampusOverview(payload: Record<string, unknown>, dateInput: Date): Pick<
  CampusSummary,
  | 'scheduleCount'
  | 'gradeCount'
  | 'hasTodayCourses'
  | 'todayCourseCount'
  | 'todayCourseSubtitle'
  | 'todayCourseEmptyText'
  | 'todayCourses'
  | 'hasGradeSummary'
  | 'latestGradeTerm'
  | 'latestGradeCourseCount'
  | 'latestGradeCredits'
  | 'latestGradeGpa'
> {
  const scheduleRows = normalizeScheduleSnapshots(Array.isArray(payload.snapshots) ? payload.snapshots : []);
  const gradeRows = normalizeGradeSnapshots(Array.isArray(payload.grade_snapshots) ? payload.grade_snapshots : []);
  const today = buildTodayScheduleSummary(scheduleRows, dateInput);
  const latestGrade = buildCampusLatestGradeSummary(gradeRows);

  return {
    scheduleCount: scheduleRows.length,
    gradeCount: gradeRows.length,
    hasTodayCourses: today.hasCourses,
    todayCourseCount: today.courseCount,
    todayCourseSubtitle: today.subtitle,
    todayCourseEmptyText: today.emptyText,
    todayCourses: today.courses,
    hasGradeSummary: latestGrade.hasGrades,
    latestGradeTerm: latestGrade.termTitle,
    latestGradeCourseCount: latestGrade.courseCount,
    latestGradeCredits: latestGrade.totalCredits,
    latestGradeGpa: latestGrade.gpa,
  };
}

function emptyCampusOverview(): ReturnType<typeof buildCampusOverview> {
  return {
    scheduleCount: 0,
    gradeCount: 0,
    hasTodayCourses: false,
    todayCourseCount: 0,
    todayCourseSubtitle: '登录后同步课表',
    todayCourseEmptyText: '登录并绑定教务系统账号后，首页会展示今日课程。',
    todayCourses: [],
    hasGradeSummary: false,
    latestGradeTerm: '暂无成绩',
    latestGradeCourseCount: 0,
    latestGradeCredits: '-',
    latestGradeGpa: '-',
  };
}

export function buildCampusSummary(payload: unknown, isLoggedIn: boolean, dateInput: Date = new Date()): CampusSummary {
  const data = payload && typeof payload === 'object' ? payload as Record<string, unknown> : {};
  const overview = isLoggedIn ? buildCampusOverview(data, dateInput) : emptyCampusOverview();

  if (!isLoggedIn) {
    return {
      title: '校园服务',
      subtitle: '登录后绑定教务系统账号，查询课表和成绩',
      statusLabel: '登录后使用',
      statusTone: 'muted',
      ...overview,
      primaryAction: '去登录',
      secondaryAction: '进校园'
    };
  }

  if (data.error) {
    return {
      title: '校园服务',
      subtitle: '校园状态暂时无法同步，仍可进入校园页查看',
      statusLabel: '同步失败',
      statusTone: 'warn',
      ...overview,
      primaryAction: '进入校园',
      secondaryAction: '稍后重试'
    };
  }

  const credential = data.credential && typeof data.credential === 'object'
    ? data.credential as Record<string, unknown>
    : {};
  const hasCredentials = !!credential.has_credentials;
  const usernameHint = cleanText(credential.username_hint, '已保存');

  if (hasCredentials) {
    return {
      title: '校园服务',
      subtitle: `已绑定 ${usernameHint}，可直接查询课表和成绩`,
      statusLabel: '已绑定',
      statusTone: 'ok',
      ...overview,
      primaryAction: '查课表',
      secondaryAction: '查成绩'
    };
  }

  return {
    title: '校园服务',
    subtitle: '绑定教务系统账号后，可在校园页查询课表和成绩',
    statusLabel: '待绑定',
    statusTone: 'warn',
    ...overview,
    primaryAction: '去绑定',
    secondaryAction: '进校园'
  };
}

export function buildStudyAdvice(
  stats: HubStats,
  weakness: HubWeaknessItem[],
  lastPractice: HubLastPractice,
  isLoggedIn: boolean
): StudyAdviceItem[] {
  const safeStats: Partial<HubStats> = stats || {};
  const safeWeakness = Array.isArray(weakness) ? weakness : [];
  const safeLastPractice: Partial<HubLastPractice> = lastPractice || {};
  const advice: StudyAdviceItem[] = [];

  if (!isLoggedIn) {
    advice.push({
      key: 'login',
      title: '登录同步学习进度',
      subtitle: '收藏、错题和练习记录会自动保存',
      action: '去登录',
      target: 'login',
      icon: 'user'
    });
  } else if (safeLastPractice.has_practice) {
    advice.push({
      key: 'continue',
      title: '继续上次练习',
      subtitle: cleanText(safeLastPractice.subject_name || safeLastPractice.display_name, '回到上次题库'),
      action: '继续',
      target: 'continue',
      icon: 'play'
    });
  }

  if (isLoggedIn && safeWeakness.length > 0) {
    const firstWeakness = safeWeakness[0] || {};
    advice.push({
      key: 'weakness',
      title: '优先巩固薄弱环节',
      subtitle: cleanText(firstWeakness.subject, '从正确率较低的题型开始'),
      action: '强化',
      target: 'weakness',
      icon: 'alert'
    });
  }

  if (isLoggedIn && toNumber(safeStats.mistakes) > 0) {
    advice.push({
      key: 'mistakes',
      title: '复盘错题',
      subtitle: `当前错题 ${toNumber(safeStats.mistakes)} 道`,
      action: '去复盘',
      target: 'review',
      icon: 'mistake'
    });
  }

  if (isLoggedIn && advice.length < DEFAULT_ADVICE_LIMIT && toNumber(safeStats.favorites) > 0) {
    advice.push({
      key: 'favorites',
      title: '回看收藏题',
      subtitle: `收藏题 ${toNumber(safeStats.favorites)} 道，适合考前快速过一遍`,
      action: '查看',
      target: 'favorites',
      icon: 'favorite'
    });
  }

  if (isLoggedIn && advice.length === 0) {
    advice.push({
      key: 'start',
      title: '开始一次练习',
      subtitle: '从题库广场选择一个题库进入练习',
      action: '去选题库',
      target: 'publicBank',
      icon: 'book'
    });
  }

  return advice.slice(0, DEFAULT_ADVICE_LIMIT);
}

export function buildRecentBanks(lastPractice: HubLastPractice, storageRows: unknown[]): RecentBankItem[] {
  const rows: RecentBankItem[] = [];
  const safeLastPractice = lastPractice || {};
  const rawRows = Array.isArray(storageRows) ? storageRows : [];

  if (safeLastPractice.has_practice) {
    rows.push({
      key: `last-${cleanText(safeLastPractice.source_type, 'practice')}-${cleanText(
        safeLastPractice.source_id || safeLastPractice.subject_id,
        'latest'
      )}`,
      title: cleanText(safeLastPractice.subject_name || safeLastPractice.display_name, '上次练习'),
      meta: cleanText(safeLastPractice.last_at_display, '最近练习'),
      source_type: safeLastPractice.source_type || '',
      source_id: safeLastPractice.source_id || safeLastPractice.subject_id || '',
      target: 'continue',
      mode: safeLastPractice.mode || ''
    });
  }

  rawRows.forEach((row, index) => {
    if (!row || typeof row !== 'object') return;
    const item = row as Record<string, unknown>;
    const title = cleanText(item.title || item.name || item.display_name || item.subject_name, '');
    if (!title) return;
    rows.push({
      key: cleanText(item.key, `stored-${index}`),
      title,
      meta: cleanText(item.meta || item.last_at_display || item.subtitle, '最近使用'),
      source_type: String(item.source_type || ''),
      source_id: (item.source_id || item.subject_id || item.bank_id || '') as string | number,
      target: cleanText(item.target, 'stored'),
      mode: String(item.mode || '')
    });
  });

  const seen: Record<string, boolean> = {};
  return rows.filter((row) => {
    const key = `${cleanText(row.source_type, 'unknown')}:${cleanText(row.source_id, row.title)}`;
    if (seen[key]) return false;
    seen[key] = true;
    return true;
  }).slice(0, DEFAULT_RECENT_LIMIT);
}

export function buildWeaknessEmptyActions(isLoggedIn: boolean, stats: HubStats): WeaknessEmptyAction[] {
  if (!isLoggedIn) {
    return [{
      key: 'login',
      title: '登录后查看薄弱环节',
      subtitle: '系统会根据练习记录生成巩固建议',
      action: '去登录',
      target: 'login'
    }];
  }

  const safeStats: Partial<HubStats> = stats || {};
  if (toNumber(safeStats.answered) <= 0) {
    return [{
      key: 'start',
      title: '还没有足够练习记录',
      subtitle: '先完成一次练习，首页会自动生成薄弱环节',
      action: '开始练习',
      target: 'publicBank'
    }];
  }

  return [{
    key: 'review',
    title: '暂未发现明显薄弱项',
    subtitle: '可以通过错题本或收藏题做一次主动复盘',
    action: '去复盘',
    target: 'review'
  }];
}
