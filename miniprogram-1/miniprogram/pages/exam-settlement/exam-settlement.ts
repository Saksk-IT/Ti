// exam-settlement.ts - 考试结算页
import { api } from '../../utils/api';
import { checkLogin } from '../../utils/auth';

type ExamInfo = {
  id: number;
  subject?: string;
  duration_minutes?: number;
  status?: string;
  started_at?: string;
  submitted_at?: string;
  total_score?: number;
};

type ExamQuestion = {
  id: number;
  user_answer?: string;
  is_correct?: number | boolean | null;
};

function formatSeconds(seconds: number): string {
  const s = Math.max(0, Math.floor(Number(seconds) || 0));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const r = s % 60;
  if (h > 0) return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(r).padStart(2, '0')}`;
  return `${String(m).padStart(2, '0')}:${String(r).padStart(2, '0')}`;
}

function parseDateTimeMaybe(val: any): number {
  const s = String(val || '').trim();
  if (!s) return NaN;
  const iso = s.includes('T') ? s : s.replace(' ', 'T');
  const d = new Date(iso);
  const t = d.getTime();
  return Number.isFinite(t) ? t : NaN;
}

function calcSecondsBetween(a: any, b: any): number | null {
  const t1 = parseDateTimeMaybe(a);
  const t2 = parseDateTimeMaybe(b);
  if (!Number.isFinite(t1) || !Number.isFinite(t2)) return null;
  const diff = Math.max(0, Math.floor((t2 - t1) / 1000));
  return diff;
}

function parsePositiveInt(val: any): number | null {
  const n = Number(val);
  if (!Number.isFinite(n) || n <= 0) return null;
  return Math.floor(n);
}

Page({
  data: {
    examId: 0,
    usedSecHint: null as number | null,
    autoSubmitted: false,

    loading: false,
    errorText: '',

    exam: null as ExamInfo | null,
    statusText: '',
    subChips: [] as string[],
    total: 0,
    correct: 0,
    wrong: 0,
    answered: 0,
    unanswered: 0,
    answeredPercent: 0,
    accuracy: 0,
    totalScore: 0,

    timeUsedText: '--',
    startedAt: '',
    submittedAt: '',

    toMistakesLoading: false,
    toMistakesDone: false,
    toMistakesCount: 0
  },

  onLoad(options: any) {
    if (!checkLogin()) {
      wx.redirectTo({ url: '/pages/login/login' });
      return;
    }

    try {
      wx.showShareMenu({ withShareTicket: true });
    } catch (e) {}

    const examId = Number(options?.exam_id || 0);
    if (!Number.isFinite(examId) || examId <= 0) {
      this.setData({ errorText: '考试参数缺失' });
      return;
    }

    const usedSecHint = parsePositiveInt(options?.used_sec);
    const autoSubmitted = String(options?.silent || '').trim() === '1';
    this.setData({ examId, usedSecHint, autoSubmitted });
    this.loadData();
  },

  onPullDownRefresh() {
    this.loadData(true);
  },

  async loadData(fromPullDown = false) {
    if (this.data.loading) return;
    this.setData({ loading: true, errorText: '' });

    try {
      const res: any = await api.getExam(this.data.examId);
      const exam: ExamInfo = (res && res.exam) ? res.exam : (res || {});
      const questions: ExamQuestion[] = Array.isArray(res?.questions) ? res.questions : [];

      const total = questions.length;
      let correct = 0;
      let wrong = 0;
      let answered = 0;

      questions.forEach((q) => {
        const ua = String(q?.user_answer || '').trim();
        if (ua) answered += 1;

        const ic = (q as any)?.is_correct;
        if (ic === 1 || ic === true) correct += 1;
        else if (ic === 0 || ic === false) wrong += 1;
      });

      const unanswered = Math.max(0, total - answered);
      const accuracy = total ? Math.round((correct * 1000) / total) / 10 : 0;
      const totalScore = Number((exam as any)?.total_score || 0) || 0;

      const startedAt = String((exam as any)?.started_at || '').trim();
      const submittedAt = String((exam as any)?.submitted_at || '').trim();

      let usedSec: number | null = this.data.usedSecHint;
      if (!usedSec) {
        usedSec = calcSecondsBetween(startedAt, submittedAt);
      }
      const timeUsedText = usedSec != null ? formatSeconds(usedSec) : '--';

      const statusText = String((exam as any)?.status || '').trim() === 'submitted' ? '已交卷' : '进行中';
      const durationMinutes = Number((exam as any)?.duration_minutes || 0) || 0;
      const subChips: string[] = [];
      if (durationMinutes > 0) subChips.push(`${durationMinutes} 分钟`);
      if (total > 0) subChips.push(`${total} 题`);
      if (timeUsedText && timeUsedText !== '--') subChips.push(`用时 ${timeUsedText}`);

      const answeredPercent = total > 0 ? Math.max(0, Math.min(100, Math.round((answered * 100) / total))) : 0;

      this.setData({
        exam,
        statusText,
        subChips,
        total,
        correct,
        wrong,
        answered,
        unanswered,
        answeredPercent,
        accuracy,
        totalScore,
        startedAt: startedAt || '--',
        submittedAt: submittedAt || '--',
        timeUsedText
      });
    } catch (e: any) {
      this.setData({ errorText: (e && e.message) || '加载失败' });
    } finally {
      this.setData({ loading: false });
      if (fromPullDown) {
        try {
          wx.stopPullDownRefresh();
        } catch (e) {}
      }
    }
  },

  onTapReview() {
    const examId = this.data.examId;
    if (!examId) return;

    const pages = getCurrentPages();
    const prev = pages && pages.length > 1 ? pages[pages.length - 2] : null;
    if (prev && (prev as any).route === 'pages/exam-run/exam-run') {
      wx.navigateBack({ delta: 1 });
      return;
    }
    wx.navigateTo({ url: `/pages/exam-run/exam-run?exam_id=${encodeURIComponent(String(examId))}` });
  },

  async onTapMistakes() {
    if (this.data.toMistakesLoading) return;
    const examId = this.data.examId;
    if (!examId) return;

    this.setData({ toMistakesLoading: true });
    try {
      const res: any = await api.examToMistakes(examId);
      const count = Number(res?.count || 0) || 0;
      this.setData({ toMistakesDone: true, toMistakesCount: count });

      if (count > 0) wx.showToast({ title: `已加入错题本：${count} 题`, icon: 'none' });
      else wx.showToast({ title: '本次没有错题', icon: 'none' });

      wx.navigateTo({ url: '/pages/mistakes-v2/mistakes-v2' });
    } catch (e: any) {
      wx.showToast({ title: (e && e.message) || '操作失败', icon: 'none' });
    } finally {
      this.setData({ toMistakesLoading: false });
    }
  },

  onTapNewExam() {
    wx.navigateTo({ url: '/pages/exams-select-v2/exams-select-v2' });
  },

  onTapExit() {
    wx.switchTab({ url: '/pages/hub-v2/hub-v2' });
  },

  onShareAppMessage() {
    const exam = this.data.exam || ({} as any);
    const scope = String((exam as any)?.subject || '').trim() || '考试';
    const score = this.data.totalScore;
    const accuracy = this.data.accuracy;
    const title = `我完成了「${scope}」考试：得分 ${score}，正确率 ${accuracy}%`;
    return {
      title,
      path: '/pages/exams-select-v2/exams-select-v2'
    };
  }
});
