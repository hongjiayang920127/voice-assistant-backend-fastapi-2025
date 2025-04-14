from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import PostgresDsn, Field, validator, AnyHttpUrl
from typing import Optional, List, Union, Any
import os
from pathlib import Path

# Determine the base directory of the project
# Correct way assuming this file is app/config.py and .env is in the project root
BASE_DIR = Path(__file__).resolve().parent.parent # Go up two levels from app/config.py to project root

class Settings(BaseSettings):
    # --- Core Settings ---
    PROJECT_NAME: str = "Voice Assistant Backend"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False # Set to True for development debug info

    # --- Database Settings ---
    POSTGRES_SERVER: str = Field(default="db")
    POSTGRES_USER: str = Field(default="user")
    POSTGRES_PASSWORD: str = Field(default="password")
    POSTGRES_DB: str = Field(default="voice_assistant_db")
    POSTGRES_PORT: int = Field(default=5432)
    DATABASE_URL: Optional[PostgresDsn] = None
    DB_ECHO: bool = False # Log SQL statements

    # --- Security Settings ---
    SECRET_KEY: str = Field(default="a_default_very_secret_key_change_in_production")
    JWT_ALGORITHM: str = Field(default="HS256")
    # Token validity period in minutes - Restored to default
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60 * 24 * 7) # Default: 7 days

    # --- Service Provider Settings ---
    LLM_PROVIDER: str = Field(default="openai")
    OPENAI_API_KEY: Optional[str] = None
    ASR_PROVIDER: str = Field(default="local_mock")
    TTS_PROVIDER: str = Field(default="local_mock")
    EMBEDDING_PROVIDER: str = Field(default="remote_mock")
    VISION_PROVIDER: str = Field(default="remote_mock")

    # --- CORS Settings ---
    BACKEND_CORS_ORIGINS: List[Union[str, AnyHttpUrl]] = Field(default=["*"]) # Allow AnyHttpUrl

    # --- Logging Settings ---
    LOG_LEVEL: str = Field(default="INFO")
    LOG_FILE_PATH: Optional[str] = Field(default=None)

    @validator("DATABASE_URL", pre=True, always=True)
    def assemble_db_connection(cls, v: Optional[str], values: dict[str, Any]) -> Any:
        if isinstance(v, str):
            return v
        port_val = values.get("POSTGRES_PORT")
        if port_val is not None and not isinstance(port_val, int):
             try:
                 port_val = int(port_val)
             except (ValueError, TypeError):
                 raise ValueError(f"Invalid value for POSTGRES_PORT: {port_val}")

        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=values.get("POSTGRES_USER"),
            password=values.get("POSTGRES_PASSWORD"),
            host=values.get("POSTGRES_SERVER"),
            port=port_val,
            path=f"{values.get('POSTGRES_DB') or ''}", 
        )

    # Specify the .env file location
    model_config = SettingsConfigDict(
        env_file=os.path.join(BASE_DIR, '.env'),
        env_file_encoding='utf-8',
        case_sensitive=True,
        extra='ignore'
    )

# Instantiate settings
settings = Settings()