from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    bot_token: str
    chat_id: int

    dav_username: str
    dav_password: str
    dav_host: str = "0.0.0.0"
    dav_port: int = 8080

    database_url: str = "sqlite+aiosqlite:///teledav.db"

    # 49.9 MB in bytes
    chunk_size: int = 49 * 1024 * 1024 + 900 * 1024


settings = Settings()
