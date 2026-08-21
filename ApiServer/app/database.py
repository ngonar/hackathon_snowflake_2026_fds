import os
import snowflake.connector
from app.config import settings

SPCS_TOKEN_PATH = "/snowflake/session/token"


def get_snowflake_connection():
    """Create a Snowflake connection using SPCS OAuth token or fallback credentials."""
    if os.path.exists(SPCS_TOKEN_PATH):
        with open(SPCS_TOKEN_PATH, "r") as f:
            token = f.read().strip()
        return snowflake.connector.connect(
            host=os.getenv("SNOWFLAKE_HOST", ""),
            account=settings.SNOWFLAKE_ACCOUNT,
            authenticator="oauth",
            token=token,
            warehouse=settings.SNOWFLAKE_WAREHOUSE,
            database=settings.SNOWFLAKE_DATABASE,
            schema=settings.SNOWFLAKE_SCHEMA,
        )
    conn_params = {
        "account": settings.SNOWFLAKE_ACCOUNT,
        "user": settings.SNOWFLAKE_USER,
        "warehouse": settings.SNOWFLAKE_WAREHOUSE,
        "database": settings.SNOWFLAKE_DATABASE,
        "schema": settings.SNOWFLAKE_SCHEMA,
    }
    if settings.SNOWFLAKE_PASSWORD:
        conn_params["password"] = settings.SNOWFLAKE_PASSWORD
    return snowflake.connector.connect(**conn_params)


def get_db():
    """Yields a Snowflake connection for use as a FastAPI dependency."""
    conn = get_snowflake_connection()
    try:
        yield conn
    finally:
        conn.close()
