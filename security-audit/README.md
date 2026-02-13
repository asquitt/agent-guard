# AgentGuard Security Audit

Automated security scanning for the AgentGuard platform.

## Prerequisites

- Python 3.11+
- Node.js (for npm audit)
- Docker Compose running (for security header checks)

## Setup

```bash
cd security-audit
pip install -r requirements.txt
chmod +x run_audit.sh
```

## Run

```bash
./run_audit.sh                              # Default: http://localhost:8001
./run_audit.sh http://staging.example.com   # Custom API URL
```

## Output

Report generated at `reports/audit-report-YYYY-MM-DD.md`.

Exit code 1 if any Critical/High findings, 0 otherwise (CI-friendly).

## Checks Performed

| # | Check | Tool | Severity |
|---|-------|------|----------|
| 1 | Python dependency CVEs | pip-audit | Critical/High |
| 2 | Node.js dependency CVEs | npm audit | Critical/High |
| 3 | Python static security analysis | bandit | High/Medium/Low |
| 4 | Dockerfile security (root user, healthcheck) | grep | Medium/Low |
| 5 | Hardcoded secrets in source | grep | High |
| 6 | Security headers on API | curl | Low/Info |

## Graceful Degradation

If `pip-audit`, `bandit`, or `npm` are not installed, that check is skipped with a warning. Install all tools for a complete audit.
