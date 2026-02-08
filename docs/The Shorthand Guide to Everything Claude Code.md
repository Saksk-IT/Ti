# The Shorthand Guide to Everything Claude Code

> **Author:** cogsec (@affaanmustafa) | 2025-01-17
>
> Here's my complete setup after 10 months of daily use: skills, hooks, subagents, MCPs, plugins, and what actually works.

---

## Skills and Commands

Skills operate like rules, constricted to certain scopes and workflows. They're shorthand to prompts when you need to execute a particular workflow.

After a long session of coding with Opus 4.5, you want to clean out dead code and loose `.md` files? Run `/refactor-clean`. Need testing? `/tdd`, `/e2e`, `/test-coverage`. Skills and commands can be chained together in a single prompt.

<!-- image: chaining commands together -->

I can make a skill that updates codemaps at checkpoints — a way for Claude to quickly navigate your codebase without burning context on exploration.

<!-- image: ~/.claude/skills/codemap-updater.md -->

Commands are skills executed via slash commands. They overlap but are stored differently:

- **Skills:** `~/.claude/skills` — broader workflow definitions
- **Commands:** `~/.claude/commands` — quick executable prompts

```bash
# Example skill structure
~/.claude/skills/
  pmx-guidelines.md      # Project-specific patterns
  coding-standards.md    # Language best practices
  tdd-workflow/          # Multi-file skill with README.md
  security-review/       # Checklist-based skill
```

---

## Hooks

Hooks are trigger-based automations that fire on specific events. Unlike skills, they're constricted to tool calls and lifecycle events.

### Hook Types

| Hook | Timing | Use Case |
| ------ | -------- | ---------- |
| `PreToolUse` | Before a tool executes | Validation, reminders |
| `PostToolUse` | After a tool finishes | Formatting, feedback loops |
| `UserPromptSubmit` | When you send a message | Input preprocessing |
| `Stop` | When Claude finishes responding | Final checks |
| `PreCompact` | Before context compaction | State preservation |
| `Notification` | Permission requests | User alerts |

**Example:** tmux reminder before long-running commands:

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

<!-- image: Example of PostToolUse hook feedback in Claude Code -->

> **Pro tip:** Use the `hookify` plugin to create hooks conversationally instead of writing JSON manually. Run `/hookify` and describe what you want.

---

## Subagents

Subagents are processes your orchestrator (main Claude) can delegate tasks to with limited scopes. They can run in background or foreground, freeing up context for the main agent.

Subagents work nicely with skills — a subagent capable of executing a subset of your skills can be delegated tasks and use those skills autonomously. They can also be sandboxed with specific tool permissions.

```bash
# Example subagent structure
~/.claude/agents/
  planner.md           # Feature implementation planning
  architect.md         # System design decisions
  tdd-guide.md         # Test-driven development
  code-reviewer.md     # Quality/security review
  security-reviewer.md # Vulnerability analysis
  build-error-resolver.md
  e2e-runner.md
  refactor-cleaner.md
```

Configure allowed tools, MCPs, and permissions per subagent for proper scoping.

---

## Rules and Memory

Your `.rules` folder holds `.md` files with best practices Claude should **always** follow. Two approaches:

- **Single `CLAUDE.md`** — Everything in one file (user or project level)
- **Rules folder** — Modular `.md` files grouped by concern

```bash
~/.claude/rules/
  security.md      # No hardcoded secrets, validate inputs
  coding-style.md  # Immutability, file organization
  testing.md       # TDD workflow, 80% coverage
  git-workflow.md  # Commit format, PR process
  agents.md        # When to delegate to subagents
  performance.md   # Model selection, context management
```

**Example rules:**

- No emojis in codebase
- Refrain from purple hues in frontend
- Always test code before deployment
- Prioritize modular code over mega-files
- Never commit `console.log`s

---

## MCPs (Model Context Protocol)

MCPs connect Claude to external services directly. Not a replacement for APIs — it's a prompt-driven wrapper around them, allowing more flexibility in navigating information.

**Example:** Supabase MCP lets Claude pull specific data, run SQL directly upstream without copy-paste. Same for databases, deployment platforms, etc.

<!-- image: Supabase MCP listing tables within the public schema -->

