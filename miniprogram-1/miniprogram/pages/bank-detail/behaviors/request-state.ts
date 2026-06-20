type RequestStateOptions = {
  loadingKey?: string;
  errorKey?: string;
  clearErrorOnStart?: boolean;
};

export const requestStateBehavior = Behavior({
  methods: {
    startLoading(this: any, options?: RequestStateOptions) {
      const loadingKey = options?.loadingKey || 'loading';
      const patch: Record<string, any> = { [loadingKey]: true };
      if (options?.clearErrorOnStart !== false) {
        patch[options?.errorKey || 'error'] = '';
      }
      this.setData(patch);
    },

    endLoading(this: any, options?: RequestStateOptions) {
      const loadingKey = options?.loadingKey || 'loading';
      this.setData({ [loadingKey]: false });
    },

    setRequestError(this: any, error: string, options?: RequestStateOptions) {
      const errorKey = options?.errorKey || 'error';
      this.setData({ [errorKey]: String(error || '').trim() });
    },

    clearRequestError(this: any, options?: RequestStateOptions) {
      const errorKey = options?.errorKey || 'error';
      this.setData({ [errorKey]: '' });
    },

    async withRequestState<T = any>(
      this: any,
      runner: () => Promise<T>,
      options?: RequestStateOptions
    ): Promise<T> {
      this.startLoading(options);
      try {
        const result = await runner();
        this.endLoading(options);
        return result;
      } catch (e: any) {
        this.setRequestError((e && e.message) ? String(e.message) : '请求失败', options);
        this.endLoading(options);
        throw e;
      }
    }
  }
});
