from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    # Telegram Bot Configuration
    bot_token: str
    chat_id: int
    
    # WebDAV Server Configuration
    dav_username: str
    dav_password: str
    dav_host: str = "0.0.0.0"
    dav_port: int = 8080

    # Database
    database_url: str = "sqlite+aiosqlite:///teledav.db"

    # S3 Storage Configuration
    s3_enabled: bool = False
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_bucket: str = "teledav"
    s3_region: str = "us-east-1"
    s3_endpoint_url: str = ""  # Для MinIO или других S3-совместимых сервисов

    # 49.9 MB in bytes
    chunk_size: int = 49 * 1024 * 1024 + 900 * 1024


settings = Settings()

