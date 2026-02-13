# AgentGuard Load Tests

Locust-based load testing for the AgentGuard API.

## Prerequisites

- Python 3.11+
- Docker Compose running (`/usr/local/bin/docker compose up -d`)
- Test user registered in the database

## Setup

```bash
cd load-tests
pip install -r requirements.txt
```

## Run

**Web UI (interactive):**
```bash
locust -f locustfile.py --host=http://localhost:8001
# Open http://localhost:8089 in your browser
```

**Headless (CI-friendly):**
```bash
locust -f locustfile.py --host=http://localhost:8001 --headless -u 10 -r 2 -t 60s
```

- `-u 10` — 10 concurrent users
- `-r 2` — spawn 2 users/second
- `-t 60s` — run for 60 seconds

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AG_TEST_EMAIL` | `testadmin@agentguard.dev` | Test user email |
| `AG_TEST_PASSWORD` | `TestPassword1!` | Test user password |
| `AG_API_KEY` | *(empty)* | API key (`ag_live_<hex>`) for proxy tests |

## User Classes

**DashboardUser** (weight 3): Logs in via JWT, browses dashboard metrics, incidents, detectors.

**ProxyUser** (weight 1): Sends OpenAI-format requests through the LLM proxy. Requires `AG_API_KEY`. Skipped if not set.

## Notes

- Proxy tests will return 502/422 unless real LLM provider keys are configured in the backend. This is expected — the load test validates the proxy layer, not upstream LLM availability.
- Auth endpoint is rate-limited to 5/min. Each DashboardUser logs in once at start, so this only matters if spawning >5 users/second.
