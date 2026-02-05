function clamp(value: number, min: number, max: number): number {
  if (!Number.isFinite(value)) return min;
  return Math.max(min, Math.min(max, value));
}

function computeQuadrantLabel(accuracyPct: number, completionPct: number) {
  const accHigh = accuracyPct >= 70;
  const compHigh = completionPct >= 70;

  if (accHigh && compHigh) {
    return { label: '稳态清零', hint: '继续保持，优先清理高复错题型并做错因归档。' };
  }
  if (accHigh && !compHigh) {
    return { label: '扩面治理', hint: '纠错效率已建立，继续扩大覆盖面，避免遗留盲区。' };
  }
  if (!accHigh && compHigh) {
    return { label: '深挖错因', hint: '覆盖较广但纠错不稳，建议按题型/知识点做专项训练与复盘。' };
  }
  return { label: '起步治理', hint: '先从高频错因入手，小范围循环训练直至稳定纠错。' };
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
    statsOverview: { type: Object, value: {} },
    statsTrend: { type: Array, value: [] },
    displayTypes: { type: Array, value: [] },
    heatCells: { type: Array, value: [] },
    statsAdvice: { type: Array, value: [] },
    ringAccuracy: {
      type: Number,
      value: 0,
      observer(this: any) {
        this.computeQuadrant();
      }
    },
    ringCompletion: {
      type: Number,
      value: 0,
      observer(this: any) {
        this.computeQuadrant();
      }
    },
    ringRepeat: { type: Number, value: 0 },
    repeatRateText: { type: String, value: '0%' },
    mistakeRateText: { type: String, value: '0%' }
  },
  data: {
    quadDotLeft: 50,
    quadDotTop: 50,
    quadLabel: '起步治理',
    quadHint: '先从高频错因入手，小范围循环训练直至稳定纠错。'
  },
  lifetimes: {
    attached(this: any) {
      this.computeQuadrant();
    }
  },
  methods: {
    computeQuadrant(this: any) {
      const accuracy = clamp(Number(this.data.ringAccuracy || 0), 0, 100);
      const completion = clamp(Number(this.data.ringCompletion || 0), 0, 100);
      const dotLeft = clamp(completion, 6, 94);
      const dotTop = clamp(100 - accuracy, 6, 94);
      const { label, hint } = computeQuadrantLabel(accuracy, completion);
      this.setData({ quadDotLeft: dotLeft, quadDotTop: dotTop, quadLabel: label, quadHint: hint });
    }
  }
});
