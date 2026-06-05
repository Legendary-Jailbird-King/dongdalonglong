"""
骑手路由：查看可抢订单、抢单、查看我的订单、确认送达（释放骑手状态）。

状态流转：
  抢单: 1 → 2（骑手 0 → 1）
  确认送达: 2 → 3（骑手 1 → 0）
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Courier, Orders
from app.schemas import ApiResponse
from app.utils import get_current_courier
from app.ws_manager import manager as ws_manager
from app.service_utils import build_order_out

router = APIRouter(prefix="/api/courier", tags=["骑手"])


# ══════════════════════════════════════════════════════════════
# 可抢订单（status=1，无骑手接单）
# ══════════════════════════════════════════════════════════════
@router.get("/available-orders", response_model=ApiResponse)
async def list_available_orders(
    courier: Courier = Depends(get_current_courier),
    db: AsyncSession = Depends(get_db),
):
    """骑手查看所有待抢订单（商家已接单但无骑手）。"""
    result = await db.execute(
        select(Orders)
        .where(Orders.status == 1, Orders.courier_id.is_(None))
        .order_by(Orders.order_time.desc())
    )
    orders = result.scalars().all()
    return ApiResponse(data=[build_order_out(o) for o in orders])


# ══════════════════════════════════════════════════════════════
# 抢单（1 → 2，骑手 0 → 1）
# ══════════════════════════════════════════════════════════════
@router.put("/order/{order_id}/pickup", response_model=ApiResponse)
async def pickup_order(
    order_id: int,
    courier: Courier = Depends(get_current_courier),
    db: AsyncSession = Depends(get_db),
):
    """
    骑手主动抢单：
      - 骑手必须空闲 (status=0)
      - 订单状态 1 → 2
      - 骑手状态 0 → 1
    """
    if courier.status != 0:
        raise HTTPException(status_code=400, detail="您当前忙碌，无法接单")

    order = await db.get(Orders, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order.status != 1:
        raise HTTPException(status_code=400, detail="该订单已被接单或不可抢")
    if order.courier_id is not None:
        raise HTTPException(status_code=400, detail="该订单已被其他骑手抢走")

    # 原子化：订单 1→2，骑手 0→1
    order.status = 2
    order.courier_id = courier.id
    order.order_time = datetime.now()
    courier.status = 1

    await db.commit()

    return ApiResponse(message="抢单成功，请及时取餐派送")


# ══════════════════════════════════════════════════════════════
# 我的派送订单
# ══════════════════════════════════════════════════════════════
@router.get("/orders", response_model=ApiResponse)
async def list_my_orders(
    courier: Courier = Depends(get_current_courier),
    db: AsyncSession = Depends(get_db),
):
    """骑手查看分配给自己的订单。"""
    result = await db.execute(
        select(Orders)
        .where(Orders.courier_id == courier.id)
        .order_by(Orders.order_time.desc())
    )
    orders = result.scalars().all()
    return ApiResponse(data=[build_order_out(o) for o in orders])


# ══════════════════════════════════════════════════════════════
# 确认送达（2 → 3，释放骑手）
# ══════════════════════════════════════════════════════════════
@router.put("/order/{order_id}/deliver", response_model=ApiResponse)
async def confirm_delivery(
    order_id: int,
    courier: Courier = Depends(get_current_courier),
    db: AsyncSession = Depends(get_db),
):
    """
    骑手确认送达：
      - 订单状态 2 → 3
      - 骑手状态 1 → 0（释放）
    """
    order = await db.get(Orders, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order.courier_id != courier.id:
        raise HTTPException(status_code=403, detail="该订单未分配给您")
    if order.status != 2:
        raise HTTPException(status_code=400, detail="仅派送中(2)的订单可以确认送达")

    # 原子化：订单 2→3，骑手 1→0
    order.status = 3
    order.order_time = datetime.now()
    courier.status = 0

    await db.commit()

    return ApiResponse(message="已确认送达，骑手状态已释放")
