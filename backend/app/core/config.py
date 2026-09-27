from functools import lru_cache
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "NZ-Golf-CRM"
    app_env: str = "local"
    debug: bool = True

    database_url: str = "postgresql+psycopg://golf:golf@localhost:5432/golf_crm"

    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 120

    # 初始超级管理员（种子脚本使用）
    first_superuser_username: str = "admin"
    first_superuser_password: str = "admin123456"
    first_superuser_full_name: str = "Association Super Admin"

    cors_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:5173",
        "http://localhost:5174",
    ]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, v):
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    @field_validator("database_url", mode="before")
    @classmethod
    def _normalize_db_scheme(cls, v):
        # 部署平台（Render/Neon 等）给的连接串通常是裸 postgresql://，
        # 这里统一补上 SQLAlchemy 需要的 +psycopg 驱动前缀，免得每次手动改。
        if isinstance(v, str):
            if v.startswith("postgres://"):
                return "postgresql+psycopg://" + v[len("postgres://"):]
            if v.startswith("postgresql://"):
                return "postgresql+psycopg://" + v[len("postgresql://"):]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
