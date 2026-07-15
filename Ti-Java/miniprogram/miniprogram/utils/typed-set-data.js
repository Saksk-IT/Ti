"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.typedSetData = typedSetData;
/**
 * typed-set-data.ts
 * 将 setData 的 as any 集中到一处，页面代码不再需要 as any
 */
function typedSetData(ctx, data, callback) {
    ctx.setData(data, callback);
}
