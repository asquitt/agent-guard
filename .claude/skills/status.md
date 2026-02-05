# Status Skill

Check system health for AgentGuard.

## Usage
Run `/status` to check all services.

## Checks

### 1. Docker Services
```bash
/usr/local/bin/docker compose ps
```

### 2. API Health
```bash
curl -s http://localhost:8000/health | jq
```

### 3. Database Connection
```bash
/usr/local/bin/docker compose exec db psql -U agentguard -c "SELECT 1"
```

### 4. Redis Connection
```bash
/usr/local/bin/docker compose exec redis redis-cli ping
```

### 5. Git Status
```bash
git status --short
git log --oneline -5
```

### 6. Type Check Status
```bash
cd agentguard-backend/backend && python -m pyright app/ --level warning 2>&1 | tail -5
cd agentguard-frontend && npx tsc --noEmit 2>&1 | tail -5
```

## Output Format
```
## AgentGuard Status - [TIMESTAMP]

### Services
- API: [running/stopped]
- Worker: [running/stopped]
- DB: [running/stopped]
- Redis: [running/stopped]

### Health
- API Health: [ok/error]
- DB Connection: [ok/error]
- Redis: [ok/error]

### Code
- Uncommitted changes: [count]
- Type errors: [count]
```
