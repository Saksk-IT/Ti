const TAB_TRANSITION_CLASS = 'tab-switch-enter';

export function restartTabPageTransition(page: WechatMiniprogram.Page.Instance<Record<string, any>, Record<string, any>>): void {
  if (!page || typeof page.setData !== 'function') return;

  page.setData({ tabPageTransitionClass: '' }, () => {
    setTimeout(() => {
      page.setData({ tabPageTransitionClass: TAB_TRANSITION_CLASS });
    }, 16);
  });
}
