"""Tiered detection pipeline -- Tier 1 regex -> Tier 2 heuristic -> Tier 3 LLM."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Callable

from app.services.detection.types import DetectionAction, DetectionResult

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class TierMetrics:
    """Metrics from a tiered detection run."""

    tier_reached: int  # 1, 2, or 3
    tier1_ms: float
    tier2_ms: float | None = None
    tier3_ms: float | None = None
    total_ms: float = 0.0


# Type alias for tier functions
TierFn = Callable[[], DetectionResult | None]


class TieredExecutor:
    """Runs detection in tiers: fast regex -> heuristic -> LLM.

    Usage:
        executor = TieredExecutor()
        result, metrics = executor.run(
            tier1_fn=lambda: regex_scan(text),
            tier2_fn=lambda: heuristic_check(text),
            tier3_fn=lambda: llm_verify(text),
            pass_result=DetectionResult(...),
        )
    """

    def run(
        self,
        tier1_fn: TierFn,
        tier2_fn: TierFn | None = None,
        tier3_fn: TierFn | None = None,
        pass_result: DetectionResult | None = None,
    ) -> tuple[DetectionResult, TierMetrics]:
        # Tier 1: Fast regex/pattern matching
        t1_start = time.perf_counter()
        t1_result = tier1_fn()
        t1_ms = (time.perf_counter() - t1_start) * 1000

        if t1_result is not None and t1_result.detected:
            metrics = TierMetrics(tier_reached=1, tier1_ms=t1_ms, total_ms=t1_ms)
            return t1_result, metrics

        # Tier 2: Heuristic/lightweight classifier
        t2_ms = None
        if tier2_fn is not None:
            t2_start = time.perf_counter()
            t2_result = tier2_fn()
            t2_ms = (time.perf_counter() - t2_start) * 1000

            if t2_result is not None and t2_result.detected:
                metrics = TierMetrics(
                    tier_reached=2,
                    tier1_ms=t1_ms,
                    tier2_ms=t2_ms,
                    total_ms=t1_ms + t2_ms,
                )
                return t2_result, metrics

        # Tier 3: LLM analysis
        t3_ms = None
        if tier3_fn is not None:
            t3_start = time.perf_counter()
            try:
                t3_result = tier3_fn()
                t3_ms = (time.perf_counter() - t3_start) * 1000
                total = t1_ms + (t2_ms or 0) + t3_ms
                if t3_result is not None and t3_result.detected:
                    metrics = TierMetrics(
                        tier_reached=3,
                        tier1_ms=t1_ms,
                        tier2_ms=t2_ms,
                        tier3_ms=t3_ms,
                        total_ms=total,
                    )
                    return t3_result, metrics
            except Exception:
                logger.exception("Tier 3 LLM analysis failed, falling through")
                t3_ms = (time.perf_counter() - t3_start) * 1000

        # All tiers passed -- no detection
        total = t1_ms + (t2_ms or 0) + (t3_ms or 0)
        tier = 3 if t3_ms is not None else (2 if t2_ms is not None else 1)
        metrics = TierMetrics(
            tier_reached=tier,
            tier1_ms=t1_ms,
            tier2_ms=t2_ms,
            tier3_ms=t3_ms,
            total_ms=total,
        )

        if pass_result:
            return pass_result, metrics

        return (
            DetectionResult(
                detected=False,
                severity="info",
                category="unknown",
                detector_id=None,
                action=DetectionAction.PASS,
                title="No detection",
            ),
            metrics,
        )


class TierStatsCollector:
    """Thread-safe aggregate statistics across tiered detection runs."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._total_runs = 0
        self._tier1_hits = 0
        self._tier2_hits = 0
        self._tier3_hits = 0
        self._total_latency_ms = 0.0

    def record(self, metrics: TierMetrics) -> None:
        """Record metrics from a single tiered run."""
        with self._lock:
            self._total_runs += 1
            self._total_latency_ms += metrics.total_ms
            if metrics.tier_reached == 1:
                self._tier1_hits += 1
            elif metrics.tier_reached == 2:
                self._tier2_hits += 1
            elif metrics.tier_reached == 3:
                self._tier3_hits += 1

    def get_stats(self) -> dict[str, float | int]:
        """Return aggregate statistics snapshot."""
        with self._lock:
            total = self._total_runs
            return {
                "total_runs": total,
                "tier1_hits": self._tier1_hits,
                "tier2_hits": self._tier2_hits,
                "tier3_hits": self._tier3_hits,
                "tier1_pct": (self._tier1_hits / total * 100) if total else 0.0,
                "tier2_pct": (self._tier2_hits / total * 100) if total else 0.0,
                "tier3_pct": (self._tier3_hits / total * 100) if total else 0.0,
                "avg_latency_ms": (
                    self._total_latency_ms / total if total else 0.0
                ),
            }
