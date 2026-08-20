import os
import json
import base64
import snowflake.connector
from cryptography.hazmat.primitives import serialization
from dotenv import load_dotenv

load_dotenv()

FDS_SCHEMA_CONTEXT = """
You have access to the following Snowflake tables in SNOWFLAKE_LEARNING_DB.FDS:

TABLE: PENDING_TRANSACTIONS (this is the primary transactions table - use this for transaction lookups)
Columns: ID (INTEGER), TXN_ID (INTEGER), REFERENCE_NUMBER (VARCHAR), SENDER_ID (INTEGER), RECIPIENT_ID (INTEGER), SOURCE_CURRENCY (VARCHAR), TARGET_CURRENCY (VARCHAR), SOURCE_AMOUNT (FLOAT), TARGET_AMOUNT (FLOAT), EXCHANGE_RATE (FLOAT), FEE (FLOAT), STATUS (VARCHAR: PENDING/FUNDED/PROCESSING/COMPLETED/CANCELLED/FAILED/SUSPICIOUS), CREATED_AT (TIMESTAMP_NTZ), PROCESSED (BOOLEAN)

TABLE: TRANSACTIONS (legacy - may be empty, prefer PENDING_TRANSACTIONS)
Columns: ID (INTEGER), REFERENCE_NUMBER (VARCHAR), SENDER_ID (INTEGER), RECIPIENT_ID (INTEGER), SOURCE_CURRENCY (VARCHAR), TARGET_CURRENCY (VARCHAR), SOURCE_AMOUNT (FLOAT), TARGET_AMOUNT (FLOAT), EXCHANGE_RATE (FLOAT), FEE (FLOAT), STATUS (VARCHAR: PENDING/FUNDED/PROCESSING/COMPLETED/CANCELLED/FAILED/SUSPICIOUS), CREATED_AT (TIMESTAMP_NTZ), UPDATED_AT (TIMESTAMP_NTZ)

TABLE: USERS
Columns: ID (INTEGER), EMAIL (VARCHAR), FULL_NAME (VARCHAR), ROLE (VARCHAR), KYC_STATUS (VARCHAR: PENDING_SUBMISSION/PENDING_APPROVAL/APPROVED/REJECTED/FROZEN), KYC_DOCUMENT_TYPE (VARCHAR), WALLET_BALANCE (FLOAT), CREATED_AT (TIMESTAMP_NTZ), UPDATED_AT (TIMESTAMP_NTZ)

TABLE: RECIPIENTS
Columns: ID (INTEGER), SENDER_ID (INTEGER), NAME (VARCHAR), BANK_NAME (VARCHAR), ACCOUNT_NUMBER (VARCHAR), ROUTING_NUMBER (VARCHAR), COUNTRY (VARCHAR), CURRENCY (VARCHAR), CREATED_AT (TIMESTAMP_NTZ)

TABLE: FRAUD_ANALYSIS_LOG
Columns: ID (INTEGER), TXN_ID (INTEGER), REFERENCE_NUMBER (VARCHAR), SENDER_ID (INTEGER), RECIPIENT_ID (INTEGER), SOURCE_AMOUNT (FLOAT), IS_FRAUD (BOOLEAN), FRAUD_TYPE (VARCHAR), ANOMALY_SCORE (FLOAT 0-100), VELOCITY_FLAGS (VARIANT/JSON array), EVIDENCE (VARIANT/JSON array), EXPLANATION (VARCHAR), DECISION (VARCHAR: FAILED/SUSPICIOUS/FUNDED), ANALYZED_AT (TIMESTAMP_NTZ)

TABLE: REMEDIATION_ACTIONS
Columns: ID (INTEGER), TXN_ID (INTEGER), REFERENCE_NUMBER (VARCHAR), SENDER_ID (INTEGER), ACTION_TYPE (VARCHAR: WALLET_FROZEN/KYC_REVERIFICATION_DISPATCHED/TRANSACTION_BLOCKED/FLAGGED_SUSPICIOUS/AUTO_APPROVED/COMPLIANCE_AUDIT/REMEDIATION_CRITICAL/REMEDIATION_HIGH/REMEDIATION_MEDIUM/REMEDIATION_LOW), RISK_TIER (VARCHAR: CRITICAL/HIGH/MEDIUM/LOW), ANOMALY_SCORE (FLOAT), FRAUD_TYPE (VARCHAR), ACTION_DETAILS (VARIANT/JSON), STATUS (VARCHAR), EXECUTED_AT (TIMESTAMP_NTZ), REVERSED_AT (TIMESTAMP_NTZ), REVERSED_BY (VARCHAR)

TABLE: WALLET_FREEZE_LOG
Columns: ID (INTEGER), USER_ID (INTEGER), TXN_ID (INTEGER), REASON (VARCHAR), FRAUD_TYPE (VARCHAR), ANOMALY_SCORE (FLOAT), FROZEN_AT (TIMESTAMP_NTZ), FREEZE_DURATION_HOURS (INTEGER), EXPIRES_AT (TIMESTAMP_NTZ), UNFROZEN_AT (TIMESTAMP_NTZ), UNFROZEN_BY (VARCHAR), STATUS (VARCHAR: ACTIVE/EXPIRED/REVERSED)

TABLE: KYC_REVERIFICATION_QUEUE
Columns: ID (INTEGER), USER_ID (INTEGER), TXN_ID (INTEGER), PRIORITY (VARCHAR: URGENT/HIGH/NORMAL), REASON (VARCHAR), FRAUD_TYPE (VARCHAR), ANOMALY_SCORE (FLOAT), QUEUED_AT (TIMESTAMP_NTZ), PROCESSED_AT (TIMESTAMP_NTZ), STATUS (VARCHAR: PENDING/PROCESSED)

Common joins:
- PENDING_TRANSACTIONS.SENDER_ID = USERS.ID
- PENDING_TRANSACTIONS.RECIPIENT_ID = RECIPIENTS.ID
- PENDING_TRANSACTIONS.REFERENCE_NUMBER = REMEDIATION_ACTIONS.REFERENCE_NUMBER
- PENDING_TRANSACTIONS.REFERENCE_NUMBER = FRAUD_ANALYSIS_LOG.REFERENCE_NUMBER
- REMEDIATION_ACTIONS.TXN_ID = PENDING_TRANSACTIONS.TXN_ID
- WALLET_FREEZE_LOG.USER_ID = USERS.ID
"""

