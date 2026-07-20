package io.saksk.ti.learning.infrastructure.migration;

import static org.assertj.core.api.Assertions.assertThat;

import com.tngtech.archunit.core.domain.JavaClass;
import com.tngtech.archunit.core.domain.JavaClasses;
import com.tngtech.archunit.core.domain.JavaMethodCall;
import com.tngtech.archunit.core.importer.ClassFileImporter;
import com.tngtech.archunit.core.importer.ImportOption;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Collectors;
import org.junit.jupiter.api.Test;

class LegacyPersonalBankTagMigrationOperatorCoreStaticTest {

    private static final String MIGRATION_PACKAGE =
            "io.saksk.ti.learning.infrastructure.migration";

    private static final Map<Class<?>, Integer> EXPECTED_STATEMENT_SURFACES = Map.of(
            BoundedSqlRetry.class, 3,
            JdbcTagMigrationStore.class, 19,
            LegacyPersonalBankTagGlobalPreflight.class, 7,
            TagMigrationSchemaVerifier.class, 10);

    private static final Set<String> LOCAL_RELATIONS = Set.of(
            "allowed_relations", "allowed_schemas", "canonical_context",
            "column_grants", "facts", "function_grants", "functions",
            "relation_grants", "relations", "schema_grants", "schemas",
            "sequence_grants");

    private static final Set<String> ALLOWED_SCHEMAS = Set.of(
            "pg_catalog", "public", "ti_migration");

    private static final Set<String> SYSTEM_CONFIGURATION_METHODS = Set.of(
            "clearProperty", "getenv", "getProperties", "getProperty",
            "setProperties", "setProperty");

    private static final Pattern RELATION_REFERENCE = Pattern.compile(
            "(?i)\\b(?:FROM|JOIN|UPDATE|INTO|REFERENCES)\\s+"
                    + "(?:(?:ONLY|LATERAL)\\s+)?"
                    + "([a-z_][a-z0-9_]*(?:\\.[a-z_][a-z0-9_]*)?)");

    private static final Pattern CTE_DECLARATION = Pattern.compile(
            "(?i)(?:\\bWITH|,)\\s*([a-z_][a-z0-9_]*)"
                    + "(?:\\s*\\([^)]*\\))?\\s+AS\\s+"
                    + "(?:(?:NOT\\s+)?MATERIALIZED\\s+)?\\(");

    private static final Pattern DYNAMIC_RELATION_REFERENCE = Pattern.compile(
            "(?i)(?:(?<!DISTINCT )\\bFROM|"
                    + "\\b(?:JOIN|UPDATE|INTO|REFERENCES))\\s+"
                    + "(?:(?:ONLY|LATERAL)\\s+)?(?:\\?|[:#$%{])");

    private static final Pattern DYNAMIC_IDENTIFIER_TEMPLATE = Pattern.compile(
            "(?i)(?:\\$\\{|#\\{|\\{\\{|%\\d*\\$?[a-z])");

    private static final Pattern DDL = Pattern.compile(
            "(?i)\\b(?:CREATE|ALTER|DROP|TRUNCATE)\\b");

    private static final Pattern UNQUALIFIED_POSTGRES_FUNCTION = Pattern.compile(
            "(?i)(?<!pg_catalog\\.)\\b(?:pg_[a-z0-9_]+|current_database|"
                    + "current_setting|convert_to|format_type|generate_series|"
                    + "has_[a-z0-9_]+_privilege|inet_server_addr|inet_server_port|"
                    + "octet_length|to_regclass|unnest|acldefault|aclexplode|"
                    + "concat_ws|encode|jsonb_agg|jsonb_build_array)\\s*\\(");

    private static final Pattern QUOTED_RELATION_REFERENCE = Pattern.compile(
            "(?i)\\b(?:FROM|JOIN|UPDATE|INTO|REFERENCES|USING|TABLE|COPY)\\s+"
                    + "(?:(?:ONLY|LATERAL)\\s+)?\\\"");

    private static final Pattern EXTERNAL_MARKER = Pattern.compile(
            "(?i)(?:\\bredis\\b|\\b(?:file|filesystem|marker|path)\\b|"
                    + "file:|/tmp/|java\\.io\\.|java\\.nio\\.file)");

