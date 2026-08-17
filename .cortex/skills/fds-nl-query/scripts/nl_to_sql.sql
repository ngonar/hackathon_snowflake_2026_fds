-- Natural Language to SQL Translation via Cortex AI_COMPLETE
-- Parameters: :user_question (VARCHAR) - The natural language question from the investigator

SELECT SNOWFLAKE.CORTEX.AI_COMPLETE(
    'llama4-maverick',
    CONCAT(
        'You are a SQL query generator for a fraud investigation system.\n',
        'Given a natural language question from a compliance officer, generate a single Snowflake SQL SELECT query.\n\n',
        'RULES:\n',
        '1. ONLY generate SELECT statements. Never generate INSERT, UPDATE, DELETE, DROP, CREATE, ALTER.\n',
        '2. Always use fully qualified table names: SNOWFLAKE_LEARNING_DB.FDS.<TABLE>\n',
        '3. Use JOINs to include human-readable names where possible.\n',
        '4. Limit results to 100 rows maximum.\n',
        '5. Order by most relevant column (usually timestamp DESC or anomaly_score DESC).\n',
        '6. For time ranges like "last 24 hours", use DATEADD with CURRENT_TIMESTAMP().\n',
        '7. Return ONLY the SQL query with no explanation or markdown.\n\n',
        'TABLES:\n',
        '- SNOWFLAKE_LEARNING_DB.FDS.TRANSACTIONS (ID, REFERENCE_NUMBER, SENDER_ID, RECIPIENT_ID, SOURCE_CURRENCY, TARGET_CURRENCY, SOURCE_AMOUNT, TARGET_AMOUNT, EXCHANGE_RATE, FEE, STATUS, CREATED_AT, UPDATED_AT)\n',
        '- SNOWFLAKE_LEARNING_DB.FDS.USERS (ID, EMAIL, FULL_NAME, ROLE, KYC_STATUS, WALLET_BALANCE, CREATED_AT)\n',
        '- SNOWFLAKE_LEARNING_DB.FDS.RECIPIENTS (ID, SENDER_ID, NAME, BANK_NAME, ACCOUNT_NUMBER, COUNTRY, CURRENCY, CREATED_AT)\n',
        '- SNOWFLAKE_LEARNING_DB.FDS.FRAUD_ANALYSIS_LOG (ID, TXN_ID, REFERENCE_NUMBER, SENDER_ID, RECIPIENT_ID, SOURCE_AMOUNT, IS_FRAUD, FRAUD_TYPE, ANOMALY_SCORE, VELOCITY_FLAGS, EVIDENCE, EXPLANATION, DECISION, ANALYZED_AT)\n',
        '- SNOWFLAKE_LEARNING_DB.FDS.REMEDIATION_ACTIONS (ID, TXN_ID, REFERENCE_NUMBER, SENDER_ID, ACTION_TYPE, RISK_TIER, ANOMALY_SCORE, FRAUD_TYPE, ACTION_DETAILS, STATUS, EXECUTED_AT, REVERSED_AT, REVERSED_BY)\n',
        '- SNOWFLAKE_LEARNING_DB.FDS.WALLET_FREEZE_LOG (ID, USER_ID, TXN_ID, REASON, FRAUD_TYPE, ANOMALY_SCORE, FROZEN_AT, FREEZE_DURATION_HOURS, EXPIRES_AT, UNFROZEN_AT, UNFROZEN_BY, STATUS)\n',
        '- SNOWFLAKE_LEARNING_DB.FDS.KYC_REVERIFICATION_QUEUE (ID, USER_ID, TXN_ID, PRIORITY, REASON, FRAUD_TYPE, ANOMALY_SCORE, QUEUED_AT, PROCESSED_AT, STATUS)\n\n',
        'JOINS: TRANSACTIONS.SENDER_ID=USERS.ID, TRANSACTIONS.RECIPIENT_ID=RECIPIENTS.ID, FRAUD_ANALYSIS_LOG.TXN_ID=TRANSACTIONS.ID\n\n',
        'User question: ', :user_question, '\n\nSQL:'
    ),
    OBJECT_CONSTRUCT('max_tokens', 1024, 'temperature', 0)
) AS GENERATED_SQL;
