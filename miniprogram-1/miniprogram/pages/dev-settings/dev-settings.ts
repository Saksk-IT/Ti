import { config } from '../../utils/config';

const DEV_API_BASE_URL_KEY = 'dev_api_base_url';
const DEV_API_HOST_KEY = 'dev_api_host';
const DEV_API_PORT_KEY = 'dev_api_port';
const PROD_API_BASE_URL_KEY = 'prod_api_base_url';
const PROD_API_PRESETS_KEY = 'prod_api_presets_v1';

type ApiMode = 'prod' | 'custom';
type ProdPreset = { name: string; url: string };

function getEnvVersion(): string {
  try {
    return wx.getAccountInfoSync().miniProgram.envVersion || '';
  } catch (e) {
    return '';
  }
}

function getPlatform(): string {
  try {
    const info = (wx as any).getDeviceInfo ? (wx as any).getDeviceInfo() : null;
    const p = info && (info as any).platform;
    if (p) return String(p);
  } catch (e) {
    // ignore
  }

  try {
    return wx.getSystemInfoSync().platform || '';
  } catch (e) {
    return '';
  }
}

function normalizeMode(input: any): ApiMode {
  const m = String(input || '').trim().toLowerCase();
  return m === 'custom' ? 'custom' : 'prod';
}

function getMode(): ApiMode {
  try {
    const m = config.getApiMode ? config.getApiMode() : wx.getStorageSync('api_mode_v1');
    return normalizeMode(m);
  } catch (e) {
    return 'prod';
  }
}

function setMode(mode: ApiMode): void {
  try {
    if (config.setApiMode) {
      config.setApiMode(mode);
      return;
    }
  } catch (e) {}
  try {
    wx.setStorageSync('api_mode_v1', mode);
  } catch (e) {}
}

function getProdApiUrl(): string {
  try {
    return (config.getProdApiUrl && config.getProdApiUrl()) || '';
  } catch (e) {
    return '';
  }
}

function readCustomInputs(): { host: string; port: string; preview: string } {
  try {
    const baseUrlRaw = wx.getStorageSync(DEV_API_BASE_URL_KEY);
    const baseUrl = String(baseUrlRaw || '').trim();
    if (baseUrl) {
      return { host: baseUrl, port: '', preview: baseUrl };
    }

    const host = String(wx.getStorageSync(DEV_API_HOST_KEY) || '').trim();
    const portRaw = wx.getStorageSync(DEV_API_PORT_KEY);
    const portNum = Number(portRaw);
    const port = String(Number.isFinite(portNum) && portNum > 0 ? Math.floor(portNum) : 5000);
    const preview = host ? `http://${host}:${port}/api` : '';
    return { host, port, preview };
  } catch (e) {
    return { host: '', port: '5000', preview: '' };
  }
}

function normalizeBaseUrl(input: any): string {
  const raw = String(input || '').trim();
  if (!raw) return '';
  const m = raw.match(/^(https?):\/\/([^/]+)(\/.*)?$/i);
  if (!m) return '';
  const scheme = String(m[1] || '').toLowerCase();
  const hostPort = String(m[2] || '').trim();
  if (!hostPort) return '';
  return `${scheme}://${hostPort}/api`;
}

function readProdPresets(defaultUrl: string): ProdPreset[] {
  const baseDefault = normalizeBaseUrl(defaultUrl) || defaultUrl;
  const fallback: ProdPreset[] = [{ name: '线上', url: baseDefault }];
  try {
    const raw: any = wx.getStorageSync(PROD_API_PRESETS_KEY);
    if (!Array.isArray(raw)) return fallback;
    const list: ProdPreset[] = [];
    raw.forEach((item: any) => {
      const name = String(item && item.name ? item.name : '').trim();
      const url = normalizeBaseUrl(item && item.url ? item.url : '');
      if (!name || !url) return;
      if (list.some((x) => x.name === name || x.url === url)) return;
      list.push({ name, url });
    });
    if (!list.some((x) => x.url === baseDefault)) list.unshift({ name: '线上', url: baseDefault });
    return list.length ? list : fallback;
  } catch (e) {
    return fallback;
  }
}

function saveProdPresets(list: ProdPreset[]): void {
  try {
    wx.setStorageSync(PROD_API_PRESETS_KEY, list);
  } catch (e) {}
}

