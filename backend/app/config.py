"""
应用全局配置：数据库连接、JWT 密钥、CORS 跨域白名单。
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # ── 数据库 ────────────────────────────────────────────
    # 默认 MySQL（asyncmy）；若用 PostgreSQL 改为：
    # mysql+asyncmy://root:password@localhost:3306/takeaway
    # 开发环境默认 SQLite（零配置）；生产请改为 MySQL/PostgreSQL：
    # 例: mysql+asyncmy://root:password@127.0.0.1:3306/takeaway
    DATABASE_URL: str = "sqlite+aiosqlite:///./takeaway.db"

    # ── JWT ──────────────────────────────────────────────
    JWT_SECRET: str = "change-me-to-a-random-secret-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24  # 24 小时

    # ── CORS ─────────────────────────────────────────────
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",
    ]

    # ── App ──────────────────────────────────────────────
    APP_TITLE: str = "外卖管理系统 API"
    APP_VERSION: str = "1.0.0"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
