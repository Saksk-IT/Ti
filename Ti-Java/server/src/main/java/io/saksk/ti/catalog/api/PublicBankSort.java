package io.saksk.ti.catalog.api;

/** Closed ORDER BY allowlist. Request text must be mapped to this enum by the web adapter. */
public enum PublicBankSort {
    LATEST,
    HOT,
    ACTIVE,
    FEATURED,
    QUESTIONS
}