    private static final Pattern SOURCE_FOR_UPDATE = Pattern.compile(
            "(?is)\\bFROM\\s+public\\.user_progress\\b.*\\bFOR\\s+UPDATE\\b");

    private static final JavaClasses MIGRATION_CLASSES = new ClassFileImporter()
            .withImportOption(ImportOption.Predefined.DO_NOT_INCLUDE_TESTS)
            .importPackages(MIGRATION_PACKAGE);

    @Test
    void operatorCoreStoreSchemaAndCommandsHaveNoAutomaticEntryPoint() {
        Set<Class<?>> targetTypes = targetTypes();
        JavaClasses bytecode = new ClassFileImporter()
                .withImportOption(ImportOption.Predefined.DO_NOT_INCLUDE_TESTS)
                .importClasses(targetTypes.toArray(Class<?>[]::new));

        List<String> forbiddenDependencies = bytecode.stream()
                .flatMap(type -> type.getDirectDependenciesFromSelf().stream())
                .filter(dependency -> isAutomaticOrExternalMarkerType(
                        dependency.getTargetClass().getName()))
                .map(dependency -> dependency.getDescription())
                .sorted()
                .toList();
        assertThat(forbiddenDependencies)
                .as("operator types must not depend on framework entry points, "
                        + "schedulers, Redis, or file markers")
                .isEmpty();

        List<String> forbiddenCalls = bytecode.stream()
                .flatMap(type -> type.getMethodCallsFromSelf().stream())
                .filter(LegacyPersonalBankTagMigrationOperatorCoreStaticTest
                        ::isAutomaticOrSystemConfigurationCall)
                .map(JavaMethodCall::getDescription)
                .sorted()
                .toList();
        assertThat(forbiddenCalls)
                .as("operator types must not read environment/system properties or start work")
                .isEmpty();

        List<String> mainMethods = targetTypes.stream()
                .flatMap(type -> Arrays.stream(type.getDeclaredMethods()))
                .filter(method -> method.getName().equals("main"))
                .map(Method::toGenericString)
                .sorted()
                .toList();
        assertThat(mainMethods)
                .as("operator types must not expose a main entry point")
                .isEmpty();

        assertThat(Arrays.stream(
                        LegacyPersonalBankTagMigrationOperatorCore
                                .FreezeReceipts.class.getDeclaredMethods())
                .map(Method::getName)
                .filter(name -> name.endsWith("WriterStopReceiptSha256")))
                .as("freeze evidence must preserve three independent writer fences")
                .containsExactlyInAnyOrder(
                        "sourceWriterStopReceiptSha256",
                        "targetWriterStopReceiptSha256",
                        "membershipWriterStopReceiptSha256");

        String storeSql = String.join(
                "\n", JdbcTagMigrationStore.statementSurface());
        assertThat(storeSql)
                .contains(
                        "source_writer_stop_receipt_sha256",
                        "target_writer_stop_receipt_sha256",
                        "membership_writer_stop_receipt_sha256")
                .doesNotContain(" writer_stop_receipt_sha256");
    }

    @Test
    void everyProductionStatementSurfaceIsFixedQualifiedAndDatabaseOnly() {
        Set<String> expectedOwners = EXPECTED_STATEMENT_SURFACES.keySet().stream()
                .map(Class::getName)
                .collect(Collectors.toUnmodifiableSet());
        Set<String> discoveredOwners = MIGRATION_CLASSES.stream()
                .filter(LegacyPersonalBankTagMigrationOperatorCoreStaticTest
                        ::declaresStatementSurface)
                .map(JavaClass::getName)
                .collect(Collectors.toUnmodifiableSet());
        assertThat(discoveredOwners)
                .as("every production statementSurface owner must be explicitly gated")
                .containsExactlyInAnyOrderElementsOf(expectedOwners);

        EXPECTED_STATEMENT_SURFACES.forEach((owner, expectedSize) -> {
            List<String> first = invokeStatementSurface(owner);
            List<String> second = invokeStatementSurface(owner);
            List<String> declaredSql = declaredSqlConstants(owner);

            assertThat(first)
                    .as(owner.getSimpleName() + " statement surface")
                    .hasSize(expectedSize)
                    .doesNotContainNull()
                    .doesNotHaveDuplicates()
                    .containsExactlyElementsOf(second)
                    .containsExactlyInAnyOrderElementsOf(declaredSql);

            first.forEach(sql -> assertSafeStatement(owner, sql));
        });
    }

