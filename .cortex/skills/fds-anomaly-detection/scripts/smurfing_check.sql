-- Smurfing Detection: Identify structured small transactions below thresholds
-- Parameters: :sender_id (INTEGER)

WITH recent_txns AS (
    SELECT
        SOURCE_AMOUNT,
        CREATED_AT
    FROM NGONAROID_FDS.FDS.TRANSACTIONS
    WHERE SENDER_ID = :sender_id
      AND CREATED_AT >= DATEADD('hour', -24, CURRENT_TIMESTAMP())
      AND STATUS IN ('FUNDED', 'COMPLETED', 'PROCESSING', 'PENDING')
),
threshold_analysis AS (
    SELECT
        COUNT(*) AS SMALL_TXN_COUNT,
        SUM(SOURCE_AMOUNT) AS AGGREGATE_VOLUME,
        AVG(SOURCE_AMOUNT) AS AVG_SMALL_AMOUNT,
        MAX(SOURCE_AMOUNT) AS MAX_SMALL_AMOUNT
    FROM recent_txns
    WHERE SOURCE_AMOUNT < 1000  -- Below typical reporting threshold
)
SELECT
    ta.SMALL_TXN_COUNT,
    ta.AGGREGATE_VOLUME,
    ta.AVG_SMALL_AMOUNT,
    ta.MAX_SMALL_AMOUNT,
    ta.SMALL_TXN_COUNT >= 3 AND ta.AGGREGATE_VOLUME >= 2000 AS SMURFING_DETECTED,
    CASE
        WHEN ta.SMALL_TXN_COUNT >= 5 AND ta.AGGREGATE_VOLUME >= 5000 THEN 'HIGH'
        WHEN ta.SMALL_TXN_COUNT >= 3 AND ta.AGGREGATE_VOLUME >= 2000 THEN 'MEDIUM'
        ELSE 'LOW'
    END AS SMURFING_SEVERITY
FROM threshold_analysis ta;
