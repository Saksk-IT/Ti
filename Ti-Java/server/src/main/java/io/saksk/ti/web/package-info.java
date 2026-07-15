@org.springframework.modulith.ApplicationModule(
        id = "web",
        displayName = "HTTP and Web Adapters",
        allowedDependencies = {
            "sharedkernel::api",
            "identity::api",
            "catalog::api",
            "personalbank::api",
            "assessment::api",
            "learning::api",
            "community::api",
            "campus::api",
            "coding::api",
            "intelligence::api",
            "messaging::api",
            "operations::api"
        })
package io.saksk.ti.web;
