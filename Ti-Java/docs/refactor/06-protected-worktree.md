# 受保护工作区清单

## 根仓库

在 Ti-Java 实施开始前已经存在、不得修改或提交：

```text
 M AGENTS.md
 D CLAUDE.md
?? .playwright-cli/
?? miniprogram-1/.gitignore
?? output/
```

根仓库当前 `git diff --check` 的既有失败为：

```text
AGENTS.md:16: new blank line at EOF.
```

该错误不由 Ti-Java 修复；阶段提交前应对 `Ti-Java/` 自身单独运行 diff check，并人工核对完整暂存清单。

## 嵌套小程序仓库

`miniprogram-1/.git/` 不得复制。嵌套仓库在开始时已有以下修改：

```text
miniprogram/pages/campus-grades/campus-grades.less
miniprogram/pages/campus-grades/campus-grades.wxml
miniprogram/pages/campus/campus-content.js
miniprogram/pages/campus/campus-content.ts
miniprogram/pages/campus/campus-query-core.js
miniprogram/pages/campus/campus-query-core.ts
miniprogram/pages/campus/campus.js
miniprogram/pages/campus/campus.less
miniprogram/pages/campus/campus.ts
miniprogram/pages/campus/campus.wxml
miniprogram/utils/api-endpoints.ts
tests/campus-content.test.js
```

Ti-Java 小程序副本来自根仓库固定提交 `700006d` 的受控文件，而不是递归复制当前目录。来源、排除项和 SHA-256 清单见 `Ti-Java/miniprogram/BASELINE.md` 与 `SOURCE-MANIFEST.sha256`。

## 每次提交前

```bash
git status --short --branch
git -C miniprogram-1 status --short --branch
git diff --check -- Ti-Java
git diff --cached --name-status
```

只有 `Ti-Java/` 当前阶段文件可以进入暂存区。
