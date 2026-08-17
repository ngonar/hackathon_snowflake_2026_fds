-- Log Remediation Action
-- Parameters: :txn_id, :reference_number, :sender_id, :action_type, :risk_tier,
--             :anomaly_score, :fraud_type, :action_details (VARCHAR JSON)

INSERT INTO SNOWFLAKE_LEARNING_DB.FDS.REMEDIATION_ACTIONS (
    TXN_ID, REFERENCE_NUMBER, SENDER_ID, ACTION_TYPE, RISK_TIER,
    ANOMALY_SCORE, FRAUD_TYPE, ACTION_DETAILS, STATUS, EXECUTED_AT
)
VALUES (
    :txn_id,
    :reference_number,
    :sender_id,
    :action_type,
    :risk_tier,
    :anomaly_score,
    :fraud_type,
    PARSE_JSON(:action_details),
    'EXECUTED',
    CURRENT_TIMESTAMP()
);
