"""
核心数据库模型 (ORM Models) —— 共 7 张表。

表结构设计遵从规范：
  - 主外键、级联、索引显式声明
  - DECIMAL 金额、软删除标记、CheckConstraint 约束
  - SQLAlchemy ORM 事件: OrderDish 变更 → 自动重算 Orders.total
"""
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, DECIMAL, DateTime, ForeignKey,
    CheckConstraint, Index, event, select, func as sqlfunc, update,
)
from sqlalchemy.orm import relationship

from app.database import Base


# ══════════════════════════════════════════════════════════════
# 1. Customer  客户
# ══════════════════════════════════════════════════════════════
class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)

    # 关系
    orders = relationship("Orders", back_populates="customer", lazy="selectin")
    shipping_addresses = relationship(
        "Shipping", back_populates="customer", lazy="selectin"
    )


# ══════════════════════════════════════════════════════════════
# 2. Merchant  商家
# ══════════════════════════════════════════════════════════════
class Merchant(Base):
    __tablename__ = "merchants"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)

    # 关系
    dishes = relationship("Dish", back_populates="merchant", lazy="selectin")
    orders = relationship("Orders", back_populates="merchant", lazy="selectin")


# ══════════════════════════════════════════════════════════════
# 3. Courier  外卖骑手
# ══════════════════════════════════════════════════════════════
class Courier(Base):
    __tablename__ = "couriers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    status = Column(
        Integer, nullable=False, default=0,
        comment="0:空闲, 1:忙碌"
    )

    # 关系
    orders = relationship("Orders", back_populates="courier", lazy="selectin")


# ══════════════════════════════════════════════════════════════
# 4. Dish  菜品
# ══════════════════════════════════════════════════════════════
class Dish(Base):
    __tablename__ = "dishes"
    __table_args__ = (
        CheckConstraint("price >= 0", name="ck_dish_price_non_negative"),
        Index("idx_dish_merchant_active", "merchant_id", "is_deleted", "is_active"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, index=True)
    price = Column(DECIMAL(10, 2), nullable=False)
    merchant_id = Column(
        Integer, ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False
    )
    is_deleted = Column(Integer, nullable=False, default=0, comment="0:正常, 1:软删除")
    is_active = Column(Integer, nullable=False, default=1, comment="0:下架, 1:上架")

    # 关系
    merchant = relationship("Merchant", back_populates="dishes", lazy="selectin")


# ══════════════════════════════════════════════════════════════
# 5. Shipping  收货地址
# ══════════════════════════════════════════════════════════════
class Shipping(Base):
    __tablename__ = "shipping_addresses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(
        Integer, ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    address = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=False)
    is_deleted = Column(Integer, nullable=False, default=0, comment="0:正常, 1:软删除")

    # 关系
    customer = relationship("Customer", back_populates="shipping_addresses", lazy="selectin")


# ══════════════════════════════════════════════════════════════
# 6. Orders  订单
# ══════════════════════════════════════════════════════════════
class Orders(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(
        Integer, ForeignKey("customers.id"), nullable=False
    )
    merchant_id = Column(
        Integer, ForeignKey("merchants.id"), nullable=False
    )
    shipping_id = Column(
        Integer, ForeignKey("shipping_addresses.id"), nullable=False
    )
    courier_id = Column(
        Integer, ForeignKey("couriers.id"), nullable=True
    )
    total = Column(DECIMAL(10, 2), nullable=False, default=0)
    status = Column(
        Integer, nullable=False, default=0,
        comment="0:待处理, 1:已接单, 2:派送中, 3:已完成, 4:客户已取消, 5:商家已拒单"
    )
    order_time = Column(DateTime, nullable=False, default=datetime.now)

    # 关系
    customer = relationship("Customer", back_populates="orders", lazy="selectin")
    merchant = relationship("Merchant", back_populates="orders", lazy="selectin")
    courier = relationship("Courier", back_populates="orders", lazy="selectin")
    shipping = relationship("Shipping", lazy="selectin")
    order_dishes = relationship(
        "OrderDish", back_populates="order",
        cascade="all, delete-orphan", lazy="selectin"
    )


# ══════════════════════════════════════════════════════════════
# 7. OrderDish  订单-菜品关联（多对多中间表）
# ══════════════════════════════════════════════════════════════
class OrderDish(Base):
    __tablename__ = "order_dishes"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_orderdish_quantity_positive"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(
        Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    dish_id = Column(
        Integer, ForeignKey("dishes.id"), nullable=False
    )
    quantity = Column(Integer, nullable=False)

    # 关系
    order = relationship("Orders", back_populates="order_dishes", lazy="selectin")
    dish = relationship("Dish", lazy="selectin")


# ══════════════════════════════════════════════════════════════
# SQLAlchemy ORM 事件：明细变更 → 自动重算订单总额（Trigger 逻辑）
# ══════════════════════════════════════════════════════════════
def _recalc_order_total(connection, order_id: int):
    """原子化重新计算某订单的 total = SUM(price * quantity)。"""
    result = connection.execute(
        select(sqlfunc.sum(OrderDish.quantity * Dish.price))
        .select_from(OrderDish)
        .join(Dish, OrderDish.dish_id == Dish.id)
        .where(OrderDish.order_id == order_id)
    )
    total = result.scalar() or 0
    connection.execute(
        update(Orders).where(Orders.id == order_id).values(total=total)
    )


@event.listens_for(OrderDish, "after_insert")
def _od_after_insert(mapper, connection, target):
    _recalc_order_total(connection, target.order_id)


@event.listens_for(OrderDish, "after_update")
def _od_after_update(mapper, connection, target):
    _recalc_order_total(connection, target.order_id)


@event.listens_for(OrderDish, "after_delete")
def _od_after_delete(mapper, connection, target):
    _recalc_order_total(connection, target.order_id)


# ══════════════════════════════════════════════════════════════
# 辅助查询：空闲骑手视图逻辑（按名称排序）
# ══════════════════════════════════════════════════════════════
def get_available_couriers_query():
    """返回查询空闲骑手的 SELECT 语句（status == 0，按名称排序）。"""
    return (
        select(Courier)
        .where(Courier.status == 0)
        .order_by(Courier.name)
    )
