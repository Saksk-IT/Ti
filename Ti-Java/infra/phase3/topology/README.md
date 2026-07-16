# Phase 3 独立切换/回滚演练

本目录只用于 `local`/`test` 的认证迁移演练。它在一个固定的 Phase 3 Compose 项目中
提供两套完全独立的 Flask/Java API、PostgreSQL、Redis、网络和命名卷，并把切换限定为：

1. 确认来源 API 正在运行、目标容器不存在、目标卷从未创建；
2. 停止来源 API，确认其运行容器数为零；
3. 从仍在本地隔离项目内的来源 PostgreSQL 生成 `custom`、`no-owner`、`no-acl` 快照；
4. 校验严格 manifest、文件类型/属主/权限/大小/SHA-256 和 PostgreSQL archive；
5. 在全新目标 PostgreSQL/Redis/应用卷恢复，事务失败即整体失败；
6. 对恢复前后的规范化 SQL 流做 SHA-256 语义等价校验：替换 `pg_restore` 自动生成且
   首尾严格配对的 `restrict` guard token；并仅在整条、非引用小写标识符的 `CHECK ...
   = ANY (...)` 定义精确匹配时，将 PostgreSQL 目录反编译产生的静态 ASCII literal
   `varchar[] -> text[]` 两种等价表示折叠为同一表示。值、顺序、cast、表达式或范围改变均不
   归一化。随后施加目标写角色和只读审计角色；
7. 启动目标 API 并再次确认来源 API 仍停止，最后移除来源容器但保留来源卷；
8. 反向回滚执行相同流程，且强制使用新的 rollback-generation 卷，不重新挂载原旧卷。

没有代理、影子流量或双写模式。脚本只使用本目录固定的
[`compose.isolated.yml`](compose.isolated.yml)，不接受外部 Compose 路径，不读取或修改
`Ti-Java/` 父目录中的 Flask Compose、源码、环境文件或数据卷。

## 威胁边界

- `topology_guard.py` 只接受 `local`/`test`，拒绝生产标识、远程 Docker 环境、非 Unix
  Docker endpoint、未固定 SHA-256 的镜像、重复端口/库/角色/卷/凭据。
- 所有端口只绑定 `127.0.0.1`。Flask 与 Java 分处不同 internal backend；任何一侧都不
  能解析或访问另一侧的数据服务。六个卷名必须不同并隶属当前一次性项目。
- 运行目录固定在被 Git 忽略的 `infra/phase3/artifacts/topology/<run-id>/`。目录为 `0700`，
  env、凭据、快照和报告为 `0600`；符号链接、硬链接、额外快照文件和覆盖已有证据均被拒绝。
- 快照包含真实数据库内容，属于敏感工件，不得提交或传输。manifest 与报告只保存摘要；
  命令输出不保存数据库内容、密码、DSN、Cookie 或 Token。
- manifest 的 `payload.canonicalization` 固定为
  `pg-restore-sql-v2-restrict-token-static-ascii-varchar-text-array`。这是 fail-closed 的版本化
  合约，不是 SQL 格式化器：除严格配对 guard token 和上述一类 PostgreSQL 18 静态数组
  反编译外，不折叠空白、注释、标识符、任意 cast 或一般 SQL 表达式。
- Phase 3 认证范围只复制 PostgreSQL。Redis Session/限流状态和应用文件卷明确不复制，目标
  必须从全新空卷开始；该边界不适用于后续需要迁移上传文件的生产切换。
- 来源 API 必须在捕获前精确运行一份，目标 API/PG/Redis 容器必须不存在，目标三卷必须
  从未创建。目标健康前来源不会重启；目标健康后来源容器移除但三个来源卷保留。
- 失败路径先停止/移除目标容器，只删除本轮刚创建且名称已门禁的目标卷，再恢复来源数据面
  和来源 API；若清理报告为失败，应保持人工接管，禁止手工同时启动两边 API。
