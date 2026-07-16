package io.saksk.ti.architecture;

import static org.assertj.core.api.Assertions.assertThat;

import java.io.IOException;
import java.lang.annotation.Annotation;
import java.lang.reflect.Modifier;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.TreeMap;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.springframework.modulith.ApplicationModule;
import org.springframework.modulith.NamedInterface;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

class ModuleContractParityTest {

    private static final ObjectMapper JSON = new ObjectMapper();

    private static Path tiJavaRoot;
    private static JsonNode contractRoot;
    private static JsonNode shapeStatusRoot;
    private static Map<String, ContractModule> contractModules;
    private static Set<Edge> eventOnlyEdges;

    @BeforeAll
    static void loadAcceptedMachineContract() throws IOException {
        tiJavaRoot = findTiJavaRoot();
        contractRoot = JSON.readTree(Files.readString(
                resolveInsideTiJava("docs/refactor/phase1/module-contracts.json"), StandardCharsets.UTF_8));
        shapeStatusRoot = JSON.readTree(Files.readString(
                resolveInsideTiJava("docs/refactor/phase4a/application-api-shape-status.json"),
                StandardCharsets.UTF_8));
        contractModules = readModules(contractRoot);
        eventOnlyEdges = readEventOnlyEdges(contractRoot);
    }

    @Test
    void everyJavaModuleDeclarationExactlyMatchesTheMachineDependencyContract() throws Exception {
        var expectedIds = new LinkedHashSet<>(contractModules.keySet());
        expectedIds.add("sharedkernel");

        var actualIds = new LinkedHashSet<String>();
        for (ContractModule module : contractModules.values()) {
            ApplicationModule declaration = packageAnnotation(module.basePackage(), ApplicationModule.class);
            actualIds.add(declaration.id());
            assertThat(declaration.id()).isEqualTo(module.id());

            Set<String> declaredQualified = Set.copyOf(Arrays.asList(declaration.allowedDependencies()));
            Set<String> expectedQualified = qualifyDependencies(module.id(), module.allowedDependencies());

            assertThat(declaredQualified)
                    .as("qualified dependencies of %s", module.id())
                    .containsExactlyInAnyOrderElementsOf(expectedQualified);
            assertThat(declaredQualified)
                    .allMatch(dependency -> dependency.contains("::"), "every dependency names an interface");
            assertThat(stripInterfaces(declaredQualified))
                    .as("provider ids of %s", module.id())
                    .containsExactlyInAnyOrderElementsOf(module.allowedDependencies());

            if (!module.id().equals("web")) {
                NamedInterface api = packageAnnotation(module.basePackage() + ".api", NamedInterface.class);
                assertThat(Arrays.asList(api.value())).contains("api");
            }
            assertPublicApplicationContract(module);
        }

        ApplicationModule sharedKernel = packageAnnotation(
                contractRoot.path("shared_kernel").path("base_package").asString(), ApplicationModule.class);
        actualIds.add(sharedKernel.id());
        assertThat(sharedKernel.id()).isEqualTo("sharedkernel");
        assertThat(sharedKernel.allowedDependencies()).isEmpty();
        assertThat(Arrays.asList(packageAnnotation(
                                "io.saksk.ti.sharedkernel.api", NamedInterface.class)
                        .value()))
                .containsExactly("api");

        assertThat(actualIds).containsExactlyInAnyOrderElementsOf(expectedIds);
    }

    @Test
    void eventOnlyEdgesCannotFallBackToTheProvidersOrdinaryApi() throws Exception {
        for (Edge edge : eventOnlyEdges) {
            ContractModule consumer = contractModules.get(edge.consumer());
            ApplicationModule declaration = packageAnnotation(consumer.basePackage(), ApplicationModule.class);
            assertThat(declaration.allowedDependencies())
                    .as("%s must consume %s events only", edge.consumer(), edge.provider())
                    .contains(edge.provider() + "::events")
                    .doesNotContain(edge.provider() + "::api");

            ContractModule provider = contractModules.get(edge.provider());
            NamedInterface events = packageAnnotation(provider.basePackage() + ".api.events", NamedInterface.class);
            assertThat(Arrays.asList(events.value()))
                    .as("provider event contract remains both public API and a narrow events interface")
                    .contains("api", "events");
        }

        assertThat(eventOnlyEdges).contains(
                new Edge("learning", "assessment"),
                new Edge("messaging", "assessment"),
                new Edge("messaging", "learning"),
                new Edge("messaging", "community"),
                new Edge("messaging", "campus"),
                new Edge("messaging", "coding"),
                new Edge("messaging", "intelligence"));
    }

    @Test
    void allDataOwnershipRowsHaveOneIdenticalOwnerInTheModuleContract() throws IOException {
        Map<ResourceKey, String> contractOwners = resourceOwnersFromContract();
        Map<ResourceKey, String> matrixOwners = resourceOwnersFromCsv(
                resolveInsideTiJava("docs/refactor/03-data-ownership.csv"));

        assertThat(contractOwners).hasSize(154);
        assertThat(contractOwners).containsExactlyInAnyOrderEntriesOf(matrixOwners);

        long tableCount = contractOwners.keySet().stream()
                .filter(key -> key.kind().equals("table"))
                .count();
        assertThat(tableCount).isEqualTo(70);
    }

