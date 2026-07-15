package io.saksk.ti.web.error;

import static org.hamcrest.Matchers.not;
import static org.hamcrest.Matchers.containsString;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import io.saksk.ti.web.request.RequestId;
import io.saksk.ti.web.request.RequestIdFilter;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.http.converter.json.JacksonJsonHttpMessageConverter;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
import tools.jackson.databind.PropertyNamingStrategies;
import tools.jackson.databind.json.JsonMapper;

class GlobalExceptionHandlerTest {

    private MockMvc mockMvc;

    @BeforeEach
    void setUp() {
        mockMvc = MockMvcBuilders
                .standaloneSetup(new FailingController())
                .setControllerAdvice(new GlobalExceptionHandler())
                .setMessageConverters(new JacksonJsonHttpMessageConverter(
                        JsonMapper.builder()
                                .propertyNamingStrategy(PropertyNamingStrategies.SNAKE_CASE)
                                .build()))
                .addFilters(new RequestIdFilter())
                .build();
    }

    @Test
    void unexpectedFailureUsesSafeEnvelopeAndNeverLeaksProblemDetailOrExceptionMessage() throws Exception {
        mockMvc.perform(get("/failure").header(RequestId.HEADER_NAME, "failure-test-01"))
                .andExpect(status().isInternalServerError())
                .andExpect(content().contentTypeCompatibleWith(MediaType.APPLICATION_JSON))
                .andExpect(header().string(RequestId.HEADER_NAME, "failure-test-01"))
                .andExpect(jsonPath("$.success").value(false))
                .andExpect(jsonPath("$.error.code").value("INTERNAL_ERROR"))
                .andExpect(jsonPath("$.error.message").value("服务暂时无法处理请求"))
                .andExpect(jsonPath("$.error.details").isArray())
                .andExpect(jsonPath("$.meta.request_id").value("failure-test-01"))
                .andExpect(content().string(not(containsString("database-password-secret"))))
                .andExpect(content().string(not(containsString("ProblemDetail"))))
                .andExpect(content().string(not(containsString("stackTrace"))))
                .andExpect(content().string(not(containsString("instance"))));
    }

    @RestController
    static class FailingController {

        @GetMapping("/failure")
        Object fail() {
            throw new IllegalStateException("database-password-secret");
        }
    }
}
