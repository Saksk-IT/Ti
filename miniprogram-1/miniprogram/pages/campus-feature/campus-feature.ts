import { themeManager, ThemeMode } from '../../utils/theme';

const FEATURE_COPY: { [key: string]: { title: string; subtitle: string; action: string } } = {
  evaluation: {
    title: '一键教评',
    subtitle: '教评自动化能力正在接入，后续会在这里完成评价流程。',
    action: '功能建设中',
  },
  more: {
    title: '更多校园',
    subtitle: '考试安排、校历提醒等校园能力会逐步接入这里。',
    action: '等待接入',
  },
};

function featureCopy(key: string) {
  return FEATURE_COPY[key] || FEATURE_COPY.more;
}

Page({
  data: {
    pageTitle: '校园功能',
    title: '更多校园',
    subtitle: '校园能力正在接入。',
    action: '功能建设中',
  },

  onLoad(options: any) {
    const key = String(options?.feature || '').trim();
    const copy = featureCopy(key);
    this.setData({
      pageTitle: copy.title,
      title: copy.title,
      subtitle: copy.subtitle,
      action: copy.action,
      ...themeManager.getPageData(),
    });
  },

  onShow() {
    try {
      this.setData({ ...themeManager.getPageData() });
    } catch (e) {}
  },

  onCycleThemeModeTap() {
    const mode = themeManager.cycleMode() as ThemeMode;
    this.setData({ ...themeManager.getPageData(), themeMode: mode });
  },
});
