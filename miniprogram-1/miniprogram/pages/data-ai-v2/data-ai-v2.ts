import { api } from '../../utils/api';
import { checkLogin } from '../../utils/auth';
import { safeNavigate } from '../../utils/nav';
import { themeManager } from '../../utils/theme';
import { normalizeDays, pct1, toInt } from '../../utils/data-center';
import { getCachedDataCenter, setCachedDataCenter } from '../../utils/data-center-cache';

type AbilityItem = { name: string; value: number };
type FocusRow = { name: string; gap: number; accuracy: number; answered: number };

function buildAiPatch(res: any) {
  const abilityList = (Array.isArray(res?.ability_radar) ? res.ability_radar : []).map((a: any) => ({
    name: String(a?.name || ''),
    value: pct1(a?.value)
  }));

  const focusRows = (Array.isArray(res?.weakness_rows) ? res.weakness_rows : [])
    .map((w: any) => {
      const acc = pct1(w?.accuracy);
      return {
        name: `${String(w?.subject || '')} 路 ${String(w?.q_type || '')}`,
        gap: pct1(100 - acc),
        accuracy: acc,
        answered: toInt(w?.answered)
      };
    })
    .sort((a, b) => b.gap - a.gap)
    .slice(0, 8);

  return { inited: true, abilityList, focusRows };
}

Page({
  data: {
    loading: false,
    inited: false,
    errorMsg: '',

    days: 30 as 7 | 30 | 90,

    abilityList: [] as AbilityItem[],
    focusRows: [] as FocusRow[],

    aiReply: '点击“生成建议”，获取基于你数据的训练方案。',
    aiPrompt: '',
    aiLoading: false
  },

  onLoad(options: any) {
    const days = normalizeDays(options?.days);
    this.setData({ days });
  },

  onShow() {
    if (!checkLogin()) {
      wx.redirectTo({ url: '/pages/login/login' });
      return;
    }

    const patch: any = {};
    let hydrated = false;
    try {
      Object.assign(patch, themeManager.getPageData());
    } catch (e) {}
    if (!this.data.inited) {
      try {
        const cached = getCachedDataCenter(this.data.days);
        if (cached) {
          Object.assign(patch, buildAiPatch(cached), { errorMsg: '' });
          const self = this;
          self.__lastLoadedAt = Date.now();
          hydrated = true;
        }
      } catch (e) {}
    }
    try {
      if (Object.keys(patch).length) this.setData(patch);
    } catch (e) {}

    if (!hydrated && !this.data.inited && !this.data.loading) {
      this.loadStats(true);
    }
  },

  onPullDownRefresh() {
    this.loadStats(true).finally(() => {
      wx.stopPullDownRefresh();
    });
  },

  onTabTap(e: any) {
    const tab = String(e?.currentTarget?.dataset?.tab || '');
    const days = this.data.days;
    const map: Record<string, string> = {
      overview: '/pages/history-v2/history-v2',
      banks: '/pages/data-banks-v2/data-banks-v2',
      trend: '/pages/data-trend-v2/data-trend-v2',
      ai: '/pages/data-ai-v2/data-ai-v2'
    };
    if (!map[tab]) return;
    safeNavigate(`${map[tab]}?days=${days}`, 'reLaunch');
  },

  onPromptInput(e: any) {
    this.setData({ aiPrompt: String(e?.detail?.value || '') });
  },

  onQuickPrompt(e: any) {
    const prompt = String(e?.currentTarget?.dataset?.prompt || '');
    if (!prompt) return;
    this.askAi(prompt);
  },

  onGenerateAdvice() {
    const prompt = '请基于我的学习数据，给出今天最重要的5条建议，并按优先级排序。';
    this.askAi(prompt);
  },

  onAskPrompt() {
    const prompt = String(this.data.aiPrompt || '').trim();
    if (!prompt) {
      wx.showToast({ title: '请先输入问题', icon: 'none' });
      return;
    }
    this.askAi(prompt);
  },

  async askAi(prompt: string) {
    if (this.data.aiLoading) return;
    this.setData({ aiLoading: true, aiReply: '正在生成建议...' });
    try {
      const res: any = await api.getDataAiAdvice(prompt, this.data.days);
      const reply = res?.reply ? String(res.reply) : 'AI暂时没有返回有效建议。';
      this.setData({ aiReply: reply });
    } catch (e: any) {
      this.setData({ aiReply: e?.message || '生成失败，请稍后再试。' });
    } finally {
      this.setData({ aiLoading: false });
    }
  },

  async loadStats(force = false) {
    if (this.data.loading) return;
    const self = this;
    const now = Date.now();
    const lastAt = Number(self.__lastLoadedAt || 0) || 0;
    if (!force && now - lastAt < 10000) return;

    self.__lastLoadedAt = now;
    this.setData({ loading: true, errorMsg: '' });

    try {
      const res: any = await api.getDataCenter(this.data.days);
      try {
        setCachedDataCenter(this.data.days, res);
      } catch (e) {}
      const abilityList = (Array.isArray(res?.ability_radar) ? res.ability_radar : []).map((a: any) => ({
        name: String(a?.name || ''),
        value: pct1(a?.value)
      }));

      const focusRows = (Array.isArray(res?.weakness_rows) ? res.weakness_rows : [])
        .map((w: any) => {
          const acc = pct1(w?.accuracy);
          return {
            name: `${String(w?.subject || '')} · ${String(w?.q_type || '')}`,
            gap: pct1(100 - acc),
            accuracy: acc,
            answered: toInt(w?.answered)
          };
        })
        .sort((a, b) => b.gap - a.gap)
        .slice(0, 8);

      this.setData({
        inited: true,
        abilityList,
        focusRows
      });
    } catch (e: any) {
      this.setData({ errorMsg: e?.message || '加载失败，请稍后再试。' });
    } finally {
      this.setData({ loading: false });
    }
  }
});
