# ADR-0001：固定 Java 25 与 Spring 稳定版本基线

- 状态：已接受
- 日期：2026-07-16
- 决策阶段：阶段 1（架构决策与契约固化）
- 适用范围：`Ti-Java/server/` 的编译、测试、镜像和运行时

## 上下文

目标契约要求 Java 25 LTS、Spring Boot 4.1.x 和与之兼容的 Spring Modulith，且禁止 Snapshot、Milestone 与未验证预览版本。阶段 0 又确认本机没有 Java Runtime 和 Maven，因此“使用开发机当前版本”既不可重复，也无法作为阶段 2 的绿色证据。

Spring Boot 4.1.0 官方系统要求是 Java 17 至 26、Maven 3.6.3 及以上；Spring Boot 项目页和参考文档均将 4.1.0 标记为稳定版本。Spring Modulith 项目页将 2.1.0 标记为当前稳定版本。Adoptium 当前 Java 25 LTS 更新为 Temurin `25.0.3+9`。这些版本满足目标技术栈，且不要求引入预览特性。

## 决策

阶段 2 创建骨架时必须固定下列版本，不使用版本范围：

| 构件 | 固定值 | 固定位置 |
| --- | --- | --- |
| Java 语言与字节码级别 | `25` | Maven Compiler `release=25` 与 Enforcer |
| JDK 发行版 | Eclipse Temurin `25.0.3+9-LTS` | 开发工具链、CI 与镜像构建参数 |
| Spring Boot | `4.1.0` | `spring-boot-starter-parent` 或等价 BOM 属性 |
| Spring Modulith | `2.1.0` | `spring-modulith-bom` |
| Maven Wrapper | `3.9.16` | `.mvn/wrapper/maven-wrapper.properties` |

同时采用以下版本治理规则：

1. Spring Framework、Jackson、Spring Security、Tomcat、Micrometer 等由 Spring Boot 依赖管理统一选择，不在单个依赖上另写版本。尤其不单独漂移 Spring Security。
2. Spring Modulith 构件只由 `spring-modulith-bom:2.1.0` 管理，禁止混用不同 Modulith 小版本。
3. Maven 插件若不受父 POM 管理，必须在 `pluginManagement` 固定精确版本；Node/pnpm 版本在 Web 骨架中用仓库文件和锁文件另行固定。
4. Maven Wrapper 的发行包 SHA-256、每个目标平台的 Temurin 包校验和及基础镜像 digest 写入可审查的构建清单。只写 tag 不算固定镜像。
5. 不启用 Java preview feature；源码、测试和生产启动命令都不得包含 `--enable-preview`。
6. patch 升级是显式维护操作：先更新本 ADR 的“已验证版本”，再运行完整 `./mvnw verify`、依赖树、安全扫描、镜像构建和独立目录验证；不能使用 `4.1.+`、`LATEST` 或浮动容器 tag 自动升级。

## 后果

正面后果：

- 开发机没有全局 Maven 也能用 Wrapper 复现构建；CI、容器和本地使用同一 Java feature release。
- Boot BOM 降低 Spring 组件被独立升级后出现二进制不兼容的风险。
- 版本升级会留下明确的评审点和回归证据。

代价与风险：

- Java 25 patch 或基础镜像安全更新不会自动进入主线，需要主动升级。
- 开发机必须安装 Temurin 25 或使用受控 JDK 容器；当前无 JDK 的环境不能直接编译。
- 如果某个第三方库尚不支持 Java 25/Boot 4.1，必须替换该库或记录新的 ADR，不能悄悄降级整个技术栈。

## 拒绝的方案

- **Java 21 或 17：** 虽然 Boot 4.1 支持，但违反本次明确的 Java 25 目标，且会让 CI 与目标生产运行时分裂。
- **Spring Boot 4.1 Snapshot/Milestone：** 不具备稳定发布保证，违反目标契约。
- **让 Maven 每次解析“最新版本”：** 构建不可重复，无法把绿色提交与依赖集合绑定。
- **为 Spring Security 等逐项覆盖 BOM 版本：** 增加未验证组合，除非安全修复无法等待 Boot patch，且必须由新的临时 ADR 说明范围和回退。
- **依赖机器全局 Maven/JDK：** 阶段 0 已证明本机没有这些工具，也不支持未来独立拆仓。

## 实施与验证约束

阶段 2 的版本门禁至少包括：

```bash
cd Ti-Java/server
./mvnw --version
./mvnw -q help:evaluate -Dexpression=java.version -DforceStdout
./mvnw -q help:effective-pom -Doutput=target/effective-pom.xml
./mvnw -q dependency:tree -DoutputFile=target/dependency-tree.txt
./mvnw verify
```

自动化测试必须断言：

- Wrapper 输出 Maven `3.9.16`，运行时 Java 为 `25.0.3+9`，编译 release 为 `25`；
- effective POM 中 Boot 为 `4.1.0`、Modulith 为 `2.1.0`；
- 没有 `SNAPSHOT`、里程碑、版本范围或未受管理的 Spring Security 构件；
- 在只复制 `Ti-Java/` 的临时目录中仍可解析依赖并完成构建；
- 多架构镜像清单中的 JDK 版本相同，digest 与受审构建清单一致。

## 事实证据

- 仓库事实：[`../00-current-state.md`](../00-current-state.md) 第 6 节记录本机工具链、无 Java/Maven 现状及稳定版本核验。
- 目标约束：[`../01-target-architecture.md`](../01-target-architecture.md) 第 2、10 节规定 Java 25、Boot 4.1、Modulith 与独立验证。
- Spring Boot 稳定版本：<https://spring.io/projects/spring-boot/>
- Spring Boot 4.1.0 系统要求：<https://docs.spring.io/spring-boot/system-requirements.html>
- Spring Boot 4.1.0 发布说明：<https://spring.io/blog/2026/06/10/spring-boot-4/>
- Spring Modulith 2.1.0：<https://spring.io/projects/spring-modulith/>
- Java SE 25 规范：<https://openjdk.org/projects/jdk/25/spec>
- Temurin 25 当前稳定更新：<https://adoptium.net/temurin/releases/?version=25>
- Maven 当前稳定下载：<https://maven.apache.org/download.cgi>
