# Claude Code 完全简明指南

> **作者：** cogsec (@affaanmustafa) | 2025-01-17
>
> 这是我日常使用 10 个月后的完整配置：skills、hooks、子代理、MCPs、插件，以及哪些真正有用。

---

## Skills 与 Commands

Skills 类似于规则，限定在特定的作用域和工作流中。当你需要执行某个特定工作流时，它们是提示词的简写形式。

用 Opus 4.5 进行了一长段编码后，想清理死代码和多余的 `.md` 文件？运行 `/refactor-clean`。需要测试？`/tdd`、`/e2e`、`/test-coverage`。Skills 和 commands 可以在一条提示中链式组合使用。

<!-- image: 链式组合 commands -->

我可以创建一个在检查点更新 codemap 的 skill —— 让 Claude 快速导航代码库，而不必在探索上消耗上下文。

<!-- image: ~/.claude/skills/codemap-updater.md -->

Commands 是通过斜杠命令执行的 skills。两者有重叠，但存储位置不同：

- **Skills：** `~/.claude/skills` —— 更广泛的工作流定义
- **Commands：** `~/.claude/commands` —— 快速可执行的提示

```bash
# Skill 目录结构示例
~/.claude/skills/
  pmx-guidelines.md      # 项目特定模式
  coding-standards.md    # 语言最佳实践
  tdd-workflow/          # 多文件 skill（含 README.md）
  security-review/       # 基于检查清单的 skill
```

---

## Hooks

Hooks 是基于触发器的自动化，在特定事件发生时触发。与 skills 不同，它们限定在工具调用和生命周期事件上。

### Hook 类型

| Hook | 触发时机 | 用途 |
| ------ | -------- | ---------- |
| `PreToolUse` | 工具执行前 | 校验、提醒 |
| `PostToolUse` | 工具执行后 | 格式化、反馈循环 |
| `UserPromptSubmit` | 发送消息时 | 输入预处理 |
| `Stop` | Claude 完成响应时 | 最终检查 |
| `PreCompact` | 上下文压缩前 | 状态保存 |
| `Notification` | 权限请求时 | 用户提醒 |

**示例：** 在长时间运行的命令前提醒使用 tmux：

```json
{
  "PreToolUse": [
    {
      "matcher": "tool == \"Bash\" && tool_input.command matches \"(npm|pnpm|yarn|cargo|pytest)\"",
      "hooks": [
        {
          "type": "command",
          "command": "if [ -z \"$TMUX\" ]; then echo '[Hook] Consider tmux for session persistence' >&2; fi"
        }
      ]
    }
  ]
}
```

<!-- image: PostToolUse hook 在 Claude Code 中的反馈示例 -->

> **小技巧：** 使用 `hookify` 插件通过对话方式创建 hooks，无需手写 JSON。运行 `/hookify` 并描述你的需求即可。

---

## 子代理（Subagents）

子代理是主编排器（主 Claude）可以委派任务的进程，具有有限的作用域。它们可以在后台或前台运行，为主代理释放上下文空间。

子代理与 skills 配合良好 —— 一个能执行部分 skills 的子代理可以被委派任务并自主使用这些 skills。它们还可以通过特定的工具权限进行沙箱隔离。

```bash
# 子代理目录结构示例
~/.claude/agents/
  planner.md           # 功能实现规划
  architect.md         # 系统设计决策
  tdd-guide.md         # 测试驱动开发
  code-reviewer.md     # 质量/安全审查
  security-reviewer.md # 漏洞分析
  build-error-resolver.md
  e2e-runner.md
  refactor-cleaner.md
```

为每个子代理配置允许的工具、MCPs 和权限，以实现合理的作用域划分。

---

## 规则与记忆（Rules and Memory）

`.rules` 文件夹存放 `.md` 文件，包含 Claude 应**始终**遵循的最佳实践。两种方式：

- **单一 `CLAUDE.md`** —— 所有内容放在一个文件中（用户级或项目级）
- **Rules 文件夹** —— 按关注点分组的模块化 `.md` 文件

```bash
~/.claude/rules/
  security.md      # 禁止硬编码密钥，校验输入
  coding-style.md  # 不可变性，文件组织
  testing.md       # TDD 工作流，80% 覆盖率
  git-workflow.md  # 提交格式，PR 流程
  agents.md        # 何时委派给子代理
  performance.md   # 模型选择，上下文管理
```

