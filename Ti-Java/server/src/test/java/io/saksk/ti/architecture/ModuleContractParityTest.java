package io.saksk.ti.architecture;

import static org.assertj.core.api.Assertions.assertThat;

import java.io.IOException;
import java.lang.annotation.Annotation;
import java.lang.reflect.Modifier;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
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
                resolveInsideTiJava("docs/refactor/phase2/application-api-shape-status.json"),
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
    void unobservedPublicShapesRemainMachineTrackedAndAbsentFromJava() throws Exception {
        assertThat(shapeStatusRoot.path("migrated_route_count").asInt()).isZero();
        assertThat(shapeStatusRoot.path("implemented_public_operation_count").asInt()).isZero();
        assertThat(shapeStatusRoot.path("event_payload_shape_status").asString())
                .isEqualTo("deferred_to_phase5");

        Map<String, JsonNode> statusByModule = new LinkedHashMap<>();
        for (JsonNode status : shapeStatusRoot.path("modules")) {
            JsonNode previous = statusByModule.put(status.path("module_id").asString(), status);
            assertThat(previous).as("duplicate Phase 2 API status row").isNull();
        }
        assertThat(statusByModule.keySet())
                .containsExactlyInAnyOrderElementsOf(
                        contractModules.keySet().stream().filter(id -> !id.equals("web")).toList());

        for (ContractModule module : contractModules.values()) {
            if (module.id().equals("web")) {
                continue;
            }
            JsonNode acceptedApi = module.node().path("public_application_apis").get(0);
            JsonNode status = statusByModule.get(module.id());
            String className = acceptedApi.path("package").asString()
                    + "."
                    + acceptedApi.path("type").asString();

            assertThat(status.path("java_api").asString()).isEqualTo(className);
            assertThat(status.path("shape_status").asString()).isEqualTo("deferred_shape");
            assertThat(strings(status.path("inputs")))
                    .containsExactlyInAnyOrderElementsOf(strings(acceptedApi.path("inputs")));
            assertThat(strings(status.path("outputs")))
                    .containsExactlyInAnyOrderElementsOf(strings(acceptedApi.path("outputs")));

            Class<?> apiType = Class.forName(className);
            assertThat(apiType.getDeclaredMethods())
                    .as("deferred API %s must not invent methods", className)
                    .isEmpty();
            assertThat(apiType.getDeclaredClasses())
                    .as("deferred API %s must not invent DTOs", className)
                    .isEmpty();
        }

        Path javaRoot = resolveInsideTiJava("server/src/main/java");
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
}
