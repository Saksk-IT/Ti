# 项目规则（Claude）

本文件用于约束 AI 助手在此仓库内的工作方式，专注于工程规则与交付质量。请将标注为 **MUST/禁止** 的内容视为硬约束。

## Project Overview

- Primary languages: Python, HTML/Markdown, C# (WPF/.NET), TypeScript. When diagnosing issues, check the specific engine/module the user mentions rather than assuming the default/built-in component.

## Windows Development

- Always use `cmd /c` wrapper when configuring MCP servers on Windows
- Be aware of MSYS bash path incompatibility with Python on Windows - use native Windows paths
- PowerShell 5.1 is the default on most Windows systems - avoid PS 7+ syntax (e.g., ternary operators)
- Use backtick-free PowerShell patterns; avoid backtick line continuation
- Test for encoding issues with Chinese characters in build scripts

## Communication

用户使用英文和中文（中文）进行交流。请使用与用户相同的语言回复。当生成面向中国市场应用（微信小程序、WPF 应用）的用户可见字符串、标签或文档时，使用中文文本。

## Code Editing Rules

在执行 Edit 操作前，必须先完整读取文件。禁止基于对文件内容的假设进行编辑——先用 Read 读取，再用 Edit 修改。

- Always fully read files before attempting Edit tool calls. Never edit a file that hasn't been read in the current context.

## UI Development

- When fixing UI bugs (WPF/Electron), ask the user to clarify the exact expected behavior before implementing. Distinguish between 'show latest result' vs 'accumulate all results' patterns.
- This project targets WPF (.NET/C#). Do NOT use UWP-only APIs or properties (e.g., CharacterSpacing). Always verify API availability against WPF before using.

## Platform Compatibility

本项目使用 Python、HTML 和 C#（.NET/WPF）。处理 WPF/XAML 时，避免使用 UWP 专属属性（如 `CharacterSpacing`），始终验证 API 与 WPF 的兼容性。编写 PowerShell 脚本时，以 PowerShell 5.1 语法为目标（不使用 PS 7+ 特性，如三元运算符或空合并运算符）。

## Debugging Guidelines

诊断 bug 时，先请用户明确具体的复现条件，再提出修复方案。不要假设根因——先通过阅读相关代码路径和日志收集证据。

## Build & Test

进行多文件变更后，必须在报告完成前运行项目构建命令和所有测试。对于 .NET/WPF 项目使用 `dotnet build`，对于 Python 项目使用已配置的测试运行器。

## Security

- When running security audits, check which issues are already fixed before attempting patches
- Follow OWASP methodology for security scans
- Always commit security fixes with clear descriptions of what was patched

## 0) 不可协商（MUST）

- 始终使用简体中文进行响应。
- 每条助手消息必须以以下两行开头：
  1) `【（必须填写本次实际使用的模型名称）】`
  2) `亲爱的 Wang`
- 每次对话结尾做本次对话的总结并且必须注明实际使用的：`工具 / MCP / skills`（没有则写“无”）。推荐格式：
  - `本次使用：工具（...）；MCP（...）；skills（...）。`
- 本轮任务完成后：在做完最小验证后，自动提交本次相关改动（只包含本次任务；提交信息需能概括改动）。

## 1) 范围与兼容性（MUST）

- 允许：修改后端（Flask）代码、添加新的小程序页面、添加新的后端端点、为可维护性做必要重构。
- 保持兼容性：小程序和网页必须共享相同的数据与语义（包括但不限于：收藏 / 错误 / 用户答案 / 用户进度 / 考试）。
- 文件与版本控制（默认策略，除非我明确要求）：  
  - 默认：不删除现有文件；优先在原文件上做**增量修改**，保留本地版本与上下文。
  - 例外（需先确认）：若**必须**删除文件或进行破坏性改动/大规模重构，先给出「原因 / 替代方案 / 影响评估」，并等待确认后再执行。

## 2.1 执行顺序（给 AI 的固定模板）

1. 用 1～2 句话复述目标 + 关键约束（端：小程序/Web；是否涉及 UI；是否要新增接口）。
2. 选择并声明将使用的 skills / MCP（如不需要也要声明"无"）。
3. 需要补充信息时，先用第 5 节的"选项式澄清问题"问 2～4 个问题再实施。
4. 修改代码尽量小步、可回滚；优先遵循现有模式与命名。
5. 交付前做最小验证（能跑就跑；不能跑就说明原因与手动验证步骤）。

## 2.2 任务开始检查清单（MUST）

每次收到新任务时，AI 必须在内部完成以下检查（无需输出给用户）：

1. [ ] 扫描用户消息中的关键词，匹配 2.5 节触发条件
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
