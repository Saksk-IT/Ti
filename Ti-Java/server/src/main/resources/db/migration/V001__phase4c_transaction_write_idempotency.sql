CREATE TABLE learning_idempotency_receipts (
    actor_id BIGINT NOT NULL,
    operation VARCHAR(64) NOT NULL,
    key_hmac BYTEA NOT NULL,
    request_sha256 BYTEA NOT NULL,
    state VARCHAR(16) NOT NULL,
    response_status INTEGER,
    response_body JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT pk_learning_idempotency_receipts
        PRIMARY KEY (actor_id, operation, key_hmac),
    CONSTRAINT ck_learning_idempotency_operation
        CHECK (operation IN (
            'favorite',
            'record-result',
            'study-learn',
            'study-review-record',
            'study-review-master',
            'checkin'
        )),
    CONSTRAINT ck_learning_idempotency_key_hmac
        CHECK (octet_length(key_hmac) = 32),
    CONSTRAINT ck_learning_idempotency_request_sha256
        CHECK (octet_length(request_sha256) = 32),
    CONSTRAINT ck_learning_idempotency_state
        CHECK (state IN ('PENDING', 'COMPLETED')),
    CONSTRAINT ck_learning_idempotency_response
        CHECK (
            (state = 'PENDING'
                AND response_status IS NULL
                AND response_body IS NULL
                AND completed_at IS NULL)
            OR
            (state = 'COMPLETED'
                AND response_status BETWEEN 200 AND 599
                AND response_body IS NOT NULL
                AND completed_at IS NOT NULL)
        ),
    CONSTRAINT ck_learning_idempotency_expiry
        CHECK (expires_at > created_at)
);

CREATE INDEX ix_learning_idempotency_receipts_expiry
    ON learning_idempotency_receipts (expires_at);

CREATE TABLE catalog_question_edit_commands (
    actor_id BIGINT NOT NULL,
    key_hmac BYTEA NOT NULL,
    request_sha256 BYTEA NOT NULL,
    question_id BIGINT NOT NULL,
    state VARCHAR(16) NOT NULL,
    response_status INTEGER,
    response_body JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT pk_catalog_question_edit_commands
        PRIMARY KEY (actor_id, key_hmac),
    CONSTRAINT ck_catalog_question_edit_key_hmac
        CHECK (octet_length(key_hmac) = 32),
    CONSTRAINT ck_catalog_question_edit_request_sha256
        CHECK (octet_length(request_sha256) = 32),
    CONSTRAINT ck_catalog_question_edit_question_id
        CHECK (question_id > 0),
    CONSTRAINT ck_catalog_question_edit_state
        CHECK (state IN ('PENDING', 'COMPLETED')),
    CONSTRAINT ck_catalog_question_edit_response
        CHECK (
            (state = 'PENDING'
                AND response_status IS NULL
                AND response_body IS NULL
                AND completed_at IS NULL)
            OR
            (state = 'COMPLETED'
                AND response_status BETWEEN 200 AND 599
                AND response_body IS NOT NULL
                AND completed_at IS NOT NULL)
        ),
    CONSTRAINT ck_catalog_question_edit_expiry
        CHECK (expires_at > created_at)
);

CREATE INDEX ix_catalog_question_edit_commands_expiry
    ON catalog_question_edit_commands (expires_at);
