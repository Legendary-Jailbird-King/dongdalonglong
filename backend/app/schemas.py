"""
Pydantic 请求/响应校验模型。

覆盖：
  - 统一响应格式
  - 各端注册 / 登录
  - 菜品 CRUD、地址簿
  - 下单（含嵌套明细）、订单列表、状态流转
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Any

from pydantic import BaseModel, Field, field_validator


# ══════════════════════════════════════════════════════════════
# 统一响应信封
# ══════════════════════════════════════════════════════════════
class ApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: Any = None


# ══════════════════════════════════════════════════════════════
# 认证
# ══════════════════════════════════════════════════════════════
class RegisterRequest(BaseModel):
    role: str = Field(..., pattern="^(customer|merchant|courier)$")
    name: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=4, max_length=128)


class LoginRequest(BaseModel):
    role: str = Field(..., pattern="^(customer|merchant|courier)$")
    name: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: int
    user_name: str


# ══════════════════════════════════════════════════════════════
# 菜品
# ══════════════════════════════════════════════════════════════
class DishCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    price: Decimal = Field(..., ge=0, max_digits=10, decimal_places=2)

    @field_validator("price", mode="before")
    @classmethod
    def price_to_decimal(cls, v):
        return Decimal(str(v))


class DishUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    price: Optional[Decimal] = Field(None, ge=0, max_digits=10, decimal_places=2)
    is_active: Optional[int] = Field(None, ge=0, le=1)

    @field_validator("price", mode="before")
    @classmethod
    def price_to_decimal(cls, v):
        if v is not None:
            return Decimal(str(v))
        return v


class DishOut(BaseModel):
    id: int
    name: str
    price: Decimal
    merchant_id: int
    is_active: int

    class Config:
        from_attributes = True


# ══════════════════════════════════════════════════════════════
# 收货地址
# ══════════════════════════════════════════════════════════════
class ShippingCreate(BaseModel):
    address: str = Field(..., min_length=1, max_length=255)
    phone: str = Field(..., min_length=1, max_length=20)


class ShippingOut(BaseModel):
    id: int
    customer_id: int
    address: str
    phone: str

    class Config:
        from_attributes = True


# ══════════════════════════════════════════════════════════════
# 下单
# ══════════════════════════════════════════════════════════════
class OrderDishItem(BaseModel):
    dish_id: int = Field(..., gt=0)
    quantity: int = Field(..., gt=0)


class OrderCreateRequest(BaseModel):
    merchant_id: int = Field(..., gt=0)
    shipping_id: int = Field(..., gt=0)
    dishes: List[OrderDishItem] = Field(..., min_length=1)


# ── 订单中的菜品明细 ──
class OrderDishDetailOut(BaseModel):
    dish_id: int
    dish_name: str
    price: Decimal
    quantity: int
    subtotal: Decimal  # price * quantity

    class Config:
        from_attributes = True


# ── 订单列表项 ──
class OrderOut(BaseModel):
    id: int
    customer_id: int
    customer_name: str = ""
    merchant_id: int
    merchant_name: str = ""
    shipping_id: int
    shipping_address: str = ""
    shipping_phone: str = ""
    courier_id: Optional[int] = None
    courier_name: str = ""
    total: Decimal
    status: int
    status_text: str = ""
    order_time: datetime
    dishes_detail: List[OrderDishDetailOut] = []
    dish_summary: str = ""  # "黄金炒饭 x2, 冰镇可乐 x1"

    class Config:
        from_attributes = True


# ── 状态变更请求 ──
class StatusUpdateRequest(BaseModel):
    """用于商家指派骑手等场景。"""
    courier_id: Optional[int] = None


# ── WebSocket 推送消息 ──
class WsMessage(BaseModel):
    type: str  # "new_order" | "order_accepted" | "order_assigned" | "order_delivered" | "order_cancelled" | "order_rejected"
    title: str
    body: str
    order_id: int
    timestamp: datetime = Field(default_factory=datetime.now)
