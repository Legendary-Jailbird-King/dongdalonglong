"""
数据库引擎、异步会话工厂、Base 声明基类。
"""
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# ── 异步引擎 ──────────────────────────────────────────────
_engine_kwargs = dict(
    echo=False,
)

# SQLite 需特殊处理（禁用线程检查 & 连接池）
if "sqlite" in settings.DATABASE_URL:
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    _engine_kwargs.update(pool_size=20, max_overflow=10, pool_pre_ping=True)

engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs)

# ── 异步会话工厂 ──────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,   # 提交后属性不过期，避免异步懒加载问题
)


# ── 声明式基类 ────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """FastAPI 依赖注入：每个请求获取独立数据库会话。"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
