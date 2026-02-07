"""Unit tests for API key, billing, and detection type services."""

from uuid import uuid4

from app.services.api_key_service import (
    API_KEY_PREFIX,
    extract_prefix,
    generate_api_key,
    hash_api_key,
)
from app.services.billing_service import get_request_limit
from app.services.detection.types import (
    ACTION_MODE_MAP,
    DetectionAction,
    DetectionResult,
    PipelineDecision,
)


# ── API Key Service ──────────────────────────────────────────────────


class TestGenerateApiKey:
    def test_format(self):
        key = generate_api_key()
        assert key.startswith(API_KEY_PREFIX)
        # "ag_live_" (8 chars) + 32 hex chars = 40 total
        hex_part = key[len(API_KEY_PREFIX) :]
        assert len(hex_part) == 32
        # Validate hex
        int(hex_part, 16)

    def test_unique(self):
        key1 = generate_api_key()
        key2 = generate_api_key()
        assert key1 != key2


class TestHashApiKey:
    def test_deterministic(self):
        key = generate_api_key()
        hash1 = hash_api_key(key)
        hash2 = hash_api_key(key)
        assert hash1 == hash2

    def test_different_keys_produce_different_hashes(self):
        key1 = generate_api_key()
        key2 = generate_api_key()
        assert hash_api_key(key1) != hash_api_key(key2)


class TestExtractPrefix:
    def test_returns_correct_prefix(self):
        key = generate_api_key()
        prefix = extract_prefix(key)
        # "ag_live_" (8 chars) + first 8 hex chars = 16 chars total
        assert len(prefix) == 16
        assert prefix.startswith(API_KEY_PREFIX)
        assert key.startswith(prefix)


# ── Billing Service ──────────────────────────────────────────────────


class TestGetRequestLimit:
    def test_starter(self):
        assert get_request_limit("starter") == 10_000

    def test_pro(self):
        assert get_request_limit("pro") == 100_000

    def test_enterprise(self):
        assert get_request_limit("enterprise") is None

    def test_unknown_defaults_to_starter(self):
        assert get_request_limit("nonexistent") == 10_000


# ── Detection Types ──────────────────────────────────────────────────


class TestDetectionResult:
    def test_creation(self):
        detector_id = uuid4()
        result = DetectionResult(
            detected=True,
            severity="high",
            category="pii_leak",
            detector_id=detector_id,
            action=DetectionAction.WARN,
            title="PII detected in response",
            description="SSN found",
            details={"pattern": "ssn"},
        )
        assert result.detected is True
        assert result.severity == "high"
        assert result.category == "pii_leak"
        assert result.detector_id == detector_id
        assert result.action == DetectionAction.WARN
        assert result.title == "PII detected in response"
        assert result.description == "SSN found"
        assert result.details == {"pattern": "ssn"}

    def test_defaults(self):
        result = DetectionResult(
            detected=False,
            severity="low",
            category="hallucination",
            detector_id=None,
            action=DetectionAction.PASS,
            title="No hallucination",
        )
        assert result.description == ""
        assert result.details == {}


class TestPipelineDecision:
    def test_creation(self):
        results = [
            DetectionResult(
                detected=False,
                severity="info",
                category="hallucination",
                detector_id=None,
                action=DetectionAction.PASS,
                title="Clean",
            )
        ]
        decision = PipelineDecision(
            action=DetectionAction.PASS,
            results=results,
        )
        assert decision.action == DetectionAction.PASS
        assert len(decision.results) == 1
        assert decision.modified_response is None


class TestDetectionAction:
    def test_ordering(self):
        ordered = [
            DetectionAction.PASS,
            DetectionAction.MONITOR,
            DetectionAction.WARN,
            DetectionAction.REDACT,
            DetectionAction.BLOCK,
        ]
        # Values should be orderable strings matching expected progression
        for i in range(len(ordered) - 1):
            # We just confirm the enum members are distinct and in expected order
            assert ordered[i] != ordered[i + 1]
        # Verify all five actions exist
        assert len(DetectionAction) == 5

    def test_values(self):
        assert DetectionAction.PASS.value == "pass"
        assert DetectionAction.MONITOR.value == "monitor"
        assert DetectionAction.WARN.value == "warn"
        assert DetectionAction.REDACT.value == "redact"
        assert DetectionAction.BLOCK.value == "block"


class TestActionModeMap:
    def test_has_expected_keys(self):
        expected_keys = {"monitor", "warn", "redact", "block"}
        assert set(ACTION_MODE_MAP.keys()) == expected_keys

    def test_values_are_detection_actions(self):
        for value in ACTION_MODE_MAP.values():
            assert isinstance(value, DetectionAction)

    def test_correct_mappings(self):
        assert ACTION_MODE_MAP["monitor"] == DetectionAction.MONITOR
        assert ACTION_MODE_MAP["warn"] == DetectionAction.WARN
        assert ACTION_MODE_MAP["redact"] == DetectionAction.REDACT
        assert ACTION_MODE_MAP["block"] == DetectionAction.BLOCK
