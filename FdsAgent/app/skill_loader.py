import os
import re
import snowflake.connector
import base64
from cryptography.hazmat.primitives import serialization
from dotenv import load_dotenv

load_dotenv()

# Cortex Extension locations for each skill
SKILL_EXTENSIONS = {
    "fds-transaction-profiling": "USER$NGARTOONIST.SKILL_SHARING.FDS_TRANSACTION_PROFILING",
    "fds-anomaly-detection": "USER$NGARTOONIST.SKILL_SHARING.FDS_ANOMALY_DETECTION",
    "fds-fraud-classification": "USER$NGARTOONIST.SKILL_SHARING.FDS_FRAUD_CLASSIFICATION",
}

# Map of skill_name/script_name -> SQL content (cached after first load)
_sql_cache: dict[str, str] = {}
_loaded = False


def _get_connection():
    token_path = "/snowflake/session/token"
    if os.path.exists(token_path):
        with open(token_path, "r") as f:
            token = f.read().strip()
        return snowflake.connector.connect(
            host=os.getenv("SNOWFLAKE_HOST"),
            account=os.getenv("SNOWFLAKE_ACCOUNT"),
            authenticator="oauth",
            token=token,
            warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
            database=os.getenv("SNOWFLAKE_DATABASE", "SNOWFLAKE_LEARNING_DB"),
            schema=os.getenv("SNOWFLAKE_SCHEMA", "FDS"),
        )
    conn_params = {
        "account": os.getenv("SNOWFLAKE_ACCOUNT"),
        "user": os.getenv("SNOWFLAKE_USER"),
        "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
        "database": os.getenv("SNOWFLAKE_DATABASE", "SNOWFLAKE_LEARNING_DB"),
        "schema": os.getenv("SNOWFLAKE_SCHEMA", "FDS"),
        "role": os.getenv("SNOWFLAKE_ROLE"),
    }
    key_b64 = os.getenv("SNOWFLAKE_PRIVATE_KEY", "")
    if key_b64:
        key_bytes = base64.b64decode(key_b64)
        pk = serialization.load_pem_private_key(key_bytes, password=None)
        conn_params["private_key"] = pk.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    else:
        conn_params["password"] = os.getenv("SNOWFLAKE_PASSWORD")
    return snowflake.connector.connect(**conn_params)


def _convert_bind_params(sql: str) -> str:
    """Convert Snowflake :param bind syntax to Python %(param)s pyformat."""
    return re.sub(r':(\w+)', r'%(\1)s', sql)


def _load_from_stage() -> dict[str, str]:
    """Try to load SQL scripts from the Cortex Extension stage."""
    loaded = {}
    conn = _get_connection()
    cursor = conn.cursor()
    try:
        for skill_name, ext_fqn in SKILL_EXTENSIONS.items():
            db, schema, ext = ext_fqn.split(".")
            stage_path = f'@"{db}"."{schema}"."{ext}"/versions/live/skills/{skill_name}/scripts/'
            try:
                cursor.execute(f"LIST {stage_path}")
                files = cursor.fetchall()
                for file_row in files:
                    file_path = file_row[0]
                    filename = file_path.split("/")[-1]
                    if filename.endswith(".sql"):
                        cursor.execute(f"SELECT $1 FROM {stage_path}{filename}")
                        rows = cursor.fetchall()
                        sql_content = "\n".join(r[0] for r in rows)
                        key = f"{skill_name}/{filename}"
                        loaded[key] = _convert_bind_params(sql_content)
            except Exception as e:
                print(f"SkillLoader: Could not load {skill_name} from stage: {e}")
    finally:
        cursor.close()
        conn.close()
    return loaded


