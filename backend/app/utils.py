"""
工具函数：密码哈希、JWT 签发与验证、角色权限依赖注入。
"""
from datetime import datetime, timedelta
from typing import Tuple

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import Customer, Merchant, Courier

# ── 密码哈希 ──────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ── JWT ───────────────────────────────────────────────────
def create_access_token(user_id: int, role: str, name: str) -> str:
    """生成 JWT，payload 中携带 user_id / role / name。"""
    expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "role": role,
        "name": name,
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """解密并返回 payload；失败时抛出 JWTError。"""
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])


# ── HTTP Bearer 提取器 ────────────────────────────────────
security = HTTPBearer()


# ── 角色依赖注入 ─────────────────────────────────────────
async def get_current_customer(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Customer:
    """校验 Token 并返回当前登录的 Customer 实例。"""
    payload = _verify_token(credentials, "customer")
    user = await db.get(Customer, int(payload["sub"]))
    if not user:
        raise HTTPException(status_code=401, detail="顾客账户不存在")
    return user


async def get_current_merchant(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Merchant:
    """校验 Token 并返回当前登录的 Merchant 实例。"""
    payload = _verify_token(credentials, "merchant")
    user = await db.get(Merchant, int(payload["sub"]))
    if not user:
        raise HTTPException(status_code=401, detail="商家账户不存在")
    return user


async def get_current_courier(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Courier:
    """校验 Token 并返回当前登录的 Courier 实例。"""
    payload = _verify_token(credentials, "courier")
    user = await db.get(Courier, int(payload["sub"]))
    if not user:
        raise HTTPException(status_code=401, detail="骑手账户不存在")
    return user


def _verify_token(credentials: HTTPAuthorizationCredentials, required_role: str) -> dict:
    """统一校验 Token 有效性与角色匹配。"""
    try:
        payload = decode_access_token(credentials.credentials)
    except JWTError:
        raise HTTPException(status_code=401, detail="Token 无效或已过期")

    if payload.get("role") != required_role:
        raise HTTPException(
            status_code=403,
            detail=f"权限不足：当前 Token 角色为 {payload.get('role')}，需要 {required_role}",
        )
    return payload


# ── 通用：从 Token 解析当前用户信息（用于 WebSocket） ──────
def parse_token_optional(token: str) -> Tuple[int, str, str] | None:
    """从 Token 解析 (user_id, role, name)；失败返回 None。"""
    try:
        payload = decode_access_token(token)
        return int(payload["sub"]), payload["role"], payload["name"]
    except (JWTError, KeyError, ValueError):
        return None
