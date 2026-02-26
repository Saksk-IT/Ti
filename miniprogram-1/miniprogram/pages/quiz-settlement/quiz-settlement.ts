// quiz-settlement.ts - 刷题/背题/加强 结算页
import { checkLogin } from '../../utils/auth';
import { themeManager } from '../../utils/theme';

type SourceType = 'public' | 'bank';
type QuizMode = 'quiz' | 'memo' | 'reinforce';

type SettlementPayload = {
  ts: number;
  sourceType: SourceType;
  sourceId: string | number;
  displayName: string;
  mode: QuizMode;
  source: 'all' | 'favorites' | 'mistakes';
  qType: string;
  tag: string;
  shuffleQuestions: boolean;
  shuffleOptions: boolean;
  reinforceKind?: '' | 'wrong' | 'similar';
  total: number;
  answered: number;
  correct: number;
  wrong: number;
  accuracy: number;
  usedSec: number;
  wrongIds: number[];
};

function formatSeconds(seconds: number): string {
  const s = Math.max(0, Math.floor(Number(seconds) || 0));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const r = s % 60;
  if (h > 0) return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(r).padStart(2, '0')}`;
  return `${String(m).padStart(2, '0')}:${String(r).padStart(2, '0')}`;
}

function modeLabel(mode: QuizMode, reinforceKind?: string): string {
  if (mode === 'memo') return '背题';
  if (mode === 'reinforce') {
    if (reinforceKind === 'similar') return '相似题加强';
    return '错题加强';
  }
  return '刷题';
}

function sourceLabel(source: string): string {
  if (source === 'favorites') return '收藏';
  if (source === 'mistakes') return '错题';
  return '全部';
}

Page({
  data: {
    loading: false,
    errorText: '',

    payload: null as SettlementPayload | null,
    title: '本次结算',

    // 主题（深浅/风格）
    isDarkMode: false,
    themeMode: 'system' as string,
    themeClass: '' as string,
    themeStyle: 'default' as string,
    themeStyleClass: '' as string,
    themeCtaColor: '#007AFF' as string,

    modeText: '',
    sourceText: '',
    qTypeText: '',
    tagText: '',
    subText: '',
    subChips: [] as string[],

    total: 0,
    answered: 0,
    correct: 0,
    wrong: 0,
    accuracy: 0,
    usedText: '--',
    usedTextClass: '',
    answeredPercent: 0,

    hasWrong: false
  },

  onLoad() {
    if (!checkLogin()) {
      wx.redirectTo({ url: '/pages/login/login' });
      return;
    }

    // 初始化主题（保证进入页面即命中 themeClass / themeStyleClass）
    try {
      this.setData(themeManager.getPageData());
    } catch (e) {}

    try {
      wx.showShareMenu({ withShareTicket: true });
    } catch (e) {}

    let payload: SettlementPayload | null = null;
    try {
      const raw = wx.getStorageSync('quiz_settlement_payload_v1');
      if (raw && typeof raw === 'object') {
        payload = raw as SettlementPayload;
      }
    } catch (e) {}

    if (!payload || !payload.ts) {
      this.setData({ errorText: '结算数据已过期，请返回重试。' });
      return;
    }

    const modeText = modeLabel(payload.mode, payload.reinforceKind);
    const sourceText = sourceLabel(payload.source);
    const qTypeText = payload.qType && payload.qType !== 'all' ? payload.qType : '全部题型';
    const tagText = payload.tag && payload.tag !== 'all' ? payload.tag : '';
    const subText = `${modeText} · ${sourceText} · ${qTypeText}${tagText ? ` · ${tagText}` : ''}`;
    const subChips = [modeText, sourceText, qTypeText].concat(tagText ? [tagText] : []);

    const usedText = formatSeconds(payload.usedSec);
    const usedTextClass = usedText.length >= 8 ? 'v--sm' : '';

    const total = Number(payload.total || 0) || 0;
    const answered = Number(payload.answered || 0) || 0;
    const answeredPercent = total > 0 ? Math.max(0, Math.min(100, Math.round((answered * 100) / total))) : 0;

    this.setData({
      payload,
      modeText,
      sourceText,
      qTypeText,
      tagText,
      subText,
      subChips,
      total,
      answered,
      correct: payload.correct,
      wrong: payload.wrong,
      accuracy: payload.accuracy,
      usedText,
      usedTextClass,
      answeredPercent,
      hasWrong: Array.isArray(payload.wrongIds) && payload.wrongIds.length > 0
    });
  },

  buildQuizUrl(mode: QuizMode): string {
    const p = this.data.payload;
    if (!p) return '/pages/hub-v2/hub-v2';

    const params: string[] = [];
    if (p.sourceType === 'bank') params.push(`bank_id=${encodeURIComponent(String(p.sourceId))}`);
    else params.push(`subject=${encodeURIComponent(String(p.sourceId))}`);

    params.push(`mode=${encodeURIComponent(String(mode))}`);

    if (mode !== 'reinforce') {
      params.push(`source=${encodeURIComponent(String(p.source || 'all'))}`);
      if (p.qType && p.qType !== 'all') params.push(`type=${encodeURIComponent(String(p.qType))}`);
      if (p.tag && p.tag !== 'all') params.push(`tag=${encodeURIComponent(String(p.tag))}`);
      if (p.shuffleQuestions) params.push('shuffle_questions=1');
      if (p.shuffleOptions) params.push('shuffle_options=1');
      return `/pages/quiz/quiz?${params.join('&')}`;
    }

    const ids = (p.wrongIds || []).slice(0, 200);
    params.push('mode=reinforce');
    params.push('rk=wrong');
    params.push(`ids=${encodeURIComponent(ids.join(','))}`);
    return `/pages/quiz/quiz?${params.join('&')}`;
  },

  onTapContinue() {
    const pages = getCurrentPages();
    if (pages && pages.length > 1) {
      wx.navigateBack({ delta: 1 });
      return;
    }

    const p = this.data.payload;
    if (!p) return;
    wx.navigateTo({ url: this.buildQuizUrl(p.mode) });
  },

  onTapReinforceWrong() {
    const p = this.data.payload;
    if (!p) return;
    if (!Array.isArray(p.wrongIds) || p.wrongIds.length === 0) {
      wx.showToast({ title: '本次没有错题', icon: 'none' });
      return;
    }
    wx.navigateTo({ url: this.buildQuizUrl('reinforce') });
  },

  onTapMistakesCenter() {
    const p = this.data.payload;
    if (!p) return;

    if (p.sourceType === 'bank') {
      wx.navigateTo({ url: `/pages/review-center-v2/review-center-v2?kind=mistakes&bank_id=${encodeURIComponent(String(p.sourceId))}` });
      return;
    }

    wx.navigateTo({ url: `/pages/review-center-v2/review-center-v2?kind=mistakes&subject=${encodeURIComponent(String(p.sourceId))}` });
  },

  onTapExam() {
    wx.navigateTo({ url: '/pages/exams-select-v2/exams-select-v2' });
  },

  onTapExit() {
    wx.switchTab({ url: '/pages/hub-v2/hub-v2' });
  },

  onShareAppMessage() {
    const p = this.data.payload;
    const name = p ? String(p.displayName || '').trim() : '';
    const scope = name || '本次练习';
    const title = `${scope}｜${this.data.modeText}：正确率 ${this.data.accuracy}%`;
    return { title, path: '/pages/hub-v2/hub-v2' };
  }
});
