"""
顾客路由：菜品浏览、地址簿（软删除）、核心：事务下单（含原子回滚）、历史订单、取消订单。

下单全生命周期状态机：
  POST /api/customer/order   → 原子事务：校验→插入 Orders→插入 OrderDish→计算 total
  PUT  /api/customer/order/{id}/cancel  → 0→4（仅待处理时可取消）
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, AsyncSessionLocal
from app.models import Customer, Dish, Shipping, Orders, OrderDish, Merchant
from app.schemas import (
    ApiResponse, DishOut, ShippingCreate, ShippingOut, OrderCreateRequest,
)
from app.utils import get_current_customer
from app.ws_manager import manager as ws_manager
from app.service_utils import build_order_out

router = APIRouter(prefix="/api/customer", tags=["顾客"])


# ══════════════════════════════════════════════════════════════
# 商家列表
# ══════════════════════════════════════════════════════════════
@router.get("/merchants", response_model=ApiResponse)
async def list_merchants(db: AsyncSession = Depends(get_db)):
    """获取有在售菜品的商家列表及其菜品数量。"""
    from sqlalchemy import func as sqlfunc
    result = await db.execute(
        select(
            Merchant.id,
            Merchant.name,
            sqlfunc.count(Dish.id).label("dish_count"),
        )
        .join(Dish, Dish.merchant_id == Merchant.id)
        .where(Dish.is_deleted == 0, Dish.is_active == 1)
        .group_by(Merchant.id, Merchant.name)
        .order_by(Merchant.id)
    )
    merchants = [
        {"id": r.id, "name": r.name, "dish_count": r.dish_count}
        for r in result.all()
    ]
    return ApiResponse(data=merchants)


# ══════════════════════════════════════════════════════════════
# 菜品浏览（过滤已删除 & 已上架）
# ══════════════════════════════════════════════════════════════
@router.get("/dishes", response_model=ApiResponse)
async def list_dishes(
    merchant_id: int = None,
    db: AsyncSession = Depends(get_db),
):
    """顾客浏览菜品：只展示 is_deleted=0 AND is_active=1 的菜品。"""
    q = (
        select(Dish)
        .where(Dish.is_deleted == 0, Dish.is_active == 1)
    )
    if merchant_id:
        q = q.where(Dish.merchant_id == merchant_id)
    q = q.order_by(Dish.merchant_id, Dish.name)

    result = await db.execute(q)
    dishes = result.scalars().all()

    return ApiResponse(
        data=[DishOut.model_validate(d).model_dump() for d in dishes]
    )


# ══════════════════════════════════════════════════════════════
# 地址簿 CRUD（软删除）
# ══════════════════════════════════════════════════════════════
@router.get("/addresses", response_model=ApiResponse)
async def list_addresses(
    customer: Customer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
):
    """获取当前顾客未删除的地址列表。"""
    result = await db.execute(
        select(Shipping)
        .where(Shipping.customer_id == customer.id, Shipping.is_deleted == 0)
        .order_by(Shipping.id.desc())
    )
    addresses = result.scalars().all()
    return ApiResponse(
        data=[ShippingOut.model_validate(a).model_dump() for a in addresses]
    )


@router.post("/addresses", response_model=ApiResponse)
async def add_address(
    req: ShippingCreate,
    customer: Customer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
):
    """新增收货地址。"""
    addr = Shipping(
        customer_id=customer.id,
        address=req.address,
        phone=req.phone,
    )
    db.add(addr)
    await db.commit()
    await db.refresh(addr)
    return ApiResponse(
        code=200,
        message="地址添加成功",
        data=ShippingOut.model_validate(addr).model_dump(),
    )


@router.delete("/addresses/{address_id}", response_model=ApiResponse)
async def delete_address(
    address_id: int,
    customer: Customer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
):
    """软删除地址（is_deleted = 1），不影响历史订单外键。"""
    addr = await db.get(Shipping, address_id)
    if not addr or addr.customer_id != customer.id:
        raise HTTPException(status_code=404, detail="地址不存在")
    if addr.is_deleted == 1:
        raise HTTPException(status_code=400, detail="地址已被删除")

    addr.is_deleted = 1
    await db.commit()
    return ApiResponse(message="地址已删除")


# ══════════════════════════════════════════════════════════════
# 🛒 核心：事务下单（原子化）
# ══════════════════════════════════════════════════════════════
@router.post("/order", response_model=ApiResponse)
async def place_order(
    req: OrderCreateRequest,
    customer: Customer = Depends(get_current_customer),
):
    """
    下单接口 —— 显式异步事务 (begin)。

    流程：
      1. 校验地址有效性（存在、归属、未删除）
      2. 校验菜品有效性（存在、未删除、已上架、属于目标商家）
      3. 插入 Orders 主记录（status=0）
      4. 循环插入 OrderDish 明细 → ORM 事件自动计算 total
      5. 任何异常 → ROLLBACK（杜绝僵尸订单）
      6. 提交后 WebSocket 推送提醒对应商家
    """
    async with AsyncSessionLocal() as db:
        try:
            async with db.begin():
                # ── 1. 校验地址 ────────────────────────────
                shipping = await db.get(Shipping, req.shipping_id)
                if not shipping:
                    raise HTTPException(status_code=404, detail="收货地址不存在")
                if shipping.customer_id != customer.id:
                    raise HTTPException(status_code=403, detail="收货地址不属于当前顾客")
                if shipping.is_deleted == 1:
                    raise HTTPException(status_code=400, detail="收货地址已被删除")

                # ── 2. 校验菜品 ────────────────────────────
                if len(req.dishes) == 0:
                    raise HTTPException(status_code=400, detail="请至少选择一个菜品")

                dish_ids = [item.dish_id for item in req.dishes]
                result = await db.execute(
                    select(Dish).where(Dish.id.in_(dish_ids))
                )
                dish_map = {d.id: d for d in result.scalars().all()}

                for item in req.dishes:
                    dish = dish_map.get(item.dish_id)
                    if not dish:
                        raise HTTPException(
                            status_code=404,
                            detail=f"菜品 #{item.dish_id} 不存在"
                        )
                    if dish.is_deleted == 1:
                        raise HTTPException(
                            status_code=400,
                            detail=f"菜品「{dish.name}」已被删除"
                        )
                    if dish.is_active == 0:
                        raise HTTPException(
                            status_code=400,
                            detail=f"菜品「{dish.name}」已下架"
                        )
                    if dish.merchant_id != req.merchant_id:
                        raise HTTPException(
                            status_code=400,
                            detail=f"菜品「{dish.name}」不属于该商家"
                        )

                # ── 3. 插入订单主记录 ──────────────────────
                order = Orders(
                    customer_id=customer.id,
                    merchant_id=req.merchant_id,
                    shipping_id=req.shipping_id,
                    status=0,  # 待处理
                    total=0,   # 初始 0，由 ORM 事件自动重算
                    order_time=datetime.now(),
                )
                db.add(order)
                await db.flush()  # 获取 order.id

                # ── 4. 插入订单明细 ────────────────────────
                for item in req.dishes:
                    od = OrderDish(
                        order_id=order.id,
                        dish_id=item.dish_id,
                        quantity=item.quantity,
                    )
                    db.add(od)

                await db.flush()  # 触发 after_insert 事件 → 自动计算 total

                # ── 刷新以获取计算后的 total ───────────────
                await db.refresh(order)

            # ── 事务提交成功（__aexit__ 自动 commit） ──────

            # ── 5. WebSocket 推送：通知商家 ────────────────
            await ws_manager.send_to_merchant(
                req.merchant_id,
                {
                    "type": "new_order",
                    "title": "🔔 新订单提醒",
                    "body": f"您有新的外卖订单（#{order.id}），请及时处理！",
                    "order_id": order.id,
                    "timestamp": datetime.now().isoformat(),
                },
            )

            return ApiResponse(
                code=200,
                message="下单成功",
                data={"order_id": order.id, "total": str(order.total)},
            )

        except HTTPException:
            raise  # 直接透传 HTTPException，FastAPI 会处理
        except Exception as e:
            # 任何未预期的异常 → 事务已由 __aexit__ 自动 ROLLBACK
            raise HTTPException(status_code=500, detail=f"下单失败：{str(e)}")


# ══════════════════════════════════════════════════════════════
# 历史订单
# ══════════════════════════════════════════════════════════════
@router.get("/orders", response_model=ApiResponse)
async def list_orders(
    customer: Customer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
):
    """顾客历史订单（含菜品详情拼接）。"""
    result = await db.execute(
        select(Orders)
        .where(Orders.customer_id == customer.id)
        .order_by(Orders.order_time.desc())
    )
    orders = result.scalars().all()

    return ApiResponse(
        data=[build_order_out(o) for o in orders]
    )


# ══════════════════════════════════════════════════════════════
# 取消订单（0 → 4）
# ══════════════════════════════════════════════════════════════
@router.put("/order/{order_id}/cancel", response_model=ApiResponse)
async def cancel_order(
    order_id: int,
    customer: Customer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
):
    """客户取消订单：仅 status=0（待处理）时可取消。"""
    order = await db.get(Orders, order_id)
    if not order or order.customer_id != customer.id:
        raise HTTPException(status_code=404, detail="订单不存在")

    if order.status != 0:
        raise HTTPException(
            status_code=400,
            detail=f"当前订单状态为「{order.status}」，无法取消（仅待处理时可取消）"
        )

    order.status = 4
    order.order_time = datetime.now()  # 状态时间戳自动更新
    await db.commit()

    # WebSocket：通知商家订单已取消
    await ws_manager.send_to_merchant(
        order.merchant_id,
        {
            "type": "order_cancelled",
            "title": "📋 订单已取消",
            "body": f"订单 #{order.id} 已被顾客取消。",
            "order_id": order.id,
            "timestamp": datetime.now().isoformat(),
        },
    )

    return ApiResponse(message="订单已取消")
