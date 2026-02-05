/**
 * 为解决小程序主包体积超限（2MB），主包不再内置完整 ECharts。
 *
 * 需要图表的页面/组件请改为在分包内引用分包自己的 echarts.js。
 * 已迁移示例：
 * - pages/bank-detail/components/ec-canvas/echarts.js
 * - pages/subject-detail-v2/components/ec-canvas/echarts.js
 * - packages/data/components/ec-canvas/echarts.js
 */
module.exports = (function () {
  throw new Error('[echarts] 主包已移除完整 ECharts，请在分包内引用对应的 echarts.js');
})();