    @Test
    void sourceForUpdateDoesNotExist() {
        List<String> forbiddenFields = MIGRATION_CLASSES.stream()
                .flatMap(type -> type.getFields().stream())
                .filter(field -> field.getName().contains("SOURCE_FOR_UPDATE"))
                .map(field -> field.getOwner().getName() + "." + field.getName())
                .sorted()
                .toList();
        assertThat(forbiddenFields).isEmpty();

        EXPECTED_STATEMENT_SURFACES.keySet().stream()
                .flatMap(owner -> invokeStatementSurface(owner).stream())
                .forEach(sql -> assertThat(SOURCE_FOR_UPDATE.matcher(sql).find())
                        .as("source rows must never be selected FOR UPDATE: %s", sql)
                        .isFalse());
    }

    private static Set<Class<?>> targetTypes() {
        var result = new LinkedHashSet<Class<?>>();
        var pending = new ArrayDeque<Class<?>>();
        pending.add(BoundedSqlRetry.class);
        pending.add(LegacyPersonalBankTagMigrationOperatorCore.class);
        pending.add(JdbcTagMigrationStore.class);
        pending.add(TagMigrationSchemaVerifier.class);
        pending.add(TagMigrationCommand.class);
        while (!pending.isEmpty()) {
            Class<?> type = pending.removeFirst();
            if (result.add(type)) {
                pending.addAll(List.of(type.getDeclaredClasses()));
            }
        }
        return result;
    }

    private static boolean isAutomaticOrExternalMarkerType(String typeName) {
        return typeName.startsWith("org.springframework.")
                || typeName.startsWith("org.quartz.")
                || typeName.startsWith("jakarta.ejb.")
                || typeName.startsWith("jakarta.servlet.")
                || typeName.startsWith("jakarta.ws.rs.")
                || typeName.startsWith("javax.ejb.")
                || typeName.startsWith("javax.servlet.")
                || typeName.startsWith("javax.ws.rs.")
                || typeName.startsWith("redis.clients.")
                || typeName.startsWith("io.lettuce.")
                || typeName.startsWith("java.nio.file.")
                || typeName.startsWith("java.io.File")
                || typeName.equals("java.io.RandomAccessFile")
                || typeName.equals("java.lang.Runnable")
                || typeName.equals("java.util.Timer")
                || typeName.equals("java.util.TimerTask")
                || typeName.equals("java.util.concurrent.ScheduledExecutorService")
                || typeName.equals("java.util.concurrent.ScheduledFuture")
                || typeName.equals("java.util.concurrent.ScheduledThreadPoolExecutor");
    }

    private static boolean isAutomaticOrSystemConfigurationCall(JavaMethodCall call) {
        String owner = call.getTarget().getOwner().getName();
        String method = call.getTarget().getName();
        return (owner.equals(System.class.getName())
                        && SYSTEM_CONFIGURATION_METHODS.contains(method))
                || (owner.equals("java.lang.ProcessBuilder")
                        && method.equals("environment"))
                || (owner.equals("java.lang.Boolean") && method.equals("getBoolean"))
                || (owner.equals("java.lang.Integer") && method.equals("getInteger"))
                || (owner.equals("java.lang.Long") && method.equals("getLong"))
                || (owner.equals("java.lang.management.RuntimeMXBean")
                        && method.equals("getSystemProperties"))
                || (owner.equals("java.util.concurrent.Executors")
                        && method.startsWith("newScheduled"))
                || (owner.equals("java.util.concurrent.CompletableFuture")
                        && method.equals("delayedExecutor"))
                || (owner.equals(Thread.class.getName()) && method.equals("start"));
    }

    private static boolean declaresStatementSurface(JavaClass type) {
        return type.getMethods().stream()
                .anyMatch(method -> method.getName().equals("statementSurface"));
    }

