@org.springframework.modulith.ApplicationModule(
        id = "personalbank",
        displayName = "Personal Question Bank",
        allowedDependencies = {"sharedkernel::api", "identity::api", "catalog::api"})
package io.saksk.ti.personalbank;
