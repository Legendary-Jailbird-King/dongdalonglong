"""
服务层共享工具：订单详情拼装（供多端路由复用）。
"""
from decimal import Decimal
from typing import List

from app.schemas import OrderDishDetailOut

# ── 状态码 → 中文 ─────────────────────────────────────────
STATUS_TEXT = {
    0: "待处理",
    1: "已接单",
    2: "派送中",
    3: "已完成",
    4: "客户已取消",
    5: "商家已拒单",
}


def build_order_out(order) -> dict:
    """将 ORM Order 对象拼装为前端友好的字典。

    包含：
      - 餐品详情扁平化字符串 "黄金炒饭 x2, 冰镇可乐 x1"
      - 各菜品明细（含小计）
    """
    from app.models import Orders  # 懒加载，避免循环导入

    details: List[OrderDishDetailOut] = []
    summary_parts: List[str] = []

    for od in order.order_dishes:
        dish = od.dish
        if dish:
            price = float(dish.price) if dish.price else 0
            details.append(OrderDishDetailOut(
                dish_id=dish.id,
                dish_name=dish.name,
                price=dish.price,
                quantity=od.quantity,
                subtotal=Decimal(str(price * od.quantity)),
            ))
            summary_parts.append(f"{dish.name} x{od.quantity}")

    return {
        "id": order.id,
        "customer_id": order.customer_id,
        "customer_name": order.customer.name if order.customer else "",
        "merchant_id": order.merchant_id,
        "merchant_name": order.merchant.name if order.merchant else "",
        "shipping_id": order.shipping_id,
        "shipping_address": order.shipping.address if order.shipping else "",
        "shipping_phone": order.shipping.phone if order.shipping else "",
        "courier_id": order.courier_id,
        "courier_name": order.courier.name if order.courier else "",
        "total": float(order.total) if order.total else 0,
        "status": order.status,
        "status_text": STATUS_TEXT.get(order.status, "未知"),
        "order_time": order.order_time.isoformat() if order.order_time else None,
        "dishes_detail": [d.model_dump() for d in details],
        "dish_summary": ", ".join(summary_parts),
    }
