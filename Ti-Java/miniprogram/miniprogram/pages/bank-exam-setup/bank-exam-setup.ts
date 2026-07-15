// bank-exam-setup.ts - 个人题库考试设置
import { api } from '../../utils/api';
import { checkLogin } from '../../utils/auth';

function normalizeTypeList(input: any): string[] {
  const list = Array.isArray(input) ? input : [];
  return list
    .filter((t: any) => typeof t === 'string' && t.trim())
    .map((t: any) => String(t).trim());
}

Page({
  data: {
    bankId: 0,
    bankName: '',
    totalQuestions: 0,
    availableTypes: [] as string[],
    duration: 60,           // 考试时长（分钟）
    questionCount: 20,      // 题目数量
    scorePerQuestion: 5,    // 每题分值
    totalScore: 100,        // 总分
    shuffleQuestions: true, // 随机抽题
    loading: false,
    creating: false,
    warnText: ''
  },

  onLoad(options: any) {
    if (!checkLogin()) {
      wx.redirectTo({ url: '/pages/login/login' });
      return;
    }

    const bankId = Number(options.bank_id || 0);
    if (!bankId) {
      wx.showToast({ title: '题库参数缺失', icon: 'none' });
      setTimeout(() => wx.navigateBack(), 1500);
      return;
    }

    this.setData({ bankId });
    this.loadBankInfo();
  },

  async loadBankInfo() {
    this.setData({ loading: true });
    try {
      const res: any = await api.getBankDetail(this.data.bankId);
      const bankData = res.data || res || {};

      const totalQuestions = bankData.question_count || 0;
      const questionCount = Math.min(20, totalQuestions);
      const availableTypes = normalizeTypeList(bankData.available_types);

      this.setData({
        bankName: bankData.name || '题库',
        totalQuestions,
        questionCount,
        availableTypes,
        loading: false
      });

      this.updateTotalScore();
    } catch (err: any) {
      console.error('加载题库信息失败:', err);
      if (err.message?.includes('401') || err.message?.includes('登录')) {
        wx.reLaunch({ url: '/pages/login/login' });
        return;
      }
      wx.showToast({ title: err.message || '加载失败', icon: 'none' });
      this.setData({ loading: false });
    }
  },

  onDurationInput(e: any) {
    const v = Number(e.detail.value);
    const duration = isFinite(v) ? Math.max(1, Math.min(240, v)) : 60;
    this.setData({ duration });
  },

  onQuestionCountInput(e: any) {
    const v = Number(e.detail.value);
    const max = this.data.totalQuestions;
    const questionCount = isFinite(v) ? Math.max(1, Math.min(max, v)) : 20;
    this.setData({ questionCount }, () => {
      this.updateTotalScore();
      this.checkWarn();
    });
  },

  onScoreInput(e: any) {
    const v = Number(e.detail.value);
    const scorePerQuestion = isFinite(v) ? Math.max(0.5, Math.min(100, v)) : 5;
    this.setData({ scorePerQuestion }, () => {
      this.updateTotalScore();
    });
  },

  onShuffleChange(e: any) {
    this.setData({ shuffleQuestions: !!e.detail.value });
  },

  updateTotalScore() {
    const total = this.data.questionCount * this.data.scorePerQuestion;
    this.setData({ totalScore: Math.round(total * 10) / 10 });
  },

  checkWarn() {
    const { questionCount, totalQuestions } = this.data;
    if (questionCount > totalQuestions) {
      this.setData({ warnText: `题目数量超过可用题目数（${totalQuestions}）` });
    } else {
      this.setData({ warnText: '' });
    }
  },

  async onStartExam() {
    const { bankId, questionCount, duration, scorePerQuestion, totalQuestions } = this.data;

    if (questionCount > totalQuestions) {
      wx.showToast({ title: '题目数量超过可用数量', icon: 'none' });
      return;
    }

    if (questionCount <= 0) {
      wx.showToast({ title: '请设置题目数量', icon: 'none' });
      return;
    }

    this.setData({ creating: true });

    try {
      wx.showLoading({ title: '创建考试...' });

      const typesList = (this.data.availableTypes || []).filter(Boolean);
      const baseTypes = typesList.length ? typesList : ['选择题', '多选题', '判断题', '填空题'];
      const n = Math.max(1, baseTypes.length);
      const base = Math.floor(questionCount / n);
      let rem = questionCount % n;

      const typesCfg: Record<string, number> = {};
      const scoresCfg: Record<string, number> = {};
      baseTypes.forEach((t) => {
        const c = base + (rem > 0 ? 1 : 0);
        if (rem > 0) rem -= 1;
        if (c > 0) {
          typesCfg[t] = c;
          scoresCfg[t] = Math.max(0, Number(scorePerQuestion) || 0);
        }
      });

      const res: any = await api.createExam({
        subject: 'all',
        duration,
        types: typesCfg,
        scores: scoresCfg,
        source: 'user_bank',
        bank_id: bankId
      });

      const examId = Number(res?.exam_id);
      if (!isFinite(examId) || examId <= 0) {
        throw new Error('创建考试失败');
      }

      wx.hideLoading();
      this.setData({ creating: false });
      wx.navigateTo({ url: `/pages/exam-run/exam-run?exam_id=${examId}` });
    } catch (err: any) {
      console.error('创建考试失败:', err);
      wx.hideLoading();
      wx.showToast({ title: err.message || '创建失败', icon: 'none' });
      this.setData({ creating: false });
    }
  }
});
