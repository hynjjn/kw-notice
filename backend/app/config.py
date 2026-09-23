from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://kwnotice:kwnotice@localhost:5433/kwnotice"
    anthropic_api_key: str = ""
    attachment_dir: Path = Path("./var/attachments")


settings = Settings()
