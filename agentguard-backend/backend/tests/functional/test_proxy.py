"""Proxy endpoint and API key functional tests."""

from .conftest import S, section, check


def test_api_keys():
    section("API Keys")
    t = S.get("t1")
    r = check("Create API key", "POST", "/api/v1/api-keys/", 201, json={"name": "func-test-key"}, token=t)
    if r and r.status_code == 201:
        data = r.json()
        S["apikey_id"] = data["id"]

    check("List API keys", "GET", "/api/v1/api-keys/", 200, token=t)

    if S.get("apikey_id"):
        check(
            "Update API key",
            "PATCH",
            f"/api/v1/api-keys/{S['apikey_id']}",
            200,
            json={"name": "renamed-key"},
            token=t,
        )
        check("Revoke API key", "DELETE", f"/api/v1/api-keys/{S['apikey_id']}", 200, token=t)

    # Create a second key for proxy tests
    r = check("Create proxy key", "POST", "/api/v1/api-keys/", 201, json={"name": "proxy-key"}, token=t)
    if r and r.status_code == 201:
        data = r.json()
        S["proxy_key"] = data.get("key")
        S["proxy_key_id"] = data["id"]


def test_proxy_endpoints():
    section("Proxy Endpoints")
    t = S.get("t1")
    r = check(
        "Create proxy endpoint",
        "POST",
        "/api/v1/proxy-endpoints/",
        201,
        json={"name": "Test Endpoint", "provider": "openai", "target_url": "https://api.openai.com", "config": {}},
        token=t,
    )
    if r and r.status_code == 201:
        S["endpoint_id"] = r.json()["id"]

    check("List proxy endpoints", "GET", "/api/v1/proxy-endpoints/", 200, token=t)

    if S.get("endpoint_id"):
        check("Get proxy endpoint", "GET", f"/api/v1/proxy-endpoints/{S['endpoint_id']}", 200, token=t)
        check(
            "Update proxy endpoint",
            "PATCH",
            f"/api/v1/proxy-endpoints/{S['endpoint_id']}",
            200,
            json={"name": "Updated Endpoint"},
            token=t,
        )
        check("Delete proxy endpoint", "DELETE", f"/api/v1/proxy-endpoints/{S['endpoint_id']}", 204, token=t)
