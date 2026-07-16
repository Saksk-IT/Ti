package io.saksk.ti.integration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.github.dockerjava.api.model.ExposedPort;
import com.github.dockerjava.api.model.HostConfig;
import io.saksk.ti.support.Phase2ContainerImages;
import java.time.Duration;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Timeout;
import org.testcontainers.containers.Container;
import org.testcontainers.containers.GenericContainer;
import org.testcontainers.containers.wait.strategy.Wait;

/**
 * Destructive, bounded capacity evidence for the isolated Redis profile used by Phase 3.
 *
 * <p>The container has no network and publishes no port. All observations go through Docker exec,
 * so this test cannot discover or mutate a Compose-managed Redis instance.</p>
 */
class Phase3RedisCapacityIT {

    private static final long REDIS_MAX_MEMORY_BYTES = 128L * 1_024 * 1_024;
    private static final long CONTAINER_MEMORY_BYTES = 192L * 1_024 * 1_024;
    private static final int VALUE_BYTES = 4_096;
    private static final int FILL_BATCH_SIZE = 512;
    private static final int MAXIMUM_FILL_ATTEMPTS = 50_000;
    private static final long SENTINEL_TTL_MILLIS = Duration.ofMinutes(10).toMillis();
    private static final String SENTINEL_KEY = "phase3:capacity:rebuildable-sentinel";
    private static final String SENTINEL_VALUE = "phase3-rebuildable-sentinel-v1";
    private static final String POST_OOM_KEY = "phase3:capacity:must-not-exist";
    private static final String VALUE_TEMPLATE = "x".repeat(VALUE_BYTES);

    private static final String FILL_UNTIL_FIRST_OOM = """
            local payload = ARGV[1]
            local first = tonumber(ARGV[2])
            local count = tonumber(ARGV[3])
            if string.len(payload) ~= 4096 then
              return redis.error_reply('capacity payload must be exactly 4096 bytes')
            end
            for offset = 0, count - 1 do
              local index = first + offset
              local suffix = string.format('%08d', index)
              local value = suffix .. string.sub(payload, 9)
              local result = redis.pcall('SET', 'phase3:capacity:fill:' .. suffix, value)
              if type(result) == 'table' and result.err then
                return {offset, index, result.err}
              end
            end
            return {count, 0, 'BATCH_COMPLETE'}
            """;

