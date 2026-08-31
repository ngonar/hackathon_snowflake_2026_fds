-- Sender Profile: Account details and KYC status
-- Parameters: :sender_id (INTEGER)

SELECT
    u.ID,
    u.EMAIL,
    u.FULL_NAME,
    u.ROLE,
    u.KYC_STATUS,
    u.KYC_DOCUMENT_TYPE,
    u.WALLET_BALANCE,
    u.CREATED_AT,
    DATEDIFF('day', u.CREATED_AT, CURRENT_TIMESTAMP()) AS ACCOUNT_AGE_DAYS
FROM SNOWFLAKE_LEARNING_DB.FDS.USERS u
WHERE u.ID = :sender_id;
