# Phase 3 本地/测试对比工具

本目录提供新旧运行时只读 HTTP 契约比较器 `READ_COMPARE`，以及隔离登录写终态离线
比较器 `ISOLATED_WRITE_COMPARE`。它们只用于 `local`/`test`，不是 Java 应用的依赖，
也不能作为生产流量代理、影子请求或双写工具。

## 强制边界

- 命令必须显式写 `READ_COMPARE --environment local|test`；没有环境默认值。
- 只接受 `GET`/`HEAD`，且只访问带显式端口的回环 `http` origin。
- legacy 与 Java 使用不同端口；`localhost` 与 `127.0.0.1` 的同端口别名也会被拒绝。
- 拒绝 userinfo、重定向、绝对请求 URL、敏感 query、生产标识及已有报告文件。
- 两边分别提供数据库、Redis、卷身份指纹；六个值任一为空或任意两个相同即停止。
- 每边请求前后都必须提供独立 auditor 的状态摘要；数据库、Redis、卷、队列、对象
  存储或外部写计数任一变化均使报告失败。runtime auditor 会把明确排除的 Flask-Limiter
  可重建 Key 从业务 Redis 摘要中剥离，但仍保存其计数；首次冷请求新增该 Key 时报告必须
  失败，预热后重新采样的暖态 before/after 相等才可通过。不能把这种冷变化写成绝对零
  Redis 写入，只能表述为“无业务事实或持久文件副作用”。
- 规范化只能来自 operation 级、带版本的精确 JSON Pointer/动态安全响应头白名单。默认数组有序；
  只有登记在 `unordered_array_json_pointers` 的数组才排序。忽略规则仅允许指向
  `request_id`、`trace_id`、`server_time`、`generated_at` 或 `current_time` 这类已批准
  动态标量字段；响应头仅可登记 `x-request-id`。不能用通配符、忽略整个对象、忽略
  ETag/缓存契约或隐藏敏感字段。
- `Content-Type` 先按 HTTP 媒体类型语法严格解析再比较；仅分号边界允许的 OWS、type/subtype、参数名及
  `charset` 值的大小写不构成差异。媒体类型、参数集合和其他参数值仍须完全相同，重复或
  非法参数会停止。报告同时保存经过安全扫描的原始值、canonical 值、原始相等结论和
  canonical 相等结论；这不是 operation 业务字段规范化。

比较器不保存请求头、原始响应正文、Cookie、Token、OpenID 或差异原值。报告只保存
原始 status、原始与 canonical Content-Type、固定安全响应头、正文 SHA-256/字节数、规范化摘要，
以及差异值的类型、SHA-256 和编码大小。敏感 JSON Pointer 段会哈希化；报告写入前
还会再次扫描疑似凭据。响应正文只在内存中处理。

报告契约为
[`read-compare-report.schema.json`](../../docs/refactor/phase3/read-compare-report.schema.json)。

## 输入契约

### 环境身份指纹

legacy 与 Java 各一份；这些值标识资源身份，而不是数据内容摘要。不要放 DSN、路径、
用户名或 Secret。报告只保存每个值的 SHA-256。

```json
{
  "schema_version": "1",
  "environment": "local",
  "side": "legacy",
  "database": "legacy-read-db-a",
  "redis": "legacy-read-redis-a",
  "volume": "legacy-read-volume-a"
}
```

### 副作用 auditor 输出

auditor 必须独立于两个被测应用。其 JSON 输出严格为：

```json
{
  "schema_version": "1",
  "environment": "local",
  "side": "legacy",
  "phase": "before",
  "auditor": "local-state-auditor-v1",
  "state": {
    "database": "sha256-of-normalized-db-state",
    "redis": "sha256-of-business-redis-state",
    "volume": "sha256-of-persistent-file-manifest",
    "queue": "sha256-of-queue-state",
    "object_store": "sha256-of-object-prefix-manifest",
    "external_writes": 0
  }
}
```

`state` 可添加 operation 所需的其他安全摘要，但不得放 Secret、Cookie、凭据、
OpenID、原始私密数据、空值、`null` 或浮点数。

推荐使用命令模式。比较器在每边请求前、后各执行一次绝对路径命令，使用
`shell=False`，并通过以下环境变量告诉 auditor 当前采样点：

- `TI_READ_COMPARE_ENVIRONMENT`
- `TI_READ_COMPARE_SIDE`
- `TI_READ_COMPARE_PHASE`（`before`/`after`）

