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
        assertThat(shapeStatusRoot.path("migrated_route_count").asInt()).isEqualTo(11);
        assertThat(shapeStatusRoot.path("implemented_route_backed_operation_count").asInt()).isEqualTo(11);
        assertThat(shapeStatusRoot.path("implemented_public_application_method_count").asInt()).isEqualTo(13);
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
                boolean directHttpOperation =
                        additionalApi.path("direct_http_operation").asBoolean();
                if (directHttpOperation) {
                    assertThat(module.id()).isEqualTo("catalog");
                    assertThat(additionalClassName)
                            .isEqualTo("io.saksk.ti.catalog.api.PublicBankCatalogApi");
                    assertThat(additionalApi.path("lifecycle").asString())
                            .isEqualTo("catalog_public_bank_snapshot_query_boundary");
                    assertThat(strings(status.path("implemented_route_ids")))
                            .contains(
                                    "14642ebe7c1d",
                                    "db1ac691d6fb",
                                    "8cfb837021af",
                                    "a473896ff467",
                                    "b7e49e77a026",
                                    "f3644c1474f3",
                                    "37cd782b28dc");
                }
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
    void phase4aSubjectAndPublicBankContractsFormOneMachineClosedLoop() throws Exception {
        Path baselinePath = resolveInsideTiJava("docs/refactor/02-route-parity-matrix.csv");
        Path phase3DeltaPath = resolveInsideTiJava("docs/refactor/phase3/route-parity-delta.csv");
        Path phase4aDeltaPath = resolveInsideTiJava("docs/refactor/phase4a/route-parity-delta.csv");
        Path ownershipDeltaPath = resolveInsideTiJava(
                "docs/refactor/phase4a/data-ownership-delta.csv");
        Path publicOpenApiPath = resolveInsideTiJava(
                "openapi/phase4a-public-bank.openapi.json");
        Path publicGoldenPath = resolveInsideTiJava(
                "docs/refactor/phase4a/golden-public-bank-reads.json");
        Path publicRateContractPath = resolveInsideTiJava(
                "docs/refactor/phase4a/public-bank-rate-limit-contract.json");
        Path publicReadContractPath = resolveInsideTiJava(
                "docs/refactor/phase4a/public-bank-read-contract.json");
        Path publicQueryPlanPath = resolveInsideTiJava(
                "docs/refactor/phase4a/public-bank-query-plan-evidence.json");
        Path approvedDifferencesPath = resolveInsideTiJava(
                "docs/refactor/phase4a/approved-differences.md");
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
        JsonNode publicOpenApi = JSON.readTree(Files.readString(
                publicOpenApiPath, StandardCharsets.UTF_8));
        JsonNode publicGolden = JSON.readTree(Files.readString(
                publicGoldenPath, StandardCharsets.UTF_8));
        JsonNode publicRateContract = JSON.readTree(Files.readString(
                publicRateContractPath, StandardCharsets.UTF_8));
        JsonNode publicReadContract = JSON.readTree(Files.readString(
                publicReadContractPath, StandardCharsets.UTF_8));
        JsonNode publicQueryPlan = JSON.readTree(Files.readString(
                publicQueryPlanPath, StandardCharsets.UTF_8));

        assertThat(sha256(baselinePath))
                .isEqualTo(effective.path("baseline").path("sha256").asString());
        assertThat(sha256(phase3DeltaPath))
                .isEqualTo(effective.path("deltas").get(0).path("sha256").asString());
        assertThat(sha256(phase4aDeltaPath))
                .isEqualTo(effective.path("deltas").get(1).path("sha256").asString());
        assertThat(sha256(resolveInsideTiJava("contracts/openapi.json")))
                .isEqualTo(openApi.path("x-ti-base-contract").path("sha256").asString());
        assertThat(openApi.path("x-ti-base-contract").path("immutable").asBoolean()).isTrue();
        assertThat(sha256(resolveInsideTiJava("contracts/openapi.json")))
                .isEqualTo(publicOpenApi.path("x-ti-base-contract").path("sha256").asString());
        assertThat(publicOpenApi.path("x-ti-base-contract").path("immutable").asBoolean())
                .isTrue();
        assertThat(sha256(resolveInsideTiJava("docs/refactor/03-data-ownership.csv")))
                .isEqualTo(ownership.path("baseline").path("sha256").asString());
        assertThat(sha256(ownershipDeltaPath))
                .isEqualTo(ownership.path("delta").path("sha256").asString());
        assertThat(ownership.path("delta").path("new_resource_count").asInt()).isEqualTo(5);
        assertThat(ownership.path("effective").path("resource_count").asInt()).isEqualTo(159);
        assertThat(ownership.path("effective").path("resources_with_exactly_one_owner").asInt())
                .isEqualTo(159);
        Set<String> expectedNewResources = Set.of(
                "ti-java:catalog:subject-read-rate:<route>:identity:v1:<hmac_sha256>:<window>:<bucket>",
                "public_bank_plaza_viewer_state",
                "public_bank_plaza_snapshot_state",
                "ti-java:catalog:public-bank-read-rate:<route>:<identity|ip>:v1:"
                        + "<hmac_sha256>:<second|hour|day>",
                "ti-java:catalog:public-bank-snapshot:refresh-lock");
        JsonNode newResources = ownership.path("effective").path("new_resources");
        assertThat(newResources).hasSize(5);
        Set<String> observedNewResources = new LinkedHashSet<>();
        for (JsonNode resource : newResources) {
            assertThat(observedNewResources.add(resource.path("resource_name").asString()))
                    .as("duplicate Phase 4A ownership resource")
                    .isTrue();
            assertThat(resource.path("owner").asString()).isEqualTo("catalog");
            assertThat(resource.path("business_fact").asBoolean()).isFalse();
            assertThat(resource.path("production_cutover").asBoolean()).isFalse();
        }
        assertThat(observedNewResources)
                .containsExactlyInAnyOrderElementsOf(expectedNewResources);
        String subjectLimiter = observedNewResources.stream()
                .filter(name -> name.startsWith("ti-java:catalog:subject-read-rate:"))
                .findFirst()
                .orElseThrow();
        assertThat(subjectLimiter)
                .contains(":identity:v1:<hmac_sha256>:")
                .doesNotContain("identity_id", ":uid:");

        List<String> ownershipDeltaLines = Files.readAllLines(
                ownershipDeltaPath, StandardCharsets.UTF_8);
        assertThat(ownershipDeltaLines).hasSize(6);
        List<String> ownershipDeltaHeader = parseCsvLine(ownershipDeltaLines.getFirst());
        Set<String> observedOwnershipDeltaNames = new LinkedHashSet<>();
        for (String line : ownershipDeltaLines.subList(1, ownershipDeltaLines.size())) {
            Map<String, String> delta = csvRow(ownershipDeltaHeader, parseCsvLine(line));
            assertThat(observedOwnershipDeltaNames.add(delta.get("resource_name"))).isTrue();
            assertThat(delta.get("base_resource")).isEqualTo("false");
            assertThat(delta.get("phase4a_owner")).isEqualTo("catalog");
            assertThat(delta.get("production_cutover")).isEqualTo("false");
        }
        assertThat(observedOwnershipDeltaNames)
                .containsExactlyInAnyOrderElementsOf(expectedNewResources);

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
        assertThat(deltaLines).hasSize(10);
        assertThat(effective.path("deltas").get(1).path("operation_count").asInt())
                .isEqualTo(9);

        Set<RouteKey> expectedSubjects = Set.of(
                new RouteKey("d3cd12aaca90", "/api/quiz/subjects", "GET"),
                new RouteKey("7fd9b0fc8111", "/api/quiz/subjects/meta", "GET"));
        Map<RouteKey, String> expectedPublicApis = Map.ofEntries(
                Map.entry(
                        new RouteKey("14642ebe7c1d", "/api/public/banks", "GET"),
                        "io.saksk.ti.catalog.api.PublicBankCatalogApi#search"),
                Map.entry(
                        new RouteKey("db1ac691d6fb", "/api/public/banks/boards", "GET"),
                        "io.saksk.ti.catalog.api.PublicBankCatalogApi#boards"),
                Map.entry(
                        new RouteKey(
                                "8cfb837021af",
                                "/api/public/banks/card/<source_type>/<int:bank_id>",
                                "GET"),
                        "io.saksk.ti.catalog.api.PublicBankCatalogApi#detail"),
                Map.entry(
                        new RouteKey("a473896ff467", "/api/public/banks/hot", "GET"),
                        "io.saksk.ti.catalog.api.PublicBankCatalogApi#hot"),
                Map.entry(
                        new RouteKey("b7e49e77a026", "/api/public/banks/list", "GET"),
                        "io.saksk.ti.catalog.api.PublicBankCatalogApi#search"),
                Map.entry(
                        new RouteKey("f3644c1474f3", "/api/public/banks/summary", "GET"),
                        "io.saksk.ti.catalog.api.PublicBankCatalogApi#summary"),
                Map.entry(
                        new RouteKey(
                                "37cd782b28dc", "/api/public/banks/<int:bank_id>", "GET"),
                        "io.saksk.ti.catalog.api.PublicBankCatalogApi#detail"));
        Set<RouteKey> expected = new LinkedHashSet<>(expectedSubjects);
        expected.addAll(expectedPublicApis.keySet());
        Set<String> expectedPublicDifferences = Set.of(
                "P4A-CATALOG-004",
                "P4A-CATALOG-005",
                "P4A-CATALOG-006",
                "P4A-CATALOG-007",
                "P4A-CATALOG-008",
                "P4A-CATALOG-009");
        Set<String> observedPublicDifferences = new LinkedHashSet<>();
        Map<RouteKey, Map<String, String>> deltas = new LinkedHashMap<>();
        for (String line : deltaLines.subList(1, deltaLines.size())) {
            Map<String, String> delta = csvRow(deltaHeader, parseCsvLine(line));
            RouteKey key = new RouteKey(delta.get("route_id"), delta.get("path"), delta.get("method"));
            assertThat(deltas.put(key, delta)).as("duplicate Phase 4A delta %s", key).isNull();
            Map<String, String> baseline = baselineOperations.get(key);
            assertThat(baseline).isNotNull();
            assertThat(delta.get("base_target_module")).isEqualTo(baseline.get("target_module"));
            assertThat(delta.get("phase4a_target_module")).isEqualTo("catalog");
            assertThat(delta.get("base_migration_status")).isEqualTo("pending");
            assertThat(delta.get("phase4a_migration_status")).isEqualTo("migrated");
            assertThat(delta.get("production_cutover")).isEqualTo("false");
            if (expectedSubjects.contains(key)) {
                assertThat(delta.get("base_target_module")).isEqualTo("learning");
                assertThat(delta.get("application_api"))
                        .isEqualTo("io.saksk.ti.catalog.api.CatalogApplicationApi#subjectCatalog");
                assertThat(delta.get("parity_evidence"))
                        .contains("sha256:" + sha256(resolveInsideTiJava(
                                "docs/refactor/phase4a/golden-subject-reads.json")));
                assertThat(delta.get("approved_difference_ids"))
                        .isEqualTo("P4A-CATALOG-001;P4A-CATALOG-002;P4A-CATALOG-003");
            } else {
                assertThat(delta.get("base_target_module")).isEqualTo("catalog");
                assertThat(delta.get("application_api")).isEqualTo(expectedPublicApis.get(key));
                assertThat(delta.get("parity_evidence"))
                        .contains(
                                "sha256:" + sha256(publicGoldenPath),
                                "sha256:" + sha256(publicQueryPlanPath));
                Set<String> operationDifferences = Set.copyOf(
                        Arrays.asList(delta.get("approved_difference_ids").split(";")));
                assertThat(operationDifferences)
                        .isSubsetOf(expectedPublicDifferences)
                        .contains(
                                "P4A-CATALOG-004",
                                "P4A-CATALOG-005",
                                "P4A-CATALOG-007",
                                "P4A-CATALOG-008",
                                "P4A-CATALOG-009");
                observedPublicDifferences.addAll(operationDifferences);
            }
        }
        assertThat(deltas.keySet()).containsExactlyInAnyOrderElementsOf(expected);
        assertThat(observedPublicDifferences)
                .containsExactlyInAnyOrderElementsOf(expectedPublicDifferences);

        assertThat(effective.path("effective").path("expanded_operation_count").asInt()).isEqualTo(611);
        assertThat(effective.path("effective").path("overridden_operation_count").asInt()).isEqualTo(11);
        assertThat(effective.path("effective").path("migration_status").path("migrated").asInt())
                .isEqualTo(11);
        assertThat(effective.path("effective").path("migration_status").path("pending").asInt())
                .isEqualTo(600);
        assertThat(effective.path("effective").path("production_cutover_operation_count").asInt())
                .isZero();
        JsonNode migratedOperations = effective.path("effective").path("migrated_operations");
        assertThat(migratedOperations).hasSize(11);
        Set<RouteKey> effectiveMigratedKeys = new LinkedHashSet<>();
        for (JsonNode operation : migratedOperations) {
            assertThat(effectiveMigratedKeys.add(new RouteKey(
                            operation.path("route_id").asString(),
                            operation.path("path").asString(),
                            operation.path("method").asString())))
                    .isTrue();
        }
        Set<RouteKey> expectedEffective = new LinkedHashSet<>(expected);
        expectedEffective.add(new RouteKey("02366fc520ac", "/api/login", "POST"));
        expectedEffective.add(new RouteKey(
                "88d7dc05cdbb", "/api/auth/login-methods", "GET"));
        assertThat(effectiveMigratedKeys)
                .containsExactlyInAnyOrderElementsOf(expectedEffective);

        assertThat(openApi.path("openapi").asString()).isEqualTo("3.1.2");
        assertThat(openApi.path("paths")).hasSize(2);
        for (RouteKey key : expectedSubjects) {
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

        JsonNode publicEvidence = publicOpenApi.path("x-ti-evidence");
        assertThat(sha256(publicGoldenPath))
                .isEqualTo(publicEvidence.path("legacyGolden").path("sha256").asString());
        int publicGoldenCaseCount = publicGolden.path("case_count").asInt();
        assertThat(publicGoldenCaseCount).isGreaterThanOrEqualTo(44);
        assertThat(publicEvidence.path("legacyGolden").path("caseCount").asInt())
                .isEqualTo(publicGoldenCaseCount);
        assertThat(sha256(publicRateContractPath))
                .isEqualTo(publicEvidence.path("rateLimitContract").path("sha256").asString());
        assertThat(sha256(publicReadContractPath))
                .isEqualTo(publicEvidence.path("readContract").path("sha256").asString());
        assertThat(sha256(publicQueryPlanPath))
                .isEqualTo(publicEvidence.path("queryPlan").path("sha256").asString());
        assertThat(sha256(approvedDifferencesPath))
                .isEqualTo(publicEvidence.path("approvedDifferences").path("sha256").asString());

        Set<String> expectedPublicOpenApiPaths = Set.of(
                "/api/public/banks",
                "/api/public/banks/boards",
                "/api/public/banks/card/{source_type}/{bank_id}",
                "/api/public/banks/hot",
                "/api/public/banks/list",
                "/api/public/banks/summary",
                "/api/public/banks/{bank_id}");
        assertThat(publicOpenApi.path("openapi").asString()).isEqualTo("3.1.2");
        assertThat(publicOpenApi.path("paths")).hasSize(7);
        Set<String> observedPublicOpenApiPaths = new LinkedHashSet<>();
        Map<String, JsonNode> publicOperationsByRouteId = new LinkedHashMap<>();
        publicOpenApi.path("paths").propertyNames().forEach(path -> {
            observedPublicOpenApiPaths.add(path);
            JsonNode operation = publicOpenApi.path("paths").path(path).path("get");
            String routeId = operation.path("x-ti-route-id").asString();
            assertThat(publicOperationsByRouteId.put(routeId, operation))
                    .as("duplicate public-bank OpenAPI route id %s", routeId)
                    .isNull();
        });
        assertThat(observedPublicOpenApiPaths)
                .containsExactlyInAnyOrderElementsOf(expectedPublicOpenApiPaths);
        assertThat(publicOperationsByRouteId.keySet())
                .containsExactlyInAnyOrderElementsOf(expectedPublicApis.keySet().stream()
                        .map(RouteKey::routeId)
                        .toList());
        for (Map.Entry<RouteKey, String> expectedOperation : expectedPublicApis.entrySet()) {
            RouteKey key = expectedOperation.getKey();
            JsonNode operation = publicOperationsByRouteId.get(key.routeId());
            assertThat(operation.path("x-ti-application-api").asString())
                    .isEqualTo(expectedOperation.getValue())
                    .isEqualTo(deltas.get(key).get("application_api"));
            assertThat(operation.path("x-ti-migration").path("status").asString())
                    .isEqualTo("migrated");
            assertThat(operation.path("x-ti-migration").path("productionCutover").asBoolean())
                    .isFalse();
            assertThat(strings(operation.path("x-ti-approved-differences")))
                    .containsExactlyInAnyOrderElementsOf(Arrays.asList(
                            deltas.get(key).get("approved_difference_ids").split(";")));
        }

        assertThat(publicGolden.path("cases")).hasSize(publicGoldenCaseCount);
        assertThat(publicGolden.path("warm_side_effect_free").asBoolean()).isTrue();
        assertThat(publicGolden.path("covered_routes")).hasSize(7);
        Set<String> publicGoldenRouteIds = new LinkedHashSet<>();
        for (JsonNode route : publicGolden.path("covered_routes")) {
            assertThat(publicGoldenRouteIds.add(route.path("route_id").asString())).isTrue();
        }
        assertThat(publicGoldenRouteIds)
                .containsExactlyInAnyOrderElementsOf(publicOperationsByRouteId.keySet());
        assertThat(publicRateContract.path("endpoints")).hasSize(7);
        assertThat(publicReadContract.path("operations")).hasSize(7);
        Set<String> publicReadRouteIds = new LinkedHashSet<>();
        for (JsonNode operation : publicReadContract.path("operations")) {
            assertThat(publicReadRouteIds.add(operation.path("route_id").asString())).isTrue();
        }
        assertThat(publicReadRouteIds)
                .containsExactlyInAnyOrderElementsOf(publicOperationsByRouteId.keySet());

        JsonNode approvedDifferenceItems = publicReadContract.path("approved_differences")
                .path("items");
        assertThat(approvedDifferenceItems).hasSize(6);
        Set<String> readContractDifferenceIds = new LinkedHashSet<>();
        for (JsonNode difference : approvedDifferenceItems) {
            assertThat(readContractDifferenceIds.add(difference.path("id").asString())).isTrue();
        }
        assertThat(readContractDifferenceIds)
                .containsExactlyInAnyOrderElementsOf(expectedPublicDifferences);
        String approvedDifferences = Files.readString(
                approvedDifferencesPath, StandardCharsets.UTF_8);
        for (String differenceId : expectedPublicDifferences) {
            assertThat(approvedDifferences).contains("## " + differenceId);
        }

        JsonNode exactRuntimeInputs = publicQueryPlan.path("inputs");
        assertThat(exactRuntimeInputs.path("adapter").asString())
                .isEqualTo("server/src/main/java/io/saksk/ti/catalog/infrastructure/persistence/"
                        + "JdbcPublicBankSnapshotQueryAdapter.java");
        assertThat(sha256(resolveInsideTiJava(exactRuntimeInputs.path("adapter").asString())))
                .isEqualTo(exactRuntimeInputs.path("adapter_sha256").asString());
        assertThat(exactRuntimeInputs.path("runtime_sql_exporter").asString())
                .isEqualTo("server/src/test/java/io/saksk/ti/catalog/infrastructure/persistence/"
                        + "PublicBankRuntimeSqlManifestTest.java");
        assertThat(sha256(resolveInsideTiJava(
                        exactRuntimeInputs.path("runtime_sql_exporter").asString())))
                .isEqualTo(exactRuntimeInputs.path("runtime_sql_exporter_sha256").asString());
        assertThat(exactRuntimeInputs.path("schema").asString())
                .isEqualTo("server/src/test/resources/db/phase4a/042-public-bank-snapshot-schema.sql");
        assertThat(sha256(resolveInsideTiJava(exactRuntimeInputs.path("schema").asString())))
                .isEqualTo(exactRuntimeInputs.path("schema_sha256").asString());
        assertThat(sha256(resolveInsideTiJava(
                        "tools/capture_phase4a_public_bank_query_plans.py")))
                .isEqualTo(exactRuntimeInputs.path("capture_tool_sha256").asString());
        assertThat(exactRuntimeInputs.path("runtime_sql_manifest").asString())
                .isEqualTo("server/target/phase4a-public-bank-runtime-sql.json");
        assertThat(exactRuntimeInputs.path("runtime_sql_manifest_sha256").asString())
                .matches("[0-9a-f]{64}");

        assertThat(publicQueryPlan.path("data_set").path("actual_row_counts_and_distribution")
                        .path("metrics").asInt())
                .isGreaterThanOrEqualTo(50_000);
        assertThat(publicQueryPlan.path("data_set").path("actual_row_counts_and_distribution")
                        .path("viewer_states").asInt())
                .isGreaterThanOrEqualTo(100_000);
        JsonNode measuredQueries = publicQueryPlan.path("measurement").path("queries");
        assertThat(measuredQueries).hasSize(7);
        Set<String> expectedQueryIds = Set.of(
                "search-count-keyword",
                "search-page-latest",
                "search-page-latest-keyword",
                "boards-directory",
                "hot-top-five",
                "summary-rolling-seven-days",
                "detail-with-both-relation");
        Set<String> observedQueryIds = new LinkedHashSet<>();
        for (JsonNode measuredQuery : measuredQueries) {
            assertThat(observedQueryIds.add(measuredQuery.path("query_id").asString())).isTrue();
            assertThat(measuredQuery.path("source").asString())
                    .isEqualTo(exactRuntimeInputs.path("adapter").asString());
            assertThat(measuredQuery.path("sql_statement_count").asInt()).isEqualTo(1);
            assertThat(measuredQuery.path("sql").asString()).isNotBlank();
            assertThat(sha256Utf8(measuredQuery.path("sql").asString()))
                    .isEqualTo(measuredQuery.path("sql_sha256").asString());
        }
        assertThat(observedQueryIds).containsExactlyInAnyOrderElementsOf(expectedQueryIds);
        assertThat(publicQueryPlan.path("assertions").path("status").asString())
                .isEqualTo("passed");
        assertThat(publicQueryPlan.path("assertions").path("fixed_sql_budget_no_n_plus_one")
                        .asBoolean())
                .isTrue();
        assertThat(publicQueryPlan.path("assertions").path("data_scale")
                        .path("metrics_at_least_50000").asBoolean())
                .isTrue();
        assertThat(publicQueryPlan.path("assertions").path("data_scale")
                        .path("viewer_rows_at_least_100000").asBoolean())
                .isTrue();

        JsonNode adapterBoundary = publicOpenApi.path("x-ti-http-adapter-boundary");
        assertThat(adapterBoundary.path("applicationApi").asString())
                .isEqualTo("io.saksk.ti.catalog.api.PublicBankCatalogApi");
        assertThat(strings(adapterBoundary.path("applicationCardFieldsExcluded")))
                .containsExactlyInAnyOrder(
                        "source_type", "source_label", "detail_url", "practice_url");
        assertThat(strings(adapterBoundary.path("webAdapterOwnedFields")))
                .containsExactlyInAnyOrder(
                        "source_type", "source_label", "detail_url", "practice_url");
        assertThat(publicReadContract.path("application_api_shape").path("interface").asString())
                .isEqualTo("PublicBankCatalogApi");
        assertThat(publicReadContract.path("application_api_shape").path("methods"))
                .hasSize(5);
        assertThat(publicReadContract.path("application_api_shape").path("http_neutrality")
                        .asString())
                .contains("web adapter owns");

        Class<?> cardView = Class.forName("io.saksk.ti.catalog.api.PublicBankCardView");
        assertThat(cardView.isRecord()).isTrue();
        assertThat(Arrays.stream(cardView.getRecordComponents())
                        .map(component -> component.getName()))
                .doesNotContain("detailUrl", "practiceUrl", "sourceLabel");
        Class<?> sourceType = Class.forName("io.saksk.ti.catalog.api.PublicBankSource");
        assertThat(sourceType.isEnum()).isTrue();
        assertThat(Arrays.stream(sourceType.getDeclaredMethods())
                        .map(method -> method.getName()))
                .doesNotContain("databaseValue", "displayLabel", "fromDatabaseValue");
        JsonNode catalogShape = java.util.stream.StreamSupport.stream(
                        shapeStatusRoot.path("modules").spliterator(), false)
                .filter(module -> module.path("module_id").asString().equals("catalog"))
                .findFirst()
                .orElseThrow();
        assertThat(strings(catalogShape.path("implemented_route_ids")))
                .containsExactlyInAnyOrderElementsOf(expected.stream()
                        .map(RouteKey::routeId)
                        .toList());
        assertThat(catalogShape.path("additional_public_apis")).hasSize(2);
        JsonNode publicBankApi = java.util.stream.StreamSupport.stream(
                        catalogShape.path("additional_public_apis").spliterator(), false)
                .filter(api -> api.path("java_api").asString()
                        .equals("io.saksk.ti.catalog.api.PublicBankCatalogApi"))
                .findFirst()
                .orElseThrow();
        assertThat(publicBankApi.path("direct_http_operation").asBoolean()).isTrue();
    }

    @Test
    void phase4aQuestionMetadataCapabilityIsMachineClosedWithoutMigratingItsHttpRoutes()
            throws Exception {
        Path contractPath = resolveInsideTiJava(
                "docs/refactor/phase4a/question-type-read-contract.json");
        Path goldenPath = resolveInsideTiJava(
                "docs/refactor/phase4a/golden-question-type-reads.json");
        Path queryPlanPath = resolveInsideTiJava(
                "docs/refactor/phase4a/question-type-query-plan-evidence.json");
        Path routeBaselinePath = resolveInsideTiJava(
                "docs/refactor/02-route-parity-matrix.csv");
        Path routeDeltaPath = resolveInsideTiJava(
                "docs/refactor/phase4a/route-parity-delta.csv");
        Path ownershipPath = resolveInsideTiJava(
                "docs/refactor/03-data-ownership.csv");
        Path approvedDifferencesPath = resolveInsideTiJava(
                "docs/refactor/phase4a/approved-differences.md");
        JsonNode contract = JSON.readTree(Files.readString(contractPath, StandardCharsets.UTF_8));
        JsonNode golden = JSON.readTree(Files.readString(goldenPath, StandardCharsets.UTF_8));
        JsonNode queryPlan = JSON.readTree(Files.readString(queryPlanPath, StandardCharsets.UTF_8));
        JsonNode effective = JSON.readTree(Files.readString(
                resolveInsideTiJava("docs/refactor/phase4a/effective-route-parity-status.json"),
                StandardCharsets.UTF_8));

        assertThat(contract.path("contract_id").asString())
                .isEqualTo("ti.phase4a.question-type-read-contract");
        assertThat(contract.path("status").asString())
                .isEqualTo("catalog_internal_capability_implemented_http_operations_deferred");
        assertThat(sha256(goldenPath))
                .isEqualTo(contract.path("evidence").path("golden")
                        .path("file_sha256").asString());
        assertThat(sha256(queryPlanPath))
                .isEqualTo(contract.path("evidence").path("query_plan")
                        .path("file_sha256").asString());
        assertThat(sha256(routeBaselinePath))
                .isEqualTo(contract.path("evidence").path("frozen_route_matrix")
                        .path("sha256").asString());
        assertThat(sha256(ownershipPath))
                .isEqualTo(contract.path("evidence").path("data_ownership")
                        .path("sha256").asString());
        assertThat(sha256(approvedDifferencesPath))
                .isEqualTo(contract.path("evidence").path("approved_differences")
                        .path("sha256").asString());
        assertThat(contract.path("evidence").path("approved_differences")
                        .path("new_difference_ids"))
                .isEmpty();
        assertThat(contract.path("evidence").path("data_ownership")
                        .path("delta_required").asBoolean())
                .isFalse();
        assertThat(resourceOwnersFromCsv(ownershipPath))
                .containsEntry(new ResourceKey("table", "questions"), "catalog");

        Set<RouteKey> deferred = Set.of(
                new RouteKey("e4cbe4d6bcc8", "/admin/api/types", "GET"),
                new RouteKey("3a346cb29186", "/admin/types", "GET"));
        List<String> baselineLines = Files.readAllLines(routeBaselinePath, StandardCharsets.UTF_8);
        List<String> baselineHeader = parseCsvLine(baselineLines.getFirst());
        Map<RouteKey, Map<String, String>> baselineOperations = new LinkedHashMap<>();
        for (String line : baselineLines.subList(1, baselineLines.size())) {
            Map<String, String> row = csvRow(baselineHeader, parseCsvLine(line));
            for (String method : row.get("methods").split(",")) {
                baselineOperations.put(
                        new RouteKey(row.get("route_id"), row.get("path"), method), row);
            }
        }
        for (RouteKey route : deferred) {
            assertThat(baselineOperations.get(route)).isNotNull();
            assertThat(baselineOperations.get(route).get("target_module")).isEqualTo("operations");
            assertThat(baselineOperations.get(route).get("migration_status")).isEqualTo("pending");
        }
        String routeDelta = Files.readString(routeDeltaPath, StandardCharsets.UTF_8);
        assertThat(routeDelta).doesNotContain("e4cbe4d6bcc8", "3a346cb29186");
        Set<String> migratedIds = new LinkedHashSet<>();
        for (JsonNode operation : effective.path("effective").path("migrated_operations")) {
            migratedIds.add(operation.path("route_id").asString());
        }
        assertThat(migratedIds).doesNotContain("e4cbe4d6bcc8", "3a346cb29186");
        assertThat(effective.path("effective").path("migration_status").path("migrated").asInt())
                .isEqualTo(11);
        assertThat(effective.path("effective").path("migration_status").path("pending").asInt())
                .isEqualTo(600);
        assertThat(effective.path("effective").path("production_cutover_operation_count").asInt())
                .isZero();

        JsonNode catalogShape = java.util.stream.StreamSupport.stream(
                        shapeStatusRoot.path("modules").spliterator(), false)
                .filter(module -> module.path("module_id").asString().equals("catalog"))
                .findFirst()
                .orElseThrow();
        assertThat(strings(catalogShape.path("implemented_route_ids")))
                .doesNotContain("e4cbe4d6bcc8", "3a346cb29186");
        JsonNode metadataApi = java.util.stream.StreamSupport.stream(
                        catalogShape.path("additional_public_apis").spliterator(), false)
                .filter(api -> api.path("java_api").asString()
                        .equals("io.saksk.ti.catalog.api.QuestionMetadataApplicationApi"))
                .findFirst()
                .orElseThrow();
        assertThat(metadataApi.path("lifecycle").asString())
                .isEqualTo("catalog_question_metadata_query_boundary");
        assertThat(metadataApi.path("direct_http_operation").asBoolean()).isFalse();
        assertThat(strings(metadataApi.path("deferred_http_route_ids")))
                .containsExactlyInAnyOrder("e4cbe4d6bcc8", "3a346cb29186");
        assertThat(metadataApi.path("deferred_http_owner").asString()).isEqualTo("operations");
        assertThat(metadataApi.path("methods")).hasSize(1);
        assertThat(strings(catalogShape.path("implemented_types")))
                .contains("QuestionTypeCatalogView");
        Class<?> api = Class.forName(
                "io.saksk.ti.catalog.api.QuestionMetadataApplicationApi");
        assertThat(api.isInterface()).isTrue();
        assertThat(api.getDeclaredMethod("questionTypes").getReturnType().getName())
                .isEqualTo("io.saksk.ti.catalog.api.QuestionTypeCatalogView");
        Class<?> view = Class.forName("io.saksk.ti.catalog.api.QuestionTypeCatalogView");
        assertThat(view.isRecord()).isTrue();
        assertThat(Arrays.stream(view.getRecordComponents()).map(component -> component.getName()))
                .containsExactly("questionTypes");

        assertThat(golden.path("contract_id").asString())
                .isEqualTo("ti.phase4a.question-type-read-goldens");
        assertThat(golden.path("legacy_commit").asString())
                .isEqualTo("700006dfdfa063deb4387be572911e782bcea0d9");
        assertThat(golden.path("case_count").asInt()).isEqualTo(22);
        assertThat(golden.path("cases")).hasSize(22);
        assertThat(golden.path("case_payload_sha256").asString())
                .isEqualTo("eecedd275bcc4545f96fc00962fbd3f78d81772e9f89d5fbbaa25d9fc2a35374");
        assertThat(golden.path("route_status").path("migration_status").asString())
                .isEqualTo("pending");
        Map<String, JsonNode> cases = new LinkedHashMap<>();
        for (JsonNode sample : golden.path("cases")) {
            assertThat(cases.put(sample.path("case_id").asString(), sample))
                    .as("duplicate question-type golden case")
                    .isNull();
            assertThat(sample.path("catalog_effects").path("questions_unchanged").asBoolean())
                    .isTrue();
            assertThat(sample.path("catalog_effects").path("question_write_statements").asInt())
                    .isZero();
        }
        assertThat(cases.get("subject-admin-modern").path("response").path("status").asInt())
                .isEqualTo(403);
        assertThat(cases.get("subject-admin-legacy").path("response").path("status").asInt())
                .isEqualTo(200);
        assertThat(orderedStrings(cases.get("whitespace-admin-modern")
                        .path("response").path("body")))
                .isEmpty();
        assertThat(orderedStrings(cases.get("whitespace-admin-legacy")
                        .path("response").path("body")))
                .containsExactly("简答题");
        assertThat(cases.get("fault-html-modern").path("response").path("status").asInt())
                .isEqualTo(500);
        assertThat(cases.get("fault-html-modern").path("response").path("body").asString())
                .isEqualTo("<h1>500 - 服务器错误</h1><p>发生了一个意外错误，请稍后再试。</p>");
        assertThat(cases.get("fault-json-modern").path("response").path("status").asInt())
                .isEqualTo(500);
        assertThat(cases.get("fault-html-legacy").path("response").path("status").asInt())
                .isEqualTo(200);
        assertThat(cases.get("fault-json-legacy").path("response").path("status").asInt())
                .isEqualTo(200);

        assertThat(queryPlan.path("evidence_id").asString())
                .isEqualTo("ti.phase4a.question-type-query-plan");
        assertThat(queryPlan.path("route_migration_status").path("status").asString())
                .isEqualTo("pending");
        assertThat(queryPlan.path("data_set").path("actual").path("questions").asInt())
                .isEqualTo(50_000);
        assertThat(queryPlan.path("data_set").path("actual")
                        .path("raw_distinct_types").asInt())
                .isEqualTo(12);
        assertThat(orderedStrings(queryPlan.path("data_set").path("legacy_normalized_labels")))
                .containsExactly("判断题", "填空题", "多选题", "简答题", "选择题");
        JsonNode questionTypeRuntimeInputs = queryPlan.path("inputs");
        assertThat(questionTypeRuntimeInputs.path("adapter").asString())
                .isEqualTo("server/src/main/java/io/saksk/ti/catalog/infrastructure/persistence/"
                        + "JdbcQuestionTypeQueryAdapter.java");
        assertThat(sha256(resolveInsideTiJava(
                        questionTypeRuntimeInputs.path("adapter").asString())))
                .isEqualTo(questionTypeRuntimeInputs.path("adapter_sha256").asString());
        assertThat(questionTypeRuntimeInputs.path("runtime_sql_exporter").asString())
                .isEqualTo("server/src/test/java/io/saksk/ti/catalog/infrastructure/persistence/"
                        + "QuestionTypeRuntimeSqlManifestTest.java");
        assertThat(sha256(resolveInsideTiJava(
                        questionTypeRuntimeInputs.path("runtime_sql_exporter").asString())))
                .isEqualTo(questionTypeRuntimeInputs.path("runtime_sql_exporter_sha256").asString());
        assertThat(sha256(resolveInsideTiJava(
                        "tools/capture_phase4a_question_type_query_plan.py")))
                .isEqualTo(questionTypeRuntimeInputs.path("capture_tool_sha256").asString());
        assertThat(questionTypeRuntimeInputs.path("runtime_sql_manifest").asString())
                .isEqualTo("server/target/phase4a-question-type-runtime-sql.json");
        assertThat(questionTypeRuntimeInputs.path("runtime_sql_manifest_sha256").asString())
                .matches("[0-9a-f]{64}");
        assertThat(queryPlan.path("measurement").path("query_count").asInt()).isEqualTo(1);
        assertThat(queryPlan.path("measurement").path("sql_statement_count").asInt())
                .isEqualTo(1);
        JsonNode measuredQuery = queryPlan.path("measurement").path("query");
        assertThat(sha256Utf8(measuredQuery.path("sql").asString()))
                .isEqualTo(measuredQuery.path("sql_sha256").asString());
        assertThat(measuredQuery.path("sql_sha256").asString())
                .isEqualTo(contract.path("evidence").path("query_plan")
                        .path("runtime_sql_sha256").asString());
        assertThat(measuredQuery.path("plan_summary")
                        .path("relation_scan_occurrences").path("questions").asInt())
                .isEqualTo(1);
        assertThat(measuredQuery.path("plan_summary").path("maximum_actual_loops").asInt())
                .isEqualTo(1);
        assertThat(measuredQuery.path("plan_summary").path("node_count").asInt())
                .isLessThanOrEqualTo(4);
        assertThat(measuredQuery.path("plan_summary").path("node_type_counts")
                        .has("Nested Loop"))
                .isFalse();
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

    private static String sha256Utf8(String value) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            return HexFormat.of().formatHex(
                    digest.digest(value.getBytes(StandardCharsets.UTF_8)));
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
