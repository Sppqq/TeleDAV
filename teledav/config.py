from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"  # Игнорируем лишние переменные окружения
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