    private static List<String> invokeStatementSurface(Class<?> owner) {
        try {
            Method method = owner.getDeclaredMethod("statementSurface");
            assertThat(Modifier.isStatic(method.getModifiers())).isTrue();
            assertThat(method.trySetAccessible()).isTrue();
            Object value = method.invoke(null);
            assertThat(value).isInstanceOf(List.class);
            List<?> raw = (List<?>) value;
            assertThat(raw).allMatch(String.class::isInstance);
            return raw.stream().map(String.class::cast).toList();
        } catch (ReflectiveOperationException failure) {
            throw new AssertionError(owner.getName() + " statementSurface invocation failed", failure);
        }
    }

    private static List<String> declaredSqlConstants(Class<?> owner) {
        var values = new ArrayList<String>();
        for (Field field : owner.getDeclaredFields()) {
            if (!field.getName().endsWith("_SQL")
                    || field.getType() != String.class
                    || !Modifier.isStatic(field.getModifiers())
                    || !Modifier.isFinal(field.getModifiers())) {
                continue;
            }
            try {
                assertThat(field.trySetAccessible()).isTrue();
                values.add((String) field.get(null));
            } catch (IllegalAccessException failure) {
                throw new AssertionError("cannot read " + owner.getName()
                        + "." + field.getName(), failure);
            }
        }
        return List.copyOf(values);
    }

    private static void assertSafeStatement(Class<?> owner, String sql) {
        String executableSql = withoutStringLiterals(sql);
        Set<String> declaredCtes = declaredCtes(executableSql);
        assertNoMatch(owner, sql, executableSql, DDL, "DDL");
        assertNoMatch(owner, sql, executableSql, DYNAMIC_RELATION_REFERENCE,
                "dynamic relation reference");
        assertNoMatch(owner, sql, executableSql, DYNAMIC_IDENTIFIER_TEMPLATE,
                "dynamic identifier template");
        assertNoMatch(owner, sql, executableSql, QUOTED_RELATION_REFERENCE,
                "quoted relation reference");
        assertNoMatch(owner, sql, executableSql, UNQUALIFIED_POSTGRES_FUNCTION,
                "unqualified PostgreSQL function");
        assertNoMatch(owner, sql, sql, EXTERNAL_MARKER, "Redis/file marker");

        Matcher relations = RELATION_REFERENCE.matcher(executableSql);
        while (relations.find()) {
            String relation = relations.group(1).toLowerCase(Locale.ROOT);
            if (LOCAL_RELATIONS.contains(relation)) {
                assertThat(declaredCtes)
                        .as("%s references an undeclared local relation in: %s",
                                owner.getSimpleName(), sql)
                        .contains(relation);
                continue;
            }
            assertThat(relation)
                    .as("%s uses an unqualified relation in: %s",
                            owner.getSimpleName(), sql)
                    .contains(".");
            String schema = relation.substring(0, relation.indexOf('.'));
            assertThat(ALLOWED_SCHEMAS)
                    .as("%s uses a relation outside fixed schemas in: %s",
                            owner.getSimpleName(), sql)
                    .contains(schema);
        }
    }

    private static Set<String> declaredCtes(String sql) {
        var names = new LinkedHashSet<String>();
        Matcher declarations = CTE_DECLARATION.matcher(sql);
        while (declarations.find()) {
            names.add(declarations.group(1).toLowerCase(Locale.ROOT));
        }
        assertThat(LOCAL_RELATIONS)
                .as("statement surface contains an unapproved CTE")
                .containsAll(names);
        return Set.copyOf(names);
    }

    private static void assertNoMatch(
            Class<?> owner,
            String sql,
            String inspectedSql,
            Pattern forbidden,
            String description
    ) {
        assertThat(forbidden.matcher(inspectedSql).find())
                .as("%s statement surface contains %s: %s",
                        owner.getSimpleName(), description, sql)
                .isFalse();
    }

    private static String withoutStringLiterals(String sql) {
        StringBuilder result = new StringBuilder(sql.length());
        boolean inLiteral = false;
        for (int index = 0; index < sql.length(); index++) {
            char value = sql.charAt(index);
            if (value != '\'') {
                result.append(inLiteral ? ' ' : value);
                continue;
            }
            result.append(' ');
            if (inLiteral && index + 1 < sql.length() && sql.charAt(index + 1) == '\'') {
                result.append(' ');
                index++;
            } else {
                inLiteral = !inLiteral;
            }
        }
        assertThat(inLiteral).as("unterminated SQL string literal").isFalse();
        return result.toString();
    }
}