**规则示例：**

- 代码库中禁止使用 emoji
- 前端避免使用紫色调
- 部署前必须测试代码
- 优先模块化代码，避免巨型文件
- 禁止提交 `console.log`

---

## MCPs（模型上下文协议）

MCPs 将 Claude 直接连接到外部服务。它不是 API 的替代品 —— 而是围绕 API 的提示驱动封装，在信息导航上提供更大的灵活性。

**示例：** Supabase MCP 让 Claude 直接拉取特定数据、在上游执行 SQL，无需复制粘贴。数据库、部署平台等同理。

<!-- image: Supabase MCP 列出 public schema 中的表 -->

**Chrome in Claude：** 内置的插件 MCP，让 Claude 自主控制你的浏览器 —— 点击浏览以了解页面工作方式。

### 关键：上下文窗口管理

对 MCPs 要精挑细选。将所有 MCPs 保留在用户配置中，但禁用所有未使用的。导航到 `/plugins` 向下滚动，或运行 `/mcp`。

你的 200k 上下文窗口在压缩前可能因启用过多工具而只剩 **70k**。性能会显著下降。

<!-- image: 使用 /plugins 导航到 MCPs 并查看状态 -->

> **经验法则：** 配置中保留 20–30 个 MCPs，但保持**启用不超过 10 个** / **活跃工具不超过 80 个**。

---

## 插件（Plugins）

插件将工具打包以便于安装，省去繁琐的手动配置。一个插件可以是 skill + MCP 的组合，也可以是 hooks/工具的捆绑包。

### 安装插件

```bash
# 添加市场
claude plugin marketplace add https://github.com/mixedbread-ai/mgrep

# 打开 Claude，运行 /plugins，找到新市场，从中安装
```

<!-- image: 新安装的 Mixedbread-Grep 市场 -->

### LSP 插件

如果你经常在编辑器外使用 Claude Code，LSP 插件特别有用。语言服务器协议为 Claude 提供实时类型检查、跳转到定义和智能补全，无需打开 IDE。

```bash
# 已启用的插件示例
typescript-lsp@claude-plugins-official  # TypeScript 智能提示
pyright-lsp@claude-plugins-official     # Python 类型检查
hookify@claude-plugins-official         # 对话式创建 hooks
mgrep@Mixedbread-Grep                   # 比 ripgrep 更好的搜索
```

> 与 MCPs 相同的警告 —— 注意你的上下文窗口。

---

## 技巧与窍门

### 键盘快捷键

| 快捷键 | 功能 |
| ---------- | -------- |
| `Ctrl+U` | 删除整行（比连按退格键快） |
| `!` | 快速 bash 命令前缀 |
| `@` | 搜索文件 |
| `/` | 启动斜杠命令 |
| `Shift+Enter` | 多行输入 |
| `Tab` | 切换思考过程显示 |
| `Esc Esc` | 中断 Claude / 恢复代码 |

### 并行工作流

- **`/fork`** —— 分叉对话以并行执行不重叠的任务，而不是排队发送消息
- **Git Worktrees** —— 用于有重叠的并行 Claude 实例而不产生冲突。每个 worktree 是一个独立的检出：

```bash
git worktree add ../feature-branch feature-branch
# 现在可以在每个 worktree 中运行独立的 Claude 实例
```

### 用 tmux 运行长时间命令

流式查看 Claude 运行的日志和 bash 进程。

<!-- video: 让 Claude Code 启动前后端服务器，通过 tmux 监控日志 -->

```bash
tmux new -s dev
# Claude 在这里运行命令，你可以分离并重新连接
tmux attach -t dev
```

### mgrep 优于 grep

`mgrep` 是对 ripgrep/grep 的显著改进。通过插件市场安装，然后使用 `/mgrep` skill。支持本地搜索和网络搜索。

```bash
mgrep "function handleSubmit"                    # 本地搜索
mgrep --web "Next.js 15 app router changes"      # 网络搜索
```

### 其他实用命令

| 命令 | 说明 |
| --------- | ------------- |
| `/rewind` | 回退到之前的状态 |
| `/statusline` | 自定义显示分支、上下文百分比、待办事项 |
| `/checkpoints` | 文件级撤销点 |
| `/compact` | 手动触发上下文压缩 |

