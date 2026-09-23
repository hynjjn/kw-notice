from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://kwnotice:kwnotice@localhost:5433/kwnotice"
    anthropic_api_key: str = ""
    attachment_dir: Path = Path("./var/attachments")

    # MVP 는 단일 사용자다. 이 이메일의 행이 읽음, 별표의 주인이 된다.
    default_user_email: str = "me@kw.ac.kr"
    # 프론트 개발 서버. 배포 시에는 CloudFront 도메인으로 바꾼다.
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]


settings = Settings()