    @Test
    @Timeout(value = 120, unit = TimeUnit.SECONDS)
    void noevictionRejectsTheFirstOverflowWriteWithoutDestroyingRebuildableState()
            throws Exception {
        try (GenericContainer<?> redis = isolatedRedis()) {
            redis.start();

            assertIsolatedProfile(redis);
            assertThat(redisCli(redis, "SET", SENTINEL_KEY, SENTINEL_VALUE,
                    "PX", Long.toString(SENTINEL_TTL_MILLIS), "NX"))
                    .isEqualTo("OK");
            long ttlBeforeFill = redisCliLong(redis, "PTTL", SENTINEL_KEY);
            assertThat(ttlBeforeFill).isBetween(1L, SENTINEL_TTL_MILLIS);

            FillResult fill = fillUntilFirstOom(redis);
            assertThat(fill.successfulWrites()).isBetween(1, MAXIMUM_FILL_ATTEMPTS - 1);
            assertThat(fill.failingAttempt()).isEqualTo(fill.successfulWrites() + 1);
            assertThat(fill.error()).contains("OOM").doesNotContain("NO_OOM_WITHIN_BOUND");

            String rejectedWrite = redisCliResult(redis, "SET", POST_OOM_KEY, "rejected");
            assertThat(rejectedWrite).contains("OOM");
            assertThat(redisCliLong(redis, "EXISTS", POST_OOM_KEY)).isZero();

            Map<String, String> stats = redisInfo(redis, "stats");
            Map<String, String> memory = redisInfo(redis, "memory");
            Map<String, String> persistence = redisInfo(redis, "persistence");
            long evictedKeys = infoLong(stats, "evicted_keys");
            long usedMemory = infoLong(memory, "used_memory");
            long usedMemoryPeak = infoLong(memory, "used_memory_peak");
            long configuredMaxMemory = infoLong(memory, "maxmemory");

            assertThat(evictedKeys).isZero();
            assertThat(configuredMaxMemory).isEqualTo(REDIS_MAX_MEMORY_BYTES);
            assertThat(usedMemory).isPositive().isLessThan(CONTAINER_MEMORY_BYTES);
            assertThat(usedMemoryPeak).isGreaterThanOrEqualTo(usedMemory)
                    .isLessThan(CONTAINER_MEMORY_BYTES);
            assertThat(persistence.get("aof_enabled")).isEqualTo("1");
            assertThat(persistence.get("aof_last_write_status")).isEqualTo("ok");

            assertThat(redisCli(redis, "GET", SENTINEL_KEY)).isEqualTo(SENTINEL_VALUE);
            long ttlAfterFill = redisCliLong(redis, "PTTL", SENTINEL_KEY);
            assertThat(ttlAfterFill).isBetween(1L, ttlBeforeFill);
            assertThat(redisCliLong(redis, "STRLEN", fillKey(1))).isEqualTo(VALUE_BYTES);
            assertThat(redisCliLong(redis, "STRLEN", fillKey(fill.successfulWrites())))
                    .isEqualTo(VALUE_BYTES);
            assertThat(redisCli(redis, "GETRANGE", fillKey(1), "0", "7"))
                    .isEqualTo("00000001");
            assertThat(redisCli(redis, "GETRANGE", fillKey(fill.successfulWrites()), "0", "7"))
                    .isEqualTo(String.format("%08d", fill.successfulWrites()));
            assertThat(redisCliLong(redis, "DBSIZE"))
                    .isEqualTo((long) fill.successfulWrites() + 1);
            assertThat(redisCli(redis, "PING")).isEqualTo("PONG");

            System.out.printf(
                    "PHASE3_REDIS_CAPACITY_EVIDENCE "
                            + "image=%s maxmemory_bytes=%d used_memory_bytes=%d "
                            + "used_memory_peak_bytes=%d successful_4k_writes=%d "
                            + "evicted_keys=%d sentinel_ttl_ms=%d first_oom=true "
                            + "host_port_bindings=0%n",
                    Phase2ContainerImages.REDIS_7,
                    configuredMaxMemory,
                    usedMemory,
                    usedMemoryPeak,
                    fill.successfulWrites(),
                    evictedKeys,
                    ttlAfterFill);
        }
    }

    private static GenericContainer<?> isolatedRedis() {
        return new GenericContainer<>(Phase2ContainerImages.redis7())
                .withNetworkMode("none")
                .withCommand(
                        "redis-server",
                        "--save", "",
                        "--appendonly", "yes",
                        "--appendfsync", "everysec",
                        "--maxmemory", "128mb",
                        "--maxmemory-policy", "noeviction")
                .withCreateContainerCmdModifier(command -> {
                    HostConfig hostConfig = command.getHostConfig();
                    if (hostConfig == null) {
                        hostConfig = HostConfig.newHostConfig();
                    }
                    command.withHostConfig(hostConfig
                            .withMemory(CONTAINER_MEMORY_BYTES)
                            .withMemorySwap(CONTAINER_MEMORY_BYTES));
                })
                .waitingFor(Wait.forLogMessage(".*Ready to accept connections.*\\n", 1))
                .withStartupTimeout(Duration.ofSeconds(30));
    }

    private static void assertIsolatedProfile(GenericContainer<?> redis) throws Exception {
        assertThat(redis.getDockerImageName()).isEqualTo(Phase2ContainerImages.REDIS_7);
        assertThat(redis.getExposedPorts()).isEmpty();
        assertThat(redis.getContainerInfo().getHostConfig().getNetworkMode()).isEqualTo("none");
        assertThat(redis.getContainerInfo().getHostConfig().getMemory())
                .isEqualTo(CONTAINER_MEMORY_BYTES);
        assertThat(redis.getContainerInfo().getHostConfig().getMemorySwap())
                .isEqualTo(CONTAINER_MEMORY_BYTES);
        assertThat(redis.getContainerInfo().getNetworkSettings().getPorts()
                .getBindings().get(new ExposedPort(6379))).isNullOrEmpty();
        assertThatThrownBy(() -> redis.getMappedPort(6379))
                .isInstanceOf(IllegalArgumentException.class);

        Map<String, String> config = alternatingPairs(redisCli(
                redis,
                "CONFIG", "GET",
                "appendfsync", "appendonly", "maxmemory", "maxmemory-policy"));
        assertThat(config).containsEntry("appendonly", "yes")
                .containsEntry("appendfsync", "everysec")
                .containsEntry("maxmemory", Long.toString(REDIS_MAX_MEMORY_BYTES))
                .containsEntry("maxmemory-policy", "noeviction");
    }

