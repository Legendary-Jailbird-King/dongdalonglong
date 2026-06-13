from concurrent.futures import ThreadPoolExecutor

import pytest


def _place_order(client, setup, dishes=None, merchant_id=None, shipping_id=None):
    return client.post(
        "/api/customer/order",
        headers=setup["customer"],
        json={
            "merchant_id": merchant_id or setup["merchant_id"],
            "shipping_id": shipping_id or setup["address_id"],
            "dishes": dishes or [{"dish_id": setup["dish_id"], "quantity": 2}],
        },
    )


def test_place_order_calculates_total_and_history(client, business_setup):
    response = _place_order(client, business_setup)
    assert response.status_code == 200
    assert response.json()["data"]["total"] == "37.00"

    orders = client.get(
        "/api/customer/orders", headers=business_setup["customer"]
    ).json()["data"]
    assert len(orders) == 1
    assert orders[0]["status"] == 0
    assert orders[0]["dish_summary"] == "测试套餐 x2"
    assert float(orders[0]["total"]) == 37.0


def test_order_rejects_deleted_address_without_creating_zombie_order(client, business_setup):
    client.delete(
        f"/api/customer/addresses/{business_setup['address_id']}",
        headers=business_setup["customer"],
    )
    response = _place_order(client, business_setup)
    assert response.status_code == 400
    assert client.get(
        "/api/customer/orders", headers=business_setup["customer"]
    ).json()["data"] == []


def test_order_rejects_unavailable_or_foreign_dish_and_rolls_back(
    client, business_setup, api_helpers
):
    client.put(
        f"/api/merchant/dishes/{business_setup['dish_id']}",
        headers=business_setup["merchant"],
        json={"is_active": 0},
    )
    unavailable = _place_order(client, business_setup)
    assert unavailable.status_code == 400

    other_merchant = api_helpers["auth_headers"](client, "merchant", "merchant-b")
    other_id = api_helpers["login"](client, "merchant", "merchant-b")["user_id"]
    other_dish = client.post(
        "/api/merchant/dishes",
        headers=other_merchant,
        json={"name": "其他商家菜品", "price": "9.00"},
    ).json()["data"]["id"]
    foreign = _place_order(
        client,
        business_setup,
        dishes=[{"dish_id": other_dish, "quantity": 1}],
        merchant_id=business_setup["merchant_id"],
    )
    assert foreign.status_code == 400
    assert other_id != business_setup["merchant_id"]
    assert client.get(
        "/api/customer/orders", headers=business_setup["customer"]
    ).json()["data"] == []


def test_order_rejects_another_customers_address(client, business_setup, api_helpers):
    other = api_helpers["auth_headers"](client, "customer", "customer-b")
    address = client.post(
        "/api/customer/addresses",
        headers=other,
        json={"address": "他人地址", "phone": "13900000000"},
    ).json()["data"]["id"]
    response = _place_order(client, business_setup, shipping_id=address)
    assert response.status_code == 403


def test_customer_can_cancel_only_pending_own_order(client, pending_order, api_helpers):
    other = api_helpers["auth_headers"](client, "customer", "customer-b")
    forbidden = client.put(
        f"/api/customer/order/{pending_order['order_id']}/cancel", headers=other
    )
    assert forbidden.status_code == 404

    cancelled = client.put(
        f"/api/customer/order/{pending_order['order_id']}/cancel",
        headers=pending_order["customer"],
    )
    assert cancelled.status_code == 200

    repeated = client.put(
        f"/api/customer/order/{pending_order['order_id']}/cancel",
        headers=pending_order["customer"],
    )
    assert repeated.status_code == 400


def test_complete_pickup_delivery_lifecycle(client, pending_order):
    accepted = client.put(
        f"/api/merchant/order/{pending_order['order_id']}/accept",
        headers=pending_order["merchant"],
    )
    assert accepted.status_code == 200

    picked_up = client.put(
        f"/api/courier/order/{pending_order['order_id']}/pickup",
        headers=pending_order["courier"],
    )
    assert picked_up.status_code == 200
    assert client.get(
        "/api/merchant/available-couriers", headers=pending_order["merchant"]
    ).json()["data"] == []

    delivered = client.put(
        f"/api/courier/order/{pending_order['order_id']}/deliver",
        headers=pending_order["courier"],
    )
    assert delivered.status_code == 200
    available = client.get(
        "/api/merchant/available-couriers", headers=pending_order["merchant"]
    ).json()["data"]
    assert [courier["name"] for courier in available] == ["courier-a"]


def test_rejected_order_cannot_be_accepted_or_picked_up(client, pending_order):
    rejected = client.put(
        f"/api/merchant/order/{pending_order['order_id']}/reject",
        headers=pending_order["merchant"],
    )
    assert rejected.status_code == 200
    assert client.put(
        f"/api/merchant/order/{pending_order['order_id']}/accept",
        headers=pending_order["merchant"],
    ).status_code == 400
    assert client.put(
        f"/api/courier/order/{pending_order['order_id']}/pickup",
        headers=pending_order["courier"],
    ).status_code == 400


def test_merchant_can_assign_idle_courier(client, pending_order):
    client.put(
        f"/api/merchant/order/{pending_order['order_id']}/accept",
        headers=pending_order["merchant"],
    )
    courier_id = client.get(
        "/api/merchant/available-couriers", headers=pending_order["merchant"]
    ).json()["data"][0]["id"]
    assigned = client.put(
        f"/api/merchant/order/{pending_order['order_id']}/assign",
        headers=pending_order["merchant"],
        json={"courier_id": courier_id},
    )
    assert assigned.status_code == 200

    courier_orders = client.get(
        "/api/courier/orders", headers=pending_order["courier"]
    ).json()["data"]
    assert courier_orders[0]["status"] == 2


@pytest.mark.concurrency
@pytest.mark.xfail(
    reason="DEF-001: pickup uses read-then-write without an atomic conditional update",
    strict=True,
)
def test_only_one_courier_can_win_concurrent_pickup(client, pending_order, api_helpers):
    courier_b = api_helpers["auth_headers"](client, "courier", "courier-b")
    client.put(
        f"/api/merchant/order/{pending_order['order_id']}/accept",
        headers=pending_order["merchant"],
    )

    def pickup(headers):
        return client.put(
            f"/api/courier/order/{pending_order['order_id']}/pickup", headers=headers
        ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(pickup, [pending_order["courier"], courier_b]))

    assert sorted(statuses) == [200, 400]