SYSTEM_PROMPT = f"""You are a SQL query generator for a fraud investigation system.
Given a natural language question from a compliance officer, generate a single Snowflake SQL SELECT query.

RULES:
1. ONLY generate SELECT statements. Never generate INSERT, UPDATE, DELETE, DROP, CREATE, ALTER, or any DDL/DML.
2. Always use fully qualified table names: SNOWFLAKE_LEARNING_DB.FDS.<TABLE>
3. Use appropriate JOINs to include human-readable names (user full_name, recipient name).
4. Limit results to 100 rows maximum unless the user specifies otherwise.
5. Order results by most relevant column (usually timestamp DESC or anomaly_score DESC).
6. Format timestamps nicely when possible.
7. If the query mentions "last 24 hours" or similar time ranges, use DATEADD with CURRENT_TIMESTAMP().
8. Return ONLY the SQL query, no explanation, no markdown, no backticks.

{FDS_SCHEMA_CONTEXT}
"""


def _load_private_key():
    key_b64 = os.getenv("SNOWFLAKE_PRIVATE_KEY", "")
    key_bytes = base64.b64decode(key_b64)
    private_key = serialization.load_pem_private_key(key_bytes, password=None)
    return private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def _get_snowflake_connection():
    return snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        private_key=_load_private_key(),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
        database="SNOWFLAKE_LEARNING_DB",
        schema="FDS",
        role=os.getenv("SNOWFLAKE_ROLE"),
    )


def _validate_query_safety(sql: str) -> bool:
    """Ensure the generated SQL is read-only."""
    normalized = sql.strip().upper()
    dangerous_keywords = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER', 'TRUNCATE', 'MERGE', 'COPY']
    first_word = normalized.split()[0] if normalized.split() else ''
    if first_word not in ('SELECT', 'WITH', 'SHOW', 'DESCRIBE'):
        return False
    for kw in dangerous_keywords:
        if f' {kw} ' in f' {normalized} ':
            if kw == 'CREATE' and 'CREATE_' in normalized:
                continue
            return False
    return True


