#!/usr/bin/env python3
"""AgentGuard Comprehensive Functional Test Suite.

Runs ~128 tests against a live Docker Compose environment.
Usage: python3 -m tests.functional
"""

import sys
import time

from .conftest import BOLD, GREEN, RED, RESET, BASE, TS, passed, failed, errors
from . import conftest
from .test_auth import test_health, test_auth_register_login, test_auth_token_lifecycle, test_auth_errors
from .test_proxy import test_api_keys, test_proxy_endpoints
from .test_detectors import test_detectors
from .test_incidents import test_incidents
from .test_alerts import test_alert_destinations
from .test_webhooks import test_webhooks
from .test_advanced import (
    test_organizations,
    test_dashboard,
    test_compliance,
    test_agents,
    test_agent_policies,
    test_conversations,
    test_red_team,
    test_shadow_ai,
    test_threat_intel,
    test_reviews,
    test_retention,
    test_traces,
    test_playground,
    test_billing,
    test_tenant_isolation,
    test_error_cases,
)
from .test_stubs import (
    test_sandbox,
    test_governance,
    test_red_team_advanced,
    test_sso,
    test_siem,
    test_organizations_advanced,
)


def main():
    print(f"\n{BOLD}{'=' * 52}{RESET}")
    print(f"{BOLD}  AgentGuard Functional Test Suite{RESET}")
    print(f"{BOLD}  Target: {BASE}{RESET}")
    print(f"{BOLD}  Run ID: {TS}{RESET}")
    print(f"{BOLD}{'=' * 52}{RESET}")

    t0 = time.time()

    # Phase 1: Infrastructure
    test_health()

    # Phase 2: Auth
    test_auth_register_login()
    test_auth_token_lifecycle()
    test_auth_errors()

    # Phase 3: Core CRUD
    test_organizations()
    test_api_keys()
    test_proxy_endpoints()
    test_detectors()

    # Phase 4: Detection & Monitoring
    test_incidents()
    test_alert_destinations()
    test_webhooks()

    # Phase 5: Analytics
    test_dashboard()
    test_compliance()

    # Phase 6: Agent Governance
    test_agents()
    test_agent_policies()

    # Phase 7: Advanced Features
    test_conversations()
    test_red_team()
    test_shadow_ai()
    test_threat_intel()
    test_reviews()
    test_retention()
    test_traces()
    test_playground()
    test_billing()

    # Phase 8: Security
    test_tenant_isolation()
    test_error_cases()

    # Phase 9: Stub tests (untested endpoints)
    test_sandbox()
    test_governance()
    test_red_team_advanced()
    test_sso()
    test_siem()
    test_organizations_advanced()

    elapsed = time.time() - t0

    print(f"\n{BOLD}{'=' * 52}{RESET}")
    total = conftest.passed + conftest.failed
    print(f"{BOLD}  RESULTS: {GREEN}{conftest.passed} passed{RESET}, {RED}{conftest.failed} failed{RESET}  ({total} total)")
    print(f"{BOLD}  Duration: {elapsed:.1f}s{RESET}")
    print(f"{BOLD}{'=' * 52}{RESET}")

    if conftest.errors:
        print(f"\n{RED}Failures:{RESET}")
        for e in conftest.errors:
            print(f"  • {e}")

    sys.exit(0 if conftest.failed == 0 else 1)


if __name__ == "__main__":
    main()
