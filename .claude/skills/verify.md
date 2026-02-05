# Verify Skill

Post-task verification for AgentGuard.

## Usage
Run `/verify` after completing any code changes.

## Verification Sequence (MANDATORY)

### 1. Type Checking
```bash
# Backend
cd agentguard-backend/backend && python -m pyright app/ --level warning

# Frontend
cd agentguard-frontend && npx tsc --noEmit
```

### 2. Model Imports (if models changed)
```bash
cd agentguard-backend/backend && python scripts/check_model_imports.py
```

### 3. Pre-commit Hooks
```bash
pre-commit run --all-files
```

### 4. API Health
```bash
curl -s http://localhost:8000/health | jq
```

### 5. Service Logs (check for errors)
```bash
/usr/local/bin/docker compose logs api --tail=20 | grep -i error
/usr/local/bin/docker compose logs worker --tail=20 | grep -i error
```

## Functional Verification

Depending on what changed:

### API Endpoint Changes
```bash
# Get auth token
TOKEN=$(curl -s 'http://localhost:8000/api/v1/auth/login' -X POST \
  -H 'Content-Type: application/json' \
  -d '{"email":"test@example.com","password":"password"}' | jq -r '.access_token')

# Test endpoint
curl -s 'http://localhost:8000/api/v1/[endpoint]' \
  -H "Authorization: Bearer $TOKEN" | jq
```

### Frontend Changes
- Use Playwright MCP to verify UI
- Check browser console for errors
- Verify component renders correctly

## Output Format
```
## Verification Results - [TIMESTAMP]

### Static Analysis
- Backend types: [pass/fail]
- Frontend types: [pass/fail]
- Model imports: [pass/fail]
- Pre-commit: [pass/fail]

### Runtime
- API health: [pass/fail]
- Error logs: [none/count]

### Functional
- [Specific verification performed]

### Status: [READY TO COMMIT / NEEDS FIXES]
```

## If Verification Fails

1. Identify the failure
2. Fix the issue immediately
3. Re-run verification
4. Only commit when ALL checks pass

**Never commit with failing verification.**