文件模式接受四份独立 auditor/编排器生成的摘要，适用于外部编排已经保证采样时序的
场景；比较器仍会按 before → HTTP → after 的顺序读取。报告中的 `source_kind` 明确
记录证据来源，不能把文件模式冒充命令内联采样。

### 规范化规则

`normalization-rules.v1.json` 当前仅登记 Phase 3 冻结 route id `88d7dc05cdbb`；三个
规范化数组均为空，固定 `X-Request-ID` 必须在响应头和正文中逐值一致。其他 operation
仍会 fail-closed。每迁移一个真实读取 operation，应在评审中显式加入，例如：

```json
{
  "schema_version": "1",
  "ruleset_version": "catalog-read-v1",
  "operations": {
    "catalog.subjects.list": {
      "ignore_json_pointers": [
        "/meta/request_id"
      ],
      "unordered_array_json_pointers": [],
      "ignore_response_headers": [
        "x-request-id"
      ]
    }
  }
}
```

即使 operation 不需规范化，也要登记三个空数组。规则未命中、命中类型错误、出现未知
字段或 operation 未登记都会停止，不会静默扩大忽略范围。

### 请求头

鉴权兼容测试可通过 `--request-headers-file` 读取临时 JSON 对象。不要在命令行参数放
凭据；请求头文件应置于被忽略的一次性工件目录。比较器会发送但永不写入报告。

## 命令模式示例

以下仅是本地占位命令；digest、快照、指纹和 auditor 都必须来自本轮真实、脱敏证据：

```bash
mkdir -p infra/phase3/artifacts/migration/local-read-001/read-diffs

python3 infra/phase3/read_compare.py READ_COMPARE \
  --environment local \
  --operation-id catalog.subjects.list \
  --fixture-id catalog-subjects-anonymous-001 \
  --snapshot-id sanitized-s0-001 \
  --legacy-artifact-digest sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  --java-artifact-digest sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb \
  --legacy-origin http://127.0.0.1:18081 \
  --java-origin http://127.0.0.1:18080 \
  --path '/api/subjects?page=1' \
  --legacy-fingerprint infra/phase3/artifacts/migration/local-read-001/legacy-fingerprint.json \
  --java-fingerprint infra/phase3/artifacts/migration/local-read-001/java-fingerprint.json \
  --normalization-rules infra/phase3/normalization-rules.v1.json \
  --legacy-auditor-command /absolute/path/to/legacy-state-auditor \
  --java-auditor-command /absolute/path/to/java-state-auditor \
  --report infra/phase3/artifacts/migration/local-read-001/read-diffs/catalog-subjects.json
```

文件模式改用四个参数：

```text
--legacy-before-evidence <file> --legacy-after-evidence <file>
--java-before-evidence <file>   --java-after-evidence <file>
```

文件模式与 auditor 命令模式不能混用。报告不会覆盖已有文件；为每轮运行分配新的
`run-id`，可以避免证据被悄悄替换。

## 隔离登录写终态比较

`isolated_write_compare.py` 只比较外部编排已经产生的四份证据，不导入网络、HTTP 或
子进程模块，也没有发送请求的参数。它不会替操作者执行 Flask/Java 写请求。允许的
唯一 operation 是 `identity.auth.login`，对应 `POST /api/login`。

### 安全执行顺序

1. 从同一个带 SHA-256 的脱敏静止快照恢复 legacy/Java 两套全新 PostgreSQL，并给两边
   分配不同的数据库、Redis、卷、端口和凭据。
2. 外部编排按声明顺序执行完整的一边，再执行另一边。例如
   `legacy:before → legacy:POST once → legacy:after → java:before → java:POST once → java:after`。
   禁止交错、转发、shadow write 或一个进程连接两个写目标。
3. Java 的 CSRF 初始化必须在 `java:before` 采样前完成；证据中的 `request_count` 只统计
   被比较的登录 POST。匿名 Redis Session 可以存在，但必须在最终状态中只剩一个目标
   authenticated Session。
4. 四份证据都要绑定同一 `run_id`、fixture、snapshot digest 及本边资源指纹；比较器校验
   `capture_sequence=1..4` 后才比较。
5. 生成报告后销毁两套副本；下一个用例重新从基础快照恢复，不能清表复用。

### 写证据契约

