package io.saksk.ti.architecture;

import com.tngtech.archunit.core.domain.Dependency;
import com.tngtech.archunit.core.domain.JavaClass;
import com.tngtech.archunit.core.importer.ClassFileImporter;
import com.tngtech.archunit.core.importer.ImportOption;
import com.tngtech.archunit.lang.ArchCondition;
import com.tngtech.archunit.lang.ConditionEvents;
import com.tngtech.archunit.lang.SimpleConditionEvent;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

class ModuleBoundaryArchUnitTest {

    private static final String ROOT = "io.saksk.ti.";
    private static final String[] BUSINESS_MODULES = {
        "identity", "catalog", "personalbank", "assessment", "learning", "community",
        "campus", "coding", "intelligence", "messaging", "operations"
    };

    private static com.tngtech.archunit.core.domain.JavaClasses productionClasses;

    @BeforeAll
    static void importProductionClassesOnly() {
        productionClasses = new ClassFileImporter()
                .withImportOption(ImportOption.Predefined.DO_NOT_INCLUDE_TESTS)
                .importPackages("io.saksk.ti");
    }

    @Test
    void modulesCannotReachAnotherModulesDomainPersistenceOrRepository() {
        com.tngtech.archunit.lang.syntax.ArchRuleDefinition.classes()
                .that()
                .resideInAnyPackage(modulePackages())
                .should(notDependOnAnotherModuleInternal())
                .check(productionClasses);
    }

    @Test
    void webCannotReachRepositoriesOrPersistenceAdapters() {
        com.tngtech.archunit.lang.syntax.ArchRuleDefinition.classes()
                .that()
                .resideInAnyPackage("io.saksk.ti.web..")
                .should(notDependOnRepositoryOrPersistence())
                .check(productionClasses);
    }

    @Test
    void sharedKernelCannotBecomeAFrameworkOrBusinessJunkDrawer() {
        com.tngtech.archunit.lang.syntax.ArchRuleDefinition.classes()
                .that()
                .resideInAnyPackage("io.saksk.ti.sharedkernel..")
                .should(remainStableAndFrameworkFree())
                .check(productionClasses);
    }

    @Test
    void blockingMvcApplicationCannotDependOnReactiveStacks() {
        com.tngtech.archunit.lang.syntax.ArchRuleDefinition.classes()
                .should(notDependOnReactiveTypes())
                .check(productionClasses);
    }

    private static String[] modulePackages() {
        var packages = new String[BUSINESS_MODULES.length + 1];
        for (int index = 0; index < BUSINESS_MODULES.length; index++) {
            packages[index] = ROOT + BUSINESS_MODULES[index] + "..";
        }
        packages[BUSINESS_MODULES.length] = ROOT + "web..";
        return packages;
    }

    private static ArchCondition<JavaClass> notDependOnAnotherModuleInternal() {
        return new ArchCondition<>("not depend on another module's domain, infrastructure, entity or repository") {
            @Override
            public void check(JavaClass source, ConditionEvents events) {
                String sourceModule = moduleOf(source.getPackageName());
                for (Dependency dependency : source.getDirectDependenciesFromSelf()) {
                    JavaClass target = dependency.getTargetClass();
                    String targetModule = moduleOf(target.getPackageName());
                    if (sourceModule != null
                            && targetModule != null
                            && !sourceModule.equals(targetModule)
                            && isInternalPersistenceOrDomain(target)) {
                        events.add(SimpleConditionEvent.violated(source, dependency.getDescription()));
                    }
                }
            }
        };
    }

    private static ArchCondition<JavaClass> notDependOnRepositoryOrPersistence() {
        return new ArchCondition<>("not depend on a repository, entity or persistence adapter") {
            @Override
            public void check(JavaClass source, ConditionEvents events) {
                for (Dependency dependency : source.getDirectDependenciesFromSelf()) {
                    JavaClass target = dependency.getTargetClass();
                    if (isInternalPersistenceOrDomain(target)
                            && (target.getPackageName().contains(".persistence")
                                    || target.getPackageName().contains(".repository")
                                    || target.getSimpleName().endsWith("Repository")
                                    || target.getSimpleName().endsWith("Entity"))) {
                        events.add(SimpleConditionEvent.violated(source, dependency.getDescription()));
                    }
                }
            }
        };
    }

    private static ArchCondition<JavaClass> remainStableAndFrameworkFree() {
        return new ArchCondition<>("contain only stable scalar primitives and Modulith declarations") {
            @Override
            public void check(JavaClass source, ConditionEvents events) {
                if (source.getSimpleName().endsWith("Repository") || source.getSimpleName().endsWith("Service")) {
                    events.add(SimpleConditionEvent.violated(source, source.getName() + " is a forbidden shared service"));
                }
                source.getAnnotations().forEach(annotation -> {
                    String annotationType = annotation.getRawType().getName();
                    if (annotationType.equals("jakarta.persistence.Entity")
                            || annotationType.equals("org.springframework.stereotype.Component")
                            || annotationType.equals("org.springframework.stereotype.Service")
                            || annotationType.equals("org.springframework.stereotype.Repository")) {
                        events.add(SimpleConditionEvent.violated(
                                source, source.getName() + " uses " + annotationType));
                    }
                });
                for (Dependency dependency : source.getDirectDependenciesFromSelf()) {
                    String target = dependency.getTargetClass().getName();
                    boolean businessDependency = moduleOf(dependency.getTargetClass().getPackageName()) != null
                            && !target.startsWith("io.saksk.ti.sharedkernel.");
                    boolean frameworkDependency = (target.startsWith("org.springframework.")
                                    && !target.startsWith("org.springframework.modulith."))
                            || target.startsWith("jakarta.persistence.");
                    if (businessDependency || frameworkDependency) {
                        events.add(SimpleConditionEvent.violated(source, dependency.getDescription()));
                    }
                }
            }
        };
    }

    private static ArchCondition<JavaClass> notDependOnReactiveTypes() {
        return new ArchCondition<>("not depend on WebFlux, Reactor or R2DBC") {
            @Override
            public void check(JavaClass source, ConditionEvents events) {
                for (Dependency dependency : source.getDirectDependenciesFromSelf()) {
                    String target = dependency.getTargetClass().getName();
                    if (target.startsWith("reactor.")
                            || target.startsWith("org.springframework.web.reactive.")
                            || target.startsWith("io.r2dbc.")) {
                        events.add(SimpleConditionEvent.violated(source, dependency.getDescription()));
                    }
                }
            }
        };
    }

    private static boolean isInternalPersistenceOrDomain(JavaClass target) {
        String packageName = target.getPackageName();
        return packageName.contains(".domain")
                || packageName.contains(".infrastructure")
                || packageName.contains(".persistence")
                || packageName.contains(".repository")
                || packageName.contains(".entity")
                || (packageName.startsWith(ROOT)
                        && (target.getSimpleName().endsWith("Entity")
                                || target.getSimpleName().endsWith("Repository")));
    }

    private static String moduleOf(String packageName) {
        if (!packageName.startsWith(ROOT)) {
            return null;
        }
        String suffix = packageName.substring(ROOT.length());
        int separator = suffix.indexOf('.');
        String candidate = separator < 0 ? suffix : suffix.substring(0, separator);
        if (candidate.equals("web") || candidate.equals("sharedkernel")) {
            return candidate;
        }
        for (String module : BUSINESS_MODULES) {
            if (module.equals(candidate)) {
                return module;
            }
        }
        return null;
    }
}
