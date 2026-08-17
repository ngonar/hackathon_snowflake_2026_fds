-- Rapid Onboarding Detection: New account + large first transaction
-- Parameters: :sender_id (INTEGER), :current_amount (FLOAT)

WITH account_info AS (
    SELECT
        u.CREATED_AT AS ACCOUNT_CREATED_AT,
        DATEDIFF('minute', u.CREATED_AT, CURRENT_TIMESTAMP()) AS ACCOUNT_AGE_MINUTES,
        DATEDIFF('day', u.CREATED_AT, CURRENT_TIMESTAMP()) AS ACCOUNT_AGE_DAYS,
        u.KYC_STATUS
    FROM NGONAROID_FDS.FDS.USERS u
    WHERE u.ID = :sender_id
),
first_txn AS (
    SELECT MIN(CREATED_AT) AS FIRST_TXN_AT
    FROM NGONAROID_FDS.FDS.TRANSACTIONS
    WHERE SENDER_ID = :sender_id
),
prior_txn_count AS (
    SELECT COUNT(*) AS COMPLETED_TXN_COUNT
    FROM NGONAROID_FDS.FDS.TRANSACTIONS
    WHERE SENDER_ID = :sender_id
      AND STATUS IN ('FUNDED', 'COMPLETED')
)
SELECT
    ai.ACCOUNT_AGE_MINUTES,
    ai.ACCOUNT_AGE_DAYS,
    ai.KYC_STATUS,
    ft.FIRST_TXN_AT,
    DATEDIFF('minute', ai.ACCOUNT_CREATED_AT, ft.FIRST_TXN_AT) AS MINUTES_TO_FIRST_TXN,
    ptc.COMPLETED_TXN_COUNT,
    :current_amount AS CURRENT_AMOUNT,
    (ai.ACCOUNT_AGE_MINUTES <= 60 AND :current_amount >= 500) AS RAPID_ONBOARDING_DETECTED
FROM account_info ai, first_txn ft, prior_txn_count ptc;
