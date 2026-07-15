@org.springframework.modulith.ApplicationModule(
        id = "learning",
        displayName = "Learning",
        allowedDependencies = {
            "sharedkernel::api",
            "identity::api",
            "catalog::api",
            "personalbank::api",
            "assessment::events"
        })
package io.saksk.ti.learning;
