-- Remediation Action History
-- Parameters: :start_date (optional, defaults to 30 days ago), :end_date (optional, defaults to now)

SELECT
    ra.ID,
    ra.TXN_ID,
    ra.REFERENCE_NUMBER,
    ra.SENDER_ID,
    u.FULL_NAME AS SENDER_NAME,
    ra.ACTION_TYPE,
    ra.RISK_TIER,
    ra.ANOMALY_SCORE,
    ra.FRAUD_TYPE,
    ra.ACTION_DETAILS,
    ra.STATUS,
    ra.EXECUTED_AT,
    ra.REVERSED_AT,
    ra.REVERSED_BY
FROM SNOWFLAKE_LEARNING_DB.FDS.REMEDIATION_ACTIONS ra
LEFT JOIN SNOWFLAKE_LEARNING_DB.FDS.USERS u ON ra.SENDER_ID = u.ID
WHERE ra.EXECUTED_AT >= COALESCE(:start_date, DATEADD('day', -30, CURRENT_TIMESTAMP()))
  AND ra.EXECUTED_AT <= COALESCE(:end_date, CURRENT_TIMESTAMP())
ORDER BY ra.EXECUTED_AT DESC;