---

## GitHub Actions CI/CD

通过 GitHub Actions 在 PR 上设置代码审查。配置后 Claude 可以自动审查 PR。

<!-- image: Claude 批准一个 bug 修复 PR -->

---

## 沙箱模式（Sandboxing）

对高风险操作使用沙箱模式 —— Claude 在受限环境中运行，不会影响你的实际系统。

> 使用 `--dangerously-skip-permissions` 可以做相反的事情，让 Claude 自由运行。**如果不小心使用，这可能具有破坏性。**

---

## 关于编辑器

虽然编辑器不是必需的，但它可以正面或负面地影响你的 Claude Code 工作流。Claude Code 可以在任何终端中运行，但搭配一个功能强大的编辑器可以解锁实时文件追踪、快速导航和集成命令执行。

### Zed（作者的选择）

基于 Rust 的编辑器，轻量、快速且高度可定制。

**为什么 Zed 与 Claude Code 配合良好：**

- **Agent 面板集成** —— 在 Claude 编辑时实时追踪文件变更。无需离开编辑器即可在 Claude 引用的文件间跳转
- **性能** —— 用 Rust 编写，即时打开，处理大型代码库无卡顿
- **`CMD+Shift+R` 命令面板** —— 在可搜索的 UI 中快速访问所有自定义斜杠命令、调试器和工具
- **资源占用低** —— 在繁重操作期间不会与 Claude 争抢系统资源
- **Vim 模式** —— 完整的 vim 键绑定

<!-- image: Zed 编辑器使用 CMD+Shift+R 显示自定义命令下拉菜单。右下角的靶心图标为 Following 模式。 -->

**编辑器集成技巧：**

- 分屏 —— 一侧是带 Claude Code 的终端，另一侧是编辑器
- `Ctrl+G` —— 在 Zed 中快速打开 Claude 当前正在处理的文件
- **自动保存** —— 启用后 Claude 读取的文件始终是最新的
- **Git 集成** —— 使用编辑器的 git 功能在提交前审查 Claude 的更改
- **文件监视器** —— 大多数编辑器会自动重新加载已更改的文件；确认此功能已启用

### VSCode / Cursor

同样是可行的选择。你可以在终端模式下使用，通过 `\ide` 自动同步以启用 LSP 功能（现在与插件有些冗余），或者选择与编辑器更深度集成的扩展版本。

> 参见文档：<https://code.claude.com/docs/en/vs-code>

---

## 我的配置

### 已安装插件

已安装（通常同时只启用 4–5 个）：

```text
ralph-wiggum@claude-code-plugins       # 循环自动化
frontend-design@claude-code-plugins    # UI/UX 模式
commit-commands@claude-code-plugins    # Git 工作流
security-guidance@claude-code-plugins  # 安全检查
pr-review-toolkit@claude-code-plugins  # PR 自动化
typescript-lsp@claude-plugins-official # TS 智能提示
hookify@claude-plugins-official        # Hook 创建
code-simplifier@claude-plugins-official
feature-dev@claude-code-plugins
explanatory-output-style@claude-code-plugins
code-review@claude-code-plugins
context7@claude-plugins-official       # 实时文档
pyright-lsp@claude-plugins-official    # Python 类型
mgrep@Mixedbread-Grep                  # 更好的搜索
```

### MCP 服务器

已配置（用户级）：

```json
{
  "github":                      { "command": "npx", "args": ["-y", "@modelcontextprotocol/server-github"] },
  "firecrawl":                   { "command": "npx", "args": ["-y", "firecrawl-mcp"] },
  "supabase":                    { "command": "npx", "args": ["-y", "@supabase/mcp-server-supabase@latest", "--project-ref=YOUR_REF"] },
  "memory":                      { "command": "npx", "args": ["-y", "@modelcontextprotocol/server-memory"] },
  "sequential-thinking":         { "command": "npx", "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"] },
  "vercel":                      { "type": "http", "url": "https://mcp.vercel.com" },
  "railway":                     { "command": "npx", "args": ["-y", "@railway/mcp-server"] },
  "cloudflare-docs":             { "type": "http", "url": "https://docs.mcp.cloudflare.com/mcp" },
  "cloudflare-workers-bindings": { "type": "http", "url": "https://bindings.mcp.cloudflare.com/mcp" },
  "cloudflare-workers-builds":   { "type": "http", "url": "https://builds.mcp.cloudflare.com/mcp" },
  "cloudflare-observability":    { "type": "http", "url": "https://observability.mcp.cloudflare.com/mcp" },
  "clickhouse":                  { "type": "http", "url": "https://mcp.clickhouse.cloud/mcp" },
  "AbletonMCP":                  { "command": "uvx", "args": ["ableton-mcp"] },
  "magic":                       { "command": "npx", "args": ["-y", "@magicuidesign/mcp@latest"] }
}
```