function isDevEnv(): boolean {
  try {
    return wx.getAccountInfoSync().miniProgram.envVersion === 'develop';
  } catch (e) {
    return false;
  }
}

Page({
  data: {
    mode: 'prod' as ApiMode,
    prodApiUrl: '',
    prodUrlInput: '',
    prodPresetName: '',
    prodPresets: [] as ProdPreset[],
    customPreview: '',
    host: '',
    port: '',
    apiUrl: '',
    envVersion: '',
    platform: '',
    saving: false,
    testing: false,
    testResult: ''
  },

  onLoad() {
    if (!isDevEnv()) {
      wx.showModal({
        title: '仅开发版可用',
        content: '「开发设置」仅在开发版（develop）开放，避免线上误操作。',
        showCancel: false,
        success: () => {
          const pages = getCurrentPages();
          if (pages.length <= 1) wx.redirectTo({ url: '/pages/login/login' });
          else wx.navigateBack();
        }
      });
      return;
    }
    this.refresh();
  },

  onShow() {
    this.refresh();
  },

  refresh() {
    const mode = getMode();
    const prodApiUrl = getProdApiUrl() || 'https://saksk.top/api';
    const prodUrlInput = prodApiUrl;
    const prodPresets = readProdPresets(prodApiUrl);
    const { host, port, preview } = readCustomInputs();
    const apiUrl = config.getApiUrl();
    this.setData({
      mode,
      prodApiUrl,
      prodUrlInput,
      prodPresets,
      customPreview: preview,
      host,
      port,
      apiUrl,
      envVersion: getEnvVersion(),
      platform: getPlatform()
    });
  },

  onModeTap(e: any) {
    const mode = normalizeMode(e && e.currentTarget && e.currentTarget.dataset && e.currentTarget.dataset.mode);
    setMode(mode);
    this.refresh();
  },

  onUseProdTap() {
    setMode('prod');
    this.refresh();
    wx.showToast({ title: '已切换到生产', icon: 'success' });
  },

  onUseCustomTap() {
    setMode('custom');
    this.refresh();
    wx.showToast({ title: '已切换到自定义', icon: 'success' });
  },

  onProdUrlInput(e: any) {
    this.setData({ prodUrlInput: (e && e.detail && e.detail.value) || '' });
  },

  onProdPresetNameInput(e: any) {
    this.setData({ prodPresetName: (e && e.detail && e.detail.value) || '' });
  },

  onSaveProdTap() {
    const input = String(this.data.prodUrlInput || '').trim();
    const url = normalizeBaseUrl(input);
    if (!url) {
      wx.showToast({ title: '生产地址无效', icon: 'none' });
      return;
    }
    try {
      if (config.setProdApiUrl) config.setProdApiUrl(url);
      else wx.setStorageSync(PROD_API_BASE_URL_KEY, url);
      setMode('prod');
      this.refresh();
      wx.showToast({ title: '生产地址已保存', icon: 'success' });
    } catch (e) {
      wx.showToast({ title: '保存失败', icon: 'none' });
    }
  },

  onClearProdTap() {
    try {
      if (config.clearProdApiUrl) config.clearProdApiUrl();
      else wx.removeStorageSync(PROD_API_BASE_URL_KEY);
      setMode('prod');
      this.refresh();
      wx.showToast({ title: '已恢复默认生产', icon: 'success' });
    } catch (e) {
      wx.showToast({ title: '操作失败', icon: 'none' });
    }
  },

  onApplyProdPresetTap(e: any) {
    const idx = Number(e && e.currentTarget && e.currentTarget.dataset && e.currentTarget.dataset.idx);
    const presets = Array.isArray(this.data.prodPresets) ? this.data.prodPresets : [];
    const item = Number.isFinite(idx) && idx >= 0 && idx < presets.length ? presets[idx] : null;
    if (!item || !item.url) return;
    try {
      if (config.setProdApiUrl) config.setProdApiUrl(item.url);
      else wx.setStorageSync(PROD_API_BASE_URL_KEY, item.url);
      setMode('prod');
      this.refresh();
      wx.showToast({ title: `已切换：${item.name || '预设'}`, icon: 'success' });
    } catch (e) {
      wx.showToast({ title: '切换失败', icon: 'none' });
    }
  },

  onDeleteProdPresetTap(e: any) {
    const idx = Number(e && e.currentTarget && e.currentTarget.dataset && e.currentTarget.dataset.idx);
    const presets = Array.isArray(this.data.prodPresets) ? this.data.prodPresets : [];
    if (!Number.isFinite(idx) || idx < 0 || idx >= presets.length) return;
    const next = presets.filter((_: any, i: number) => i !== idx);
    saveProdPresets(next);
    this.refresh();
    wx.showToast({ title: '已删除预设', icon: 'success' });
  },

  onSaveProdPresetTap() {
    const name = String(this.data.prodPresetName || '').trim();
    if (!name) {
      wx.showToast({ title: '请填写预设名称', icon: 'none' });
      return;
    }
    const url = normalizeBaseUrl(this.data.prodUrlInput);
    if (!url) {
      wx.showToast({ title: '预设地址无效', icon: 'none' });
      return;
    }

    const list = Array.isArray(this.data.prodPresets) ? this.data.prodPresets : [];
    if (list.some((x: any) => x && (x.name === name || x.url === url))) {
      wx.showToast({ title: '预设已存在', icon: 'none' });
      return;
    }

    const next = [...list, { name, url }];
    saveProdPresets(next);
    this.setData({ prodPresetName: '' });
    this.refresh();
    wx.showToast({ title: '预设已保存', icon: 'success' });
  },

  onHostInput(e: any) {
    this.setData({ host: (e && e.detail && e.detail.value) || '' });
  },

  onPortInput(e: any) {
    this.setData({ port: (e && e.detail && e.detail.value) || '' });
  },

  onSaveTap() {
    if (this.data.saving) return;
    const hostInput = String(this.data.host || '').trim();
    const portInput = String(this.data.port || '').trim();
    if (!hostInput) {
      wx.showToast({ title: '请填写 Host 或完整 URL', icon: 'none' });
      return;
    }

    const isFullUrl = /^https?:\/\//i.test(hostInput);
    this.setData({ saving: true });
    try {
      config.setDevHost(hostInput);
      // Host 输入为完整 URL（含 https）时，以 URL 为准并忽略 Port
      if (!isFullUrl && portInput) {
        const n = Number(portInput);
        if (!Number.isFinite(n) || n <= 0 || n > 65535) {
          wx.showToast({ title: '端口无效', icon: 'none' });
          this.setData({ saving: false });
          return;
        }
        if (config.setDevPort) config.setDevPort(n);
      }

      const apiUrl = config.getApiUrl();
      setMode('custom');
      this.setData({ apiUrl, saving: false, testResult: '' });
      this.refresh();
      wx.showToast({ title: '已保存并启用', icon: 'success' });
    } catch (e) {
      this.setData({ saving: false });
      wx.showToast({ title: '保存失败', icon: 'none' });
    }
  },

  onResetTap() {
    wx.showModal({
      title: '清除自定义',
      content: '将清除自定义 Host/Port/URL，并切回生产模式。',
      confirmText: '清除',
      cancelText: '取消',
      success: (res) => {
        if (!res.confirm) return;
        try {
          if (config.clearDevServer) config.clearDevServer();
          setMode('prod');
          this.refresh();
          wx.showToast({ title: '已清除', icon: 'success' });
        } catch (e) {
          wx.showToast({ title: '操作失败', icon: 'none' });
        }
      }
    });
  },

  onTestTap() {
    if (this.data.testing) return;

    const apiUrl = config.getApiUrl();
    this.setData({ testing: true, testResult: '' });

    wx.request({
      url: `${apiUrl}/ping`,
      method: 'GET',
      timeout: 8000,
      success: (res: any) => {
        const ok =
          res &&
          res.statusCode === 200 &&
          res.data &&
          ((res.data.status === 'success' && res.data.data) || (res.data.code === 0 && res.data.data));

        const msg = ok
          ? `连接成功：${apiUrl}`
          : `连接失败：HTTP ${res && res.statusCode ? res.statusCode : '未知'}\n${JSON.stringify(res && res.data ? res.data : {}, null, 2)}`;

        this.setData({ testing: false, testResult: msg });
        wx.showToast({ title: ok ? '连接成功' : '连接失败', icon: ok ? 'success' : 'none' });
      },
      fail: (err: any) => {
        const errorMsg = (err && (err.errMsg || err.message)) || '请求失败';
        this.setData({ testing: false, testResult: `请求失败：${errorMsg}\nAPI: ${apiUrl}` });
        wx.showToast({ title: '请求失败', icon: 'none' });
      }
    });
  }
});