**Chrome in Claude:** A built-in plugin MCP that lets Claude autonomously control your browser — clicking around to see how things work.

### CRITICAL: Context Window Management

Be picky with MCPs. Keep all MCPs in user config but disable everything unused. Navigate to `/plugins` and scroll down or run `/mcp`.

Your 200k context window before compacting might only be **70k** with too many tools enabled. Performance degrades significantly.

<!-- image: Using /plugins to navigate to MCPs and check status -->

> **Rule of thumb:** Have 20–30 MCPs in config, but keep **under 10 enabled** / **under 80 tools active**.

---

## Plugins

Plugins package tools for easy installation instead of tedious manual setup. A plugin can be a skill + MCP combined, or hooks/tools bundled together.

### Installing Plugins

```bash
# Add a marketplace
claude plugin marketplace add https://github.com/mixedbread-ai/mgrep

# Open Claude, run /plugins, find new marketplace, install from there
```

<!-- image: Newly installed Mixedbread-Grep marketplace -->

### LSP Plugins

Particularly useful if you run Claude Code outside editors frequently. Language Server Protocol gives Claude real-time type checking, go-to-definition, and intelligent completions without needing an IDE open.

```bash
# Enabled plugins example
typescript-lsp@claude-plugins-official  # TypeScript intelligence
pyright-lsp@claude-plugins-official     # Python type checking
hookify@claude-plugins-official         # Create hooks conversationally
mgrep@Mixedbread-Grep                   # Better search than ripgrep
```

> Same warning as MCPs — watch your context window.

---

## Tips and Tricks

### Keyboard Shortcuts

| Shortcut | Action |
| ---------- | -------- |
| `Ctrl+U` | Delete entire line (faster than backspace spam) |
| `!` | Quick bash command prefix |
| `@` | Search for files |
| `/` | Initiate slash commands |
| `Shift+Enter` | Multi-line input |
| `Tab` | Toggle thinking display |
| `Esc Esc` | Interrupt Claude / restore code |

### Parallel Workflows

- **`/fork`** — Fork conversations to do non-overlapping tasks in parallel instead of spamming queued messages
- **Git Worktrees** — For overlapping parallel Claudes without conflicts. Each worktree is an independent checkout:

```bash
git worktree add ../feature-branch feature-branch
# Now run separate Claude instances in each worktree
```

### tmux for Long-Running Commands

Stream and watch logs/bash processes Claude runs.

<!-- video: Letting Claude Code spin up frontend and backend servers, monitoring logs via tmux -->

```bash
tmux new -s dev
# Claude runs commands here, you can detach and reattach
tmux attach -t dev
```

### mgrep > grep

`mgrep` is a significant improvement from ripgrep/grep. Install via plugin marketplace, then use the `/mgrep` skill. Works with both local search and web search.

```bash
mgrep "function handleSubmit"                    # Local search
mgrep --web "Next.js 15 app router changes"      # Web search
```

### Other Useful Commands

| Command | Description |
| --------- | ------------- |
| `/rewind` | Go back to a previous state |
| `/statusline` | Customize with branch, context %, todos |
| `/checkpoints` | File-level undo points |
| `/compact` | Manually trigger context compaction |

---

## GitHub Actions CI/CD

Set up code review on your PRs with GitHub Actions. Claude can review PRs automatically when configured.

<!-- image: Claude approving a bug fix PR -->

---

## Sandboxing

Use sandbox mode for risky operations — Claude runs in restricted environment without affecting your actual system.

> Use `--dangerously-skip-permissions` to do the opposite and let Claude roam free. **This can be destructive if not careful.**

---

## On Editors

While an editor isn't needed, it can positively or negatively impact your Claude Code workflow. Claude Code works from any terminal, but pairing it with a capable editor unlocks real-time file tracking, quick navigation, and integrated command execution.

### Zed (Author's Preference)

A Rust-based editor that's lightweight, fast, and highly customizable.

**Why Zed works well with Claude Code:**

- **Agent Panel Integration** — Track file changes in real-time as Claude edits. Jump between files Claude references without leaving the editor
- **Performance** — Written in Rust, opens instantly and handles large codebases without lag
- **`CMD+Shift+R` Command Palette** — Quick access to all custom slash commands, debuggers, and tools in a searchable UI
- **Minimal Resource Usage** — Won't compete with Claude for system resources during heavy operations
- **Vim Mode** — Full vim keybindings if that's your thing