    @Test
    void latestPublicShapesExactlyMatchImplementedOperationsAndKeepTheRestDeferred() throws Exception {
        assertThat(shapeStatusRoot.path("migrated_route_count").asInt()).isEqualTo(4);
        assertThat(shapeStatusRoot.path("implemented_route_backed_operation_count").asInt()).isEqualTo(4);
        assertThat(shapeStatusRoot.path("implemented_public_application_method_count").asInt()).isEqualTo(7);
        assertThat(shapeStatusRoot.path("event_payload_shape_status").asString())
                .isEqualTo("deferred_to_phase5");

        Map<String, JsonNode> statusByModule = new LinkedHashMap<>();
        for (JsonNode status : shapeStatusRoot.path("modules")) {
            JsonNode previous = statusByModule.put(status.path("module_id").asString(), status);
            assertThat(previous).as("duplicate latest API status row").isNull();
        }
        assertThat(statusByModule.keySet())
                .containsExactlyInAnyOrderElementsOf(
                        contractModules.keySet().stream().filter(id -> !id.equals("web")).toList());

        int implementedMethodCount = 0;
        Set<String> trackedApiSources = new LinkedHashSet<>();
        for (ContractModule module : contractModules.values()) {
            if (module.id().equals("web")) {
                continue;
            }
            JsonNode acceptedApi = module.node().path("public_application_apis").get(0);
            JsonNode status = statusByModule.get(module.id());
            String className = acceptedApi.path("package").asString()
                    + "."
                    + acceptedApi.path("type").asString();
            trackedApiSources.add(className.replace('.', '/') + ".java");

            assertThat(status.path("java_api").asString()).isEqualTo(className);
            assertThat(strings(status.path("phase1_inputs")))
                    .containsExactlyInAnyOrderElementsOf(strings(acceptedApi.path("inputs")));
            assertThat(strings(status.path("phase1_outputs")))
                    .containsExactlyInAnyOrderElementsOf(strings(acceptedApi.path("outputs")));

            Class<?> apiType = Class.forName(className);
            JsonNode methods = status.path("methods");
            if (status.path("shape_status").asString().equals("deferred_shape")) {
                assertThat(methods).isEmpty();
                assertThat(apiType.getDeclaredMethods())
                        .as("deferred API %s must not invent methods", className)
                        .isEmpty();
            } else {
                assertThat(status.path("shape_status").asString()).isEqualTo("partially_implemented");
                assertThat(module.id()).isIn("identity", "catalog", "operations");
                assertExactMethodShapes(apiType, methods);
                implementedMethodCount += methods.size();
            }
            assertThat(apiType.getDeclaredClasses())
                    .as("application API %s must use top-level reviewed DTOs", className)
                    .isEmpty();

            for (JsonNode additionalApi : status.path("additional_public_apis")) {
                String additionalClassName = additionalApi.path("java_api").asString();
                trackedApiSources.add(additionalClassName.replace('.', '/') + ".java");
                Class<?> additionalType = Class.forName(additionalClassName);
                assertThat(additionalType.isInterface()).isTrue();
                assertThat(Modifier.isPublic(additionalType.getModifiers())).isTrue();
                assertThat(additionalApi.path("direct_http_operation").asBoolean()).isFalse();
                JsonNode additionalMethods = additionalApi.path("methods");
                assertExactMethodShapes(additionalType, additionalMethods);
                implementedMethodCount += additionalMethods.size();
            }
        }
        assertThat(implementedMethodCount)
                .isEqualTo(shapeStatusRoot.path("implemented_public_application_method_count").asInt());

        Path javaRoot = resolveInsideTiJava("server/src/main/java");
        try (var sources = Files.walk(javaRoot)) {
            Set<String> actualApiSources = sources
                    .filter(Files::isRegularFile)
                    .map(javaRoot::relativize)
                    .map(path -> path.toString().replace('\\', '/'))
                    .filter(path -> path.contains("/api/") && path.endsWith("Api.java"))
                    .collect(java.util.stream.Collectors.toCollection(LinkedHashSet::new));
            assertThat(actualApiSources)
                    .as("every public application API source must be tracked by the latest shape status")
                    .containsExactlyInAnyOrderElementsOf(trackedApiSources);
        }
        try (var sources = Files.walk(javaRoot)) {
            assertThat(sources
                            .filter(Files::isRegularFile)
                            .filter(path -> path.toString().replace('\\', '/').contains("/api/events/"))
                            .filter(path -> !path.getFileName().toString().equals("package-info.java"))
                            .toList())
                    .as("event payload records stay deferred until Phase 5 evidence")
                    .isEmpty();
        }
    }

