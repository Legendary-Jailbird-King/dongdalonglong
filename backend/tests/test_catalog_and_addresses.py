def test_customer_only_sees_active_non_deleted_dishes(client, business_setup):
    visible = client.get("/api/customer/dishes").json()["data"]
    assert [dish["id"] for dish in visible] == [business_setup["dish_id"]]

    response = client.put(
        f"/api/merchant/dishes/{business_setup['dish_id']}",
        headers=business_setup["merchant"],
        json={"is_active": 0},
    )
    assert response.status_code == 200
    assert client.get("/api/customer/dishes").json()["data"] == []

    client.put(
        f"/api/merchant/dishes/{business_setup['dish_id']}",
        headers=business_setup["merchant"],
        json={"is_active": 1},
    )
    client.delete(
        f"/api/merchant/dishes/{business_setup['dish_id']}",
        headers=business_setup["merchant"],
    )
    assert client.get("/api/customer/dishes").json()["data"] == []


def test_dish_price_and_status_validation(client, business_setup):
    negative = client.post(
        "/api/merchant/dishes",
        headers=business_setup["merchant"],
        json={"name": "bad", "price": -0.01},
    )
    assert negative.status_code == 422

    invalid_status = client.put(
        f"/api/merchant/dishes/{business_setup['dish_id']}",
        headers=business_setup["merchant"],
        json={"is_active": 2},
    )
    assert invalid_status.status_code == 422


def test_merchant_cannot_modify_another_merchants_dish(client, business_setup, api_helpers):
    other_headers = api_helpers["auth_headers"](client, "merchant", "merchant-b")
    response = client.put(
        f"/api/merchant/dishes/{business_setup['dish_id']}",
        headers=other_headers,
        json={"name": "越权修改"},
    )
    assert response.status_code == 404


def test_address_soft_delete_and_ownership(client, business_setup, api_helpers):
    other_headers = api_helpers["auth_headers"](client, "customer", "customer-b")
    forbidden = client.delete(
        f"/api/customer/addresses/{business_setup['address_id']}",
        headers=other_headers,
    )
    assert forbidden.status_code == 404

    deleted = client.delete(
        f"/api/customer/addresses/{business_setup['address_id']}",
        headers=business_setup["customer"],
    )
    assert deleted.status_code == 200
    assert client.get(
        "/api/customer/addresses", headers=business_setup["customer"]
    ).json()["data"] == []

    repeated = client.delete(
        f"/api/customer/addresses/{business_setup['address_id']}",
        headers=business_setup["customer"],
    )
    assert repeated.status_code == 400


def test_merchants_list_only_includes_merchants_with_active_dishes(client, business_setup):
    merchants = client.get("/api/customer/merchants").json()["data"]
    assert merchants == [
        {"id": business_setup["merchant_id"], "name": "merchant-a", "dish_count": 1}
    ]
