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
    SNOWFLAKE_HOST: str = os.getenv("SNOWFLAKE_HOST", "")
    SNOWFLAKE_USER: str = os.getenv("SNOWFLAKE_USER", "")
    SNOWFLAKE_PASSWORD: str = os.getenv("SNOWFLAKE_PASSWORD", "")
    SNOWFLAKE_PRIVATE_KEY: str = os.getenv("SNOWFLAKE_PRIVATE_KEY", "")
    SNOWFLAKE_WAREHOUSE: str = os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH")
    SNOWFLAKE_DATABASE: str = os.getenv("SNOWFLAKE_DATABASE", "SNOWFLAKE_LEARNING_DB")
    SNOWFLAKE_SCHEMA: str = os.getenv("SNOWFLAKE_SCHEMA", "FDS")

    class Config:
        env_file = ".env"

settings = Settings()