    @Test
    void phase3RouteAndOpenApiDeltasMaterializeExactlyTwoOperationsWithoutChangingBaselines()
            throws Exception {
        Path routeBaseline = resolveInsideTiJava("docs/refactor/02-route-parity-matrix.csv");
        Path deltaPath = resolveInsideTiJava("docs/refactor/phase3/route-parity-delta.csv");
        JsonNode effective = JSON.readTree(Files.readString(
                resolveInsideTiJava("docs/refactor/phase3/effective-route-parity-status.json"),
                StandardCharsets.UTF_8));
        JsonNode openApi = JSON.readTree(Files.readString(
                resolveInsideTiJava("openapi/phase3-authentication.openapi.json"),
                StandardCharsets.UTF_8));

        assertThat(sha256(routeBaseline))
                .isEqualTo(effective.path("baseline").path("sha256").asString());
        assertThat(sha256(deltaPath))
                .isEqualTo(effective.path("delta").path("sha256").asString());
        assertThat(sha256(resolveInsideTiJava("contracts/openapi.json")))
                .isEqualTo(openApi.path("x-ti-base-contract").path("sha256").asString());
        assertThat(openApi.path("x-ti-base-contract").path("immutable").asBoolean()).isTrue();

        List<String> baselineLines = Files.readAllLines(routeBaseline, StandardCharsets.UTF_8);
        List<String> baselineHeader = parseCsvLine(baselineLines.getFirst());
        Map<String, Integer> baselineColumns = csvColumns(baselineHeader);
        Map<RouteKey, Map<String, String>> baselineOperations = new LinkedHashMap<>();
        for (String line : baselineLines.subList(1, baselineLines.size())) {
            List<String> values = parseCsvLine(line);
            Map<String, String> row = csvRow(baselineHeader, values);
            for (String method : row.get("methods").split(",")) {
                RouteKey key = new RouteKey(row.get("route_id"), row.get("path"), method);
                assertThat(baselineOperations.put(key, row)).as("duplicate baseline operation %s", key).isNull();
            }
        }
        assertThat(baselineColumns).containsKeys("target_module", "migration_status");
        assertThat(baselineLines).hasSize(593);
        assertThat(baselineOperations).hasSize(611);

        List<String> deltaLines = Files.readAllLines(deltaPath, StandardCharsets.UTF_8);
        List<String> deltaHeader = parseCsvLine(deltaLines.getFirst());
        assertThat(deltaHeader).containsExactly(
                "route_id",
                "path",
                "method",
                "base_target_module",
                "phase3_target_module",
                "base_migration_status",
                "phase3_migration_status",
                "application_api",
                "java_evidence",
                "parity_evidence",
                "approved_difference_ids",
                "production_cutover");
        assertThat(deltaLines).hasSize(3);

        Map<RouteKey, String> expectedParityEvidence = Map.of(
                new RouteKey("88d7dc05cdbb", "/api/auth/login-methods", "GET"),
                "p3-009 warm READ_COMPARE pass report "
                        + "sha256:37128ff0786211474f84f60a131934ebcbaac4c8cc0fa02bd5299f46a19590aa; "
                        + "cold expected fail report "
                        + "sha256:d733dc7f62c7b86dd185d0f2c731069cad6a2d2b82926d346ef2fd4ff8c275c2 "
                        + "only excluded Flask-Limiter runtime key; no business or persistent side effect",
                new RouteKey("02366fc520ac", "/api/login", "POST"),
                "p3-009 isolated same-snapshot Flask/Java final-state report pass "
                        + "sha256:3dc21a524bfae335d763ac49d4f480962c536ec5c99af021ac27b583ae9c40f5");
        Map<RouteKey, Map<String, String>> deltas = new LinkedHashMap<>();
        for (String line : deltaLines.subList(1, deltaLines.size())) {
            Map<String, String> delta = csvRow(deltaHeader, parseCsvLine(line));
            RouteKey key = new RouteKey(delta.get("route_id"), delta.get("path"), delta.get("method"));
            assertThat(deltas.put(key, delta)).as("duplicate Phase 3 delta %s", key).isNull();

            Map<String, String> baseline = baselineOperations.get(key);
            assertThat(baseline).as("Phase 3 delta must match a frozen baseline operation").isNotNull();
            assertThat(delta.get("base_target_module")).isEqualTo(baseline.get("target_module"));
            assertThat(delta.get("base_migration_status")).isEqualTo(baseline.get("migration_status"));
            assertThat(delta.get("base_migration_status")).isEqualTo("pending");
            assertThat(delta.get("phase3_migration_status")).isEqualTo("migrated");
            assertThat(delta.get("production_cutover")).isEqualTo("false");
            assertThat(delta.get("java_evidence")).isNotBlank();
            assertThat(delta.get("parity_evidence"))
                    .as("Phase 3 parity evidence must be exact for %s", key)
                    .isEqualTo(expectedParityEvidence.get(key));
        }

        Set<RouteKey> expected = Set.of(
                new RouteKey("02366fc520ac", "/api/login", "POST"),
                new RouteKey("88d7dc05cdbb", "/api/auth/login-methods", "GET"));
        assertThat(deltas.keySet()).containsExactlyInAnyOrderElementsOf(expected);

        assertThat(effective.path("baseline").path("rule_count").asInt()).isEqualTo(592);
        assertThat(effective.path("baseline").path("expanded_operation_count").asInt()).isEqualTo(611);
        assertThat(effective.path("effective").path("expanded_operation_count").asInt()).isEqualTo(611);
        assertThat(effective.path("effective").path("overridden_operation_count").asInt()).isEqualTo(2);
        assertThat(effective.path("effective").path("migration_status").path("pending").asInt())
                .isEqualTo(baselineOperations.size() - deltas.size());
        assertThat(effective.path("effective").path("migration_status").path("migrated").asInt())
                .isEqualTo(deltas.size());
        assertThat(effective.path("effective").path("production_cutover_operation_count").asInt())
                .isZero();
        Map<RouteKey, String> materializedMigrated = new LinkedHashMap<>();
        for (JsonNode operation : effective.path("effective").path("migrated_operations")) {
            RouteKey key = new RouteKey(
                    operation.path("route_id").asString(),
                    operation.path("path").asString(),
                    operation.path("method").asString());
            assertThat(materializedMigrated.put(key, operation.path("target_module").asString()))
                    .as("duplicate materialized Phase 3 route %s", key)
                    .isNull();
        }
        assertThat(materializedMigrated.keySet()).containsExactlyInAnyOrderElementsOf(deltas.keySet());
        for (Map.Entry<RouteKey, Map<String, String>> entry : deltas.entrySet()) {
            assertThat(materializedMigrated.get(entry.getKey()))
                    .isEqualTo(entry.getValue().get("phase3_target_module"));
        }

        assertThat(openApi.path("openapi").asString()).isEqualTo("3.1.2");
        assertThat(openApi.path("paths").size()).isEqualTo(2);
        assertThat(openApi.path("paths").has("/api/csrf")).isFalse();
        assertThat(openApi.path("x-ti-supporting-security-endpoints")).hasSize(1);
        JsonNode supportingCsrf = openApi.path("x-ti-supporting-security-endpoints").get(0);
        assertThat(supportingCsrf.path("path").asString()).isEqualTo("/api/csrf");
        assertThat(supportingCsrf.path("method").asString()).isEqualTo("GET");
        assertThat(supportingCsrf.path("legacyMigrationRoute").asBoolean()).isFalse();
        assertThat(supportingCsrf.path("anonymousSessionTimeoutSeconds").asInt()).isEqualTo(600);
        assertThat(supportingCsrf.path("countsTowardMigratedRouteTotal").asBoolean())
                .isFalse();
        JsonNode authenticationTransition =
                openApi.path("x-ti-supporting-authentication-transition");
        assertThat(authenticationTransition.path("legacyBearerBehavior").asString())
                .contains("current request only", "without falling back", "never creates or extends");
        assertThat(strings(authenticationTransition.path("approvedDifferenceIds")))
                .containsExactly("P3-AUTH-006");
        assertThat(authenticationTransition.path("legacyMigrationRoute").asBoolean()).isFalse();
        assertThat(authenticationTransition.path("countsTowardMigratedRouteTotal").asBoolean())
                .isFalse();
        int renderedOperations = 0;
        for (Map.Entry<RouteKey, Map<String, String>> entry : deltas.entrySet()) {
            RouteKey key = entry.getKey();
            JsonNode pathItem = openApi.path("paths").path(key.path());
            assertThat(pathItem.size())
                    .as("Phase 3 OpenAPI path %s must contain exactly one HTTP operation", key.path())
                    .isEqualTo(1);
            JsonNode operation = pathItem.path(key.method().toLowerCase());
            assertThat(operation.isMissingNode()).isFalse();
            assertThat(operation.path("x-ti-route-id").asString()).isEqualTo(key.routeId());
            assertThat(operation.path("x-ti-application-api").asString())
                    .isEqualTo(entry.getValue().get("application_api"));
            assertThat(operation.path("x-ti-migration").path("status").asString()).isEqualTo("migrated");
            assertThat(operation.path("x-ti-migration").path("productionCutover").asBoolean()).isFalse();
            JsonNode migrationEvidence = operation.path("x-ti-migration");
            if (key.routeId().equals("88d7dc05cdbb")) {
                assertThat(migrationEvidence.path("liveDualRuntimeReadReport").asString())
                        .isEqualTo("sha256:37128ff0786211474f84f60a131934ebcbaac4c8cc0fa02bd5299f46a19590aa");
                assertThat(migrationEvidence.path("coldReadProbeReport").asString())
                        .isEqualTo("sha256:d733dc7f62c7b86dd185d0f2c731069cad6a2d2b82926d346ef2fd4ff8c275c2");
                assertThat(migrationEvidence.path("coldReadProbeOutcome").asString())
                        .isEqualTo("expected-fail:one-excluded-flask-limiter-runtime-key:"
                                + "no-business-or-persistent-side-effect");
                assertThat(migrationEvidence.path("isolatedSameSnapshotWriteReport").isMissingNode())
                        .isTrue();
            } else if (key.routeId().equals("02366fc520ac")) {
                assertThat(migrationEvidence.path("isolatedSameSnapshotWriteReport").asString())
                        .isEqualTo("sha256:3dc21a524bfae335d763ac49d4f480962c536ec5c99af021ac27b583ae9c40f5");
                assertThat(migrationEvidence.path("liveDualRuntimeReadReport").isMissingNode())
                        .isTrue();
                assertThat(migrationEvidence.path("coldReadProbeReport").isMissingNode())
                        .isTrue();
            } else {
                throw new AssertionError("unexpected Phase 3 route evidence: " + key);
            }
            assertThat(strings(operation.path("tags")))
                    .containsExactly(entry.getValue().get("phase3_target_module"));
            String differences = entry.getValue().get("approved_difference_ids");
            if (differences.equals("none")) {
                assertThat(operation.path("x-ti-approved-differences").isMissingNode()).isTrue();
            } else {
                assertThat(strings(operation.path("x-ti-approved-differences")))
                        .containsExactlyInAnyOrderElementsOf(List.of(differences.split(";")));
            }
            renderedOperations++;
        }
        assertThat(openApi.path("paths").path("/api/login").path("post")
                        .path("responses").has("413"))
                .isTrue();
        assertThat(openApi.path("paths").path("/api/login").path("post")
                        .path("responses").path("429").path("description").asString())
                .contains("global", "HMAC-pseudonymized client-IP", "normalized-account");
        for (String status : List.of("429", "503")) {
            JsonNode alternatives = openApi.path("paths").path("/api/login").path("post")
                    .path("responses").path(status).path("content").path("application/json")
                    .path("schema").path("oneOf");
            assertThat(alternatives).hasSize(2);
            assertThat(java.util.stream.StreamSupport.stream(alternatives.spliterator(), false)
                            .map(node -> node.path("$ref").asString())
                            .toList())
                    .as("/api/login %s must document controller and pre-security envelopes", status)
                    .containsExactly(
                            "#/components/schemas/LegacyLoginError",
                            "#/components/schemas/SecurityErrorEnvelope");
        }
        assertThat(renderedOperations).isEqualTo(2);
    }