- 审练只连接真实存在的本机 Unix Docker socket。`DOCKER_HOST` 仅可显式固定到该 socket，
  且 Docker 实际解析出的 endpoint 必须逐字一致；`DOCKER_CONTEXT`、TLS 变量、TCP/SSH
  endpoint、相对路径、不存在路径或普通文件都会在任何停服动作前失败。调用方未提供
  `DOCKER_HOST` 时，预检会在验证当前 endpoint 后立即把同一冻结子进程环境固定到它，
  后续命令不再依赖可变的 `currentContext`。

## 准备一次运行

先分别构建旧/新镜像，并用 `docker image inspect --format '{{.Id}}' <image>` 获取本地不可变
`sha256:` ID。然后创建一次性配置和九份互不相同的随机凭据：

```bash
ENV_FILE=$(python3 infra/phase3/topology/prepare_run.py PREPARE \
  --environment local \
  --run-id auth-cutover-001 \
  --legacy-image sha256:<64-hex> \
  --java-image sha256:<64-hex>)
```

生成路径会打印到标准输出。不要 `source` 该文件；所有后续命令都使用
`docker compose --env-file` 或受控 Python 工具。先在这套隔离项目的 legacy 三卷中恢复经过
脱敏的本地夹具并启动 legacy API；这一准备动作不得引用旧项目现有卷。门禁要求切换开始时
`legacy-api`、`legacy-postgres`、`legacy-redis` 正常运行，Java 容器和 Java 三卷均不存在。

可先验证渲染配置，不拉取或启动镜像：

```bash
python3 infra/phase3/topology/topology_guard.py VALIDATE --env-file "$ENV_FILE"
docker compose --env-file "$ENV_FILE" \
  -f infra/phase3/topology/compose.isolated.yml \
  --profile runtime config --quiet
```

## 真实 `READ_COMPARE` 运行态审计

[`runtime_state_auditor.py`](runtime_state_auditor.py) 是
`read_compare.py --*-auditor-command` 的独立只读采样器。它不接受命令行连接参数，而是由
`TI_READ_COMPARE_ENVIRONMENT`、`TI_READ_COMPARE_SIDE`、`TI_READ_COMPARE_PHASE` 选择采样点；
这三个变量由比较器逐次注入。操作者只需额外导出两份 env 文件：

```bash
export TI_PHASE3_AUDIT_LEGACY_ENV_FILE=/absolute/path/to/legacy-run/compose.env
export TI_PHASE3_AUDIT_JAVA_ENV_FILE=/absolute/path/to/java-run/compose.env
AUDITOR=$(pwd -P)/infra/phase3/topology/runtime_state_auditor.py

python3 infra/phase3/read_compare.py READ_COMPARE \
  ... \
  --legacy-auditor-command "$AUDITOR" \
  --java-auditor-command "$AUDITOR" \
  --auditor-timeout-seconds 60
```

两份 env 必须属于同一 `local`/`test` 环境但对应不同 run-id 和 Compose project；不能把同一
双栈 Compose 文件同时冒充两边证据。每次采样先确认本机 Unix Docker context，再确认本侧
API/PostgreSQL/Redis 各恰好一份、健康、Compose label/命名卷正确且容器镜像 ID 与固定镜像
对应。状态摘要包括：

- 只读 audit role 执行的 PostgreSQL 全库 `data-only` dump；仅规范化 `pg_dump` 随机且首尾
  配对的 `restrict` token，原始行不写盘；
- Redis 全部 Key 的 Key/值脱敏摘要、类型与绝对过期时间。唯一允许排除的是 legacy
  `GET /api/auth/login-methods` 产生、形如
  `LIMITS:LIMITER/ip:<private-ip>/auth.auth_api.api_auth_login_methods/<limit>` 的
  Flask-Limiter Key；前缀、端点、私有/回环 IPv4、三档固定额度、string 类型、正整数计数
  和 TTL 都要逐项通过，摘要会记录固定 policy SHA 与实际排除数，其他 `LIMITS:*` 及所有
  其他 Key 一律纳入；