# Bundled SQL fallbacks (converted from :param to %(param)s at definition time)
_BUNDLED_SQL = {
    # --- Transaction Profiling ---
    "fds-transaction-profiling/sender_profile.sql": """
SELECT u.ID, u.EMAIL, u.FULL_NAME, u.ROLE, u.KYC_STATUS, u.KYC_DOCUMENT_TYPE,
       u.WALLET_BALANCE, u.CREATED_AT,
       DATEDIFF('day', u.CREATED_AT, CURRENT_TIMESTAMP()) AS ACCOUNT_AGE_DAYS
FROM SNOWFLAKE_LEARNING_DB.FDS.USERS u
WHERE u.ID = %(sender_id)s""",

    "fds-transaction-profiling/sender_behavior.sql": """
WITH sender_txns AS (
    SELECT t.SOURCE_AMOUNT, t.TARGET_AMOUNT, t.RECIPIENT_ID, t.STATUS, t.CREATED_AT,
           EXTRACT(HOUR FROM t.CREATED_AT) AS TXN_HOUR
    FROM SNOWFLAKE_LEARNING_DB.FDS.TRANSACTIONS t
    WHERE t.SENDER_ID = %(sender_id)s
      AND t.STATUS IN ('FUNDED', 'COMPLETED', 'PROCESSING')
),
hourly_dist AS (
    SELECT TXN_HOUR, COUNT(*) AS TXN_COUNT FROM sender_txns GROUP BY TXN_HOUR
),
top_recipients AS (
    SELECT r.NAME AS RECIPIENT_NAME, r.COUNTRY, COUNT(*) AS SEND_COUNT
    FROM sender_txns st
    JOIN SNOWFLAKE_LEARNING_DB.FDS.RECIPIENTS r ON st.RECIPIENT_ID = r.ID
    GROUP BY r.NAME, r.COUNTRY ORDER BY SEND_COUNT DESC LIMIT 5
)
SELECT COUNT(*) AS TOTAL_TXN_COUNT, SUM(SOURCE_AMOUNT) AS LIFETIME_VOLUME,
       AVG(SOURCE_AMOUNT) AS AVG_AMOUNT, STDDEV(SOURCE_AMOUNT) AS STDDEV_AMOUNT,
       MAX(SOURCE_AMOUNT) AS MAX_AMOUNT, MIN(SOURCE_AMOUNT) AS MIN_AMOUNT,
       COUNT(DISTINCT RECIPIENT_ID) AS UNIQUE_RECIPIENT_COUNT,
       DATEDIFF('day', MAX(CREATED_AT), CURRENT_TIMESTAMP()) AS DAYS_SINCE_LAST_TXN,
       (SELECT ARRAY_AGG(OBJECT_CONSTRUCT('hour', TXN_HOUR, 'count', TXN_COUNT)) FROM hourly_dist) AS HOURLY_DISTRIBUTION,
       (SELECT ARRAY_AGG(OBJECT_CONSTRUCT('name', RECIPIENT_NAME, 'country', COUNTRY, 'count', SEND_COUNT)) FROM top_recipients) AS TOP_RECIPIENTS
FROM sender_txns""",

    "fds-transaction-profiling/recipient_profile.sql": """
SELECT r.ID, r.NAME, r.BANK_NAME, r.ACCOUNT_NUMBER, r.COUNTRY, r.CURRENCY, r.CREATED_AT,
       DATEDIFF('day', r.CREATED_AT, CURRENT_TIMESTAMP()) AS RECIPIENT_AGE_DAYS,
       (SELECT COUNT(DISTINCT t.SENDER_ID) FROM SNOWFLAKE_LEARNING_DB.FDS.TRANSACTIONS t
        WHERE t.RECIPIENT_ID = r.ID) AS DISTINCT_SENDER_COUNT
FROM SNOWFLAKE_LEARNING_DB.FDS.RECIPIENTS r
WHERE r.ID = %(recipient_id)s""",

    "fds-transaction-profiling/recipient_inflow.sql": """
SELECT COUNT(*) AS TOTAL_INFLOW_COUNT, SUM(t.SOURCE_AMOUNT) AS TOTAL_INFLOW_VOLUME,
       AVG(t.SOURCE_AMOUNT) AS AVG_INFLOW_AMOUNT,
       COUNT(DISTINCT t.SENDER_ID) AS DISTINCT_SENDER_COUNT,
       MIN(t.CREATED_AT) AS FIRST_INFLOW_AT, MAX(t.CREATED_AT) AS LAST_INFLOW_AT,
       DATEDIFF('day', MIN(t.CREATED_AT), MAX(t.CREATED_AT)) AS INFLOW_SPAN_DAYS
FROM SNOWFLAKE_LEARNING_DB.FDS.TRANSACTIONS t
WHERE t.RECIPIENT_ID = %(recipient_id)s
  AND t.STATUS IN ('FUNDED', 'COMPLETED', 'PROCESSING')""",

    # --- Anomaly Detection ---
    "fds-anomaly-detection/velocity_check.sql": """
WITH recent_txns AS (
    SELECT t.SOURCE_AMOUNT, t.RECIPIENT_ID, t.CREATED_AT
    FROM SNOWFLAKE_LEARNING_DB.FDS.TRANSACTIONS t
    WHERE t.SENDER_ID = %(sender_id)s
      AND t.CREATED_AT >= DATEADD('hour', -24, CURRENT_TIMESTAMP())
      AND t.STATUS IN ('FUNDED', 'COMPLETED', 'PROCESSING', 'PENDING')
),
historical_avg AS (
    SELECT AVG(SOURCE_AMOUNT) AS AVG_AMOUNT, STDDEV(SOURCE_AMOUNT) AS STDDEV_AMOUNT
    FROM SNOWFLAKE_LEARNING_DB.FDS.TRANSACTIONS
    WHERE SENDER_ID = %(sender_id)s AND STATUS IN ('FUNDED', 'COMPLETED', 'PROCESSING')
),
new_recipients_24h AS (
    SELECT COUNT(DISTINCT rt.RECIPIENT_ID) AS NEW_RCPT_COUNT
    FROM recent_txns rt
    WHERE rt.RECIPIENT_ID NOT IN (
        SELECT DISTINCT t2.RECIPIENT_ID FROM SNOWFLAKE_LEARNING_DB.FDS.TRANSACTIONS t2
        WHERE t2.SENDER_ID = %(sender_id)s
          AND t2.CREATED_AT < DATEADD('hour', -24, CURRENT_TIMESTAMP())
          AND t2.STATUS IN ('FUNDED', 'COMPLETED', 'PROCESSING')
    )
)
SELECT (SELECT COUNT(*) FROM recent_txns) AS TXN_COUNT_24H,
       (SELECT COUNT(*) FROM recent_txns) > 5 AS HIGH_FREQUENCY_24H,
       (SELECT NEW_RCPT_COUNT FROM new_recipients_24h) AS NEW_RECIPIENTS_24H,
       (SELECT NEW_RCPT_COUNT FROM new_recipients_24h) >= 3 AS NEW_RECIPIENT_BURST,
       h.AVG_AMOUNT AS HISTORICAL_AVG, h.STDDEV_AMOUNT AS HISTORICAL_STDDEV,
       %(current_amount)s AS CURRENT_AMOUNT,
       CASE WHEN h.AVG_AMOUNT > 0 THEN %(current_amount)s / h.AVG_AMOUNT ELSE 0 END AS AMOUNT_RATIO,
       CASE WHEN h.AVG_AMOUNT > 0 AND %(current_amount)s > h.AVG_AMOUNT * 3 THEN TRUE ELSE FALSE END AS AMOUNT_SPIKE
FROM historical_avg h""",

    "fds-anomaly-detection/time_evasion.sql": """
WITH recent_txns AS (
    SELECT CREATED_AT, EXTRACT(HOUR FROM CREATED_AT) AS TXN_HOUR,
           LAG(CREATED_AT) OVER (ORDER BY CREATED_AT) AS PREV_TXN_AT
    FROM SNOWFLAKE_LEARNING_DB.FDS.TRANSACTIONS
    WHERE SENDER_ID = %(sender_id)s
      AND CREATED_AT >= DATEADD('day', -7, CURRENT_TIMESTAMP())
      AND STATUS IN ('FUNDED', 'COMPLETED', 'PROCESSING', 'PENDING')
    ORDER BY CREATED_AT DESC
),
spacing AS (
    SELECT DATEDIFF('minute', PREV_TXN_AT, CREATED_AT) AS MINUTES_BETWEEN, TXN_HOUR
    FROM recent_txns WHERE PREV_TXN_AT IS NOT NULL
)
SELECT %(txn_hour)s BETWEEN 1 AND 5 AS UNUSUAL_HOURS,
       %(txn_hour)s AS CURRENT_TXN_HOUR,
       (SELECT COUNT(*) FROM recent_txns WHERE TXN_HOUR BETWEEN 1 AND 5) AS NIGHTTIME_TXN_COUNT_7D,
       (SELECT AVG(MINUTES_BETWEEN) FROM spacing) AS AVG_SPACING_MINUTES,
       (SELECT STDDEV(MINUTES_BETWEEN) FROM spacing) AS STDDEV_SPACING_MINUTES,
       (SELECT COUNT(*) FROM spacing WHERE MINUTES_BETWEEN < 5) AS RAPID_SUCCESSION_COUNT""",

    "fds-anomaly-detection/smurfing_check.sql": """
WITH recent_txns AS (
    SELECT SOURCE_AMOUNT, CREATED_AT
    FROM SNOWFLAKE_LEARNING_DB.FDS.TRANSACTIONS
    WHERE SENDER_ID = %(sender_id)s
      AND CREATED_AT >= DATEADD('hour', -24, CURRENT_TIMESTAMP())
      AND STATUS IN ('FUNDED', 'COMPLETED', 'PROCESSING', 'PENDING')
),
threshold_analysis AS (
    SELECT COUNT(*) AS SMALL_TXN_COUNT, SUM(SOURCE_AMOUNT) AS AGGREGATE_VOLUME,
           AVG(SOURCE_AMOUNT) AS AVG_SMALL_AMOUNT, MAX(SOURCE_AMOUNT) AS MAX_SMALL_AMOUNT
    FROM recent_txns WHERE SOURCE_AMOUNT < 1000
)
SELECT ta.SMALL_TXN_COUNT, ta.AGGREGATE_VOLUME, ta.AVG_SMALL_AMOUNT, ta.MAX_SMALL_AMOUNT,
       ta.SMALL_TXN_COUNT >= 3 AND ta.AGGREGATE_VOLUME >= 2000 AS SMURFING_DETECTED,
       CASE WHEN ta.SMALL_TXN_COUNT >= 5 AND ta.AGGREGATE_VOLUME >= 5000 THEN 'HIGH'
            WHEN ta.SMALL_TXN_COUNT >= 3 AND ta.AGGREGATE_VOLUME >= 2000 THEN 'MEDIUM'
            ELSE 'LOW' END AS SMURFING_SEVERITY
FROM threshold_analysis ta""",

    "fds-anomaly-detection/rapid_onboarding.sql": """
WITH account_info AS (
    SELECT u.CREATED_AT AS ACCOUNT_CREATED_AT,
           DATEDIFF('minute', u.CREATED_AT, CURRENT_TIMESTAMP()) AS ACCOUNT_AGE_MINUTES,
           DATEDIFF('day', u.CREATED_AT, CURRENT_TIMESTAMP()) AS ACCOUNT_AGE_DAYS,
           u.KYC_STATUS
    FROM SNOWFLAKE_LEARNING_DB.FDS.USERS u WHERE u.ID = %(sender_id)s
),
first_txn AS (
    SELECT MIN(CREATED_AT) AS FIRST_TXN_AT
    FROM SNOWFLAKE_LEARNING_DB.FDS.TRANSACTIONS WHERE SENDER_ID = %(sender_id)s
),
prior_txn_count AS (
    SELECT COUNT(*) AS COMPLETED_TXN_COUNT
    FROM SNOWFLAKE_LEARNING_DB.FDS.TRANSACTIONS
    WHERE SENDER_ID = %(sender_id)s AND STATUS IN ('FUNDED', 'COMPLETED')
)
SELECT ai.ACCOUNT_AGE_MINUTES, ai.ACCOUNT_AGE_DAYS, ai.KYC_STATUS, ft.FIRST_TXN_AT,
       DATEDIFF('minute', ai.ACCOUNT_CREATED_AT, ft.FIRST_TXN_AT) AS MINUTES_TO_FIRST_TXN,
       ptc.COMPLETED_TXN_COUNT, %(current_amount)s AS CURRENT_AMOUNT,
       (ai.ACCOUNT_AGE_MINUTES <= 60 AND %(current_amount)s >= 500) AS RAPID_ONBOARDING_DETECTED
FROM account_info ai, first_txn ft, prior_txn_count ptc""",

    "fds-anomaly-detection/circular_check.sql": """
WITH outbound AS (
    SELECT DISTINCT t.SENDER_ID AS HOP1_SENDER, t.RECIPIENT_ID AS HOP1_RECIPIENT,
           r.SENDER_ID AS HOP1_RCPT_OWNER
    FROM SNOWFLAKE_LEARNING_DB.FDS.TRANSACTIONS t
    JOIN SNOWFLAKE_LEARNING_DB.FDS.RECIPIENTS r ON t.RECIPIENT_ID = r.ID
    WHERE t.SENDER_ID = %(sender_id)s
      AND t.CREATED_AT >= DATEADD('day', -7, CURRENT_TIMESTAMP())
),
hop2 AS (
    SELECT DISTINCT t2.SENDER_ID AS HOP2_SENDER, t2.RECIPIENT_ID AS HOP2_RECIPIENT,
           r2.SENDER_ID AS HOP2_RCPT_OWNER
    FROM SNOWFLAKE_LEARNING_DB.FDS.TRANSACTIONS t2
    JOIN SNOWFLAKE_LEARNING_DB.FDS.RECIPIENTS r2 ON t2.RECIPIENT_ID = r2.ID
    JOIN outbound o ON t2.SENDER_ID = o.HOP1_RCPT_OWNER
    WHERE t2.CREATED_AT >= DATEADD('day', -7, CURRENT_TIMESTAMP())
      AND t2.SENDER_ID != %(sender_id)s
),
circular AS (
    SELECT h.HOP2_SENDER, h.HOP2_RECIPIENT, h.HOP2_RCPT_OWNER
    FROM hop2 h WHERE h.HOP2_RCPT_OWNER = %(sender_id)s
)
SELECT CASE WHEN COUNT(*) > 0 THEN TRUE ELSE FALSE END AS CIRCULAR_TRANSFER_DETECTED,
       COUNT(*) AS CIRCULAR_PATH_COUNT
FROM circular""",
}


def load_skills():
    """Load SQL templates from Cortex Extension stage, falling back to bundled copies."""
    global _sql_cache, _loaded
    if _loaded:
        return

    # Start with bundled SQL as baseline
    _sql_cache.update(_BUNDLED_SQL)

    # Try to refresh from Cortex Extension stage
    try:
        stage_sql = _load_from_stage()
        if stage_sql:
            _sql_cache.update(stage_sql)
            print(f"SkillLoader: Refreshed {len(stage_sql)} SQL scripts from Cortex Extension stage")
        else:
            print("SkillLoader: No scripts loaded from stage, using bundled SQL")
    except Exception as e:
        print(f"SkillLoader: Stage load failed ({e}), using bundled SQL")

    _loaded = True
    print(f"SkillLoader: {len(_sql_cache)} SQL templates ready")


def get_sql(skill_name: str, script_name: str) -> str:
    """Get a cached SQL template by skill/script name."""
    if not _loaded:
        load_skills()
    key = f"{skill_name}/{script_name}"
    if key not in _sql_cache:
        raise KeyError(f"SQL template not found: {key}")
    return _sql_cache[key]