    @Test
    void phase4aSubjectContractsMaterializeTwoAdditionalCatalogOperations() throws Exception {
        Path baselinePath = resolveInsideTiJava("docs/refactor/02-route-parity-matrix.csv");
        Path phase3DeltaPath = resolveInsideTiJava("docs/refactor/phase3/route-parity-delta.csv");
        Path phase4aDeltaPath = resolveInsideTiJava("docs/refactor/phase4a/route-parity-delta.csv");
        JsonNode effective = JSON.readTree(Files.readString(
                resolveInsideTiJava("docs/refactor/phase4a/effective-route-parity-status.json"),
                StandardCharsets.UTF_8));
        JsonNode openApi = JSON.readTree(Files.readString(
                resolveInsideTiJava("openapi/phase4a-subject-directory.openapi.json"),
                StandardCharsets.UTF_8));
        JsonNode golden = JSON.readTree(Files.readString(
                resolveInsideTiJava("docs/refactor/phase4a/golden-subject-reads.json"),
                StandardCharsets.UTF_8));
        JsonNode queryPlan = JSON.readTree(Files.readString(
                resolveInsideTiJava("docs/refactor/phase4a/subject-query-plan.json"),
                StandardCharsets.UTF_8));
        JsonNode subjectContract = JSON.readTree(Files.readString(
                resolveInsideTiJava("docs/refactor/phase4a/subject-read-contract.json"),
                StandardCharsets.UTF_8));
        JsonNode businessInvariants = JSON.readTree(Files.readString(
                resolveInsideTiJava("docs/refactor/phase4a/business-invariants.json"),
                StandardCharsets.UTF_8));
        JsonNode ownership = JSON.readTree(Files.readString(
                resolveInsideTiJava("docs/refactor/phase4a/effective-data-ownership-status.json"),
                StandardCharsets.UTF_8));

        assertThat(sha256(baselinePath))
                .isEqualTo(effective.path("baseline").path("sha256").asString());
        assertThat(sha256(phase3DeltaPath))
                .isEqualTo(effective.path("deltas").get(0).path("sha256").asString());
        assertThat(sha256(phase4aDeltaPath))
                .isEqualTo(effective.path("deltas").get(1).path("sha256").asString());
        assertThat(sha256(resolveInsideTiJava("contracts/openapi.json")))
                .isEqualTo(openApi.path("x-ti-base-contract").path("sha256").asString());
        assertThat(openApi.path("x-ti-base-contract").path("immutable").asBoolean()).isTrue();
        assertThat(sha256(resolveInsideTiJava("docs/refactor/03-data-ownership.csv")))
                .isEqualTo(ownership.path("baseline").path("sha256").asString());
        assertThat(sha256(resolveInsideTiJava(
                        "docs/refactor/phase4a/data-ownership-delta.csv")))
                .isEqualTo(ownership.path("delta").path("sha256").asString());
        assertThat(ownership.path("effective").path("resource_count").asInt()).isEqualTo(155);
        assertThat(ownership.path("effective").path("resources_with_exactly_one_owner").asInt())
                .isEqualTo(155);
        JsonNode limiterOwnership = ownership.path("effective").path("new_resources").get(0);
        assertThat(limiterOwnership.path("owner").asString()).isEqualTo("catalog");
        assertThat(limiterOwnership.path("resource_name").asString())
                .contains(":identity:v1:<hmac_sha256>:")
                .doesNotContain("identity_id", ":uid:");
        assertThat(limiterOwnership.path("business_fact").asBoolean()).isFalse();
        assertThat(limiterOwnership.path("production_cutover").asBoolean()).isFalse();

        List<String> baselineLines = Files.readAllLines(baselinePath, StandardCharsets.UTF_8);
        List<String> baselineHeader = parseCsvLine(baselineLines.getFirst());
        Map<RouteKey, Map<String, String>> baselineOperations = new LinkedHashMap<>();
        for (String line : baselineLines.subList(1, baselineLines.size())) {
            Map<String, String> row = csvRow(baselineHeader, parseCsvLine(line));
            for (String method : row.get("methods").split(",")) {
                baselineOperations.put(new RouteKey(row.get("route_id"), row.get("path"), method), row);
            }
        }

        List<String> deltaLines = Files.readAllLines(phase4aDeltaPath, StandardCharsets.UTF_8);
        List<String> deltaHeader = parseCsvLine(deltaLines.getFirst());
        assertThat(deltaHeader).containsExactly(
                "route_id",
                "path",
                "method",
                "base_target_module",
                "phase4a_target_module",
                "base_migration_status",
                "phase4a_migration_status",
                "application_api",
                "java_evidence",
                "parity_evidence",
                "approved_difference_ids",
                "production_cutover");
        assertThat(deltaLines).hasSize(3);

        Set<RouteKey> expected = Set.of(
                new RouteKey("d3cd12aaca90", "/api/quiz/subjects", "GET"),
                new RouteKey("7fd9b0fc8111", "/api/quiz/subjects/meta", "GET"));
        Map<RouteKey, Map<String, String>> deltas = new LinkedHashMap<>();
        for (String line : deltaLines.subList(1, deltaLines.size())) {
            Map<String, String> delta = csvRow(deltaHeader, parseCsvLine(line));
            RouteKey key = new RouteKey(delta.get("route_id"), delta.get("path"), delta.get("method"));
            assertThat(deltas.put(key, delta)).as("duplicate Phase 4A delta %s", key).isNull();
            Map<String, String> baseline = baselineOperations.get(key);
            assertThat(baseline).isNotNull();
            assertThat(delta.get("base_target_module")).isEqualTo(baseline.get("target_module"));
            assertThat(delta.get("base_target_module")).isEqualTo("learning");
            assertThat(delta.get("phase4a_target_module")).isEqualTo("catalog");
            assertThat(delta.get("base_migration_status")).isEqualTo("pending");
            assertThat(delta.get("phase4a_migration_status")).isEqualTo("migrated");
            assertThat(delta.get("application_api"))
                    .isEqualTo("io.saksk.ti.catalog.api.CatalogApplicationApi#subjectCatalog");
            assertThat(delta.get("parity_evidence"))
                    .contains("sha256:" + sha256(resolveInsideTiJava(
                            "docs/refactor/phase4a/golden-subject-reads.json")));
            assertThat(delta.get("approved_difference_ids"))
                    .isEqualTo("P4A-CATALOG-001;P4A-CATALOG-002;P4A-CATALOG-003");
            assertThat(delta.get("production_cutover")).isEqualTo("false");
        }
        assertThat(deltas.keySet()).containsExactlyInAnyOrderElementsOf(expected);

        assertThat(effective.path("effective").path("expanded_operation_count").asInt()).isEqualTo(611);
        assertThat(effective.path("effective").path("overridden_operation_count").asInt()).isEqualTo(4);
        assertThat(effective.path("effective").path("migration_status").path("migrated").asInt())
                .isEqualTo(4);
        assertThat(effective.path("effective").path("migration_status").path("pending").asInt())
                .isEqualTo(607);
        assertThat(effective.path("effective").path("production_cutover_operation_count").asInt())
                .isZero();
        assertThat(effective.path("effective").path("migrated_operations")).hasSize(4);

        assertThat(openApi.path("openapi").asString()).isEqualTo("3.1.2");
        assertThat(openApi.path("paths")).hasSize(2);
        for (RouteKey key : expected) {
            JsonNode operation = openApi.path("paths").path(key.path()).path("get");
            assertThat(operation.path("x-ti-route-id").asString()).isEqualTo(key.routeId());
            assertThat(operation.path("x-ti-application-api").asString())
                    .isEqualTo(deltas.get(key).get("application_api"));
            assertThat(operation.path("x-ti-migration").path("status").asString())
                    .isEqualTo("migrated");
            assertThat(operation.path("x-ti-migration").path("productionCutover").asBoolean())
                    .isFalse();
            assertThat(strings(operation.path("x-ti-approved-differences")))
                    .containsExactlyInAnyOrder(
                            "P4A-CATALOG-001",
                            "P4A-CATALOG-002",
                            "P4A-CATALOG-003");
            assertThat(operation.path("x-ti-query-budget")
                            .path("authenticationAuthoritySelects").asInt())
                    .isEqualTo(1);
            assertThat(operation.path("x-ti-query-budget")
                            .path("businessUseCaseSelects").asInt())
                    .isEqualTo(2);
            assertThat(operation.path("x-ti-query-budget")
                            .path("normalSuccessfulHttpSelects").asInt())
                    .isEqualTo(3);
            assertThat(operation.path("security")).hasSize(3);
            for (String status : List.of("200", "401", "429", "500", "503")) {
                assertThat(operation.path("responses").has(status)).isTrue();
            }
        }
        assertThat(java.util.stream.StreamSupport.stream(
                        openApi.path("x-ti-credential-semantics")
                                .path("precedence").spliterator(),
                        false)
                .map(JsonNode::asString)
                .toList())
                .containsExactly("Authorization", "targetSession", "legacyFlaskSession");
        for (String responseName : List.of("RateLimited", "RuntimeUnavailable")) {
            assertThat(openApi.path("components").path("responses").path(responseName)
                            .path("content").path("application/json").path("schema")
                            .path("oneOf"))
                    .hasSize(2);
        }

        assertThat(golden.path("database_side_effect_free").asBoolean()).isTrue();
        assertThat(golden.path("cases")).hasSize(7);
        JsonNode rateGolden = java.util.stream.StreamSupport.stream(
                        golden.path("cases").spliterator(), false)
                .filter(node -> node.path("case_id").asString().equals("subjects-rate-limited"))
                .findFirst()
                .orElseThrow();
        assertThat(rateGolden.path("response").path("status").asInt()).isEqualTo(429);
        assertThat(rateGolden.path("response").path("body").path("payload").isNull()).isTrue();
        assertThat(rateGolden.path("response").path("headers").path("X-RateLimit-Limit").asString())
                .isEqualTo("60");

        assertThat(queryPlan.path("data_set").path("actual_row_counts").path("subjects").asInt())
                .isGreaterThanOrEqualTo(5_000);
        assertThat(queryPlan.path("data_set").path("actual_row_counts").path("questions").asInt())
                .isGreaterThanOrEqualTo(50_000);
        assertThat(queryPlan.path("measurement").path("queries")).hasSize(2);
        assertThat(queryPlan.path("scope").asString())
                .isEqualTo("protected-subject-directory-business-queries");
        assertThat(queryPlan.path("scope_note").asString())
                .contains("two SELECTs", "authentication-authority SELECT", "three SELECTs");
        assertThat(queryPlan.path("interpretation").path("status").asString())
                .isEqualTo("observational_evidence_only");
        assertThat(openApi.path("paths").path("/api/quiz/subjects/meta").path("get")
                        .path("x-ti-migration").path("queryPlanEvidence").asString())
                .isEqualTo("sha256:" + sha256(resolveInsideTiJava(
                        "docs/refactor/phase4a/subject-query-plan.json")));

        JsonNode queryBudget = subjectContract.path("query_budget");
        assertThat(queryBudget.path("authentication_authority_selects").asInt()).isEqualTo(1);
        assertThat(queryBudget.path("business_use_case_selects").asInt()).isEqualTo(2);
        assertThat(queryBudget.path("maximum_selects_per_http_request").asInt()).isEqualTo(3);
        JsonNode runtimeWrites = subjectContract.path("transaction")
                .path("redis_runtime_writes_by_credential");
        assertThat(runtimeWrites).hasSize(3);
        assertThat(runtimeWrites.has("legacy_bearer")).isTrue();
        assertThat(runtimeWrites.has("target_session")).isTrue();
        assertThat(runtimeWrites.has("legacy_flask_session_exchange")).isTrue();
        assertThat(businessInvariants.path("invariants")).hasSize(12);
        assertThat(businessInvariants.path("invariants").get(7).path("statement").asString())
                .contains("total of three");
        assertThat(businessInvariants.path("invariants").get(8).path("statement").asString())
                .contains("Bearer", "target Session", "Flask Session");
    }

