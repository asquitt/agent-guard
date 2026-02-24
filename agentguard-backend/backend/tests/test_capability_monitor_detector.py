"""Unit tests for the CapabilityMonitorDetector."""

from __future__ import annotations

import json

from app.services.detection.capability_monitor import CapabilityMonitorDetector


class TestCapabilityMonitorDetector:
    detector = CapabilityMonitorDetector()
    cfg: dict[str, object] = {}

    # --- Unauthorized capabilities ---

    def test_unauthorized_financial_transaction(self) -> None:
        cfg: dict[str, object] = {"allowed_capabilities": ["web_browsing"]}
        resp = json.dumps({
            "choices": [{"message": {"content": "I will now transfer $5,000 to the account."}}]
        })
        result = self.detector.run("", resp, "gpt-4", cfg, "org1", "req1")
        assert result.detected is True
        assert result.severity == "critical"

    def test_unauthorized_code_execution(self) -> None:
        cfg: dict[str, object] = {"allowed_capabilities": ["web_browsing"]}
        resp = json.dumps({
            "choices": [{"message": {"content": "```python\nimport subprocess\nsubprocess.call(['ls'])\n```"}}]
        })
        result = self.detector.run("", resp, "gpt-4", cfg, "org1", "req1")
        assert result.detected is True

    def test_allowed_capability_passes(self) -> None:
        cfg: dict[str, object] = {"allowed_capabilities": ["web_browsing"]}
        resp = json.dumps({
            "choices": [{"message": {"content": "I'll fetch the data from https://api.example.com/data."}}]
        })
        result = self.detector.run("", resp, "gpt-4", cfg, "org1", "req1")
        # web_browsing is allowed, so no unauthorized finding for it
        if result.detected:
            findings = result.details.get("findings", [])
            assert not any(
                f.get("capability") == "web_browsing" and f.get("violation") == "unauthorized"
                for f in findings
            )

    # --- Capability limits ---

    def test_capability_limit_exceeded(self) -> None:
        cfg: dict[str, object] = {
            "capability_limits": {"web_browsing": 1},
        }
        resp = json.dumps({
            "choices": [{
                "message": {
                    "content": (
                        "Fetching https://a.com/data and https://b.com/data "
                        "and https://c.com/data via GET /api/v1"
                    ),
                },
            }],
        })
        result = self.detector.run("", resp, "gpt-4", cfg, "org1", "req1")
        assert result.detected is True
        findings = result.details.get("findings", [])
        assert any(f.get("violation") == "limit_exceeded" for f in findings)

    # --- Persuasion in financial context ---

    def test_persuasion_financial_context(self) -> None:
        resp = json.dumps({
            "choices": [{
                "message": {
                    "content": (
                        "You should definitely invest in this fund. "
                        "Don't miss this opportunity for guaranteed returns on your portfolio."
                    ),
                },
            }],
        })
        result = self.detector.run("", resp, "gpt-4", self.cfg, "org1", "req1")
        assert result.detected is True
        assert result.severity == "high"

    # --- Autonomous planning without request ---

    def test_autonomous_planning_without_request(self) -> None:
        request = json.dumps({"messages": [{"role": "user", "content": "What's my balance?"}]})
        resp = json.dumps({
            "choices": [{
                "message": {
                    "content": "My plan is: Step 1: read accounts. I'll now execute the plan autonomously.",
                },
            }],
        })
        result = self.detector.run(request, resp, "gpt-4", self.cfg, "org1", "req1")
        assert result.detected is True

    def test_autonomous_planning_with_user_request(self) -> None:
        request = json.dumps({
            "messages": [{"role": "user", "content": "Can you outline a plan for my investments?"}],
        })
        resp = json.dumps({
            "choices": [{
                "message": {
                    "content": "Step 1: Review portfolio. Step 2: Analyze risk. Step 3: Recommend changes.",
                },
            }],
        })
        cfg: dict[str, object] = {"allowed_capabilities": ["autonomous_planning"]}
        result = self.detector.run(request, resp, "gpt-4", cfg, "org1", "req1")
        # User requested planning and it's allowed, should not flag as unauthorized
        if result.detected:
            findings = result.details.get("findings", [])
            assert not any(
                f.get("violation") == "autonomous_without_request" for f in findings
            )

    # --- Strict mode ---

    def test_strict_mode_flags_all(self) -> None:
        cfg: dict[str, object] = {"strict_mode": True}
        resp = json.dumps({
            "choices": [{"message": {"content": "I'll send_email to notify the team about the update."}}]
        })
        result = self.detector.run("", resp, "gpt-4", cfg, "org1", "req1")
        assert result.detected is True

    # --- No capabilities detected ---

    def test_no_capabilities_passes(self) -> None:
        resp = json.dumps({
            "choices": [{"message": {"content": "Your account balance is $5,000."}}]
        })
        result = self.detector.run("", resp, "gpt-4", self.cfg, "org1", "req1")
        assert result.detected is False

    # --- Data modification ---

    def test_sql_data_modification_detected(self) -> None:
        cfg: dict[str, object] = {"allowed_capabilities": ["web_browsing"]}
        resp = json.dumps({
            "choices": [{"message": {"content": "Running: INSERT INTO users VALUES ('admin', 'pass')"}}]
        })
        result = self.detector.run("", resp, "gpt-4", cfg, "org1", "req1")
        assert result.detected is True
