function clamp(value: number, min: number, max: number): number {
  if (!Number.isFinite(value)) return min;
  return Math.max(min, Math.min(max, value));
}

function computeQuadrantLabel(purityPct: number, coveragePct: number) {
  const purityHigh = purityPct >= 80;
  const covHigh = coveragePct >= 70;

  if (purityHigh && covHigh) {
    return { label: '优质资产', hint: '保持收藏纪律，定期清洗“含错率”偏高的题型。' };
  }
  if (purityHigh && !covHigh) {
    return { label: '精选扩面', hint: '收藏池很干净，继续扩面收藏以补齐关键题型结构。' };
  }
  if (!purityHigh && covHigh) {
    return { label: '高噪资产', hint: '覆盖已大但噪声偏高，建议先清洗再补齐，避免越收越乱。' };
  }
  return { label: '待清洗', hint: '先建立收藏标准：只收典型错因/高价值题，再逐步扩面。' };
}

Component({
  options: {
    styleIsolation: 'apply-shared',
    addGlobalClass: true
  },
  properties: {
    contextName: { type: String, value: '' },
    statsLoading: { type: Boolean, value: false },
    statsError: { type: String, value: '' },
    statsOverview: {
      type: Object,
      value: {},
      observer(this: any) {
        this.computeQuadrant();
      }
    },
    statsTrend: { type: Array, value: [] },
    displayTypes: { type: Array, value: [] },
    heatCells: { type: Array, value: [] },
    statsAdvice: { type: Array, value: [] },
    ringAccuracy: { type: Number, value: 0 },
    ringCompletion: {
      type: Number,
      value: 0,
      observer(this: any) {
        this.computeQuadrant();
      }
    },
    ringActive: { type: Number, value: 0 },
    activeDaysRate: { type: Number, value: 0 },
    favMistakeRateText: { type: String, value: '0%' }
  },
  data: {
    quadDotLeft: 50,
    quadDotTop: 50,
    quadLabel: '待清洗',
    quadHint: '先建立收藏标准：只收典型错因/高价值题，再逐步扩面。',
    purityText: '0%'
  },
  lifetimes: {
    attached(this: any) {
      this.computeQuadrant();
    }
  },
  methods: {
    computeQuadrant(this: any) {
      const coverage = clamp(Number(this.data.ringCompletion || 0), 0, 100);
      const overview: any = this.data.statsOverview || {};
      const total = Number(overview?.total || 0) || 0;
      const mistakes = Number(overview?.mistakes || 0) || 0;
      const purity = total > 0 ? clamp(((total - mistakes) / total) * 100, 0, 100) : 0;
      const dotLeft = clamp(coverage, 6, 94);
      const dotTop = clamp(100 - purity, 6, 94);
      const { label, hint } = computeQuadrantLabel(purity, coverage);
      this.setData({
        quadDotLeft: dotLeft,
        quadDotTop: dotTop,
        quadLabel: label,
        quadHint: hint,
        purityText: `${purity.toFixed(0)}%`
      });
    }
  }
});