四份 JSON 使用相同严格字段；以下是 `legacy:after` 示例。`java:after` 只把 Session
`storage_profile`/`authority_profile` 改为 `server-redis`/`postgresql-per-request`，这两项
固定映射到已批准的 `P3-AUTH-002`。未知字段、浮点数、原始 `password_hash`、Cookie、
Session ID、账号、OpenID 或 Secret 会被拒绝或永远不会进入报告。

```json
{
  "schema_version": "1",
  "environment": "local",
  "run_id": "auth-login-write-001",
  "side": "legacy",
  "phase": "after",
  "capture_sequence": 2,
  "operation_id": "identity.auth.login",
  "fixture_id": "auth-login-success-001",
  "snapshot_id": "sanitized-auth-s0-001",
  "snapshot_digest": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "resource_binding_sha256": "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  "auditor": "phase3-auth-state-auditor-v1",
  "request_count": 1,
  "response": {
    "observed": true,
    "status": 200,
    "content_type": "application/json; charset=utf-8",
    "normalized_body_sha256": "sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
    "authenticated_session_issued": true,
    "remember_applied": true
  },
  "state": {
    "database": {
      "schema_sha256": "sha256:dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",
      "normalized_business_state_sha256": "sha256:eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
      "users_row_count": 5,
      "credential": {
        "format_family": "werkzeug-scrypt",
        "target_parameters": "32768:8:1",
        "verifies_fixture_password": true,
        "has_password_set": true,
        "session_version": 7,
        "last_active_state": "null"
      },
      "constraint_violations": 0,
      "unexpected_row_changes": 0
    },
    "session": {
      "authenticated": true,
      "principal_binding_hmac_sha256": "sha256:ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
      "session_version": 7,
      "remember": true,
      "storage_profile": "signed-client-cookie",
      "authority_profile": "signed-login-snapshot",
      "credential_material_count": 0
    },
    "redis": {
      "business_fact_keys": 0,
      "server_session_records": 0,
      "rate_limit_attempt_recorded": true,
      "rebuildable_only": true,
      "unexpected_keys": 0
    },
    "external": {
      "queue_messages": 0,
      "object_writes": 0,
      "persistent_file_writes": 0,
      "external_writes": 0
    }
  }
}
```

`before` 把 `request_count` 置 `0`，`response` 固定为 `observed=false`、`status=0`、三个
响应布尔值为 `false`，`content_type`/`normalized_body_sha256` 为 `none`；Session 固定为
未认证、两个 profile 为 `none`、身份 HMAC 与 version 为字符串 `none`。Java 可因 CSRF
准备而已有匿名 `server_session_records`，这个实现计数不参与跨栈等价比较。黄金夹具的
`before` credential 与示例 `after` 相同，但 `has_password_set` 必须为 `false`；两边成功
登录后都必须精确变为 `true`。

`normalized_business_state_sha256` 必须由独立 auditor 对 operation 所有业务事实稳定排序
后计算。它只能在黄金 fixture 用户行中把以下四列替换为固定、与值无关的 projected
sentinel：`password_hash`、`has_password_set`、`session_version`、`last_active`。该用户行
的其余列、其他用户行和其他表不得排除、置零或宽泛规范化。四个 projected 值分别由
`credential.format_family/target_parameters/verifies_fixture_password`、
`credential.has_password_set`、`credential.session_version`、
`credential.last_active_state` 明文语义字段补回并逐项比较；密码哈希原文始终不能进入
证据或报告。

当前 v1 黄金成功用例唯一允许的数据库迁移是两边各自的 fixture
`has_password_set: false → true`。`format_family=werkzeug-scrypt`、
`target_parameters=32768:8:1`、fixture 密码验证结果、`session_version` 与 `last_active`
必须在每侧 before/after 完全一致；`unexpected_row_changes` 对扣除上述唯一批准列迁移后
的任何其他行/列变化计数，因此必须为 `0`。这样 before/after 的非 projected 摘要保持
相等，同时 legacy/Java 的 initial database 和 final database 仍分别精确相等。PBKDF2
升级属于 `P3-AUTH-004` 的独立迁移/回滚用例，不能用本工具静默抹平为“同终态”。

`resource_binding_sha256` 的确定性算法是：对 UTF-8 字节
`ti-phase3-isolated-write-fingerprint-v1\0<database>\0<redis>\0<volume>` 计算 SHA-256；
三个值来自本边环境指纹文件。报告只保存各值摘要，不保存资源身份原文。

### 离线比较命令

