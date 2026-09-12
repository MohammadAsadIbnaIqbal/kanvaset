import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_and_login(client: AsyncClient):
    # 1. Register
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "charlie@example.com",
            "username": "charlie",
            "password": "strongPassword123!",
        },
    )
    assert reg_resp.status_code == 201
    data = reg_resp.json()
    assert "access_token" in data
    assert data["user"]["email"] == "charlie@example.com"
    assert data["user"]["username"] == "charlie"

    # 2. Duplicate registration fails
    dup_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "charlie@example.com",
            "username": "charlie2",
            "password": "password",
        },
    )
    assert dup_resp.status_code == 400
    assert "Email already registered" in dup_resp.json()["detail"]

    # 3. Login success
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "charlie@example.com",
            "password": "strongPassword123!",
        },
    )
    assert login_resp.status_code == 200
    token_data = login_resp.json()
    assert "access_token" in token_data
    token = token_data["access_token"]

    # 4. Profile /me
    me_resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["username"] == "charlie"

    # 5. Invalid credentials
    bad_login = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "charlie@example.com",
            "password": "wrongpassword",
        },
    )
    assert bad_login.status_code == 401