<!-- image: Zed Editor with custom commands dropdown using CMD+Shift+R. Following mode shown as the bullseye in the bottom right. -->

**Editor integration tips:**

- Split your screen — Terminal with Claude Code on one side, editor on the other
- `Ctrl+G` — Quickly open the file Claude is currently working on in Zed
- **Auto-save** — Enable so Claude's file reads are always current
- **Git integration** — Use editor's git features to review Claude's changes before committing
- **File watchers** — Most editors auto-reload changed files; verify this is enabled

### VSCode / Cursor

Also a viable choice. You can use it in terminal format with automatic sync via `\ide` enabling LSP functionality (somewhat redundant with plugins now), or opt for the extension which is more integrated with the editor UI.

> See the docs at <https://code.claude.com/docs/en/vs-code>

---

## My Setup

### Installed Plugins

Installed (usually only 4–5 enabled at a time):

```text
ralph-wiggum@claude-code-plugins       # Loop automation
frontend-design@claude-code-plugins    # UI/UX patterns
commit-commands@claude-code-plugins    # Git workflow
security-guidance@claude-code-plugins  # Security checks
pr-review-toolkit@claude-code-plugins  # PR automation
typescript-lsp@claude-plugins-official # TS intelligence
hookify@claude-plugins-official        # Hook creation
code-simplifier@claude-plugins-official
feature-dev@claude-code-plugins
explanatory-output-style@claude-code-plugins
code-review@claude-code-plugins
context7@claude-plugins-official       # Live documentation
pyright-lsp@claude-plugins-official    # Python types
mgrep@Mixedbread-Grep                  # Better search
```

### MCP Servers

Configured (User Level):

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

Disabled per project (context window management):

```json
// In ~/.claude.json under projects.[path].disabledMcpServers
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

> **Key insight:** 14 MCPs configured but only ~5–6 enabled per project. Keeps context window healthy.

### Key Hooks

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

### Custom Status Line

Shows user, directory, git branch with dirty indicator, context remaining %, model, time, and todo count.

<!-- image: Example statusline in Mac root directory -->

### Rules Structure

```text
~/.claude/rules/
  security.md      # Mandatory security checks
  coding-style.md  # Immutability, file size limits
  testing.md       # TDD, 80% coverage
  git-workflow.md  # Conventional commits
  agents.md        # Subagent delegation rules
  patterns.md      # API response formats
  performance.md   # Model selection (Haiku vs Sonnet vs Opus)
  hooks.md         # Hook documentation
```

### Configured Subagents

```text
~/.claude/agents/
  planner.md           # Break down features
  architect.md         # System design
  tdd-guide.md         # Write tests first
  code-reviewer.md     # Quality review
  security-reviewer.md # Vulnerability scan
  build-error-resolver.md
  e2e-runner.md        # Playwright tests
  refactor-cleaner.md  # Dead code removal
  doc-updater.md       # Keep docs synced
```

---

## Key Takeaways

1. **Don't overcomplicate** — treat configuration like fine-tuning, not architecture
2. **Context window is precious** — disable unused MCPs and plugins
3. **Parallel execution** — fork conversations, use git worktrees
4. **Automate the repetitive** — hooks for formatting, linting, reminders
5. **Scope your subagents** — limited tools = focused execution

---

## References

- [Plugins Reference](https://docs.anthropic.com/en/docs/claude-code/plugins)
- [Hooks Documentation](https://docs.anthropic.com/en/docs/claude-code/hooks)
- [Checkpointing](https://docs.anthropic.com/en/docs/claude-code/checkpoints)
- [Interactive Mode](https://docs.anthropic.com/en/docs/claude-code/interactive-mode)
- [Memory System](https://docs.anthropic.com/en/docs/claude-code/memory)
- [Subagents](https://docs.anthropic.com/en/docs/claude-code/sub-agents)
- [MCP Overview](https://docs.anthropic.com/en/docs/claude-code/mcp)

> **Note:** This is a subset of detail. The author might make more posts on specifics if people are interested.
