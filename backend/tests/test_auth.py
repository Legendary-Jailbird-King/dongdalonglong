import pytest


def test_health_check(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "外卖管理系统 API",
        "version": "1.0.0",
    }


@pytest.mark.parametrize("role", ["customer", "merchant", "courier"])
def test_register_and_login_each_role(client, api_helpers, role):
    response = api_helpers["register"](client, role, f"{role}-user")
    assert response.status_code == 200
    assert response.json()["data"]["role"] == role

    data = api_helpers["login"](client, role, f"{role}-user")
    assert data["role"] == role
    assert data["access_token"]


def test_duplicate_name_is_rejected_within_same_role(client, api_helpers):
    assert api_helpers["register"](client, "customer", "same-name").status_code == 200
    response = api_helpers["register"](client, "customer", "same-name")
    assert response.status_code == 409
    assert response.json()["detail"] == "用户名已存在"


def test_same_name_is_allowed_across_roles(client, api_helpers):
    assert api_helpers["register"](client, "customer", "shared").status_code == 200
    assert api_helpers["register"](client, "merchant", "shared").status_code == 200


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"role": "admin", "name": "u", "password": "pass1234"}, "role"),
        ({"role": "customer", "name": "", "password": "pass1234"}, "name"),
        ({"role": "customer", "name": "u", "password": "123"}, "password"),
    ],
)
def test_registration_input_validation(client, payload, field):
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 422
    assert field in response.text


def test_login_rejects_unknown_user_and_wrong_password(client, api_helpers):
    missing = client.post(
        "/api/auth/login",
        json={"role": "customer", "name": "missing", "password": "pass1234"},
    )
    assert missing.status_code == 400

    api_helpers["register"](client, "customer", "known")
    wrong = client.post(
        "/api/auth/login",
        json={"role": "customer", "name": "known", "password": "wrong"},
    )
    assert wrong.status_code == 400


def test_protected_endpoint_requires_token(client):
    response = client.get("/api/customer/addresses")
    assert response.status_code == 403


def test_role_based_access_control(client, api_helpers):
    merchant_headers = api_helpers["auth_headers"](client, "merchant", "merchant-only")
    response = client.get("/api/customer/addresses", headers=merchant_headers)
    assert response.status_code == 403
    assert "需要 customer" in response.json()["detail"]


def test_invalid_token_is_rejected(client):
    response = client.get(
        "/api/customer/addresses",
        headers={"Authorization": "Bearer definitely-invalid"},
    )
    assert response.status_code == 401
