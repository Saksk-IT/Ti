# 项目规则（AI）

本文件用于约束 AI 助手在此仓库内的工作方式，专注于工程规则与交付质量。请将标注为 **MUST/禁止** 的内容视为硬约束。

## 0) 不可协商（MUST）

- 始终使用简体中文进行响应。
- 每条助手消息必须以以下两行开头：
  1) `【（必须填写本次实际使用的模型名称）】`
  2) `亲爱的 Wang`
- 结尾做简单本轮总结。
- 本轮任务完成后：在做完最小验证后，自动提交本次相关改动（只包含本次任务；提交信息需能概括改动。

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
  
  # Agent Orchestration

## Available Agents

Located in `~/.claude/agents/`:

| Agent | Purpose | When to Use |
|-------|---------|-------------|
| planner | Implementation planning | Complex features, refactoring |
| architect | System design | Architectural decisions |
| tdd-guide | Test-driven development | New features, bug fixes |
| code-reviewer | Code review | After writing code |
| security-reviewer | Security analysis | Before commits |
| build-error-resolver | Fix build errors | When build fails |
| e2e-runner | E2E testing | Critical user flows |
| refactor-cleaner | Dead code cleanup | Code maintenance |
| doc-updater | Documentation | Updating docs |

## Immediate Agent Usage

No user prompt needed:
1. Complex feature requests - Use **planner** agent
2. Code just written/modified - Use **code-reviewer** agent
3. Bug fix or new feature - Use **tdd-guide** agent
4. Architectural decision - Use **architect** agent

## Parallel Task Execution

ALWAYS use parallel Task execution for independent operations:

```markdown
# GOOD: Parallel execution
Launch 3 agents in parallel:
1. Agent 1: Security analysis of auth module
2. Agent 2: Performance review of cache system
3. Agent 3: Type checking of utilities

# BAD: Sequential when unnecessary
First agent 1, then agent 2, then agent 3
```

## Multi-Perspective Analysis

For complex problems, use split role sub-agents:
- Factual reviewer
- Senior engineer
- Security expert
- Consistency reviewer
- Redundancy checker


# Coding Style

## Immutability (CRITICAL)

ALWAYS create new objects, NEVER mutate existing ones:

```
// Pseudocode
WRONG:  modify(original, field, value) → changes original in-place
CORRECT: update(original, field, value) → returns new copy with change
```

Rationale: Immutable data prevents hidden side effects, makes debugging easier, and enables safe concurrency.

## File Organization

MANY SMALL FILES > FEW LARGE FILES:
- High cohesion, low coupling
- 200-400 lines typical, 800 max
- Extract utilities from large modules
- Organize by feature/domain, not by type

## Error Handling

ALWAYS handle errors comprehensively:
- Handle errors explicitly at every level
- Provide user-friendly error messages in UI-facing code
- Log detailed error context on the server side
- Never silently swallow errors

## Input Validation

ALWAYS validate at system boundaries:
- Validate all user input before processing
- Use schema-based validation where available
- Fail fast with clear error messages
- Never trust external data (API responses, user input, file content)

## Code Quality Checklist

Before marking work complete:
- [ ] Code is readable and well-named
- [ ] Functions are small (<50 lines)
- [ ] Files are focused (<800 lines)
- [ ] No deep nesting (>4 levels)
- [ ] Proper error handling
- [ ] No hardcoded values (use constants or config)
- [ ] No mutation (immutable patterns used)


# Git Workflow

## Commit Message Format

```
<type>: <description>

<optional body>
```

Types: feat, fix, refactor, docs, test, chore, perf, ci

Note: Attribution disabled globally via ~/.claude/settings.json.

## Pull Request Workflow

When creating PRs:
1. Analyze full commit history (not just latest commit)
2. Use `git diff [base-branch]...HEAD` to see all changes
3. Draft comprehensive PR summary
4. Include test plan with TODOs
5. Push with `-u` flag if new branch

## Feature Implementation Workflow

1. **Plan First**
   - Use **planner** agent to create implementation plan
   - Identify dependencies and risks
   - Break down into phases

2. **TDD Approach**
   - Use **tdd-guide** agent
   - Write tests first (RED)
   - Implement to pass tests (GREEN)
   - Refactor (IMPROVE)
   - Verify 80%+ coverage

3. **Code Review**
   - Use **code-reviewer** agent immediately after writing code
   - Address CRITICAL and HIGH issues
   - Fix MEDIUM issues when possible

4. **Commit & Push**
   - Detailed commit messages
   - Follow conventional commits format


# Hooks System

## Hook Types

- **PreToolUse**: Before tool execution (validation, parameter modification)
- **PostToolUse**: After tool execution (auto-format, checks)
- **Stop**: When session ends (final verification)

