"""Resource monitoring for sandboxed agent executions.

Checks CPU, memory, token budget, and timeout limits against Docker container stats.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.services.sandbox.types import ResourceLimitViolation, ResourceUsage

logger = logging.getLogger(__name__)


def check_resource_limits(
    resource_usage: ResourceUsage,
    limits: dict[str, Any],
    started_at: datetime | None = None,
) -> ResourceLimitViolation | None:
    """Check if current resource usage exceeds configured limits.

    Returns a violation if any limit is breached, None if within bounds.
    """
    memory_mb = limits.get("memory_mb", 256)
    if resource_usage.memory_peak_mb > memory_mb:
        return ResourceLimitViolation(
            resource="memory",
            limit=memory_mb,
            current=resource_usage.memory_peak_mb,
            message=f"Memory usage {resource_usage.memory_peak_mb:.1f}MB exceeds limit {memory_mb}MB",
        )

    max_tokens = limits.get("max_tokens", 10000)
    if resource_usage.tokens_used > max_tokens:
        return ResourceLimitViolation(
            resource="tokens",
            limit=max_tokens,
            current=resource_usage.tokens_used,
            message=f"Token usage {resource_usage.tokens_used} exceeds budget {max_tokens}",
        )

    timeout_seconds = limits.get("timeout_seconds", 300)
    if started_at:
        elapsed = (datetime.now(timezone.utc) - started_at).total_seconds()
        if elapsed > timeout_seconds:
            return ResourceLimitViolation(
                resource="timeout",
                limit=timeout_seconds,
                current=elapsed,
                message=f"Execution time {elapsed:.0f}s exceeds timeout {timeout_seconds}s",
            )

    return None


def get_container_stats(docker_client: Any, container_id: str) -> ResourceUsage:
    """Fetch resource usage from a running Docker container.

    Args:
        docker_client: docker.DockerClient instance
        container_id: Docker container ID

    Returns:
        ResourceUsage with current stats.
    """
    try:
        container = docker_client.containers.get(container_id)
        stats = container.stats(stream=False)

        cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - stats[
            "precpu_stats"
        ]["cpu_usage"]["total_usage"]
        system_delta = stats["cpu_stats"]["system_cpu_usage"] - stats[
            "precpu_stats"
        ]["system_cpu_usage"]

        cpu_seconds = cpu_delta / 1e9 if system_delta > 0 else 0.0

        memory_usage = stats.get("memory_stats", {}).get("usage", 0)
        memory_mb = memory_usage / (1024 * 1024)

        networks = stats.get("networks", {})
        network_bytes = sum(
            net.get("rx_bytes", 0) + net.get("tx_bytes", 0)
            for net in networks.values()
        )

        return ResourceUsage(
            cpu_seconds=cpu_seconds,
            memory_peak_mb=memory_mb,
            network_bytes=network_bytes,
        )
    except Exception as e:
        logger.warning("Failed to get container stats for %s: %s", container_id, e)
        return ResourceUsage()
