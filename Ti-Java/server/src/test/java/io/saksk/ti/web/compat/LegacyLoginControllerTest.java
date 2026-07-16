package io.saksk.ti.web.compat;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import io.saksk.ti.identity.api.AuthenticationResult;
import io.saksk.ti.identity.api.IdentityApplicationApi;
import io.saksk.ti.identity.api.IdentitySummary;
import io.saksk.ti.web.request.RequestId;
import io.saksk.ti.web.request.RequestIdFilter;
import io.saksk.ti.web.security.ClientAddressResolver;
import io.saksk.ti.web.security.LoginRateLimiter;
import io.saksk.ti.web.security.TargetSessionAttributes;
import io.saksk.ti.web.security.TargetSessionIssuer;
import io.saksk.ti.web.security.TargetSessionProperties;
import io.saksk.ti.web.security.TargetSessionRegistry;
import jakarta.servlet.http.HttpSession;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.List;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.http.converter.json.JacksonJsonHttpMessageConverter;
import org.springframework.mock.web.MockHttpSession;
import org.springframework.security.web.csrf.CsrfTokenRepository;
import org.springframework.session.Session;
import org.springframework.session.SessionRepository;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import tools.jackson.databind.PropertyNamingStrategies;
import tools.jackson.databind.json.JsonMapper;

class LegacyLoginControllerTest {

    private static final Instant AUTHENTICATED_AT = Instant.parse("2026-07-16T00:00:00Z");
    private static final IdentitySummary IDENTITY =
            new IdentitySummary(42, "wang", true, false, true, 7);

    private IdentityApplicationApi identity;
    private LoginRateLimiter rateLimiter;
    private CsrfTokenRepository csrfTokens;
    private MockMvc mockMvc;

    @BeforeEach
    void setUp() {
        identity = mock(IdentityApplicationApi.class);
        rateLimiter = mock(LoginRateLimiter.class);
        csrfTokens = mock(CsrfTokenRepository.class);
        when(rateLimiter.acquire(any(), any()))
                .thenReturn(new LoginRateLimiter.Decision(true, 5, 4, 30));
        TargetSessionRegistry registry = mock(TargetSessionRegistry.class);
        when(registry.registerAndSelectEvictions(anyLong(), anyString()))
                .thenReturn(List.of());
        @SuppressWarnings("unchecked")
        SessionRepository<? extends Session> sessionRepository = mock(SessionRepository.class);
        TargetSessionIssuer targetSessions = new TargetSessionIssuer(
                registry,
                sessionRepository,
                csrfTokens,
                Clock.fixed(AUTHENTICATED_AT, ZoneOffset.UTC));
        LegacyLoginController controller = new LegacyLoginController(
                identity,
                rateLimiter,
                request -> request.getRemoteAddr(),
                targetSessions,
                new TargetSessionProperties("ti_dev_session", "ti_dev_csrf", false));
        mockMvc = MockMvcBuilders.standaloneSetup(controller)
                .setMessageConverters(new JacksonJsonHttpMessageConverter(
                        JsonMapper.builder()
                                .propertyNamingStrategy(PropertyNamingStrategies.SNAKE_CASE)
                                .build()))
                .addFilters(new RequestIdFilter())
                .build();
    }

