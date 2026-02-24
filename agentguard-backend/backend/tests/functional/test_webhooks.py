"""Webhook CRUD and delivery functional tests."""

from .conftest import S, section, check


def test_webhooks():
    section("Webhooks")
    t = S.get("t1")
    r = check(
        "Create webhook",
        "POST",
        "/api/v1/webhooks/",
        201,
        json={"name": "Test WH", "url": "https://example.com/wh", "secret": "s3cret", "event_types": ["incident.created"]},
        token=t,
    )
    if r and r.status_code == 201:
        S["wh_id"] = r.json()["id"]

    check("List webhooks", "GET", "/api/v1/webhooks/", 200, token=t)

    if S.get("wh_id"):
        check("Get webhook", "GET", f"/api/v1/webhooks/{S['wh_id']}", 200, token=t)
        check("Delivery stats", "GET", f"/api/v1/webhooks/{S['wh_id']}/deliveries/stats", 200, token=t)
        check("List deliveries", "GET", f"/api/v1/webhooks/{S['wh_id']}/deliveries", 200, token=t)
        check("Update webhook", "PATCH", f"/api/v1/webhooks/{S['wh_id']}", 200, json={"name": "Updated WH"}, token=t)
