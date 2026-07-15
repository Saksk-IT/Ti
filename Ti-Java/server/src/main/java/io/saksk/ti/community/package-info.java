@org.springframework.modulith.ApplicationModule(
        id = "community",
        displayName = "Community",
        allowedDependencies = {"sharedkernel::api", "identity::api", "catalog::api"})
package io.saksk.ti.community;
