"""
商家路由：菜品管理（含软删除/上下架）、接单/拒单、指派骑手、空闲骑手查询。

状态流转：
  接单: 0 → 1
  拒单: 0 → 5
  指派骑手: 1 → 2 (同步骑手状态 0 → 1)
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Merchant, Dish, Orders, Courier
from app.schemas import (
    ApiResponse, DishCreate, DishUpdate, DishOut, StatusUpdateRequest,
)
from app.utils import get_current_merchant, parse_token_optional
from app.models import get_available_couriers_query
from app.ws_manager import manager
from app.service_utils import build_order_out

router = APIRouter(prefix="/api/merchant", tags=["商家"])


# ══════════════════════════════════════════════════════════════
# WebSocket 端点（商家 & 骑手共用入口）
# ══════════════════════════════════════════════════════════════

@router.websocket("/ws/{role}/{user_id}")
async def ws_endpoint(ws: WebSocket, role: str, user_id: int, token: str = ""):
    """
    WebSocket 长连接。

    客户端连接示例：
      ws://localhost:8000/api/merchant/ws/merchant/1?token=eyJ...
    """
    if not token:
        await ws.close(code=4001, reason="缺少鉴权 Token")
        return

    parsed = parse_token_optional(token)
    if not parsed or parsed[1] != role or parsed[0] != user_id:
        await ws.close(code=4003, reason="Token 无效或角色不匹配")
        return

    await manager.connect(ws, role, user_id)
    try:
        while True:
            # 保持连接，接收客户端心跳
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        manager.disconnect(ws, role, user_id)


# ══════════════════════════════════════════════════════════════
# 菜品管理 CRUD
# ══════════════════════════════════════════════════════════════
@router.get("/dishes", response_model=ApiResponse)
async def list_my_dishes(
    merchant: Merchant = Depends(get_current_merchant),
    db: AsyncSession = Depends(get_db),
):
    """商家查看自己的菜品列表（含已删除，方便恢复）。"""
    result = await db.execute(
        select(Dish)
        .where(Dish.merchant_id == merchant.id)
        .order_by(Dish.is_deleted, Dish.id.desc())
    )
    dishes = result.scalars().all()
    return ApiResponse(
        data=[{
            "id": d.id,
            "name": d.name,
            "price": str(d.price),
            "is_deleted": d.is_deleted,
            "is_active": d.is_active,
        } for d in dishes]
    )


@router.post("/dishes", response_model=ApiResponse)
async def add_dish(
    req: DishCreate,
    merchant: Merchant = Depends(get_current_merchant),
    db: AsyncSession = Depends(get_db),
):
    """新增菜品。"""
    dish = Dish(
        name=req.name,
        price=req.price,
        merchant_id=merchant.id,
    )
    db.add(dish)
    await db.commit()
    await db.refresh(dish)
    return ApiResponse(message="菜品添加成功", data=DishOut.model_validate(dish).model_dump())


@router.put("/dishes/{dish_id}", response_model=ApiResponse)
async def update_dish(
    dish_id: int,
    req: DishUpdate,
    merchant: Merchant = Depends(get_current_merchant),
    db: AsyncSession = Depends(get_db),
):
    """更新菜品信息（名称/价格/上下架）。"""
    dish = await db.get(Dish, dish_id)
    if not dish or dish.merchant_id != merchant.id:
        raise HTTPException(status_code=404, detail="菜品不存在")

    if req.name is not None:
        dish.name = req.name
    if req.price is not None:
        dish.price = req.price
    if req.is_active is not None:
        dish.is_active = req.is_active

    await db.commit()
    await db.refresh(dish)
    return ApiResponse(message="菜品更新成功", data=DishOut.model_validate(dish).model_dump())


@router.delete("/dishes/{dish_id}", response_model=ApiResponse)
async def soft_delete_dish(
    dish_id: int,
    merchant: Merchant = Depends(get_current_merchant),
    db: AsyncSession = Depends(get_db),
):
    """软删除菜品（is_deleted = 1），不影响历史订单。"""
    dish = await db.get(Dish, dish_id)
    if not dish or dish.merchant_id != merchant.id:
        raise HTTPException(status_code=404, detail="菜品不存在")
    if dish.is_deleted == 1:
        raise HTTPException(status_code=400, detail="菜品已被删除")

    dish.is_deleted = 1
    await db.commit()
    return ApiResponse(message="菜品已删除")


# ══════════════════════════════════════════════════════════════
# 订单管理
# ══════════════════════════════════════════════════════════════
@router.get("/orders", response_model=ApiResponse)
async def list_merchant_orders(
    merchant: Merchant = Depends(get_current_merchant),
    db: AsyncSession = Depends(get_db),
):
    """查看该商家的所有订单（最新在前）。"""
    result = await db.execute(
        select(Orders)
        .where(Orders.merchant_id == merchant.id)
        .order_by(Orders.order_time.desc())
    )
    orders = result.scalars().all()
    return ApiResponse(data=[build_order_out(o) for o in orders])


@router.put("/order/{order_id}/accept", response_model=ApiResponse)
async def accept_order(
    order_id: int,
    merchant: Merchant = Depends(get_current_merchant),
    db: AsyncSession = Depends(get_db),
):
    """商家接单：0 → 1。"""
    order = await db.get(Orders, order_id)
    if not order or order.merchant_id != merchant.id:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order.status != 0:
        raise HTTPException(status_code=400, detail="仅待处理(0)的订单可以接单")

    order.status = 1
    order.order_time = datetime.now()
    await db.commit()
    return ApiResponse(message="已接单")


@router.put("/order/{order_id}/reject", response_model=ApiResponse)
async def reject_order(
    order_id: int,
    merchant: Merchant = Depends(get_current_merchant),
    db: AsyncSession = Depends(get_db),
):
    """商家拒单：0 → 5。"""
    order = await db.get(Orders, order_id)
    if not order or order.merchant_id != merchant.id:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order.status != 0:
        raise HTTPException(status_code=400, detail="仅待处理(0)的订单可以拒单")

    order.status = 5
    order.order_time = datetime.now()
    await db.commit()
    return ApiResponse(message="已拒单")


@router.put("/order/{order_id}/assign", response_model=ApiResponse)
async def assign_courier(
    order_id: int,
    req: StatusUpdateRequest,
    merchant: Merchant = Depends(get_current_merchant),
    db: AsyncSession = Depends(get_db),
):
    """
    商家指派空闲骑手：1 → 2。

    约束：
      - 订单必须为「已接单」(1)
      - 骑手必须为空闲状态 (status=0)
      - 若无空闲骑手，必须报错阻断
      - 原子化：订单状态 + 骑手状态同步更新
    """
    if not req.courier_id:
        raise HTTPException(status_code=400, detail="请指定骑手 ID")

    order = await db.get(Orders, order_id)
    if not order or order.merchant_id != merchant.id:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order.status != 1:
        raise HTTPException(status_code=400, detail="仅已接单(1)的订单可以指派骑手")

    courier = await db.get(Courier, req.courier_id)
    if not courier:
        raise HTTPException(status_code=404, detail="骑手不存在")
    if courier.status != 0:
        raise HTTPException(status_code=400, detail="该骑手当前忙碌，请选择空闲骑手")

    # 原子化：订单状态 1→2，骑手 0→1
    order.status = 2
    order.courier_id = courier.id
    order.order_time = datetime.now()
    courier.status = 1

    await db.commit()

    # WebSocket：通知骑手有新任务
    await manager.send_to_courier(
        courier.id,
        {
            "type": "order_assigned",
            "title": "🛵 新派送任务",
            "body": f"订单 #{order.id} 已分配给您，请及时取餐派送！",
            "order_id": order.id,
            "timestamp": datetime.now().isoformat(),
        },
    )

    return ApiResponse(message="骑手指派成功")


# ══════════════════════════════════════════════════════════════
# 空闲骑手查询
# ══════════════════════════════════════════════════════════════
@router.get("/available-couriers", response_model=ApiResponse)
async def available_couriers(
    merchant: Merchant = Depends(get_current_merchant),
    db: AsyncSession = Depends(get_db),
):
    """查询所有空闲骑手（status=0），按名称排序。"""
    result = await db.execute(get_available_couriers_query())
    couriers = result.scalars().all()
    return ApiResponse(data=[{
        "id": c.id,
        "name": c.name,
        "status": c.status,
    } for c in couriers])