```bash
python3 infra/phase3/isolated_write_compare.py ISOLATED_WRITE_COMPARE \
  --environment local \
  --operation-id identity.auth.login \
  --run-id auth-login-write-001 \
  --fixture-id auth-login-success-001 \
  --snapshot-id sanitized-auth-s0-001 \
  --snapshot-digest sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  --legacy-artifact-digest sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb \
  --java-artifact-digest sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc \
  --execution-order legacy-then-java \
  --legacy-fingerprint infra/phase3/artifacts/auth-write-001/legacy-fingerprint.json \
  --java-fingerprint infra/phase3/artifacts/auth-write-001/java-fingerprint.json \
  --legacy-before-evidence infra/phase3/artifacts/auth-write-001/legacy-before.json \
  --legacy-after-evidence infra/phase3/artifacts/auth-write-001/legacy-after.json \
  --java-before-evidence infra/phase3/artifacts/auth-write-001/java-before.json \
  --java-after-evidence infra/phase3/artifacts/auth-write-001/java-after.json \
  --report infra/phase3/artifacts/auth-write-001/final-state-report.json
```

通过条件是：两边初始与最终数据库分别精确相等；每侧非 projected 业务摘要保持不变，
且只有 `has_password_set` 从 `false` 变为 `true`；`users` 行数、目标 hash 语义、
`session_version`、`last_active` 和约束满足不变量；两边 Session 的
身份/version/remember 等价；Redis 只含可重建 Session/限流状态且没有业务事实或未知
Key；已配置且实际采样的队列、对象、文件和外部写为零。若某类外部边界明确
`configured=false` 且 `runtime_observation_performed=false`，报告只证明双方配置边界等价，
不能提升为“已运行态观察到零写入”。退出码仍为 `0` 通过、`1` 已写失败报告、`2`
输入/安全协议错误且不生成报告。

## p3-009 脱敏证据索引

p3-009 使用固定 legacy `sha256:324b50f5ac0b5daa4d0e96cd6c495221e241b4fb0df90efe4de94a73387fb1b4`
和 Java `sha256:1dfca1d79f5b6fe8fa40ec9958028f14ee6c68db5371ac6c331231bf6a4c6077`：

- 冷 READ_COMPARE 报告 SHA-256 为
  `d733dc7f62c7b86dd185d0f2c731069cad6a2d2b82926d346ef2fd4ff8c275c2`，唯一差异是上述
  Flask-Limiter 排除运行时 Key 计数；暖报告 SHA-256 为
  `37128ff0786211474f84f60a131934ebcbaac4c8cc0fa02bd5299f46a19590aa`，差异数为 0。
- 隔离写报告 SHA-256 为
  `3dc21a524bfae335d763ac49d4f480962c536ec5c99af021ac27b583ae9c40f5`，两侧使用同一快照、
  不同资源，严格串行各执行一次登录；比较器自身没有网络或写请求能力。
- CUTOVER 与 ROLLBACK 报告 SHA-256 分别为
  `ece1199c3e0bd3ca90df4756cc6709c1d211e03a621d2dce6cad5e5ebcf89091` 和
  `3fca94f6841ade5a26f0f53669026a04ee7c5293616a5754ab20c745d9c6fc1a`。

这里只登记不可逆摘要。快照含敏感数据库内容，原始快照、请求、响应、Cookie、Token、
Session ID 和 Secret 都不得提交或复制进文档。

## 差异与退出码

结构化正文比较明确区分：

- `missing`：字段不存在；与存在且为 `null` 不同；
- `type`：JSON 类型不同；
- `array_order`：元素多重集相同但顺序不同；
- `array_length`、`value`、`invalid_json`、`body_bytes`；
- `side_effect` scope：任一 auditor before/after 状态变化。

差异值从不原样落盘，只记录类型、哈希和编码大小。

退出码：`0` 为零差异且零副作用；`1` 为已安全生成失败报告；`2` 为配置、安全、网络、
重定向、敏感扫描或证据校验错误，此时不生成报告。

## 验证与独立运行

```bash
./infra/phase3/verify-static.sh
./infra/phase3/topology/verify-static.sh
```

第一条当前运行 15 项 READ_COMPARE 与 14 项 ISOLATED_WRITE_COMPARE 测试，共 29 项；
第二条运行 24 项 topology、15 项 runtime auditor 与 20 项 write capture 测试，共 59 项。
测试从临时工作目录用绝对路径启动比较器，并运行两个独立回环 stub server；比较器没有
父目录搜索、旧 Flask import、生产依赖或 Java 运行时依赖。复制整个 `Ti-Java/` 到任意
目录后仍可执行相同命令。