    private static FillResult fillUntilFirstOom(GenericContainer<?> redis) throws Exception {
        int successfulWrites = 0;
        while (successfulWrites < MAXIMUM_FILL_ATTEMPTS) {
            int batchSize = Math.min(
                    FILL_BATCH_SIZE,
                    MAXIMUM_FILL_ATTEMPTS - successfulWrites);
            int firstAttempt = successfulWrites + 1;
            String output = redisCli(
                    redis,
                    "EVAL", FILL_UNTIL_FIRST_OOM, "0",
                    VALUE_TEMPLATE,
                    Integer.toString(firstAttempt),
                    Integer.toString(batchSize));
            List<String> lines = output.lines().toList();
            assertThat(lines).hasSizeGreaterThanOrEqualTo(3);
            int batchWrites = Integer.parseInt(lines.get(0));
            int failingAttempt = Integer.parseInt(lines.get(1));
            String status = String.join("\n", lines.subList(2, lines.size()));
            successfulWrites += batchWrites;
            if (failingAttempt > 0) {
                return new FillResult(successfulWrites, failingAttempt, status);
            }
            assertThat(batchWrites).isEqualTo(batchSize);
            assertThat(status).isEqualTo("BATCH_COMPLETE");
        }
        return new FillResult(
                successfulWrites,
                0,
                "NO_OOM_WITHIN_BOUND");
    }

    private static Map<String, String> redisInfo(GenericContainer<?> redis, String section)
            throws Exception {
        Map<String, String> result = new LinkedHashMap<>();
        redisCli(redis, "INFO", section).lines()
                .filter(line -> !line.isBlank() && line.charAt(0) != '#')
                .forEach(line -> {
                    int separator = line.indexOf(':');
                    assertThat(separator).as("INFO line has a key separator: %s", line)
                            .isPositive();
                    result.put(line.substring(0, separator), line.substring(separator + 1));
                });
        return result;
    }

    private static long infoLong(Map<String, String> info, String key) {
        assertThat(info).containsKey(key);
        return Long.parseLong(info.get(key));
    }

    private static Map<String, String> alternatingPairs(String output) {
        List<String> lines = output.lines().toList();
        assertThat(lines.size() % 2).isZero();
        Map<String, String> result = new LinkedHashMap<>();
        for (int index = 0; index < lines.size(); index += 2) {
            result.put(lines.get(index), lines.get(index + 1));
        }
        return result;
    }

    private static long redisCliLong(GenericContainer<?> redis, String... arguments)
            throws Exception {
        return Long.parseLong(redisCli(redis, arguments));
    }

    private static String redisCli(GenericContainer<?> redis, String... arguments)
            throws Exception {
        Container.ExecResult result = execRedisCli(redis, arguments);
        assertThat(result.getExitCode())
                .as("redis-cli stderr: %s", result.getStderr().strip())
                .isZero();
        assertThat(result.getStderr()).isBlank();
        return result.getStdout().strip();
    }

    private static String redisCliResult(GenericContainer<?> redis, String... arguments)
            throws Exception {
        Container.ExecResult result = execRedisCli(redis, arguments);
        assertThat(result.getExitCode()).isZero();
        return (result.getStdout() + result.getStderr()).strip();
    }

    private static Container.ExecResult execRedisCli(
            GenericContainer<?> redis,
            String... arguments
    ) throws Exception {
        List<String> command = new ArrayList<>(List.of("redis-cli", "--raw"));
        command.addAll(List.of(arguments));
        return redis.execInContainer(command.toArray(String[]::new));
    }

    private static String fillKey(int index) {
        return "phase3:capacity:fill:" + String.format("%08d", index);
    }

    private record FillResult(int successfulWrites, int failingAttempt, String error) {
    }
}
