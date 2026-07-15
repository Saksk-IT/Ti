@org.springframework.modulith.ApplicationModule(
        id = "messaging",
        displayName = "Messaging and Notifications",
        allowedDependencies = {
            "sharedkernel::api",
            "identity::api",
            "assessment::events",
            "learning::events",
            "community::events",
            "campus::events",
            "coding::events",
            "intelligence::events"
        })
package io.saksk.ti.messaging;
