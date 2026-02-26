/**
 * typed-set-data.ts
 * 将 setData 的 as any 集中到一处，页面代码不再需要 as any
 */
export function typedSetData(
  ctx: WechatMiniprogram.Component.TrivialInstance | WechatMiniprogram.Page.TrivialInstance,
  data: Record<string, unknown>,
  callback?: () => void
): void {
  ctx.setData(data as WechatMiniprogram.IAnyObject, callback);
}
