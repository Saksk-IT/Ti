package io.saksk.ti;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.security.autoconfigure.UserDetailsServiceAutoConfiguration;
import org.springframework.modulith.Modulithic;

@Modulithic(systemName = "Ti")
@SpringBootApplication(exclude = UserDetailsServiceAutoConfiguration.class)
public class TiApplication {

    public static void main(String[] args) {
        SpringApplication.run(TiApplication.class, args);
    }
}
