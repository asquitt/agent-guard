"""Alert destination CRUD functional tests."""

from .conftest import S, section, check


def test_alert_destinations():
    section("Alert Destinations")
    t = S.get("t1")
    r = check(
        "Create Slack destination",
        "POST",
        "/api/v1/alerts/destinations",
        201,
        json={"name": "Test Slack", "destination_type": "slack", "config": {"webhook_url": "https://hooks.slack.com/test"}},
        token=t,
    )
    if r and r.status_code == 201:
        S["alert_dest_id"] = r.json()["id"]

    check("List destinations", "GET", "/api/v1/alerts/destinations", 200, token=t)

    if S.get("alert_dest_id"):
        check(
            "Update destination",
            "PATCH",
            f"/api/v1/alerts/destinations/{S['alert_dest_id']}",
            200,
            json={"name": "Updated Slack"},
            token=t,
        )

    check("List alerts", "GET", "/api/v1/alerts/", 200, token=t)

    if S.get("alert_dest_id"):
        check("Delete destination", "DELETE", f"/api/v1/alerts/destinations/{S['alert_dest_id']}", 204, token=t)
