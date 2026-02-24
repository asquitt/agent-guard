"""Detector CRUD and rule management functional tests."""

from .conftest import S, section, check


def test_detectors():
    section("Detectors + Rules")
    t = S.get("t1")
    r = check(
        "Create PII detector",
        "POST",
        "/api/v1/detectors/",
        201,
        json={"name": "PII Detector", "category": "pii_leak", "action_mode": "monitor"},
        token=t,
    )
    if r and r.status_code == 201:
        S["det1_id"] = r.json()["id"]

    r = check(
        "Create compliance detector",
        "POST",
        "/api/v1/detectors/",
        201,
        json={"name": "Compliance Det", "category": "compliance", "action_mode": "monitor"},
        token=t,
    )
    if r and r.status_code == 201:
        S["det2_id"] = r.json()["id"]

    check("List detectors", "GET", "/api/v1/detectors/", 200, token=t)

    if S.get("det1_id"):
        check("Get detector", "GET", f"/api/v1/detectors/{S['det1_id']}", 200, token=t)
        check(
            "Update detector",
            "PATCH",
            f"/api/v1/detectors/{S['det1_id']}",
            200,
            json={"name": "PII Detector Updated"},
            token=t,
        )
        r = check(
            "Add rule to detector",
            "POST",
            f"/api/v1/detectors/{S['det1_id']}/rules",
            201,
            json={"name": "SSN Rule", "rule_type": "regex", "parameters": {"pattern": "\\d{3}-\\d{2}-\\d{4}"}},
            token=t,
        )
        if r and r.status_code == 201:
            S["rule_id"] = r.json()["id"]

        if S.get("rule_id"):
            check(
                "Delete rule",
                "DELETE",
                f"/api/v1/detectors/{S['det1_id']}/rules/{S['rule_id']}",
                204,
                token=t,
            )

    if S.get("det2_id"):
        check("Delete detector", "DELETE", f"/api/v1/detectors/{S['det2_id']}", 204, token=t)
