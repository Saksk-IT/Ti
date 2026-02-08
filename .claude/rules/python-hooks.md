# Python Hooks

> 扩展自 [common/hooks.md](通用 hooks 规则)，针对本项目 Flask/Python 技术栈。

## PostToolUse Hooks

在 `.claude/settings.local.json` 中配置：

- **ruff**: 编辑 `.py` 文件后自动格式化和 lint
- **mypy/pyright**: 编辑 `.py` 文件后运行类型检查

## 警告

- 编辑文件中发现 `print()` 语句时发出警告（应使用 `logging` 模块代替）
- 编辑文件中发现硬编码密钥时发出警告
