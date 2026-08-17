-- Freeze Wallet: Record wallet freeze and set expiration
-- Parameters: :user_id, :txn_id, :reason, :fraud_type, :anomaly_score, :duration_hours (default 72)

INSERT INTO SNOWFLAKE_LEARNING_DB.FDS.WALLET_FREEZE_LOG (
    USER_ID, TXN_ID, REASON, FRAUD_TYPE, ANOMALY_SCORE,
    FROZEN_AT, FREEZE_DURATION_HOURS, EXPIRES_AT, STATUS
)
VALUES (
    :user_id,
    :txn_id,
    :reason,
    :fraud_type,
    :anomaly_score,
    CURRENT_TIMESTAMP(),
    :duration_hours,
    DATEADD('hour', :duration_hours, CURRENT_TIMESTAMP()),
    'ACTIVE'
);
