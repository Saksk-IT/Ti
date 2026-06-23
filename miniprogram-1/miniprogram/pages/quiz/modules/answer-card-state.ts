export type AnswerCardHiddenMap = Record<string, boolean>;

export function normalizeAnswerCardKey(questionKey: unknown): string {
  if (questionKey == null) return '';
  return String(questionKey).trim();
}

function cloneAnswerCardHiddenMap(hiddenMap: AnswerCardHiddenMap | null | undefined): AnswerCardHiddenMap {
  const current = hiddenMap || {};
  return Object.keys(current).reduce((next: AnswerCardHiddenMap, key) => {
    next[key] = current[key];
    return next;
  }, {});
}

export function getAnswerCardHidden(hiddenMap: AnswerCardHiddenMap | null | undefined, questionKey: unknown): boolean {
  const key = normalizeAnswerCardKey(questionKey);
  if (!key || !hiddenMap) return false;
  return hiddenMap[key] === true;
}

export function toggleAnswerCardHidden(hiddenMap: AnswerCardHiddenMap | null | undefined, questionKey: unknown): AnswerCardHiddenMap {
  const key = normalizeAnswerCardKey(questionKey);
  const current = hiddenMap || {};
  const next = cloneAnswerCardHiddenMap(current);
  if (!key) return next;
  next[key] = !getAnswerCardHidden(current, key);
  return next;
}

export function resetAnswerCardHidden(hiddenMap: AnswerCardHiddenMap | null | undefined, questionKey?: unknown): AnswerCardHiddenMap {
  const current = hiddenMap || {};
  if (questionKey == null) return {};

  const key = normalizeAnswerCardKey(questionKey);
  if (!key) return cloneAnswerCardHiddenMap(current);

  return Object.keys(current).reduce((next: AnswerCardHiddenMap, itemKey) => {
    if (itemKey !== key) {
      next[itemKey] = current[itemKey];
    }
    return next;
  }, {});
}
