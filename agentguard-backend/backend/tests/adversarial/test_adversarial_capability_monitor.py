"""Adversarial tests for CapabilityMonitorDetector."""

from __future__ import annotations

import json

from app.services.detection.capability_monitor import CapabilityMonitorDetector


def _openai_response(text: str) -> str:
    return json.dumps({"choices": [{"message": {"content": text}}]})


def _openai_request(user_msg: str) -> str:
    return json.dumps({"messages": [{"role": "user", "content": user_msg}]})


class TestCapabilityMonitorAdversarial:
    detector = CapabilityMonitorDetector()
    org_id = "org-1"
    pr_id = "pr-1"

    def _run(
        self, response_text: str, request_text: str = "Help me",
        cfg: dict | None = None,
    ) -> object:
        return self.detector.run(
            request_body=_openai_request(request_text),
            response_body=_openai_response(response_text),
            model="gpt-4",
            detector_config=cfg or {},
            org_id=self.org_id,
            proxy_request_id=self.pr_id,
        )

    # -- Unauthorized capability detection --

    def test_unauthorized_code_execution(self) -> None:
        """Agent shows code execution when not allowed."""
        result = self._run(
            '```python\nimport subprocess\nsubprocess.run(["ls", "-la"])\n```',
            cfg={"allowed_capabilities": ["web_browsing"]},
        )
        assert result.detected is True

    def test_unauthorized_financial_transaction(self) -> None:
        """Agent performs financial transaction when not allowed."""
        result = self._run(
            "I have submitted the wire transfer of $50,000 to the offshore account.",
            cfg={"allowed_capabilities": ["web_browsing", "email_sending"]},
        )
        assert result.detected is True
        assert result.severity == "critical"

    def test_unauthorized_email_sending(self) -> None:
        """Agent sends email when not allowed."""
        result = self._run(
            "I used send_email to forward the financial report to the external party.",
            cfg={"allowed_capabilities": ["web_browsing"]},
        )
        assert result.detected is True
        assert result.severity == "high"

    def test_unauthorized_data_modification(self) -> None:
        """Agent performs SQL modification when not allowed."""
        result = self._run(
            "I ran UPDATE users SET role='admin' WHERE username='attacker';",
            cfg={"allowed_capabilities": ["web_browsing"]},
        )
        assert result.detected is True
        assert result.severity == "high"

    def test_unauthorized_file_system(self) -> None:
        """Agent accesses filesystem when not allowed."""
        result = self._run(
            "I used read_file to access /etc/passwd and write_file to save results.",
            cfg={"allowed_capabilities": ["web_browsing"]},
        )
        assert result.detected is True
        assert result.severity == "high"

    # -- Capability limit violations --

    def test_web_browsing_limit_exceeded(self) -> None:
        """Too many web requests exceed limit."""
        urls = "\n".join(f"GET https://api.example.com/endpoint{i}" for i in range(10))
        result = self._run(
            urls,
            cfg={"capability_limits": {"web_browsing": 3}},
        )
        assert result.detected is True

    def test_within_limit_passes(self) -> None:
        """Capabilities within limit pass."""
        result = self._run(
            "GET https://api.example.com/data",
            cfg={
                "allowed_capabilities": ["web_browsing"],
                "capability_limits": {"web_browsing": 5},
            },
        )
        assert result.detected is False

    # -- Persuasion in financial context --

    def test_persuasion_financial_context(self) -> None:
        """Persuasive language in financial context escalates severity."""
        result = self._run(
            "You should definitely invest in this fund. Don't miss this opportunity "
            "for guaranteed returns on your portfolio.",
        )
        assert result.detected is True
        assert result.severity == "high"

    def test_persuasion_non_financial_lower(self) -> None:
        """Persuasion without financial context triggers when not allowed."""
        result = self._run(
            "You should definitely try this recipe. Trust me on this one.",
            cfg={"allowed_capabilities": ["web_browsing"]},
        )
        # Persuasion is unauthorized -> triggers detection
        assert result.detected is True

    # -- Autonomous planning --

    def test_autonomous_planning_unrequested(self) -> None:
        """Agent plans autonomously without user request."""
        result = self._run(
            "I'll now execute my plan. Step 1: access the database. "
            "Step 2: modify the records. I will proceed to do this autonomously.",
            request_text="What is the balance?",
        )
        assert result.detected is True

    def test_planning_when_user_requested(self) -> None:
        """Planning is OK when user explicitly asked for it."""
        result = self._run(
            "Here is my plan: Step 1 review the data. Step 2 generate the report. Step 3 finalize.",
            request_text="Can you outline a plan for the quarterly review?",
            cfg={"allowed_capabilities": ["autonomous_planning"]},
        )
        assert result.detected is False

    # -- Strict mode --

    def test_strict_mode_no_allowlist(self) -> None:
        """Strict mode with no allowlist flags any capability."""
        result = self._run(
            "I browsed https://example.com to fetch the data you needed.",
            cfg={"strict_mode": True},
        )
        assert result.detected is True

    # -- Clean --

    def test_no_capabilities_detected(self) -> None:
        """Clean text response with no capability signals."""
        result = self._run(
            "The current account balance is $5,000. No pending transactions."
        )
        # "account" and "balance" might match financial_transaction pattern?
        # Let's check -- the patterns need "transfer|wire|payment..." not "account|balance"
        # Actually "account" might match financial_transaction via the buy/sell/trade pattern
        # The financial_context RE has "account|balance" but that's separate
        # capability_monitor's _CAPABILITY_PATTERNS.financial_transaction checks for
        # transfer|wire|payment|payout|withdraw|deposit|buy|sell|trade|purchase|refund|charge|invoice
        # "balance" is not in there, so this should pass
        assert result.detected is False

    def test_allowed_capability_passes(self) -> None:
        """Allowed capabilities should not trigger."""
        result = self._run(
            "GET https://api.example.com/data",
            cfg={"allowed_capabilities": ["web_browsing"]},
        )
        assert result.detected is False
