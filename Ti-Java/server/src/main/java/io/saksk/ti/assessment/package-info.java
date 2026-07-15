@org.springframework.modulith.ApplicationModule(
        id = "assessment",
        displayName = "Assessment",
        allowedDependencies = {
            "sharedkernel::api", "identity::api", "catalog::api", "personalbank::api"
        })
package io.saksk.ti.assessment;
