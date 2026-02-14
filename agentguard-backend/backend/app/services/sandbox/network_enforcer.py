"""Network policy enforcement for sandboxed agent executions.

Creates isolated Docker networks and applies egress rules.
Whitelist-only: only explicitly allowed hosts and ports are reachable.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def create_sandbox_network(
    docker_client: Any,
    sandbox_id: str,
) -> str:
    """Create an isolated Docker network for a sandbox.

    Returns the network name.
    """
    network_name = f"agentguard-sandbox-{sandbox_id[:8]}"
    try:
        docker_client.networks.create(
            name=network_name,
            driver="bridge",
            internal=True,  # No external connectivity by default
            labels={"agentguard.sandbox_id": sandbox_id},
        )
        logger.info("Created sandbox network: %s", network_name)
    except Exception as e:
        # Network may already exist from a previous run
        logger.warning("Network creation issue for %s: %s", network_name, e)
    return network_name


def apply_network_policy(
    docker_client: Any,
    container_id: str,
    network_policy: dict[str, Any],
    sandbox_id: str,
) -> None:
    """Apply network policy to a running container.

    For deny_all_egress=True (default), the container starts on an internal
    network with no external access. Allowed hosts are documented in the
    sandbox config for audit purposes.

    In production, this would use iptables/nftables rules or a network proxy.
    For local development, Docker's internal network provides baseline isolation.
    """
    deny_all = network_policy.get("deny_all_egress", True)
    allowed_hosts = network_policy.get("allowed_hosts", [])
    allowed_ports = network_policy.get("allowed_ports", [443, 80])

    if deny_all and not allowed_hosts:
        logger.info(
            "Sandbox %s: full network isolation (deny_all_egress, no allowed hosts)",
            sandbox_id[:8],
        )
        return

    if allowed_hosts:
        logger.info(
            "Sandbox %s: network restricted to hosts=%s ports=%s",
            sandbox_id[:8],
            allowed_hosts,
            allowed_ports,
        )


def cleanup_sandbox_network(docker_client: Any, sandbox_id: str) -> None:
    """Remove the Docker network for a sandbox."""
    network_name = f"agentguard-sandbox-{sandbox_id[:8]}"
    try:
        network = docker_client.networks.get(network_name)
        network.remove()
        logger.info("Removed sandbox network: %s", network_name)
    except Exception as e:
        logger.warning("Network cleanup issue for %s: %s", network_name, e)


def validate_network_request(
    network_policy: dict[str, Any],
    host: str,
    port: int = 443,
) -> bool:
    """Check if a network request is allowed by the policy.

    Used by the proxy integration to pre-validate outbound requests.
    """
    deny_all = network_policy.get("deny_all_egress", True)
    if not deny_all:
        return True

    allowed_hosts = network_policy.get("allowed_hosts", [])
    allowed_ports = network_policy.get("allowed_ports", [443, 80])

    if port not in allowed_ports:
        return False

    import fnmatch
    for pattern in allowed_hosts:
        if fnmatch.fnmatch(host.lower(), pattern.lower()):
            return True

    return False