按项目禁用（上下文窗口管理）：

```json
// 在 ~/.claude.json 的 projects.[path].disabledMcpServers 下
[
  "playwright",
  "cloudflare-workers-builds",
  "cloudflare-workers-bindings",
  "cloudflare-observability",
  "cloudflare-docs",
  "clickhouse",
  "AbletonMCP",
  "context7",
  "magic"
]
```

> **关键洞察：** 配置了 14 个 MCPs，但每个项目只启用约 5–6 个。保持上下文窗口健康。

### 关键 Hooks

```json
{
  "PreToolUse": [
    { "matcher": "npm|pnpm|yarn|cargo|pytest", "hooks": ["tmux reminder"] },
    { "matcher": "Write && .md file",          "hooks": ["block unless README/CLAUDE"] },
    { "matcher": "git push",                   "hooks": ["open editor for review"] }
  ],
  "PostToolUse": [
    { "matcher": "Edit && .ts/.tsx/.js/.jsx",  "hooks": ["prettier --write"] },
    { "matcher": "Edit && .ts/.tsx",            "hooks": ["tsc --noEmit"] },
    { "matcher": "Edit",                       "hooks": ["grep console.log warning"] }
  ],
  "Stop": [
    { "matcher": "*",                          "hooks": ["check modified files for console.log"] }
  ]
}
```

### 自定义状态栏

显示用户、目录、git 分支（含脏标记）、剩余上下文百分比、模型、时间和待办事项计数。

<!-- image: Mac 根目录下的状态栏示例 -->

### 规则结构

```text
~/.claude/rules/
  security.md      # 强制安全检查
  coding-style.md  # 不可变性，文件大小限制
  testing.md       # TDD，80% 覆盖率
  git-workflow.md  # 约定式提交
  agents.md        # 子代理委派规则
  patterns.md      # API 响应格式
  performance.md   # 模型选择（Haiku vs Sonnet vs Opus）
  hooks.md         # Hook 文档
```

### 已配置的子代理

```text
~/.claude/agents/
  planner.md           # 分解功能
  architect.md         # 系统设计
  tdd-guide.md         # 先写测试
  code-reviewer.md     # 质量审查
  security-reviewer.md # 漏洞扫描
  build-error-resolver.md
  e2e-runner.md        # Playwright 测试
  refactor-cleaner.md  # 死代码清理
  doc-updater.md       # 保持文档同步
```

---

## 核心要点

1. **不要过度复杂化** —— 把配置当作微调，而不是架构设计
2. **上下文窗口很宝贵** —— 禁用未使用的 MCPs 和插件
3. **并行执行** —— 分叉对话，使用 git worktrees
4. **自动化重复工作** —— 用 hooks 处理格式化、lint、提醒
5. **限定子代理作用域** —— 有限的工具 = 专注的执行

---

## 参考资料

- [插件参考](https://docs.anthropic.com/en/docs/claude-code/plugins)
- [Hooks 文档](https://docs.anthropic.com/en/docs/claude-code/hooks)
- [检查点](https://docs.anthropic.com/en/docs/claude-code/checkpoints)
- [交互模式](https://docs.anthropic.com/en/docs/claude-code/interactive-mode)
- [记忆系统](https://docs.anthropic.com/en/docs/claude-code/memory)
- [子代理](https://docs.anthropic.com/en/docs/claude-code/sub-agents)
- [MCP 概览](https://docs.anthropic.com/en/docs/claude-code/mcp)

> **注：** 这只是部分细节。如果大家感兴趣，作者可能会发布更多关于具体内容的文章。