    @Test
    void successfulLoginMatchesLegacyEnvelopeRotatesSessionAndStoresOnlyAuthoritativeScalars()
            throws Exception {
        when(identity.authenticate(any())).thenReturn(AuthenticationResult.authenticated(IDENTITY, true));
        MockHttpSession previous = new MockHttpSession();
        previous.setAttribute("untrusted", "must-not-survive");

        MvcResult result = mockMvc.perform(post("/api/login")
                        .session(previous)
                        .header(RequestId.HEADER_NAME, "phase3-login-success")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"username":" wang@example.com ","password":"secret",
                                 "remember":"yes","redirect":"/practice"}
                                """))
                .andExpect(status().isOk())
                .andExpect(content().contentType("application/json;charset=UTF-8"))
                .andExpect(header().string(RequestId.HEADER_NAME, "phase3-login-success"))
                .andExpect(header().string("Set-Cookie", org.hamcrest.Matchers.containsString("session=;")))
                .andExpect(jsonPath("$.status").value("success"))
                .andExpect(jsonPath("$.redirect").value("/practice"))
                .andExpect(jsonPath("$.remember").value(true))
                .andExpect(jsonPath("$.needs_password_set").value(false))
                .andExpect(jsonPath("$.message").value(""))
                .andExpect(jsonPath("$.data.redirect").value("/practice"))
                .andExpect(jsonPath("$.data.remember").value(true))
                .andExpect(jsonPath("$.data.needs_password_set").value(false))
                .andExpect(jsonPath("$.request_id").value("phase3-login-success"))
                .andReturn();

        HttpSession issued = result.getRequest().getSession(false);
        assertThat(issued).isNotNull();
        assertThat(issued.getId()).isNotEqualTo(previous.getId());
        assertThat(issued.getMaxInactiveInterval()).isEqualTo(604_800);
        assertThat(issued.getAttribute(TargetSessionAttributes.IDENTITY_ID)).isEqualTo(42L);
        assertThat(issued.getAttribute(TargetSessionAttributes.SESSION_VERSION)).isEqualTo(7);
        assertThat(issued.getAttribute(TargetSessionAttributes.AUTHENTICATED_AT))
                .isEqualTo(AUTHENTICATED_AT.getEpochSecond());
        assertThat(issued.getAttribute(TargetSessionAttributes.REMEMBER)).isEqualTo(true);
        assertThat(issued.getAttribute("untrusted")).isNull();
        verify(csrfTokens).saveToken(
                org.mockito.ArgumentMatchers.isNull(),
                org.mockito.ArgumentMatchers.any(),
                org.mockito.ArgumentMatchers.any());
    }

    @Test
    void invalidCredentialsAndLockedAccountMatchLegacyStatusAndErrorEnvelope() throws Exception {
        when(identity.authenticate(any()))
                .thenReturn(AuthenticationResult.invalidCredentials())
                .thenReturn(AuthenticationResult.accountLocked());

        performLogin("invalid-credentials")
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.status").value("error"))
                .andExpect(jsonPath("$.message").value("账号或密码错误"))
                .andExpect(jsonPath("$.status_code").value(400))
                .andExpect(jsonPath("$.request_id").value("invalid-credentials"));

        performLogin("locked-account")
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.message").value("账户已被锁定，请联系管理员"))
                .andExpect(jsonPath("$.status_code").value(403));
    }

    @Test
    void inputErrorsAndUnsafeRedirectsAreFailClosed() throws Exception {
        when(identity.authenticate(any())).thenReturn(AuthenticationResult.authenticated(IDENTITY, false));

        mockMvc.perform(post("/api/login")
                        .header(RequestId.HEADER_NAME, "malformed-json")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.message").value("请求数据格式不正确"))
                .andExpect(jsonPath("$.status_code").value(400));

        mockMvc.perform(post("/api/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"username\":\"   \",\"password\":\"x\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.message").value("账号和密码不能为空"));

        mockMvc.perform(post("/api/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"username\":\"legacy-name\",\"password\":\"x\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.message").value("暂不支持用户名登录，请使用邮箱或手机号"));

        mockMvc.perform(post("/api/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"username":"wang@example.com","password":"x",
                                 "redirect":"//evil.example/steal"}
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.redirect").value("/"))
                .andExpect(jsonPath("$.data.redirect").value("/"));
    }

    @Test
    void authenticationInfrastructureFailureUsesStableUnavailableEnvelope() throws Exception {
        when(identity.authenticate(any())).thenThrow(new IllegalStateException("database-secret"));

        performLogin("dependency-failure")
                .andExpect(status().isServiceUnavailable())
                .andExpect(content().string(org.hamcrest.Matchers.not(
                        org.hamcrest.Matchers.containsString("database-secret"))))
                .andExpect(jsonPath("$.message").value("登录服务暂时不可用，请稍后重试"))
                .andExpect(jsonPath("$.status_code").value(503));
    }

    @Test
    void excessiveLoginAttemptsReturnStableEnvelopeAndRetryMetadata() throws Exception {
        when(rateLimiter.acquire(any(), any()))
                .thenReturn(new LoginRateLimiter.Decision(false, 5, 0, 17));

        performLogin("rate-limited")
                .andExpect(status().isTooManyRequests())
                .andExpect(header().string("Retry-After", "17"))
                .andExpect(header().string("X-RateLimit-Limit", "5"))
                .andExpect(header().string("X-RateLimit-Remaining", "0"))
                .andExpect(jsonPath("$.status").value("error"))
                .andExpect(jsonPath("$.message").value("请求过于频繁，请稍后重试"))
                .andExpect(jsonPath("$.status_code").value(429))
                .andExpect(jsonPath("$.request_id").value("rate-limited"));
    }

    private org.springframework.test.web.servlet.ResultActions performLogin(String requestId)
            throws Exception {
        return mockMvc.perform(post("/api/login")
                .header(RequestId.HEADER_NAME, requestId)
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"username\":\"wang@example.com\",\"password\":\"secret\"}"));
    }
}