    private static void assertPublicApplicationContract(ContractModule module) throws ClassNotFoundException {
        JsonNode applicationApis = module.node().path("public_application_apis");
        if (module.id().equals("web")) {
            assertThat(applicationApis).isEmpty();
            return;
        }

        assertThat(applicationApis).hasSize(1);
        JsonNode applicationApi = applicationApis.get(0);
        String className = applicationApi.path("package").asString()
                + "."
                + applicationApi.path("type").asString();
        Class<?> apiType = Class.forName(className);
        assertThat(apiType.isInterface()).isTrue();
        assertThat(Modifier.isPublic(apiType.getModifiers())).isTrue();
    }

    private static Set<String> qualifyDependencies(String consumer, Set<String> providers) {
        var result = new LinkedHashSet<String>();
        for (String provider : providers) {
            String namedInterface = eventOnlyEdges.contains(new Edge(consumer, provider)) ? "events" : "api";
            result.add(provider + "::" + namedInterface);
        }
        return result;
    }

    private static Set<String> stripInterfaces(Set<String> dependencies) {
        var result = new LinkedHashSet<String>();
        for (String dependency : dependencies) {
            result.add(dependency.substring(0, dependency.indexOf("::")));
        }
        return result;
    }

    private static Map<String, ContractModule> readModules(JsonNode root) {
        var modules = new LinkedHashMap<String, ContractModule>();
        for (JsonNode module : root.path("modules")) {
            String id = module.path("module_id").asString();
            Set<String> dependencies = strings(module.path("allowed_dependencies"));
            ContractModule previous = modules.put(
                    id,
                    new ContractModule(
                            id, module.path("base_package").asString(), dependencies, module));
            if (previous != null) {
                throw new IllegalStateException("duplicate contract module: " + id);
            }
        }
        return Map.copyOf(modules);
    }

