from decimal import Decimal

import pytest
from fastapi import WebSocketDisconnect

from app.models import Courier
from app.service_utils import STATUS_TEXT
from app.utils import create_access_token, decode_access_token, hash_password, verify_password


def test_password_hash_and_jwt_round_trip():
    hashed = hash_password("pass1234")
    assert hashed != "pass1234"
    assert verify_password("pass1234", hashed)
    assert not verify_password("wrong", hashed)

    token = create_access_token(7, "customer", "tester")
    payload = decode_access_token(token)
    assert payload["sub"] == "7"
    assert payload["role"] == "customer"
    assert payload["name"] == "tester"


def test_all_order_statuses_have_labels():
    assert STATUS_TEXT == {
        0: "待处理",
        1: "已接单",
        2: "派送中",
        3: "已完成",
        4: "客户已取消",
        5: "商家已拒单",
    }


@pytest.mark.websocket
def test_websocket_accepts_matching_identity(client, api_helpers):
    api_helpers["register"](client, "merchant", "ws-merchant")
    data = api_helpers["login"](client, "merchant", "ws-merchant")
    with client.websocket_connect(
        f"/api/merchant/ws/merchant/{data['user_id']}?token={data['access_token']}"
    ) as websocket:
        websocket.send_text("ping")


@pytest.mark.websocket
def test_websocket_rejects_missing_or_mismatched_token(client, api_helpers):
    with pytest.raises(WebSocketDisconnect) as missing:
        with client.websocket_connect("/api/merchant/ws/merchant/1"):
            pass
    assert missing.value.code == 4001

    api_helpers["register"](client, "customer", "ws-customer")
    data = api_helpers["login"](client, "customer", "ws-customer")
    with pytest.raises(WebSocketDisconnect) as mismatch:
        with client.websocket_connect(
            f"/api/merchant/ws/merchant/{data['user_id']}?token={data['access_token']}"
        ):
            pass
    assert mismatch.value.code == 4003
