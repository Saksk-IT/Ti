@org.springframework.modulith.ApplicationModule(
        id = "intelligence",
        displayName = "Intelligence",
        allowedDependencies = {
            "sharedkernel::api", "identity::api", "catalog::api", "personalbank::api", "coding::api"
        })
package io.saksk.ti.intelligence;
