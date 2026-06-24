type SettingsNavKey = 'account' | 'theme' | 'about';
type AccountSubKey = 'profile' | 'security' | 'bindings';
type AboutTab = 'app' | 'legal';

function normalizeNavKey(raw: any): SettingsNavKey {
  const v = String(raw || '').trim().toLowerCase();
  if (v === 'theme' || v === 'about') return v;
  return 'account';
}

function normalizeAccTab(raw: any): AccountSubKey {
  const v = String(raw || '').trim().toLowerCase();
  if (v === 'security' || v === 'bindings') return v;
  return 'profile';
}

function normalizeAboutTab(raw: any): AboutTab {
  const v = String(raw || '').trim().toLowerCase();
  return v === 'legal' ? 'legal' : 'app';
}

function buildTargetUrl(options: any): string {
  const navKey = normalizeNavKey(options?.navKey || options?.nav || options?.tab);
  const accTab = normalizeAccTab(options?.accTab || options?.acc || options?.sub);
  const aboutTab = normalizeAboutTab(options?.aboutTab || options?.about);

  if (navKey === 'theme') return '/pages/settings-theme-v2/settings-theme-v2';
  if (navKey === 'about') {
    return aboutTab === 'legal'
      ? '/pages/settings-about-v2/settings-about-v2?aboutTab=legal'
      : '/pages/settings-about-v2/settings-about-v2';
  }

  if (accTab === 'security') return '/pages/settings-account-security-v2/settings-account-security-v2';
  if (accTab === 'bindings') return '/pages/settings-account-bindings-v2/settings-account-bindings-v2';

  const edit = String(options?.edit || '');
  return edit === '1'
    ? '/pages/settings-account-profile-v2/settings-account-profile-v2?edit=1'
    : '/pages/settings-account-profile-v2/settings-account-profile-v2';
}

Page({
  onLoad(options: any) {
    wx.redirectTo({ url: buildTargetUrl(options || {}) });
  }
});
