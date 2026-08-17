-- Log Fraud Analysis Result to FRAUD_ANALYSIS_LOG
-- Parameters: :txn_id, :reference_number, :sender_id, :recipient_id,
--             :source_amount, :is_fraud, :fraud_type, :anomaly_score,
--             :velocity_flags (VARIANT), :evidence (VARIANT),
--             :explanation, :decision

INSERT INTO NGONAROID_FDS.FDS.FRAUD_ANALYSIS_LOG (
    TXN_ID, REFERENCE_NUMBER, SENDER_ID, RECIPIENT_ID,
    SOURCE_AMOUNT, IS_FRAUD, FRAUD_TYPE, ANOMALY_SCORE,
    VELOCITY_FLAGS, EVIDENCE, EXPLANATION, DECISION, ANALYZED_AT
)
VALUES (
    :txn_id,
    :reference_number,
    :sender_id,
    :recipient_id,
    :source_amount,
    :is_fraud,
    :fraud_type,
    :anomaly_score,
    PARSE_JSON(:velocity_flags),
    PARSE_JSON(:evidence),
    :explanation,
    :decision,
    CURRENT_TIMESTAMP()
);
