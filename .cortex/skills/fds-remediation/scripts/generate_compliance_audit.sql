-- Generate Compliance Audit Record
-- Parameters: :txn_id, :reference_number, :sender_id, :anomaly_score, :fraud_type,
--             :decision, :velocity_flags (VARCHAR JSON), :evidence (VARCHAR JSON),
--             :explanation, :risk_tier

INSERT INTO SNOWFLAKE_LEARNING_DB.FDS.REMEDIATION_ACTIONS (
    TXN_ID, REFERENCE_NUMBER, SENDER_ID, ACTION_TYPE, RISK_TIER,
    ANOMALY_SCORE, FRAUD_TYPE, ACTION_DETAILS, STATUS, EXECUTED_AT
)
VALUES (
    :txn_id,
    :reference_number,
    :sender_id,
    'COMPLIANCE_AUDIT',
    :risk_tier,
    :anomaly_score,
    :fraud_type,
    OBJECT_CONSTRUCT(
        'decision', :decision,
        'velocity_flags', PARSE_JSON(:velocity_flags),
        'evidence', PARSE_JSON(:evidence),
        'explanation', :explanation,
        'audit_generated_at', CURRENT_TIMESTAMP()::VARCHAR,
        'requires_manual_review', :anomaly_score >= 65.0
    ),
    'EXECUTED',
    CURRENT_TIMESTAMP()
);
