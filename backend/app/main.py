"""
FastAPI 应用入口：注册路由、WebSocket、CORS、启动事件。
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base


# ── 启动/关闭生命周期 ────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时：创建所有表（开发环境；生产环境请用 Alembic 迁移）
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # 关闭时：释放连接池
    await engine.dispose()


# ── 创建应用 ──────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_TITLE,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# ── CORS 跨域 ─────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── 注册路由 ──────────────────────────────────────────────
from app.routers.auth import router as auth_router          # noqa: E402
from app.routers.customer import router as customer_router  # noqa: E402
from app.routers.merchant import router as merchant_router  # noqa: E402
from app.routers.courier import router as courier_router    # noqa: E402

app.include_router(auth_router)
app.include_router(customer_router)
app.include_router(merchant_router)
app.include_router(courier_router)


# ── 根路径健康检查 ────────────────────────────────────────
@app.get("/", tags=["健康检查"])
async def root():
    return {"status": "ok", "service": settings.APP_TITLE, "version": settings.APP_VERSION}
