import asyncio
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text


TEST_DB = Path(__file__).parent / "test_takeaway.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB.as_posix()}"
os.environ["JWT_SECRET"] = "test-only-secret"

from app.database import engine  # noqa: E402
from app.main import app  # noqa: E402


async def _truncate_database():
    async with engine.begin() as conn:
        await conn.execute(text("PRAGMA foreign_keys=OFF"))
        for table in (
            "order_dishes",
            "orders",
            "shipping_addresses",
            "dishes",
            "couriers",
            "merchants",
            "customers",
        ):
            await conn.execute(text(f"DELETE FROM {table}"))
        await conn.execute(text("PRAGMA foreign_keys=ON"))


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def clean_database(client):
    asyncio.run(_truncate_database())
    yield


def register(client, role, name, password="pass1234"):
    return client.post(
        "/api/auth/register",
        json={"role": role, "name": name, "password": password},
    )


def login(client, role, name, password="pass1234"):
    response = client.post(
        "/api/auth/login",
        json={"role": role, "name": name, "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def auth_headers(client, role, name, password="pass1234"):
    register_response = register(client, role, name, password)
    assert register_response.status_code == 200, register_response.text
    token = login(client, role, name, password)["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def api_helpers():
    return {
        "register": register,
        "login": login,
        "auth_headers": auth_headers,
    }


@pytest.fixture
def business_setup(client, api_helpers):
    auth = api_helpers["auth_headers"]
    customer_headers = auth(client, "customer", "customer-a")
    merchant_headers = auth(client, "merchant", "merchant-a")
    courier_headers = auth(client, "courier", "courier-a")

    address = client.post(
        "/api/customer/addresses",
        headers=customer_headers,
        json={"address": "软件园 1 号", "phone": "13800000000"},
    ).json()["data"]
    dish = client.post(
        "/api/merchant/dishes",
        headers=merchant_headers,
        json={"name": "测试套餐", "price": "18.50"},
    ).json()["data"]
    merchant_id = api_helpers["login"](client, "merchant", "merchant-a")["user_id"]

    return {
        "customer": customer_headers,
        "merchant": merchant_headers,
        "courier": courier_headers,
        "address_id": address["id"],
        "dish_id": dish["id"],
        "merchant_id": merchant_id,
    }


@pytest.fixture
def pending_order(client, business_setup):
    response = client.post(
        "/api/customer/order",
        headers=business_setup["customer"],
        json={
            "merchant_id": business_setup["merchant_id"],
            "shipping_id": business_setup["address_id"],
            "dishes": [{"dish_id": business_setup["dish_id"], "quantity": 2}],
        },
    )
    assert response.status_code == 200, response.text
    return {**business_setup, "order_id": response.json()["data"]["order_id"]}
