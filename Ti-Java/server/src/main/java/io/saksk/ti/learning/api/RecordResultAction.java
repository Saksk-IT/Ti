package io.saksk.ti.learning.api;

/** Legacy-compatible action emitted after recording one public-question answer. */
public enum RecordResultAction {
    ADDED_MISTAKE("added_mistake"),
    REMOVED_MISTAKE("removed_mistake"),
    KEPT_MISTAKE("kept_mistake");

    private final String wireValue;

    RecordResultAction(String wireValue) {
        this.wireValue = wireValue;
    }

    public String wireValue() {
        return wireValue;
    }

    public static RecordResultAction fromWireValue(String value) {
        for (RecordResultAction action : values()) {
            if (action.wireValue.equals(value)) {
                return action;
            }
        }
        throw new IllegalArgumentException("Unknown record-result action");
    }
}
