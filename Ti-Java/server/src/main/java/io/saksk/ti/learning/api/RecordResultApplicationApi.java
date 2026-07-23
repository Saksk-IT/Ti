package io.saksk.ti.learning.api;

/** Public application boundary for the two legacy record-result aliases. */
public interface RecordResultApplicationApi {

    RecordResultResult recordResult(RecordResultCommand command);
}
