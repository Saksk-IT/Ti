# Mac / Windows 双机开发同步教程（以当前 Mac 为起点）

适用场景：同一名开发者，在 Mac 和 Windows 两台机器上交替开发同一个仓库，要求改动可追溯、可恢复、不丢失。

## 目标

- Windows 开发前，先拿到 Mac 的最新代码。
- Mac 开发前，先拿到 Windows 的最新代码。
- 避免换行符、文件名大小写、未提交改动导致的冲突。

## 核心原则（必须执行）

1. 远程仓库（GitHub/GitLab）是唯一真源。
2. 切机器前必须 `commit + push`。
3. 到新机器后必须先 `pull --rebase`，再开始开发。
4. 不在两台机器同时改同一分支的未同步代码。

## 一次性初始化（在这台 Mac 上先做）

### 1) 检查远程仓库

```bash
git remote -v
```

如果还没有远程仓库，先添加：

```bash
git remote add origin <你的远程仓库地址>
```

### 2) 配置当前仓库的 Git（Mac 推荐）

```bash
git config --local core.autocrlf input
git config --local core.safecrlf true
git config --local pull.rebase true
git config --local rebase.autoStash true
```

说明：
- `core.autocrlf=input`：提交时自动转 LF，检出不强制改写。
- `pull.rebase=true`：默认使用 rebase，减少无意义 merge commit。
- `rebase.autoStash=true`：`pull --rebase` 时自动暂存本地未提交改动。

### 3) 推送当前 Mac 的基线代码

```bash
git status
git add -A
git commit -m "chore: baseline sync from mac"
git push -u origin main
```

如果当前分支不是 `main`，把命令中的 `main` 改为你的主分支名。

## Windows 首次接入

### 1) 克隆仓库

```bash
git clone <你的远程仓库地址>
cd Ti-main
```

### 2) 配置当前仓库 Git（Windows 推荐）

```bash
git config --local core.autocrlf true
git config --local core.safecrlf true
git config --local pull.rebase true
git config --local rebase.autoStash true
git config --local core.ignorecase false
```

说明：
- `core.autocrlf=true`：检出 CRLF、提交转 LF，适合 Windows 编辑器生态。
- `core.ignorecase=false`：尽量显式感知大小写变更，降低跨平台歧义。

## 每日切换流程（最关键）

### A. 在 Mac 结束开发，切去 Windows 前

```bash
git status
git add -A
git commit -m "feat: xxx"   # 或 fix/refactor/docs/chore
git push
```

### B. Windows 开始开发前

```bash
git fetch origin
git pull --rebase
git status
```

确认工作区干净后再写代码。

### C. 在 Windows 结束开发，切回 Mac 前

```bash
git status
git add -A
git commit -m "feat: xxx"
git push
```

### D. Mac 再次开始开发前

```bash
git fetch origin
git pull --rebase
git status
```

## 未完成功能怎么同步（推荐）

如果功能没做完也要切机器，不要把改动只留在本地。

方案 1（推荐）：临时提交到 WIP 分支

```bash
git checkout -b wip/<日期>-<主题>
git add -A
git commit -m "wip: <主题>"
git push -u origin wip/<日期>-<主题>
```

在另一台机器拉取同名分支继续开发。

方案 2：短期 `stash`（仅当天短切换）

```bash
git stash push -m "wip: <主题>"
git pull --rebase
git stash pop
```

注意：`stash` 不适合跨天长期存放，优先使用 WIP 分支。

## 冲突处理（最小流程）

```bash
git pull --rebase
# 按提示解决冲突后：
git add <冲突文件>
git rebase --continue
git push
```

如果想放弃本次 rebase：

```bash
git rebase --abort
```

## 本仓库已落地的跨平台保护

仓库根目录新增 `.gitattributes`，统一了换行符策略：
- 默认文本文件使用 LF。
- `*.bat/*.cmd/*.ps1` 使用 CRLF。
- 常见二进制文件标记为 binary，避免误转换。

这会显著降低 Mac/Windows 互切时“整文件换行变化”的噪音提交。

## 开发纪律检查清单（切机前 30 秒）

1. `git status` 是否干净？
2. 是否已 `commit`？
3. 是否已 `push`？
4. 另一台机器是否已先 `pull --rebase` 再开发？

只要四步都满足，双机同步基本不会出问题。
