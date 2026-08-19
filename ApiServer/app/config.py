import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./remittance.db")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super_secret_remittance_encryption_key_38472918")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # Seed configuration
    DEFAULT_ADMIN_EMAIL: str = "admin@remit.com"
    DEFAULT_ADMIN_PASSWORD: str = "AdminPass123!"

    # Snowflake configuration
    SNOWFLAKE_ACCOUNT: str = os.getenv("SNOWFLAKE_ACCOUNT", "")
    SNOWFLAKE_USER: str = os.getenv("SNOWFLAKE_USER", "")
    SNOWFLAKE_PRIVATE_KEY: str = os.getenv("SNOWFLAKE_PRIVATE_KEY", "")
    SNOWFLAKE_WAREHOUSE: str = os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH")
    SNOWFLAKE_DATABASE: str = os.getenv("SNOWFLAKE_DATABASE", "NGONAROID_FDS")
    SNOWFLAKE_SCHEMA: str = os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC")

    class Config:
        env_file = ".env"

settings = Settings()
