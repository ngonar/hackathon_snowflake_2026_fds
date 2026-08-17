-- Expire Stale Freezes: Auto-expire wallet freezes past their duration
-- No parameters required. Run periodically via Snowflake task.

UPDATE SNOWFLAKE_LEARNING_DB.FDS.WALLET_FREEZE_LOG
SET STATUS = 'EXPIRED',
    UNFROZEN_AT = CURRENT_TIMESTAMP(),
    UNFROZEN_BY = 'SYSTEM_AUTO_EXPIRE'
WHERE STATUS = 'ACTIVE'
  AND EXPIRES_AT <= CURRENT_TIMESTAMP();
