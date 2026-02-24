"""Auth-related functional tests: registration, login, token lifecycle, errors."""

from .conftest import (
    TS, PASSWORD, NEW_PASSWORD, S,
    section, check, register, login,
)


def test_health():
    section("Health Checks")
    check("Liveness probe", "GET", "/health", 200)
    check("Readiness probe", "GET", "/health/ready", 200)
    check("Detailed health", "GET", "/health/detailed", 200)


def test_auth_register_login():
    section("Auth: Registration & Login")
    email1 = f"func-{TS}-1@agentguard.dev"
    email2 = f"func-{TS}-2@agentguard.dev"
    S["email1"] = email1
    S["email2"] = email2

    tokens1 = register(email1, "Func Test 1", f"FuncOrg-{TS}-1")
    if tokens1:
        S["t1"] = tokens1["access_token"]
        S["r1"] = tokens1["refresh_token"]

    tokens2 = register(email2, "Func Test 2", f"FuncOrg-{TS}-2")
    if tokens2:
        S["t2"] = tokens2["access_token"]
        S["r2"] = tokens2["refresh_token"]

    login_tokens = login(email1)
    if login_tokens:
        S["t1"] = login_tokens["access_token"]
        S["r1"] = login_tokens["refresh_token"]

    login_tokens2 = login(email2)
    if login_tokens2:
        S["t2"] = login_tokens2["access_token"]
        S["r2"] = login_tokens2["refresh_token"]

    r = check("Get /me", "GET", "/api/v1/auth/me", 200, token=S.get("t1"))
    if r and r.status_code == 200:
        data = r.json()
        S["org1_id"] = data.get("organization", {}).get("id")

    # Duplicate
    check(
        "Duplicate register",
        "POST",
        "/api/v1/auth/register",
        409,
        json={"email": email1, "password": PASSWORD, "full_name": "Dup", "org_name": "Dup"},
    )


def test_auth_token_lifecycle():
    section("Auth: Token Lifecycle")
    old_refresh = ""
    r = check(
        "Refresh token",
        "POST",
        "/api/v1/auth/refresh",
        200,
        json={"refresh_token": S.get("r1", "")},
    )
    if r and r.status_code == 200:
        data = r.json()
        S["t1"] = data["access_token"]
        old_refresh = S["r1"]
        S["r1"] = data["refresh_token"]

    r = check(
        "Change password",
        "POST",
        "/api/v1/auth/change-password",
        200,
        json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
        token=S.get("t1"),
    )
    if r and r.status_code == 200:
        data = r.json()
        S["t1"] = data["access_token"]
        S["r1"] = data["refresh_token"]

    check(
        "Old refresh token fails",
        "POST",
        "/api/v1/auth/refresh",
        401,
        json={"refresh_token": old_refresh or "invalid"},
    )


def test_auth_errors():
    section("Auth: Error Cases")
    check(
        "Wrong password",
        "POST",
        "/api/v1/auth/login",
        401,
        json={"email": S.get("email1", "x@x.com"), "password": "WrongPass1!xxxx"},
    )
    check(
        "Nonexistent email",
        "POST",
        "/api/v1/auth/login",
        401,
        json={"email": "nobody@nowhere.dev", "password": PASSWORD},
    )
    check(
        "Weak password register",
        "POST",
        "/api/v1/auth/register",
        422,
        json={"email": "weak@test.dev", "password": "short", "full_name": "W", "org_name": "W"},
    )
    check("No auth header", "GET", "/api/v1/incidents/", 403, headers={"Content-Type": "application/json"})
