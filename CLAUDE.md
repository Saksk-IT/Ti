## 1) 范围与兼容性（MUST）

- 允许：修改后端（Flask）代码、添加新的小程序页面、添加新的后端端点、为可维护性做必要重构。
- 保持兼容性：小程序和网页必须共享相同的数据与语义（包括但不限于：收藏 / 错误 / 用户答案 / 用户进度 / 考试）。

## 2.1 执行顺序（给 AI 的固定模板）

1. 用 1～2 句话复述目标 + 关键约束（端：小程序/Web；是否涉及 UI；是否要新增接口）。
2. 选择并声明将使用的 skills / MCP（如不需要也要声明"无"）。
3. 需要补充信息时，先用第 5 节的"选项式澄清问题"问 2～4 个问题再实施。
4. 修改代码尽量小步、可回滚；优先遵循现有模式与命名。
5. 交付前做最小验证（能跑就跑；不能跑就说明原因与手动验证步骤）。

## 2.2 任务开始检查清单（MUST）

每次收到新任务时，AI 必须在内部完成以下检查（无需输出给用户）：

1. [ ] 扫描用户消息中的关键词，匹配skills、mcp、commands触发条件
2. [ ] 若匹配到触发条件，自动加载对应 skill 或调用 MCP
3. [ ] 若涉及框架/库用法不确定，主动调用 Context7 查询
4. [ ] 若涉及前端页面调试，主动使用 chrome-devtools 获取页面状态
5. [ ] 若无匹配，声明"本次使用：工具（...）；MCP（无）；skills（无）"

## 3) 前端设计要求（MUST）

- 所有 Web 页面必须适配移动端（响应式布局、触控友好）。
- Web 端与小程序端的主题在元素/颜色/风格上保持一致；新老页面都要适配主题风格切换与深色/浅色模式切换。
- 尽量避免高饱和颜色，使用半饱和颜色代替。
- UI 结构尽量避免“容器套容器”；能用一层容器解决就不要两层互相嵌套。

## 4) 代码风格与结构（SHOULD）

- 尽量保持小变更，避免无关重构（除非明确提出“重构/抛弃/重做”等）。
- 倾向模块化：避免巨大文件；当单文件代码行数超过 1500 行时，按领域/服务/工具等维度拆分。
- 遵循现有项目模式与命名规范。

## 5) 当需求不明确时（MUST）

- 在实施前先提出 2～4 个“可直接选项回复”的澄清问题（避免跑偏）。你可以只回复选项字母/数字，例如：`1C 2A 3B 4A`。
- 说明：这里不限制我“提问的范围”，只是要求尽量把问题做成选择题模板；仍可补充其他澄清问题，并尽量提供可选项。
- 推荐提问模板（按需选 2～4 条）：
  1) 影响端：A) 仅小程序 B) 仅 Web C) 两端都要 D) 先小程序后 Web
  2) 入口/页面/路由：A) 我会提供明确入口 B) 需要你在仓库里帮我定位 C) 题库广场→题库详情 D) 个人题库→题库详情 E) 其他（我补充）
  3) 后端与数据：A) 不需要后端改动 B) 只改现有接口 C) 新增接口 D) 调整数据结构（字段/表）
  4) 兼容性边界：A) 必须兼容旧数据/旧接口/旧页面 B) 允许新增字段但不破坏旧用法 C) 允许迁移（需说明迁移方式） D) 旧页面可保留但不保证一致
- 若仍不明确，最多再追问 1 个开放式问题：请给 1～2 个“期望输入→期望输出”的具体例子（或截图/接口样例）。
- 当功能或设计不完美时，可以给我 1～3 个可选优化灵感，但不要大幅发散。

## 6) 额外业务上下文（MUST）

- 题库详情页存在两个入口：（题库广场 → 题库详情页）与（个人题库 → 题库详情页）。

## 7) ECC 插件可用命令参考

本项目已配置 Everything Claude Code 插件，以下命令可直接使用：

| 命令 | 用途 |
| ---- | ---- |
| `/plan` | 创建实现计划（复杂功能前必用） |
| `/tdd` | 测试驱动开发工作流 |
| `/code-review` | 代码质量审查 |
| `/python-review` | Python 专项代码审查 |
| `/build-fix` | 修复构建错误 |
| `/refactor-clean` | 清理死代码和冗余文件 |
| `/e2e` | 端到端测试 |
| `/test-coverage` | 检查测试覆盖率 |
| `/update-docs` | 更新文档 |

### 项目级 Python 规则

位于 `.claude/rules/`：

- `python-coding-style.md` — PEP 8、类型注解、不可变性
- `python-patterns.md` — Protocol、Dataclass、Flask 蓝图模式
- `python-testing.md` — pytest、覆盖率、Flask 测试 fixtures
- `python-security.md` — 密钥管理、bandit 扫描、Flask 安全要点
- `python-hooks.md` — PostToolUse hooks 说明

### 项目级 Hooks

配置于 `.claude/settings.local.json`：

- **PostToolUse**: 编辑 `.py` 文件后检测 `print()` 语句并警告；检测硬编码密钥
- **PreToolUse**: Flask 开发服务器和 pytest 运行前提醒使用 tmux

## 8) 骨架屏（Skeleton Loading）规范

### 已知坑点

- **flex 容器必须设 `width: 100%`**：若父容器使用 `max-width` + `flex`，骨架阶段内容少会导致容器宽度远小于数据加载后的宽度，产生跳动。修复方式：`width: 100%; box-sizing: border-box;`。
- **骨架必须复用真实组件的 CSS 类**：不要用 `border:none; background:transparent; padding:0` 覆盖真实样式。直接使用 `.forum-comment`、`.comment-header`、`.comment-footer` 等原始类，保证 padding/border/border-radius 一致。
- **骨架行高要匹配实际 font-size / line-height**：例如 `post-title` 是 20px，`post-body` 行高 25.5px（15px × 1.7），`comment-body` 行高 22.4px（14px × 1.6）。

### 验证方法（CDP 远程调试）

当骨架屏尺寸不确定时，使用 Chrome DevTools Protocol 实测：

1. 启动 Chrome：`chrome.exe --remote-debugging-port=9222 --user-data-dir="C:/tmp/chrome-debug"`
2. 用 `Network.setBlockedURLs` 阻断 API 请求，使骨架保持可见
3. 用 `Runtime.evaluate` 获取 `offsetWidth` / `offsetHeight` 与加载后对比
4. 确保骨架阶段与数据加载后的容器宽度一致（高度差异可接受）

### 项目中已有骨架样式

复用 `_styles.html` 中的基础类：
- `.forum-skeleton-row`：矩形占位条（shimmer 动画）
- `.forum-skeleton-avatar`：圆形头像占位（shimmer 动画）
- `.forum-detail-skel`：详情页骨架容器（pulse 动画）
- `@keyframes skeleton-shimmer`：横向光泽滑动
