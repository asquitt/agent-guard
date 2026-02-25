"""Adversarial tests for TieredExecutor and TierStatsCollector."""

from __future__ import annotations

from app.services.detection.tiered import TieredExecutor, TierMetrics, TierStatsCollector
from app.services.detection.types import DetectionAction, DetectionResult


def _detected(title: str = "hit", severity: str = "high") -> DetectionResult:
    return DetectionResult(
        detected=True, severity=severity, category="test",
        detector_id=None, action=DetectionAction.MONITOR, title=title,
    )


def _clean(title: str = "clean") -> DetectionResult:
    return DetectionResult(
        detected=False, severity="info", category="test",
        detector_id=None, action=DetectionAction.PASS, title=title,
    )


class TestTieredExecutorAdversarial:
    executor = TieredExecutor()

    # -- Tier 1 detection --

    def test_tier1_hit_short_circuits(self) -> None:
        """Tier 1 detection stops the pipeline."""
        result, metrics = self.executor.run(
            tier1_fn=lambda: _detected("tier1"),
            tier2_fn=lambda: (_ for _ in ()).throw(AssertionError("should not reach tier2")),
            tier3_fn=lambda: (_ for _ in ()).throw(AssertionError("should not reach tier3")),
        )
        assert result.detected is True
        assert result.title == "tier1"
        assert metrics.tier_reached == 1
        assert metrics.tier2_ms is None
        assert metrics.tier3_ms is None

    def test_tier1_pass_proceeds_to_tier2(self) -> None:
        """Tier 1 pass proceeds to tier 2."""
        result, metrics = self.executor.run(
            tier1_fn=lambda: None,
            tier2_fn=lambda: _detected("tier2"),
        )
        assert result.detected is True
        assert result.title == "tier2"
        assert metrics.tier_reached == 2

    # -- Tier 2 detection --

    def test_tier2_hit_stops_pipeline(self) -> None:
        """Tier 2 detection stops before tier 3."""
        result, metrics = self.executor.run(
            tier1_fn=lambda: None,
            tier2_fn=lambda: _detected("tier2 hit"),
            tier3_fn=lambda: (_ for _ in ()).throw(AssertionError("should not reach")),
        )
        assert result.detected is True
        assert metrics.tier_reached == 2
        assert metrics.tier3_ms is None

    def test_tier2_pass_proceeds_to_tier3(self) -> None:
        """Tier 2 pass proceeds to tier 3."""
        result, metrics = self.executor.run(
            tier1_fn=lambda: None,
            tier2_fn=lambda: None,
            tier3_fn=lambda: _detected("tier3"),
        )
        assert result.detected is True
        assert result.title == "tier3"
        assert metrics.tier_reached == 3

    # -- Tier 3 detection --

    def test_tier3_llm_hit(self) -> None:
        """Tier 3 LLM detects something tiers 1-2 missed."""
        result, metrics = self.executor.run(
            tier1_fn=lambda: None,
            tier2_fn=lambda: None,
            tier3_fn=lambda: _detected("llm caught it"),
        )
        assert result.detected is True
        assert result.title == "llm caught it"
        assert metrics.tier_reached == 3
        assert metrics.tier3_ms is not None

    def test_tier3_exception_falls_through(self) -> None:
        """Tier 3 LLM exception fails open (no detection)."""
        result, metrics = self.executor.run(
            tier1_fn=lambda: None,
            tier2_fn=lambda: None,
            tier3_fn=lambda: (_ for _ in ()).throw(RuntimeError("LLM down")),
        )
        assert result.detected is False
        assert metrics.tier_reached == 3

    # -- All tiers pass --

    def test_all_tiers_pass(self) -> None:
        """All tiers return None/clean -> no detection."""
        result, metrics = self.executor.run(
            tier1_fn=lambda: None,
            tier2_fn=lambda: None,
            tier3_fn=lambda: None,
        )
        assert result.detected is False
        assert metrics.tier_reached == 3

    def test_custom_pass_result(self) -> None:
        """Custom pass result used when all tiers pass."""
        custom = _clean("custom pass")
        result, metrics = self.executor.run(
            tier1_fn=lambda: None,
            pass_result=custom,
        )
        assert result.detected is False
        assert result.title == "custom pass"

    # -- Tier-skipping --

    def test_no_tier2_or_tier3(self) -> None:
        """Only tier 1 provided, passes cleanly."""
        result, metrics = self.executor.run(
            tier1_fn=lambda: None,
        )
        assert result.detected is False
        assert metrics.tier_reached == 1

    def test_no_tier3(self) -> None:
        """Tier 1 and 2 only, both pass."""
        result, metrics = self.executor.run(
            tier1_fn=lambda: None,
            tier2_fn=lambda: None,
        )
        assert result.detected is False
        assert metrics.tier_reached == 2

    # -- Timing verification --

    def test_metrics_timing_non_negative(self) -> None:
        """All timing values should be non-negative."""
        result, metrics = self.executor.run(
            tier1_fn=lambda: None,
            tier2_fn=lambda: None,
            tier3_fn=lambda: _detected("tier3"),
        )
        assert metrics.tier1_ms >= 0
        assert metrics.tier2_ms is not None and metrics.tier2_ms >= 0
        assert metrics.tier3_ms is not None and metrics.tier3_ms >= 0
        assert metrics.total_ms >= 0


class TestTierStatsCollector:
    """Tests for aggregate statistics collection."""

    def test_empty_stats(self) -> None:
        """Empty collector returns zeros."""
        collector = TierStatsCollector()
        stats = collector.get_stats()
        assert stats["total_runs"] == 0
        assert stats["tier1_hits"] == 0

    def test_records_tier1_hit(self) -> None:
        """Record a tier 1 hit."""
        collector = TierStatsCollector()
        collector.record(TierMetrics(tier_reached=1, tier1_ms=1.0, total_ms=1.0))
        stats = collector.get_stats()
        assert stats["total_runs"] == 1
        assert stats["tier1_hits"] == 1
        assert stats["tier1_pct"] == 100.0

    def test_records_multiple_tiers(self) -> None:
        """Record hits across different tiers."""
        collector = TierStatsCollector()
        collector.record(TierMetrics(tier_reached=1, tier1_ms=1.0, total_ms=1.0))
        collector.record(TierMetrics(tier_reached=2, tier1_ms=1.0, tier2_ms=2.0, total_ms=3.0))
        collector.record(TierMetrics(tier_reached=3, tier1_ms=1.0, tier2_ms=2.0, tier3_ms=5.0, total_ms=8.0))
        stats = collector.get_stats()
        assert stats["total_runs"] == 3
        assert stats["tier1_hits"] == 1
        assert stats["tier2_hits"] == 1
        assert stats["tier3_hits"] == 1
        assert stats["avg_latency_ms"] == 4.0  # (1 + 3 + 8) / 3