def translate_and_execute(natural_language_query: str) -> dict:
    """
    Translates a natural language query to SQL using Cortex AI_COMPLETE,
    validates safety, executes it, and returns results.
    """
    conn = _get_snowflake_connection()
    try:
        cursor = conn.cursor()

        # Step 1: Generate SQL from natural language using Cortex
        prompt = f"{SYSTEM_PROMPT}\n\nUser question: {natural_language_query}\n\nSQL:"
        escaped_prompt = prompt.replace("'", "''")

        cursor.execute(f"""
            SELECT SNOWFLAKE.CORTEX.COMPLETE(
                'llama3.1-70b',
                '{escaped_prompt}'
            )
        """)
        row = cursor.fetchone()
        generated_sql = row[0].strip()

        # The LLM output may have doubled single quotes from Snowflake string escaping
        # e.g. ''REMIT-123'' instead of 'REMIT-123' - fix this
        import re
        generated_sql = re.sub(r"''([^']+)''", r"'\1'", generated_sql)

        print(f"NL Query: Generated SQL: {generated_sql}")

        # Clean up markdown formatting if present
        if generated_sql.startswith('```'):
            lines = generated_sql.split('\n')
            lines = [l for l in lines if not l.startswith('```')]
            generated_sql = '\n'.join(lines).strip()

        # Strip any preamble text before the actual SQL statement
        for keyword in ('SELECT', 'WITH'):
            idx = generated_sql.upper().find(keyword)
            if idx > 0:
                generated_sql = generated_sql[idx:]
                break

        # Remove trailing explanation or text after the SQL statement
        # Find the last semicolon and truncate after it
        semi_idx = generated_sql.rfind(';')
        if semi_idx > 0:
            generated_sql = generated_sql[:semi_idx + 1]
        # Remove trailing semicolons for execution
        generated_sql = generated_sql.rstrip(';').strip()

        # Step 2: Validate query safety
        if not _validate_query_safety(generated_sql):
            return {
                "success": False,
                "error": "Generated query contains unsafe operations. Only SELECT queries are allowed.",
                "sql": generated_sql,
                "results": []
            }

        # Step 3: Execute the generated SQL (with one retry on compilation error)
        try:
            cursor.execute(generated_sql)
        except Exception as sql_err:
            if "SQL compilation error" in str(sql_err):
                # Retry: ask the model to fix the query
                fix_prompt = (
                    f"{SYSTEM_PROMPT}\n\n"
                    f"The following SQL query failed with this error:\n"
                    f"Query: {generated_sql}\n"
                    f"Error: {str(sql_err)}\n\n"
                    f"Please generate a corrected SQL query. Return ONLY the SQL, no explanation.\n\nSQL:"
                )
                escaped_fix = fix_prompt.replace("'", "''")
                cursor.execute(f"""
                    SELECT SNOWFLAKE.CORTEX.COMPLETE('llama3.1-70b', '{escaped_fix}')
                """)
                fixed_sql = cursor.fetchone()[0].strip()
                if fixed_sql.startswith('```'):
                    lines = fixed_sql.split('\n')
                    lines = [l for l in lines if not l.startswith('```')]
                    fixed_sql = '\n'.join(lines).strip()
                for keyword in ('SELECT', 'WITH'):
                    idx = fixed_sql.upper().find(keyword)
                    if idx > 0:
                        fixed_sql = fixed_sql[idx:]
                        break
                fixed_sql = fixed_sql.rstrip(';').strip()
                generated_sql = fixed_sql
                cursor.execute(generated_sql)
            else:
                raise

        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()

        # Convert to list of dicts
        results = []
        for row in rows:
            record = {}
            for i, col in enumerate(columns):
                val = row[i]
                if val is not None and hasattr(val, 'isoformat'):
                    val = val.isoformat()
                elif isinstance(val, bytes):
                    val = val.decode('utf-8', errors='replace')
                record[col] = val
            results.append(record)

        return {
            "success": True,
            "sql": generated_sql,
            "columns": columns,
            "results": results,
            "row_count": len(results)
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "sql": generated_sql if 'generated_sql' in dir() else None,
            "results": []
        }
    finally:
        conn.close()
