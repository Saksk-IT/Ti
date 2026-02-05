import { api } from '../../utils/api';

type ExamSource = 'public' | 'user_bank';

type ExamTypeRow = {
  name: string;
  enabled: boolean;
  available: number;
  count: number;
  score: number;
  subtotalText: string;
};

type ExamConfig = {
  source: ExamSource;
  subject: string;
  bank_id: number | null;
  duration: number;
  targetTotal: number;
  types: Record<string, number>;
  scores: Record<string, number>;
  label?: string;
};

type UserTemplate = {
  id: number;
  title: string;
  config: any;
  created_at?: string;
  updated_at?: string;
};

type TemplateOption = { id: number; label: string };

const QUICK_PRESETS = [
  { duration: 15, total: 20, label: '15min/20题' },
  { duration: 30, total: 30, label: '30min/30题' },
  { duration: 60, total: 50, label: '60min/50题' }
];

const FALLBACK_PUBLIC_Q_TYPES = ['单选题', '多选题', '判断题', '填空题', '简答题', '综合题', '计算题'];
const DEFAULT_PICKED_TYPES = ['单选题', '多选题', '判断题'];

function todayStamp(): string {
  const now = new Date();
  const y = String(now.getFullYear());
  const m = String(now.getMonth() + 1).padStart(2, '0');
  const d = String(now.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

function clampInt(v: any, fallback: number, minV: number, maxV: number): number {
  const n = Math.floor(Number(v));
  if (!Number.isFinite(n)) return fallback;
  return Math.max(minV, Math.min(maxV, n));
}

function clampFloat(v: any, fallback: number, minV: number, maxV: number): number {
  const n = Number(v);
  if (!Number.isFinite(n)) return fallback;
  return Math.max(minV, Math.min(maxV, n));
}

function formatNum(n: any): string {
  const v = Number(n);
  if (!Number.isFinite(v)) return '0';
  if (Math.abs(v - Math.round(v)) < 1e-6) return String(Math.round(v));
  return String(v.toFixed(2)).replace(/\.?0+$/, '');
}

function distributeCounts(targetTotal: number, enabledTypes: Array<{ name: string; available: number }>): Record<string, number> {
  const cfg: Record<string, number> = {};
  const n = enabledTypes.length;
  if (n <= 0) return cfg;

  const target = clampInt(targetTotal, 30, 1, 300);
  const base = Math.floor(target / n);
  let rem = target % n;

  enabledTypes.forEach((t) => {
    const want = base + (rem > 0 ? 1 : 0);
    if (rem > 0) rem -= 1;
    cfg[t.name] = Math.min(want, Math.max(0, t.available));
  });

  let assignedTotal = Object.values(cfg).reduce((s, v) => s + (Number(v) || 0), 0);
  let remaining = target - assignedTotal;
  let safety = 5000;
  while (remaining > 0 && safety-- > 0) {
    let progressed = false;
    for (const t of enabledTypes) {
      if (remaining <= 0) break;
      const cap = Math.max(0, t.available) - (cfg[t.name] || 0);
      if (cap > 0) {
        cfg[t.name] = (cfg[t.name] || 0) + 1;
        remaining -= 1;
        progressed = true;
      }
    }
    if (!progressed) break;
  }

  assignedTotal = Object.values(cfg).reduce((s, v) => s + (Number(v) || 0), 0);
  if (assignedTotal <= 0) {
    enabledTypes.forEach((t) => {
      cfg[t.name] = Math.min(1, Math.max(0, t.available));
    });
  }
  return cfg;
}

function normalizeTemplateConfig(raw: any): ExamConfig | null {
  if (!raw || typeof raw !== 'object') return null;
  const source: ExamSource = String(raw.source || 'public').toLowerCase() === 'user_bank' ? 'user_bank' : 'public';
  const subject = String(raw.subject || 'all').trim() || 'all';
  const bank_id = raw.bank_id != null && raw.bank_id !== '' ? Number(raw.bank_id) : null;
  const duration = clampInt(raw.duration, 60, 1, 1440);

  const typesRaw = raw.types && typeof raw.types === 'object' ? raw.types : {};
  const scoresRaw = raw.scores && typeof raw.scores === 'object' ? raw.scores : {};

  const types: Record<string, number> = {};
  const scores: Record<string, number> = {};

  Object.keys(typesRaw || {}).forEach((k) => {
    const name = String(k || '').trim();
    if (!name) return;
    const c = clampInt((typesRaw as any)[k], 0, 0, 500);
    if (c <= 0) return;
    types[name] = c;
    scores[name] = clampFloat((scoresRaw as any)[k], 1, 0, 1000);
  });

  let targetTotal = raw.targetTotal ?? raw.total ?? raw.target_total;
  targetTotal = clampInt(targetTotal, 0, 0, 300);
  if (!targetTotal) {
    targetTotal = Object.values(types).reduce((sum, v) => sum + (Number(v) || 0), 0);
    targetTotal = clampInt(targetTotal, 0, 0, 300);
  }

  return {
    source,
    subject,
    bank_id: source === 'user_bank' ? (Number.isFinite(bank_id as any) ? (bank_id as number) : null) : null,
    duration,
    targetTotal,
    types,
    scores
  };
}

function buildTemplateMeta(cfg: ExamConfig): string {
  const duration = clampInt(cfg.duration, 60, 1, 1440);
  const total = clampInt(cfg.targetTotal, 0, 0, 300);
  return total ? `${duration} 分钟 · ${total} 题` : `${duration} 分钟`;
}

function isSameScope(cfg: ExamConfig, source: ExamSource, subject: string, bankId: number): boolean {
  if (source === 'user_bank') return cfg.source === 'user_bank' && Number(cfg.bank_id || 0) === bankId;
  const s = subject || 'all';
  return cfg.source === 'public' && String(cfg.subject || 'all') === s;
}

Component({
  properties: {
    source: {
      type: String,
      value: 'public'
    },
    subject: {
      type: String,
      value: ''
    },
    bankId: {
      type: Number,
      value: 0
    },
    bankName: {
      type: String,
      value: ''
    }
  },

  data: {
    quickPresets: QUICK_PRESETS,

    scopeText: '',
    emptyText: '暂无题型数据',

    examDuration: 60,
    examTargetTotal: 30,

    examTypes: [] as ExamTypeRow[],
    examLoading: false,
    examCreating: false,
    examMsg: '',
    examMsgKind: '' as '' | 'error',

    examSumScope: '',
    examSumDuration: '',
    examSumAssigned: '',
    examSumScore: '',
    examSumTypes: [] as Array<{ name: string; meta: string; subtotal: string }>,
    examStartDisabled: true,

    templatesLoading: false,
    templateOptions: [{ id: 0, label: '不使用模板' }] as TemplateOption[],
    templateIndex: 0,
    templateLabel: '不使用模板',
    templateMeta: '',
    templateMsg: '',
    templateMsgKind: '' as '' | 'error',

    presetApplied: false,

    saveModalOpen: false,
    saveTemplateTitle: '',
    savingTemplate: false
  },

  lifetimes: {
    attached() {
      this.bootstrap();
    }
  },

  pageLifetimes: {
    show() {
      this.loadUserTemplates();
    }
  },

  observers: {
    'source,subject,bankId,bankName': function () {
      this.bootstrap();
    }
  },

  methods: {
    normalizeSource(): ExamSource {
      const raw = String((this.properties as any).source || '').trim().toLowerCase();
      return raw === 'user_bank' ? 'user_bank' : 'public';
    },

    buildScopeText(): string {
      const source = this.normalizeSource();
      if (source === 'user_bank') {
        const bankId = Number((this.properties as any).bankId || 0) || 0;
        const bankName = String((this.properties as any).bankName || '').trim() || (bankId > 0 ? `题库#${bankId}` : '未选择题库');
        return `个人题库 · ${bankName}`;
      }
      const subject = String((this.properties as any).subject || '').trim() || '全部科目';
      return `公共题库 · ${subject}`;
    },

    async bootstrap() {
      const scopeText = this.buildScopeText();
      const source = this.normalizeSource();
      const subject = String((this.properties as any).subject || '').trim();
      const bankId = Number((this.properties as any).bankId || 0) || 0;

      let emptyText = '暂无题型数据';
      if (source === 'user_bank' && bankId <= 0) emptyText = '请先选择一个题库';
      if (source === 'public' && !subject) emptyText = '缺少科目参数';

      this.setData(
        {
          scopeText,
          emptyText,
          presetApplied: false,
          examMsg: '',
          examMsgKind: '',
          examTypes: [],
          templatesLoading: false,
          templateOptions: [{ id: 0, label: '不使用模板' }],
          templateIndex: 0,
          templateLabel: '不使用模板',
          templateMeta: '',
          templateMsg: '',
          templateMsgKind: ''
        },
        () => {
          (this as any).__tplCfgById = {};
          (this as any).__tplMetaById = {};
          (this as any).__lastTplLoadAt = 0;
          this.reloadExamTypes();
          this.loadUserTemplates(true);
        }
      );
    },

    setTemplateMsg(text: string, kind: '' | 'error' = '') {
      this.setData({ templateMsg: String(text || ''), templateMsgKind: kind });
    },

    onGoExamCenterTemplates() {
      const source = this.normalizeSource();
      const subject = String((this.properties as any).subject || '').trim() || 'all';
      const bankId = Number((this.properties as any).bankId || 0) || 0;

      const qs: string[] = ['tab=templates', `source=${source}`];
      if (source === 'public') qs.push(`subject=${encodeURIComponent(subject)}`);
      if (source === 'user_bank' && bankId > 0) qs.push(`bank_id=${bankId}`);

      wx.navigateTo({ url: `/pages/index-v2/index-v2?${qs.join('&')}` });
    },

    async loadUserTemplates(force: boolean = false) {
      const rawSubject = String((this.properties as any).subject || '').trim();
      const source = this.normalizeSource();
      const subject = rawSubject || 'all';
      const bankId = Number((this.properties as any).bankId || 0) || 0;

      if (source === 'public' && !rawSubject) {
        (this as any).__tplCfgById = {};
        (this as any).__tplMetaById = {};
        this.setData({
          templatesLoading: false,
          templateOptions: [{ id: 0, label: '不使用模板' }],
          templateIndex: 0,
          templateLabel: '不使用模板',
          templateMeta: ''
        });
        return;
      }

      if (source === 'user_bank' && bankId <= 0) {
        (this as any).__tplCfgById = {};
        (this as any).__tplMetaById = {};
        this.setData({
          templatesLoading: false,
          templateOptions: [{ id: 0, label: '不使用模板' }],
          templateIndex: 0,
          templateLabel: '不使用模板',
          templateMeta: ''
        });
        return;
      }

      const now = Date.now();
      const lastAt = Number((this as any).__lastTplLoadAt || 0) || 0;
      if (!force && now - lastAt < 5000 && (this.data.templateOptions || []).length > 1) return;
      if (this.data.templatesLoading) return;

      this.setData({ templatesLoading: true, templateMsg: '', templateMsgKind: '' });
      try {
        const res = (await api.getExamTemplates()) as unknown as UserTemplate[];
        const list = Array.isArray(res) ? res : [];

        const options: TemplateOption[] = [{ id: 0, label: '不使用模板' }];
        const cfgById: Record<string, ExamConfig> = {};
        const metaById: Record<string, string> = {};

        list.forEach((tpl: any) => {
          const id = Number(tpl?.id || 0);
          if (!Number.isFinite(id) || id <= 0) return;
          const title = String(tpl?.title || '').trim() || `模板 #${id}`;
          const cfg = normalizeTemplateConfig(tpl?.config);
          if (!cfg) return;
          if (!isSameScope(cfg, source, subject, bankId)) return;

          cfgById[String(id)] = { ...cfg, label: title };
          metaById[String(id)] = buildTemplateMeta(cfg);
          options.push({ id, label: title });
        });

        (this as any).__tplCfgById = cfgById;
        (this as any).__tplMetaById = metaById;
        (this as any).__lastTplLoadAt = now;

        const currentId = Number((this.data.templateOptions || [])[this.data.templateIndex]?.id || 0);
        let templateIndex = 0;
        if (currentId > 0) {
          const foundIdx = options.findIndex((o) => Number(o?.id || 0) === currentId);
          if (foundIdx >= 0) templateIndex = foundIdx;
        }

        const finalPicked = options[templateIndex] || options[0];
        const finalId = Number(finalPicked?.id || 0);

        this.setData({
          templateOptions: options,
          templateIndex,
          templateLabel: finalPicked?.label || '不使用模板',
          templateMeta: finalId > 0 ? String(metaById[String(finalId)] || '') : '',
          templatesLoading: false
        });
      } catch (e: any) {
        (this as any).__tplCfgById = {};
        (this as any).__tplMetaById = {};
        (this as any).__lastTplLoadAt = now;

        this.setData({
          templatesLoading: false,
          templateOptions: [{ id: 0, label: '不使用模板' }],
          templateIndex: 0,
          templateLabel: '不使用模板',
          templateMeta: ''
        });
        this.setTemplateMsg((e && e.message) || '模板加载失败，请稍后重试', 'error');
      }
    },

    onTemplatePickerChange(e: any) {
      const idx = Number(e?.detail?.value);
      const options: TemplateOption[] = (this.data.templateOptions || []) as any;
      const safeIdx = Number.isFinite(idx) ? Math.max(0, Math.min(options.length - 1, idx)) : 0;
      const opt = options[safeIdx] || { id: 0, label: '不使用模板' };

      const metaById = ((this as any).__tplMetaById || {}) as Record<string, string>;
      const meta = opt.id > 0 ? String(metaById[String(opt.id)] || '') : '';

      this.setData({
        templateIndex: safeIdx,
        templateLabel: opt.label || '不使用模板',
        templateMeta: meta,
        templateMsg: '',
        templateMsgKind: ''
      });

      if (!opt.id) {
        this.setData({ examTypes: [], presetApplied: false }, () => this.reloadExamTypes());
        return;
      }

      const cfgById = ((this as any).__tplCfgById || {}) as Record<string, ExamConfig>;
      const cfg = cfgById[String(opt.id)];
      if (!cfg) {
        this.setTemplateMsg('模板不可用，请稍后刷新', 'error');
        return;
      }

      this.setData(
        {
          examDuration: clampInt(cfg.duration, 60, 1, 1440),
          examTargetTotal: clampInt(cfg.targetTotal, 30, 1, 300),
          presetApplied: true,
          examMsg: '',
          examMsgKind: ''
        },
        () => this.reloadExamTypes({ applyConfig: cfg })
      );
    },

    async getQTypesForScope(): Promise<string[]> {
      const source = this.normalizeSource();
      const subject = String((this.properties as any).subject || '').trim();
      const bankId = Number((this.properties as any).bankId || 0) || 0;

      try {
        if (source === 'user_bank') {
          if (bankId <= 0) return [];
          const info: any = await api.getBankDetail(bankId);
          const infoData: any = (info as any)?.data || info || {};
          const arr = Array.isArray(infoData?.available_types) ? infoData.available_types : [];
          return (arr || []).filter((x: any) => typeof x === 'string' && String(x).trim()).map((s: any) => String(s).trim());
        }

        if (!subject || subject === 'all') return FALLBACK_PUBLIC_Q_TYPES.slice();
        const info: any = await api.getSubjectInfo(subject);
        const infoData: any = (info as any)?.data || info || {};
        const arr = Array.isArray(infoData?.available_types) ? infoData.available_types : [];
        return (arr || []).filter((x: any) => typeof x === 'string' && String(x).trim()).map((s: any) => String(s).trim());
      } catch {
        return [];
      }
    },

    recomputeTypeSubtotals(rows: ExamTypeRow[]): ExamTypeRow[] {
      return (rows || []).map((r) => {
        const subtotal = r.enabled ? (Number(r.count) || 0) * (Number(r.score) || 0) : 0;
        return { ...r, subtotalText: formatNum(subtotal) };
      });
    },

    applyDefaultPresetIfEmpty(rows: ExamTypeRow[]): ExamTypeRow[] {
      const assigned = (rows || []).reduce((sum, r) => sum + (r.enabled ? Math.max(0, Number(r.count) || 0) : 0), 0);
      if (assigned > 0) return rows;
      if (this.data.presetApplied) return rows;

      const qTypes = rows.map((r) => r.name);
      const picked = DEFAULT_PICKED_TYPES.filter((t) => qTypes.includes(t));
      const fallbackPicked = picked.length ? picked : qTypes.slice(0, Math.min(3, qTypes.length));

      const enabledTypes = rows
        .filter((r) => fallbackPicked.includes(r.name))
        .map((r) => ({ name: r.name, available: r.available }));
      const distributed = distributeCounts(this.data.examTargetTotal, enabledTypes);

      return rows.map((r) => {
        const enabled = fallbackPicked.includes(r.name);
        const count = enabled ? clampInt(distributed[r.name] || 0, 0, 0, r.available) : 0;
        return { ...r, enabled, count, score: 1 };
      });
    },

    refreshExamSummary() {
      const source = this.normalizeSource();
      const subject = String((this.properties as any).subject || '').trim();
      const bankId = Number((this.properties as any).bankId || 0) || 0;
      const scopeText = this.buildScopeText();

      const rows = this.data.examTypes || [];
      const types: Record<string, number> = {};
      const scores: Record<string, number> = {};
      let assigned = 0;
      let totalScore = 0;

      rows.forEach((r) => {
        if (!r.enabled) return;
        const count = clampInt(r.count, 0, 0, 500);
        const score = clampFloat(r.score, 1, 0, 1000);
        if (count <= 0) return;
        types[r.name] = count;
        scores[r.name] = score;
        assigned += count;
        totalScore += count * score;
      });

      const examSumTypes = Object.keys(types).map((name) => {
        const count = types[name] || 0;
        const score = scores[name] ?? 1;
        return { name, meta: `${count} × ${formatNum(score)}`, subtotal: formatNum(count * score) };
      });

      const startDisabled =
        assigned <= 0 ||
        (source === 'public' && !subject) ||
        (source === 'user_bank' && bankId <= 0) ||
        this.data.examLoading ||
        this.data.examCreating;

      this.setData({
        examSumScope: scopeText,
        examSumDuration: `${clampInt(this.data.examDuration, 60, 1, 1440)} 分钟`,
        examSumAssigned: `${assigned} 题`,
        examSumScore: `${formatNum(totalScore)} 分`,
        examSumTypes,
        examStartDisabled: startDisabled
      });
    },

    async reloadExamTypes(opts?: { applyConfig?: ExamConfig }) {
      if (this.data.examLoading) return;
      this.setData({ examLoading: true, examMsg: '', examMsgKind: '' });

      const source = this.normalizeSource();
      const subject = String((this.properties as any).subject || '').trim();
      const bankId = Number((this.properties as any).bankId || 0) || 0;

      if (source === 'public' && !subject) {
        this.setData({ examTypes: [], examLoading: false }, () => this.refreshExamSummary());
        return;
      }
      if (source === 'user_bank' && bankId <= 0) {
        this.setData({ examTypes: [], examLoading: false }, () => this.refreshExamSummary());
        return;
      }

      try {
        const qTypes = (await this.getQTypesForScope()).filter(Boolean);
        if (!qTypes.length) {
          this.setData({ examTypes: [], examLoading: false }, () => this.refreshExamSummary());
          return;
        }

        const counts = await Promise.all(
          qTypes.map(async (t) => {
            try {
              if (source === 'user_bank') {
                const res: any = await api.getBankUserCounts(bankId, { q_type: t, source: 'all' });
                return { name: t, available: clampInt(res?.total, 0, 0, 999999) };
              }
              const res: any = await api.getQuestionsCount({ subject: subject || 'all', type: t });
              return { name: t, available: clampInt(res?.count, 0, 0, 999999) };
            } catch {
              return { name: t, available: 0 };
            }
          })
        );

        const prevMap = new Map<string, ExamTypeRow>();
        (this.data.examTypes || []).forEach((r) => prevMap.set(r.name, r));

        const applyConfig = opts?.applyConfig;
        let rows: ExamTypeRow[] = counts
          .filter((x) => x.available > 0)
          .map((x) => {
            if (applyConfig) {
              const cfgTypes = applyConfig.types || {};
              const cfgScores = applyConfig.scores || {};
              const cfgCount = clampInt((cfgTypes as any)[x.name], 0, 0, x.available);
              const enabled = cfgCount > 0;
              const score = enabled ? clampFloat((cfgScores as any)[x.name], 1, 0, 1000) : 1;
              return { name: x.name, enabled, available: x.available, count: enabled ? cfgCount : 0, score, subtotalText: '0' };
            }

            const prev = prevMap.get(x.name);
            const enabled = prev ? !!prev.enabled : false;
            const score = prev ? clampFloat(prev.score, 1, 0, 1000) : 1;
            const count = enabled ? clampInt(prev?.count, 0, 0, x.available) : 0;
            return { name: x.name, enabled, available: x.available, count, score, subtotalText: '0' };
          });

        if (!applyConfig) rows = this.applyDefaultPresetIfEmpty(rows);
        rows = this.recomputeTypeSubtotals(rows);

        this.setData({ examTypes: rows, examLoading: false, presetApplied: true }, () => this.refreshExamSummary());
      } catch {
        this.setData({ examTypes: [], examLoading: false }, () => this.refreshExamSummary());
      }
    },

    onExamDurationInput(e: any) {
      const duration = clampInt(e?.detail?.value, 60, 1, 1440);
      this.setData({ examDuration: duration }, () => this.refreshExamSummary());
    },

    onExamTargetTotalInput(e: any) {
      const total = clampInt(e?.detail?.value, 30, 1, 300);
      this.setData({ examTargetTotal: total }, () => this.refreshExamSummary());
    },

    onQuickPresetTap(e: any) {
      const duration = clampInt(e?.currentTarget?.dataset?.duration, 60, 1, 1440);
      const total = clampInt(e?.currentTarget?.dataset?.total, 30, 1, 300);
      this.setData({ examDuration: duration, examTargetTotal: total }, () => {
        this.onAutoDistributeTap();
        this.refreshExamSummary();
      });
    },

    onTypeToggleTap(e: any) {
      const name = e?.currentTarget?.dataset?.name;
      if (!name) return;
      const next = (this.data.examTypes || []).map((r) => {
        if (r.name !== name) return r;
        const enabled = !r.enabled;
        return { ...r, enabled, count: enabled ? r.count : 0 };
      });
      this.setData({ examTypes: this.recomputeTypeSubtotals(next), examMsg: '', examMsgKind: '' }, () => this.refreshExamSummary());
    },

    onTypeCountInput(e: any) {
      const name = e?.currentTarget?.dataset?.name;
      if (!name) return;
      const next = (this.data.examTypes || []).map((r) => {
        if (r.name !== name) return r;
        const count = clampInt(e?.detail?.value, 0, 0, r.available);
        return { ...r, count };
      });
      this.setData({ examTypes: this.recomputeTypeSubtotals(next), examMsg: '', examMsgKind: '' }, () => this.refreshExamSummary());
    },

    onTypeScoreInput(e: any) {
      const name = e?.currentTarget?.dataset?.name;
      if (!name) return;
      const next = (this.data.examTypes || []).map((r) => {
        if (r.name !== name) return r;
        const score = clampFloat(e?.detail?.value, 1, 0, 1000);
        return { ...r, score };
      });
      this.setData({ examTypes: this.recomputeTypeSubtotals(next), examMsg: '', examMsgKind: '' }, () => this.refreshExamSummary());
    },

    onAutoDistributeTap() {
      const enabledRows = (this.data.examTypes || []).filter((r) => r.enabled);
      if (!enabledRows.length) {
        this.setData({ examMsg: '请先勾选至少一种题型，再进行均分。', examMsgKind: 'error' }, () => this.refreshExamSummary());
        return;
      }
      const distributed = distributeCounts(
        this.data.examTargetTotal,
        enabledRows.map((r) => ({ name: r.name, available: r.available }))
      );
      const next = (this.data.examTypes || []).map((r) => {
        if (!r.enabled) return { ...r, count: 0 };
        return { ...r, count: clampInt(distributed[r.name] || 0, 0, 0, r.available) };
      });
      this.setData({ examTypes: this.recomputeTypeSubtotals(next), examMsg: '', examMsgKind: '' }, () => this.refreshExamSummary());
    },

    onResetScoresTap() {
      const next = (this.data.examTypes || []).map((r) => ({ ...r, score: 1 }));
      this.setData({ examTypes: this.recomputeTypeSubtotals(next), examMsg: '', examMsgKind: '' }, () => this.refreshExamSummary());
    },

    stopTap() {},

    onOpenSaveTemplate() {
      if (this.data.savingTemplate) return;
      const cfg = this.collectTemplateConfig();
      if (!cfg) {
        wx.showToast({ title: '缺少范围参数', icon: 'none' });
        return;
      }
      if (!Object.keys(cfg.types).length) {
        wx.showToast({ title: '请先设置题型与题量', icon: 'none' });
        return;
      }
      const title = `自定义模板 ${todayStamp()}`;
      this.setData({ saveModalOpen: true, saveTemplateTitle: title });
    },

    onCloseSaveModal() {
      if (this.data.savingTemplate) return;
      this.setData({ saveModalOpen: false, saveTemplateTitle: '' });
    },

    onSaveTemplateTitleInput(e: any) {
      const v = e && e.detail && e.detail.value ? String(e.detail.value) : '';
      this.setData({ saveTemplateTitle: v });
    },

    collectTemplateConfig(): (ExamConfig & { types: Record<string, number>; scores: Record<string, number> }) | null {
      const source = this.normalizeSource();
      const subjectRaw = String((this.properties as any).subject || '').trim();
      const bankId = Number((this.properties as any).bankId || 0) || 0;

      if (source === 'public' && !subjectRaw) return null;
      if (source === 'user_bank' && bankId <= 0) return null;

      const duration = clampInt(this.data.examDuration, 60, 1, 1440);
      const targetTotal = clampInt(this.data.examTargetTotal, 30, 1, 300);

      const types: Record<string, number> = {};
      const scores: Record<string, number> = {};
      (this.data.examTypes || []).forEach((r) => {
        if (!r.enabled) return;
        const count = clampInt(r.count, 0, 0, 500);
        const score = clampFloat(r.score, 1, 0, 1000);
        if (count <= 0) return;
        types[r.name] = count;
        scores[r.name] = score;
      });

      const cfg: ExamConfig = {
        source,
        subject: source === 'public' ? subjectRaw : 'all',
        bank_id: source === 'user_bank' ? bankId : null,
        duration,
        targetTotal,
        types,
        scores
      };
      return cfg as any;
    },

    async onConfirmSaveTemplate() {
      if (this.data.savingTemplate) return;

      const title = String(this.data.saveTemplateTitle || '').trim();
      if (!title) {
        wx.showToast({ title: '模板名称不能为空', icon: 'none' });
        return;
      }

      const cfg = this.collectTemplateConfig();
      if (!cfg) {
        wx.showToast({ title: '缺少范围参数', icon: 'none' });
        return;
      }
      if (!Object.keys(cfg.types).length) {
        wx.showToast({ title: '请先设置题型与题量', icon: 'none' });
        return;
      }

      this.setData({ savingTemplate: true });
      wx.showLoading({ title: '保存中…' });
      try {
        await api.createExamTemplate({ title, config: cfg });
        wx.hideLoading();
        this.setData({ savingTemplate: false, saveModalOpen: false, saveTemplateTitle: '' });
        wx.showToast({ title: '已设为模板', icon: 'success' });
        this.loadUserTemplates(true);
      } catch (e: any) {
        wx.hideLoading();
        this.setData({ savingTemplate: false });
        wx.showToast({ title: (e && e.message) || '保存失败', icon: 'none' });
      }
    },

    collectExamPayload(): { source: ExamSource; subject: string; bank_id: number | null; duration: number; types: Record<string, number>; scores: Record<string, number> } | null {
      const source = this.normalizeSource();
      const subject = String((this.properties as any).subject || '').trim();
      const bankId = Number((this.properties as any).bankId || 0) || 0;

      if (source === 'public' && !subject) return null;
      if (source === 'user_bank' && bankId <= 0) return null;

      const duration = clampInt(this.data.examDuration, 60, 1, 1440);

      const types: Record<string, number> = {};
      const scores: Record<string, number> = {};
      (this.data.examTypes || []).forEach((r) => {
        if (!r.enabled) return;
        const count = clampInt(r.count, 0, 0, 500);
        const score = clampFloat(r.score, 1, 0, 1000);
        if (count <= 0) return;
        types[r.name] = count;
        scores[r.name] = score;
      });

      return {
        source,
        subject: source === 'user_bank' ? (String((this.properties as any).bankName || '').trim() || 'all') : subject,
        bank_id: source === 'user_bank' ? bankId : null,
        duration,
        types,
        scores
      };
    },

    async onStartExamTap() {
      if (this.data.examCreating || this.data.examLoading) return;
      const cfg = this.collectExamPayload();
      if (!cfg) {
        this.setData({ examMsg: '缺少范围参数，无法创建考试。', examMsgKind: 'error' }, () => this.refreshExamSummary());
        return;
      }
      if (!Object.keys(cfg.types).length) {
        this.setData({ examMsg: '请先设置题型与题量。', examMsgKind: 'error' }, () => this.refreshExamSummary());
        return;
      }

      this.setData({ examCreating: true, examMsg: '', examMsgKind: '' });
      wx.showLoading({ title: '创建中…' });
      try {
        const res: any = await api.createExam({
          source: cfg.source,
          subject: cfg.subject,
          bank_id: cfg.bank_id,
          duration: cfg.duration,
          types: cfg.types,
          scores: cfg.scores
        });
        const examId = Number(res?.exam_id || res?.id || 0);
        if (!Number.isFinite(examId) || examId <= 0) throw new Error('创建考试失败');
        wx.hideLoading();
        this.setData({ examCreating: false });
        wx.navigateTo({ url: `/pages/exam-run/exam-run?exam_id=${examId}` });
        this.triggerEvent('created', { exam_id: examId }, {});
      } catch (e: any) {
        wx.hideLoading();
        this.setData({ examCreating: false, examMsg: (e && e.message) || '创建失败', examMsgKind: 'error' }, () =>
          this.refreshExamSummary()
        );
      }
    }
  }
});