## Auto-Accept Permissions

Use with caution:
- Enable for trusted, well-defined plans
- Disable for exploratory work
- Never use dangerously-skip-permissions flag
- Configure `allowedTools` in `~/.claude.json` instead

## TodoWrite Best Practices

Use TodoWrite tool to:
- Track progress on multi-step tasks
- Verify understanding of instructions
- Enable real-time steering
- Show granular implementation steps

Todo list reveals:
- Out of order steps
- Missing items
- Extra unnecessary items
- Wrong granularity
- Misinterpreted requirements


# Common Patterns

## Skeleton Projects

When implementing new functionality:
1. Search for battle-tested skeleton projects
2. Use parallel agents to evaluate options:
   - Security assessment
   - Extensibility analysis
   - Relevance scoring
   - Implementation planning
3. Clone best match as foundation
4. Iterate within proven structure

## Design Patterns

### Repository Pattern

Encapsulate data access behind a consistent interface:
- Define standard operations: findAll, findById, create, update, delete
- Concrete implementations handle storage details (database, API, file, etc.)
- Business logic depends on the abstract interface, not the storage mechanism
- Enables easy swapping of data sources and simplifies testing with mocks

### API Response Format

Use a consistent envelope for all API responses:
- Include a success/status indicator
- Include the data payload (nullable on error)
- Include an error message field (nullable on success)
- Include metadata for paginated responses (total, page, limit)


# Performance Optimization

## Model Selection Strategy

**Haiku 4.5** (90% of Sonnet capability, 3x cost savings):
- Lightweight agents with frequent invocation
- Pair programming and code generation
- Worker agents in multi-agent systems

**Sonnet 4.5** (Best coding model):
- Main development work
- Orchestrating multi-agent workflows
- Complex coding tasks

**Opus 4.5** (Deepest reasoning):
- Complex architectural decisions
- Maximum reasoning requirements
- Research and analysis tasks

## Context Window Management

Avoid last 20% of context window for:
- Large-scale refactoring
- Feature implementation spanning multiple files
- Debugging complex interactions

Lower context sensitivity tasks:
- Single-file edits
- Independent utility creation
- Documentation updates
- Simple bug fixes

## Extended Thinking + Plan Mode

Extended thinking is enabled by default, reserving up to 31,999 tokens for internal reasoning.

Control extended thinking via:
- **Toggle**: Option+T (macOS) / Alt+T (Windows/Linux)
- **Config**: Set `alwaysThinkingEnabled` in `~/.claude/settings.json`
- **Budget cap**: `export MAX_THINKING_TOKENS=10000`
- **Verbose mode**: Ctrl+O to see thinking output

For complex tasks requiring deep reasoning:
1. Ensure extended thinking is enabled (on by default)
2. Enable **Plan Mode** for structured approach
3. Use multiple critique rounds for thorough analysis
4. Use split role sub-agents for diverse perspectives

## Build Troubleshooting

If build fails:
1. Use **build-error-resolver** agent
2. Analyze error messages
3. Fix incrementally
4. Verify after each fix


# Security Guidelines

## Mandatory Security Checks

Before ANY commit:
- [ ] No hardcoded secrets (API keys, passwords, tokens)
- [ ] All user inputs validated
- [ ] SQL injection prevention (parameterized queries)
- [ ] XSS prevention (sanitized HTML)
- [ ] CSRF protection enabled
- [ ] Authentication/authorization verified
- [ ] Rate limiting on all endpoints
- [ ] Error messages don't leak sensitive data

## Secret Management

- NEVER hardcode secrets in source code
- ALWAYS use environment variables or a secret manager
- Validate that required secrets are present at startup
- Rotate any secrets that may have been exposed

## Security Response Protocol

If security issue found:
1. STOP immediately
2. Use **security-reviewer** agent
3. Fix CRITICAL issues before continuing
4. Rotate any exposed secrets
5. Review entire codebase for similar issues


# Testing Requirements

## Minimum Test Coverage: 80%

Test Types (ALL required):
1. **Unit Tests** - Individual functions, utilities, components
2. **Integration Tests** - API endpoints, database operations
3. **E2E Tests** - Critical user flows (framework chosen per language)

## Test-Driven Development

MANDATORY workflow:
1. Write test first (RED)
2. Run test - it should FAIL
3. Write minimal implementation (GREEN)
4. Run test - it should PASS
5. Refactor (IMPROVE)
6. Verify coverage (80%+)

## Troubleshooting Test Failures

1. Use **tdd-guide** agent
2. Check test isolation
3. Verify mocks are correct
4. Fix implementation, not tests (unless tests are wrong)

## Agent Support

- **tdd-guide** - Use PROACTIVELY for new features, enforces write-tests-first
