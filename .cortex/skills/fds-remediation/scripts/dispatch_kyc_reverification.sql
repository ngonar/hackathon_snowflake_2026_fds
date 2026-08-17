-- Dispatch KYC Re-Verification Alert
-- Parameters: :user_id, :txn_id, :priority (URGENT/HIGH/NORMAL), :reason, :fraud_type, :anomaly_score

INSERT INTO SNOWFLAKE_LEARNING_DB.FDS.KYC_REVERIFICATION_QUEUE (
    USER_ID, TXN_ID, PRIORITY, REASON, FRAUD_TYPE, ANOMALY_SCORE,
    QUEUED_AT, STATUS
)
VALUES (
    :user_id,
    :txn_id,
    :priority,
    :reason,
    :fraud_type,
    :anomaly_score,
    CURRENT_TIMESTAMP(),
    'PENDING'
);
