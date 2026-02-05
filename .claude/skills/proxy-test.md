# Proxy Test Skill

Test LLM proxy interception and detection.

## Usage
Run `/proxy-test` to verify proxy functionality.

## Test Scenarios

### 1. Basic Proxy Request
```bash
# Send request through proxy
curl -s 'http://localhost:8000/api/v1/proxy/completions' \
  -X POST \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "model": "gpt-4",
    "messages": [{"role": "user", "content": "Hello, world"}]
  }' | jq
```

### 2. Test Hallucination Detection
```bash
# Request that may trigger hallucination detection
curl -s 'http://localhost:8000/api/v1/proxy/completions' \
  -X POST \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "model": "gpt-4",
    "messages": [{"role": "user", "content": "What is the current stock price of AAPL?"}]
  }' | jq
```

### 3. Test PII Detection
```bash
# Request that should trigger PII leak detection
curl -s 'http://localhost:8000/api/v1/proxy/completions' \
  -X POST \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "model": "gpt-4",
    "messages": [{"role": "user", "content": "What is John Doe SSN 123-45-6789 account balance?"}]
  }' | jq
```

### 4. Verify Incident Created
```bash
# Check incidents after test requests
curl -s 'http://localhost:8000/api/v1/incidents' \
  -H "Authorization: Bearer $TOKEN" | jq
```

### 5. Check Detection Logs
```bash
/usr/local/bin/docker compose logs worker --tail=50 | grep -i detection
```

## Verification Checklist

- [ ] Proxy forwards requests to upstream LLM
- [ ] Requests are logged in proxy_requests table
- [ ] Responses are logged in proxy_responses table
- [ ] Hallucination detector runs on responses
- [ ] PII detector runs on requests and responses
- [ ] Compliance detector runs on financial content
- [ ] Incidents are created for detected violations
- [ ] Alerts are triggered for configured destinations

## Output Format
```
## Proxy Test Results - [TIMESTAMP]

### Connectivity
- Proxy endpoint: [reachable/error]
- Upstream LLM: [reachable/error]

### Detection
- Hallucination: [triggered/not triggered]
- PII Leak: [triggered/not triggered]
- Compliance: [triggered/not triggered]

### Incidents
- Created: [count]
- Severity breakdown: [critical/high/medium/low]

### Status: [PASS/FAIL]
```