    private static Set<Edge> readEventOnlyEdges(JsonNode root) {
        var edges = new LinkedHashSet<Edge>();
        for (JsonNode edge : root.path("public_event_edges")) {
            if (edge.path("mode").asString().equals("asynchronous_consumption_only")) {
                edges.add(new Edge(edge.path("consumer").asString(), edge.path("provider").asString()));
            }
        }
        return Set.copyOf(edges);
    }

    private static Set<String> strings(JsonNode array) {
        var values = new LinkedHashSet<String>();
        for (JsonNode node : array) {
            values.add(node.asString());
        }
        return Set.copyOf(values);
    }

    private static List<String> orderedStrings(JsonNode array) {
        var values = new ArrayList<String>();
        for (JsonNode node : array) {
            values.add(node.asString());
        }
        return List.copyOf(values);
    }

    private static void assertExactMethodShapes(Class<?> apiType, JsonNode methods) throws Exception {
        assertThat(apiType.getDeclaredMethods()).hasSize(methods.size());
        for (JsonNode methodShape : methods) {
            Class<?>[] parameters = orderedStrings(methodShape.path("parameter_types")).stream()
                    .map(ModuleContractParityTest::resolveType)
                    .toArray(Class<?>[]::new);
            var method = apiType.getDeclaredMethod(methodShape.path("name").asString(), parameters);
            assertThat(method.getReturnType().getName())
                    .isEqualTo(methodShape.path("return_type").asString());
            if (methodShape.has("generic_return_type")) {
                assertThat(method.getGenericReturnType().getTypeName())
                        .isEqualTo(methodShape.path("generic_return_type").asString());
            }
            assertThat(Modifier.isPublic(method.getModifiers())).isTrue();
            assertThat(Modifier.isAbstract(method.getModifiers())).isTrue();
        }
    }

