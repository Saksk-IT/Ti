# Ti-Java 补充工程规则

本目录继承仓库根目录 `AGENTS.md` 的全部规则，并增加以下约束：

- `Ti-Java/` 必须能够在未来被独立抽取；生产运行时、构建和测试不得读取父目录文件。
- 根目录旧 Flask、Jinja、静态资源、`miniprogram-1/`、Alembic 与 Compose 只作只读契约参考。
- 旧项目盘点工具必须显式接收 `--legacy-root`，不得成为 Java/Web/小程序的运行时依赖。
- 后端按业务模块组织；禁止建立全局 `controller/service/repository/model` 技术层目录。
- 每个阶段先补契约和测试，再实现；不得以空实现、跳过测试或放宽断言通过验收。
- PostgreSQL 是业务事实源；Redis 仅用于可重建的缓存、限流、会话辅助与短期协调。
- Hibernate 只允许 schema 校验，不允许自动创建或修改业务表。
- `docs/refactor/05-progress.md` 是连续执行的唯一恢复入口，每次提交前后必须更新。
- 每次提交只暂存本阶段在 `Ti-Java/` 中产生的文件；不得暂存根目录既有脏工作区。
