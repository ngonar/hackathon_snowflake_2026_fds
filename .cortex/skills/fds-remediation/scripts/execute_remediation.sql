-- Execute Remediation: Master orchestration stored procedure
-- Chains all remediation actions based on risk tier
-- Parameters: :txn_id, :reference_number, :sender_id, :anomaly_score, :fraud_type,
--             :decision, :velocity_flags, :evidence, :explanation

DECLARE
    risk_tier VARCHAR;
    duration_hours INTEGER;
    priority VARCHAR;
    freeze_reason VARCHAR;
BEGIN
    -- Determine risk tier
    IF (:anomaly_score >= 85.0) THEN
        risk_tier := 'CRITICAL';
    ELSEIF (:anomaly_score >= 65.0) THEN
        risk_tier := 'HIGH';
    ELSEIF (:anomaly_score >= 50.0) THEN
        risk_tier := 'MEDIUM';
    ELSE
        risk_tier := 'LOW';
    END IF;

    -- CRITICAL: Full remediation chain
    IF (risk_tier = 'CRITICAL') THEN
        -- 1. Freeze wallet (72h)
        duration_hours := 72;
        freeze_reason := 'Auto-frozen: ' || :fraud_type || ' detected (score: ' || :anomaly_score::VARCHAR || ')';
        INSERT INTO SNOWFLAKE_LEARNING_DB.FDS.WALLET_FREEZE_LOG
            (USER_ID, TXN_ID, REASON, FRAUD_TYPE, ANOMALY_SCORE, FROZEN_AT, FREEZE_DURATION_HOURS, EXPIRES_AT, STATUS)
        VALUES
            (:sender_id, :txn_id, :freeze_reason, :fraud_type, :anomaly_score,
             CURRENT_TIMESTAMP(), :duration_hours, DATEADD('hour', :duration_hours, CURRENT_TIMESTAMP()), 'ACTIVE');

        -- 2. Log freeze action
        INSERT INTO SNOWFLAKE_LEARNING_DB.FDS.REMEDIATION_ACTIONS
            (TXN_ID, REFERENCE_NUMBER, SENDER_ID, ACTION_TYPE, RISK_TIER, ANOMALY_SCORE, FRAUD_TYPE, ACTION_DETAILS, STATUS, EXECUTED_AT)
        VALUES
            (:txn_id, :reference_number, :sender_id, 'WALLET_FROZEN', :risk_tier, :anomaly_score, :fraud_type,
             OBJECT_CONSTRUCT('freeze_duration_hours', :duration_hours, 'reason', :freeze_reason), 'EXECUTED', CURRENT_TIMESTAMP());

        -- 3. Dispatch KYC re-verification (URGENT)
        priority := 'URGENT';
        INSERT INTO SNOWFLAKE_LEARNING_DB.FDS.KYC_REVERIFICATION_QUEUE
            (USER_ID, TXN_ID, PRIORITY, REASON, FRAUD_TYPE, ANOMALY_SCORE, QUEUED_AT, STATUS)
        VALUES
            (:sender_id, :txn_id, :priority,
             'Critical fraud risk detected. Immediate KYC re-verification required.',
             :fraud_type, :anomaly_score, CURRENT_TIMESTAMP(), 'PENDING');

        -- 4. Log KYC dispatch action
        INSERT INTO SNOWFLAKE_LEARNING_DB.FDS.REMEDIATION_ACTIONS
            (TXN_ID, REFERENCE_NUMBER, SENDER_ID, ACTION_TYPE, RISK_TIER, ANOMALY_SCORE, FRAUD_TYPE, ACTION_DETAILS, STATUS, EXECUTED_AT)
        VALUES
            (:txn_id, :reference_number, :sender_id, 'KYC_REVERIFICATION_DISPATCHED', :risk_tier, :anomaly_score, :fraud_type,
             OBJECT_CONSTRUCT('priority', :priority), 'EXECUTED', CURRENT_TIMESTAMP());

    -- HIGH: Block + Compliance
    ELSEIF (risk_tier = 'HIGH') THEN
        INSERT INTO SNOWFLAKE_LEARNING_DB.FDS.REMEDIATION_ACTIONS
            (TXN_ID, REFERENCE_NUMBER, SENDER_ID, ACTION_TYPE, RISK_TIER, ANOMALY_SCORE, FRAUD_TYPE, ACTION_DETAILS, STATUS, EXECUTED_AT)
        VALUES
            (:txn_id, :reference_number, :sender_id, 'TRANSACTION_BLOCKED', :risk_tier, :anomaly_score, :fraud_type,
             OBJECT_CONSTRUCT('requires_manual_review', TRUE), 'EXECUTED', CURRENT_TIMESTAMP());

    -- MEDIUM: Flag suspicious
    ELSEIF (risk_tier = 'MEDIUM') THEN
        INSERT INTO SNOWFLAKE_LEARNING_DB.FDS.REMEDIATION_ACTIONS
            (TXN_ID, REFERENCE_NUMBER, SENDER_ID, ACTION_TYPE, RISK_TIER, ANOMALY_SCORE, FRAUD_TYPE, ACTION_DETAILS, STATUS, EXECUTED_AT)
        VALUES
            (:txn_id, :reference_number, :sender_id, 'FLAGGED_SUSPICIOUS', :risk_tier, :anomaly_score, :fraud_type,
             OBJECT_CONSTRUCT('monitoring_active', TRUE), 'EXECUTED', CURRENT_TIMESTAMP());

    -- LOW: Auto-approve
    ELSE
        INSERT INTO SNOWFLAKE_LEARNING_DB.FDS.REMEDIATION_ACTIONS
            (TXN_ID, REFERENCE_NUMBER, SENDER_ID, ACTION_TYPE, RISK_TIER, ANOMALY_SCORE, FRAUD_TYPE, ACTION_DETAILS, STATUS, EXECUTED_AT)
        VALUES
            (:txn_id, :reference_number, :sender_id, 'AUTO_APPROVED', :risk_tier, :anomaly_score, :fraud_type,
             OBJECT_CONSTRUCT('auto_funded', TRUE), 'EXECUTED', CURRENT_TIMESTAMP());
    END IF;

    -- Always generate compliance audit for non-LOW tiers
    IF (risk_tier != 'LOW') THEN
        INSERT INTO SNOWFLAKE_LEARNING_DB.FDS.REMEDIATION_ACTIONS
            (TXN_ID, REFERENCE_NUMBER, SENDER_ID, ACTION_TYPE, RISK_TIER, ANOMALY_SCORE, FRAUD_TYPE, ACTION_DETAILS, STATUS, EXECUTED_AT)
        VALUES
            (:txn_id, :reference_number, :sender_id, 'COMPLIANCE_AUDIT', :risk_tier, :anomaly_score, :fraud_type,
             OBJECT_CONSTRUCT(
                'decision', :decision,
                'velocity_flags', PARSE_JSON(:velocity_flags),
                'evidence', PARSE_JSON(:evidence),
                'explanation', :explanation
             ), 'EXECUTED', CURRENT_TIMESTAMP());
    END IF;

    RETURN risk_tier;
END;
