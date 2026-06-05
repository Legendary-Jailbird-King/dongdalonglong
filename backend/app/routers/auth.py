"""
认证路由：统一注册、多端登录、Token 派发。
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Customer, Merchant, Courier
from app.schemas import (
    RegisterRequest, LoginRequest, TokenResponse, ApiResponse,
)
from app.utils import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/api/auth", tags=["认证"])


# ── 注册 ──────────────────────────────────────────────────
@router.post("/register", response_model=ApiResponse)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """多端统一注册：根据 role 写入对应表。"""
    model_map = {
        "customer": Customer,
        "merchant": Merchant,
        "courier": Courier,
    }
    model = model_map[req.role]

    # 检查同名用户
    existing = await db.execute(
        select(model).where(model.name == req.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="用户名已存在")

    user = model(name=req.name, password_hash=hash_password(req.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return ApiResponse(
        code=200,
        message="注册成功",
        data={"user_id": user.id, "name": user.name, "role": req.role},
    )


# ── 登录 ──────────────────────────────────────────────────
@router.post("/login", response_model=ApiResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    """多端统一登录，返回 JWT Token。"""
    model_map = {
        "customer": Customer,
        "merchant": Merchant,
        "courier": Courier,
    }
    model = model_map[req.role]

    result = await db.execute(select(model).where(model.name == req.name))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=400, detail="用户不存在，请先注册")
    if not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=400, detail="密码错误")

    token = create_access_token(user.id, req.role, user.name)

    return ApiResponse(
        code=200,
        message="登录成功",
        data=TokenResponse(
            access_token=token,
            role=req.role,
            user_id=user.id,
            user_name=user.name,
        ).model_dump(),
    )