- 应用命名卷的目录、普通文件、符号链接、mode/uid/gid 与文件内容全量 manifest。Java 不
  允许排除；legacy 最多只排除 `logs/app.log.1` 到 `logs/app.log.10` 的普通轮转文件，并记录
  policy SHA 与数量，活动 `app.log` 仍参与摘要；
- 隔离 Compose 未配置 queue、object store 或 external write sink 的固定边界摘要。

标准输出只有严格 READ_COMPARE auditor JSON，不含原始数据库行、Redis Key/值、文件路径、
Secret、Cookie 或 Session ID。任何未知 Redis 类型、采样期间卷变化、镜像漂移、额外实例、
非健康容器或权限不正确都会失败；该排除策略只针对已冻结的 login-methods 读取，不可复用于
其他 operation。

## 串行登录写证据采集

[`capture_login_write_evidence.py`](capture_login_write_evidence.py) 为
`isolated_write_compare.py` 生成严格限界的 `before`/`after` 证据。采集器没有 HTTP 客户端
能力，只读两份不同 guarded run 的 Docker 元数据、PostgreSQL audit role 和 Redis；登录请求
必须由操作者在两个采样点之间外部串行执行。两份 env、Compose project、端口、数据库、卷、
镜像以及六个 comparator fingerprint 值都会交叉验证，不能用同一运行或资源冒充两边。

`before` 同时生成一个 `0600` 私有 proof。它保存全库“只将 id=1 的
`has_password_set` 投影为 sentinel”后的摘要，以及凭据材料摘要、`session_version`、
`last_active`、schema、行数和约束状态；不保存原始密码哈希。`after` 必须紧邻该 proof，且全库
转移摘要完全相同、凭据材料摘要完全相同，并精确观察到 `false -> true`，因此其他表、其他行或
同一行其他字段的任何变化都会失败。公开 evidence 使用 comparator 约定的四字段投影摘要，
仍逐项补回并验证凭据语义。

Redis 分类在 Redis 内部一次 Lua 采样完成，只返回计数和进程内临时 Session ID。legacy
`before` 必须零 Key，`after` 必须恰好一个值为 `1` 的 login Flask-Limiter Key；Java `before`
精确要求一次 GET `/api/csrf` 产生两个值为 `1` 的限流 Key 和一个匿名 Session hash，验证
`anonymous_expires_at`、43 字节 CSRF token 与最多 10 分钟 TTL。Java 明确使用 Spring Boot 4.1
默认的非索引 `RedisSessionRepository`，所以每个 Session 只有一个 hash，不接受 indexed
repository 的 expiry/expiration-set 结构。Java `after` 必须恰有三个值为 `1` 的 login 限流
Key、原有两个 CSRF 限流 Key、一个 id=1/session_version=7/remember=true 的认证 Session hash，
以及五个完整 identity/global registry Key。Session ID 与两个 zset、owners hash、sequence
逐一关联；任何额外 Key、未知类型、空 registry、重复请求计数或 TTL 越界均 fail closed。

Java 响应 Cookie 按 `DefaultCookieSerializer` 的标准 Base64 合约规范解码为 UUIDv4；脱敏观察与
Redis Lua 只在进程内分别计算同一域隔离 SHA-256，二者不一致即拒绝，原始 Cookie/Session ID
不写盘。legacy 脱敏观察绑定 guarded run/project/数据库/Redis/应用卷，并用响应 `Date` 校验
签名 Cookie 的签发窗口，不能跨运行复用。每侧 `before` 还保存应用卷全量 manifest 摘要，
`after` 必须完全一致，随后才允许 evidence 声明 `persistent_file_writes=0`。

操作者可先把已经由 `curl -D`/`-o` 捕获的临时响应脱敏；此子命令只读取文件，验证零重定向、
200/JSON UTF-8、两边完整统一成功信封、固定 `request_id=phase3-login-write-001`、固定
`redirect=/practice` 与 remember Cookie 属性。legacy 还必须传入 guarded env；工具用标准库
独立校验 Flask `cookie-session` 签名、签发时间和 id=1/roles/session_version/remember 安全标量，
原始 Cookie 与解码正文均不写盘。输出只有状态、完整规范响应 SHA 和布尔语义：

