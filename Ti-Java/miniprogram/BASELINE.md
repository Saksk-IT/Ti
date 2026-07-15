# 小程序受控基线

- 来源：仓库根目录 `miniprogram-1/` 在提交 `700006dfdfa063deb4387be572911e782bcea0d9` 中受根仓库版本控制的文件。
- 复制日期：2026-07-16。
- 目的：作为 Ti-Java 自己维护的微信原生 TypeScript 小程序；后续只修改本目录副本。
- 未复制：嵌套 `.git`、`node_modules`、`.cloudbase`、`_archived`、`analyse-data.json`、`log.txt`、`project.private.config.json`、缓存和本地日志。
- 旧 `miniprogram-1/` 始终只读，Ti-Java 的构建与运行不得回读该目录。
- 来源提交过滤后共有 611 个受控文件；逐文件 SHA-256 与 `git show 700006d:miniprogram-1/<path>` 一致。`SOURCE-MANIFEST.sha256` 还覆盖本目录新增的 `.gitignore` 与本说明，共校验 613 个文件。

基线保留当前受控的 `.ts` 与微信运行所需 `.js` 文件；两者的漂移将在后续小程序迁移阶段用专项检查治理。
