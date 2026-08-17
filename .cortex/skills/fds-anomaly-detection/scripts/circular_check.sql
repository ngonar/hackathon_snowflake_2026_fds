-- Circular Transfer Detection: A→B→C→A money flow within 7 days
-- Parameters: :sender_id (INTEGER), :recipient_id (INTEGER)

WITH outbound AS (
    -- Transactions FROM recipient's owner accounts (B sends to C)
    SELECT DISTINCT
        t.SENDER_ID AS HOP1_SENDER,
        t.RECIPIENT_ID AS HOP1_RECIPIENT,
        r.SENDER_ID AS HOP1_RCPT_OWNER
    FROM NGONAROID_FDS.FDS.TRANSACTIONS t
    JOIN NGONAROID_FDS.FDS.RECIPIENTS r ON t.RECIPIENT_ID = r.ID
    WHERE t.SENDER_ID = :sender_id
      AND t.CREATED_AT >= DATEADD('day', -7, CURRENT_TIMESTAMP())
),
hop2 AS (
    -- Find if any recipient owner (B) sent money that eventually reaches back
    SELECT DISTINCT
        t2.SENDER_ID AS HOP2_SENDER,
        t2.RECIPIENT_ID AS HOP2_RECIPIENT,
        r2.SENDER_ID AS HOP2_RCPT_OWNER
    FROM NGONAROID_FDS.FDS.TRANSACTIONS t2
    JOIN NGONAROID_FDS.FDS.RECIPIENTS r2 ON t2.RECIPIENT_ID = r2.ID
    JOIN outbound o ON t2.SENDER_ID = o.HOP1_RCPT_OWNER
    WHERE t2.CREATED_AT >= DATEADD('day', -7, CURRENT_TIMESTAMP())
      AND t2.SENDER_ID != :sender_id
),
circular AS (
    -- Check if hop2 recipient owner is the original sender
    SELECT
        h.HOP2_SENDER,
        h.HOP2_RECIPIENT,
        h.HOP2_RCPT_OWNER
    FROM hop2 h
    WHERE h.HOP2_RCPT_OWNER = :sender_id
)
SELECT
    CASE WHEN COUNT(*) > 0 THEN TRUE ELSE FALSE END AS CIRCULAR_TRANSFER_DETECTED,
    COUNT(*) AS CIRCULAR_PATH_COUNT
FROM circular;