    private static Class<?> resolveType(String type) {
        return switch (type) {
            case "int" -> int.class;
            case "long" -> long.class;
            case "boolean" -> boolean.class;
            default -> {
                try {
                    yield Class.forName(type);
                } catch (ClassNotFoundException exception) {
                    throw new IllegalStateException("missing Phase 3 API type: " + type, exception);
                }
            }
        };
    }

    private static Map<String, Integer> csvColumns(List<String> header) {
        var columns = new LinkedHashMap<String, Integer>();
        for (int index = 0; index < header.size(); index++) {
            assertThat(columns.put(header.get(index), index)).as("duplicate CSV column").isNull();
        }
        return Map.copyOf(columns);
    }

    private static Map<String, String> csvRow(List<String> header, List<String> values) {
        assertThat(values).hasSameSizeAs(header);
        var row = new LinkedHashMap<String, String>();
        for (int index = 0; index < header.size(); index++) {
            row.put(header.get(index), values.get(index));
        }
        return Map.copyOf(row);
    }

    private static String sha256(Path path) throws IOException {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            return HexFormat.of().formatHex(digest.digest(Files.readAllBytes(path)));
        } catch (java.security.NoSuchAlgorithmException exception) {
            throw new IllegalStateException("SHA-256 is unavailable", exception);
        }
    }

    private static Map<ResourceKey, String> resourceOwnersFromContract() {
        var owners = new TreeMap<ResourceKey, String>();
        for (ContractModule module : contractModules.values()) {
            for (JsonNode table : module.node().path("owned_tables")) {
                putUnique(owners, new ResourceKey("table", table.asString()), module.id());
            }
            for (JsonNode resource : module.node().path("owned_resources")) {
                putUnique(
                        owners,
                        new ResourceKey(
                                resource.path("kind").asString(), resource.path("name").asString()),
                        module.id());
            }
        }
        return Map.copyOf(owners);
    }

    private static Map<ResourceKey, String> resourceOwnersFromCsv(Path csv) throws IOException {
        List<String> lines = Files.readAllLines(csv, StandardCharsets.UTF_8);
        assertThat(lines).isNotEmpty();
        assertThat(parseCsvLine(lines.getFirst()))
                .startsWith("resource_kind", "resource_name", "legacy_owner", "legacy_source", "target_owner");

        var owners = new TreeMap<ResourceKey, String>();
        for (String line : lines.subList(1, lines.size())) {
            if (line.isBlank()) {
                continue;
            }
            List<String> columns = parseCsvLine(line);
            assertThat(columns).as("CSV row: %s", line).hasSize(9);
            putUnique(owners, new ResourceKey(columns.get(0), columns.get(1)), columns.get(4));
        }
        return Map.copyOf(owners);
    }

    private static List<String> parseCsvLine(String line) {
        var columns = new ArrayList<String>();
        var current = new StringBuilder();
        boolean quoted = false;
        for (int index = 0; index < line.length(); index++) {
            char character = line.charAt(index);
            if (character == '"') {
                if (quoted && index + 1 < line.length() && line.charAt(index + 1) == '"') {
                    current.append('"');
                    index++;
                } else {
                    quoted = !quoted;
                }
            } else if (character == ',' && !quoted) {
                columns.add(current.toString());
                current.setLength(0);
            } else {
                current.append(character);
            }
        }
        if (quoted) {
            throw new IllegalArgumentException("unterminated CSV quote: " + line);
        }
        columns.add(current.toString());
        return List.copyOf(columns);
    }

    private static <K> void putUnique(Map<K, String> owners, K resource, String owner) {
        String previous = owners.put(resource, owner);
        if (previous != null) {
            throw new IllegalStateException(
                    "resource has multiple owners: " + resource + " -> " + previous + ", " + owner);
        }
    }

    private static <A extends Annotation> A packageAnnotation(String packageName, Class<A> annotationType)
            throws ClassNotFoundException {
        Package targetPackage = Class.forName(packageName + ".package-info").getPackage();
        A annotation = targetPackage.getAnnotation(annotationType);
        assertThat(annotation)
                .as("@%s on %s", annotationType.getSimpleName(), packageName)
                .isNotNull();
        return annotation;
    }

    private static Path findTiJavaRoot() throws IOException {
        String configuredBaseDirectory = Objects.requireNonNull(
                System.getProperty("basedir"), "Maven must provide the fixed server basedir");
        Path serverRoot = Path.of(configuredBaseDirectory).toRealPath();
        if (!Files.isRegularFile(serverRoot.resolve("pom.xml"))) {
            throw new IllegalStateException("basedir is not the Ti-Java/server project: " + serverRoot);
        }
        Path root = serverRoot.getParent().toRealPath();
        return root;
    }

    private static Path resolveInsideTiJava(String relativePath) throws IOException {
        Path candidate = tiJavaRoot.resolve(relativePath).normalize().toRealPath();
        if (!candidate.startsWith(tiJavaRoot)) {
            throw new IllegalStateException("contract path escaped Ti-Java: " + candidate);
        }
        return candidate;
    }

    private record ContractModule(
            String id, String basePackage, Set<String> allowedDependencies, JsonNode node) {}

    private record Edge(String consumer, String provider) {}

    private record ResourceKey(String kind, String name) implements Comparable<ResourceKey> {
        @Override
        public int compareTo(ResourceKey other) {
            int kindOrder = kind.compareTo(other.kind);
            return kindOrder == 0 ? name.compareTo(other.name) : kindOrder;
        }
    }

    private record RouteKey(String routeId, String path, String method) {}
}