```bash
chmod 600 "$HEADER_FILE" "$BODY_FILE"
python3 infra/phase3/topology/capture_login_write_evidence.py SANITIZE_RESPONSE \
  --side legacy \
  --legacy-env-file "$LEGACY_ENV_FILE" \
  --headers-file "$HEADER_FILE" \
  --body-file "$BODY_FILE" \
  --output "$RUN_DIR/write-evidence/legacy-observation.json"
rm -f -- "$HEADER_FILE" "$BODY_FILE"
```

随后按完整串行序号采样；Java 使用相同命令但选择 Java side/env/fingerprint。`before-proof` 在
before 时必须不存在，after 时必须指向刚生成的同侧 proof；所有路径均应为绝对路径：

```bash
python3 infra/phase3/topology/capture_login_write_evidence.py CAPTURE \
  --environment local --side legacy --phase before --capture-sequence 1 \
  --run-id auth-login-write-p3-003 \
  --fixture-id auth-login-success-001 \
  --snapshot-id auth-parity-p3-003-cutover-initial \
  --snapshot-digest sha256:<64-hex> \
  --legacy-env-file "$LEGACY_ENV_FILE" --java-env-file "$JAVA_ENV_FILE" \
  --legacy-fingerprint "$LEGACY_FINGERPRINT" --java-fingerprint "$JAVA_FINGERPRINT" \
  --before-proof "$RUN_DIR/write-evidence/legacy-before.private.json" \
  --evidence "$RUN_DIR/write-evidence/legacy-before.json"
```

after 命令增加 `--observation <sanitized-observation.json>`。采集器和比较器都不发写请求；
操作者必须保持 `legacy:before -> 外部一次登录 -> legacy:after -> Java 外部 GET /api/csrf ->
java:before -> 外部一次登录 -> java:after`。Java before 捕获的是已受限的匿名 CSRF Session，
不是登录写；两侧仍必须来自同一已恢复快照并使用不同数据库、Redis 和应用卷。

## 正向切换与反向回滚

正向演练的确认串绑定当前 run-id：

```bash
python3 infra/phase3/topology/rehearse_switch.py CUTOVER \
  --env-file "$ENV_FILE" \
  --confirm 'STOP_LEGACY_CAPTURE_RESTORE_JAVA:auth-cutover-001'
```

成功后 Java API 运行，旧 API/PG/Redis 容器被移除但旧三卷保留。反向回滚必须分配一个从未
使用的 generation；工具会为 legacy 创建另一组三个全新卷，而不会重新写原旧卷：

```bash
python3 infra/phase3/topology/rehearse_switch.py ROLLBACK \
  --env-file "$ENV_FILE" \
  --generation rb001 \
  --confirm 'STOP_JAVA_CAPTURE_RESTORE_LEGACY:auth-cutover-001:rb001'
```

成功报告在 `reports/`，受控数据库快照在 `snapshots/`。报告的 `snapshot` 同时记录规范化
版本和规范 SQL 摘要，便于把摘要绑定到具体规则。二者都拒绝覆盖；重复演练应创建新
run-id/generation。快照可独立复核：

```bash
python3 infra/phase3/topology/snapshot_bundle.py VALIDATE \
  --env-file "$ENV_FILE" \
  --bundle "$(dirname "$ENV_FILE")/snapshots/auth-cutover-001-cutover-initial" \
  --expected-source legacy \
  --expected-target java
```

## 验证

```bash
./infra/phase3/topology/verify-static.sh
./infra/phase3/topology/verify-data-plane.sh
```

验证包含真实 `docker compose config` 拓扑检查，以及从无关工作目录执行的门禁/快照黑盒
测试、正向切换状态机、事务恢复失败清理和反向回滚新卷测试。数据面验证只启动本目录的四个
一次性 PG/Redis 容器，实际检验写角色/只读角色、Redis 空状态和 PostgreSQL dump/事务恢复/
规范化语义指纹闭环；两条命令都不会启动现有 Phase 2 Compose，也不会访问父目录旧项目数据。
