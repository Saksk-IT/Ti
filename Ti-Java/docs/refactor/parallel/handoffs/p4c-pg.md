# Phase 4C PostgreSQL termination fingerprint handoff

## Identity and immutable integration point

- lane: `p4c-pg`
- Worker code: `p4c-pg`
- branch: `codex/parallel-p4c-pg`
- `BASE_SHA`: `765e4470f1ddb60f0ce6f23227d6303961f47fcf`
- implementation commit SHA: `0f584743dbdc187b6bc6fc67899a2d6718cb13c8`
- recommended integration SHA: `0f584743dbdc187b6bc6fc67899a2d6718cb13c8`
- integration rule: review and integrate the fixed implementation object above; do not substitute
  the branch tip or this handoff-only commit for the implementation SHA.

## Exact ownership target

The user explicitly authorized this single PostgreSQL termination-evidence slice, limited to these
three implementation paths plus this lane's handoff exception:

- `Ti-Java/server/src/test/java/io/saksk/ti/integration/Phase4cUserCountsTerminationFingerprintIT.java`
- `Ti-Java/server/src/test/java/io/saksk/ti/support/Phase4cUserCountsTerminationFingerprintSupport.java`
- `Ti-Java/server/src/test/resources/db/phase4c/073-personal-bank-user-counts-termination-fingerprint-seed.sql`
- handoff exception: `Ti-Java/docs/refactor/parallel/handoffs/p4c-pg.md`

No production source or shared test class was changed. In particular, the lane did not edit or
reuse as its probe implementation `LegacyPersonalBankUserCountsGoldenTargetExecutionIT`,
`LegacyPersonalBankUserCountsNetworkIT`, or `Phase4cUserCountsFaultInjectingDataSource`.

## Fixed implementation diff

Command:

```text
git diff --name-status 765e4470f1ddb60f0ce6f23227d6303961f47fcf...0f584743dbdc187b6bc6fc67899a2d6718cb13c8
```

Result:

```text
A  Ti-Java/server/src/test/java/io/saksk/ti/integration/Phase4cUserCountsTerminationFingerprintIT.java
A  Ti-Java/server/src/test/java/io/saksk/ti/support/Phase4cUserCountsTerminationFingerprintSupport.java
A  Ti-Java/server/src/test/resources/db/phase4c/073-personal-bank-user-counts-termination-fingerprint-seed.sql
```

## Implemented evidence

The new test runs the real Spring Boot security/controller/application/JDBC chain through MockMvc,
real Redis and pinned Testcontainers PostgreSQL images. It does not use Mockito or a type-binding
shortcut. The test performs six complete HTTP requests per PostgreSQL version (twelve total):

- anonymous API `401` and Web `302`, both with zero JDBC;
- signature-valid but revoked-version Bearer `401`, with exactly the authoritative `users` SQL and
  no business JDBC;
- valid identity against a private bank `403`, with actual `BANK_ACCESS` and `SHARE_ACCESS` SQL;
- injected business `500`, observing PostgreSQL SQLSTATE `42703`, then same-transaction `25P02`;
- an immediate successful `200` retry after rollback.

The dedicated support records `{PG version, PostgreSQL backend PID}` for physical connection
identity, normalized application SQL, JDBC read-only, auto-commit, and server-side
`SHOW transaction_read_only`. Each version has a one-connection Hikari pool with
`autosave=never` and `readOnlyMode=transaction`, allowing a deterministic assertion that the
exceptional transaction rolls back and the same backend PID subsequently executes successful
authority and read-only business SQL.

For PostgreSQL 16.14 and 18.4 independently, the test also compares before/after fingerprints for
all nine key tables:

1. `users`
2. `user_progress`
3. `user_question_banks`
4. `bank_shares`
5. `bank_share_records`
6. `user_bank_questions`
7. `user_bank_favorites`
8. `user_bank_mistakes`
9. `user_question_tag_items`

It asserts total write DML `0`, `users.last_active` DML `0`, schema mutations `0`, direct
`users.last_active IS NOT NULL` rows `0`, and identical before/after fingerprints.

## Verification and heavy lock record

- The Worker first observed `heavy-verify.lock` owned by `p4c-redis` and waited without deleting,
  stealing or bypassing it.
- Acquired atomically with `mkdir` at `2026-07-18T13:14:06Z`.
- Owner metadata recorded lane, branch, worktree, UTC start and the exact planned command.
- Held continuously for the Maven wrapper, Docker socket use, Testcontainers, both PostgreSQL
  containers, Redis, packaging check and cleanup.
- Released by the same Worker after the command and container cleanup; absence was reconfirmed at
  `2026-07-18T13:19:22Z`.

Executed command:

```text
./infra/phase2/verify-in-maven-container.sh \
  -Dit.test=Phase4cUserCountsTerminationFingerprintIT verify
```

Result:

- `BUILD SUCCESS`, Maven total time `03:01 min`;
- compile: `275` main sources and `237` test sources;
- default Surefire lifecycle: `709` tests, `0` failures, `0` errors, `0` skipped;
- targeted Failsafe IT: `2` tests, `0` failures, `0` errors, `0` skipped;
- pinned PostgreSQL server versions asserted as exactly `16.14` and `18.4`;
- the two intentional safe `500` controller log entries correspond to the injected PG16 and PG18
  business faults and are asserted not to leak the missing column or SQLSTATEs.

## Risks, dependencies and intentionally unproven items

- No shared production change was required; there is no dependency on another Worker lane.
- The test deliberately fixes one physical connection per PostgreSQL version to make post-rollback
  reuse an invariant rather than a pool scheduling coincidence.
- This lane proves the requested MockMvc target-stack PostgreSQL termination evidence. It does not
  claim real Tomcat/network header parity, Redis outage/recovery, production cutover, or any route
  status change; those remain separate gates.
- Concurrent lanes may add other Phase 4C test resources. INT should retain this exact explicitly
  copied resource path when integrating the fixed implementation SHA.

## Central authority follow-up for INT

After independently reviewing and integrating the fixed implementation SHA, INT may append a new
successor/delta that records `pg16_pg18_termination_fingerprints_complete=true` and advances the
next gate. INT must not edit the historical typed-normalization contract, WORM, acceptance,
parity, route matrix/delta, or other immutable predecessor evidence in place.

## Declarations

- No central authority file was modified.
- No historical contract, WORM, acceptance, parity, successor, route matrix/delta, data ownership,
  global OpenAPI, `server/pom.xml`, Compose, global configuration, `SecurityConfiguration`, or
  shared authentication filter was modified.
- Root user assets remained byte/state untouched and were never staged: `AGENTS.md` stayed
  modified, `CLAUDE.md` stayed deleted, and `.playwright-cli/`, `miniprogram-1/.gitignore`, and
  `output/` stayed untracked, exactly as observed at the base.
- The Worker did not switch to, commit on, or push `main`.
