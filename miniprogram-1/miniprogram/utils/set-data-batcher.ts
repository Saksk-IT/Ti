type SetDataFn = (patch: Record<string, any>, callback?: () => void) => void;

type BatcherOptions = {
  immediate?: boolean;
};

type PendingBatch = {
  patch: Record<string, any>;
  callbacks: Array<() => void>;
};

function mergePatch(target: Record<string, any>, incoming: Record<string, any>): void {
  if (!incoming || typeof incoming !== 'object') return;
  Object.keys(incoming).forEach((key) => {
    target[key] = incoming[key];
  });
}

export function createSetDataBatcher(setData: SetDataFn) {
  let scheduled = false;
  let pending: PendingBatch | null = null;

  const flush = () => {
    scheduled = false;
    const current = pending;
    pending = null;
    if (!current) return;
    const callbacks = current.callbacks.slice();
    setData(current.patch, () => {
      callbacks.forEach((cb) => {
        try {
          cb();
        } catch (e) {}
      });
    });
  };

  const scheduleFlush = () => {
    if (scheduled) return;
    scheduled = true;
    Promise.resolve().then(flush);
  };

  return (patch: Record<string, any>, callback?: () => void, options?: BatcherOptions) => {
    const immediate = !!options?.immediate;
    if (immediate) {
      setData(patch, callback);
      return;
    }

    if (!pending) {
      pending = { patch: {}, callbacks: [] };
    }
    mergePatch(pending.patch, patch || {});
    if (callback) pending.callbacks.push(callback);
    scheduleFlush();
  };
}
