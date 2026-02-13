#!/usr/bin/env bash
# AgentGuard Security Audit Script
#
# Runs 6 automated checks and generates a markdown report.
# Exit code 1 if any Critical/High findings, 0 otherwise.
#
# Usage: ./run_audit.sh [--api-url http://localhost:8001]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/agentguard-backend/backend"
FRONTEND_DIR="$PROJECT_ROOT/agentguard-frontend"
API_URL="${1:-http://localhost:8001}"
REPORT_DIR="$SCRIPT_DIR/reports"
DATE=$(date +%Y-%m-%d)
REPORT_FILE="$REPORT_DIR/audit-report-${DATE}.md"

CRITICAL=0
HIGH=0
MEDIUM=0
LOW=0
INFO=0

mkdir -p "$REPORT_DIR"

# --- Report header ---
cat > "$REPORT_FILE" << EOF
# AgentGuard Security Audit Report

**Date:** $DATE
**Auditor:** Automated (run_audit.sh)
**Target:** $API_URL

---

EOF

echo "=== AgentGuard Security Audit ==="
echo "Report: $REPORT_FILE"
echo ""

# ============================================================
# Check 1: Python Dependency Vulnerabilities
# ============================================================
echo "--- Check 1: Python Dependencies (pip-audit) ---"
echo "## 1. Python Dependency Vulnerabilities" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

if command -v pip-audit &>/dev/null; then
    PIP_AUDIT_OUT=$(pip-audit -r "$BACKEND_DIR/requirements.txt" --format json 2>/dev/null || true)
    VULN_COUNT=$(echo "$PIP_AUDIT_OUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    deps = data.get('dependencies', [])
    vulns = [d for d in deps if d.get('vulns')]
    print(len(vulns))
except:
    print(0)
" 2>/dev/null || echo "0")

    if [ "$VULN_COUNT" -gt 0 ]; then
        HIGH=$((HIGH + VULN_COUNT))
        echo "  FOUND: $VULN_COUNT vulnerable packages"
        echo "**Severity: HIGH** - $VULN_COUNT vulnerable package(s) found" >> "$REPORT_FILE"
        echo "" >> "$REPORT_FILE"
        echo "| Package | Version | Vulnerability | Fix Version |" >> "$REPORT_FILE"
        echo "|---------|---------|---------------|-------------|" >> "$REPORT_FILE"
        echo "$PIP_AUDIT_OUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for dep in data.get('dependencies', []):
        for v in dep.get('vulns', []):
            fix = v.get('fix_versions', ['N/A'])
            fix_str = ', '.join(fix) if fix else 'N/A'
            print(f\"| {dep['name']} | {dep['version']} | {v['id']} | {fix_str} |\")
except:
    pass
" >> "$REPORT_FILE" 2>/dev/null
    else
        echo "  OK: No vulnerabilities found"
        echo "**No vulnerabilities found.**" >> "$REPORT_FILE"
        INFO=$((INFO + 1))
    fi
else
    echo "  SKIPPED: pip-audit not installed (pip install pip-audit)"
    echo "*Skipped: pip-audit not installed.*" >> "$REPORT_FILE"
fi
echo "" >> "$REPORT_FILE"

# ============================================================
# Check 2: Node.js Dependency Vulnerabilities
# ============================================================
echo "--- Check 2: Node.js Dependencies (npm audit) ---"
echo "## 2. Node.js Dependency Vulnerabilities" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

if command -v npm &>/dev/null && [ -f "$FRONTEND_DIR/package.json" ]; then
    NPM_AUDIT_OUT=$(cd "$FRONTEND_DIR" && npm audit --json 2>/dev/null || true)
    NPM_VULNS=$(echo "$NPM_AUDIT_OUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    meta = data.get('metadata', {}).get('vulnerabilities', {})
    c = meta.get('critical', 0)
    h = meta.get('high', 0)
    m = meta.get('moderate', 0)
    l = meta.get('low', 0)
    print(f'{c},{h},{m},{l}')
except:
    print('0,0,0,0')
" 2>/dev/null || echo "0,0,0,0")

    IFS=',' read -r NPM_C NPM_H NPM_M NPM_L <<< "$NPM_VULNS"
    CRITICAL=$((CRITICAL + NPM_C))
    HIGH=$((HIGH + NPM_H))
    MEDIUM=$((MEDIUM + NPM_M))
    LOW=$((LOW + NPM_L))
    TOTAL_NPM=$((NPM_C + NPM_H + NPM_M + NPM_L))

    if [ "$TOTAL_NPM" -gt 0 ]; then
        echo "  FOUND: $TOTAL_NPM vulnerabilities (critical=$NPM_C, high=$NPM_H, moderate=$NPM_M, low=$NPM_L)"
        echo "**$TOTAL_NPM vulnerabilities found:** Critical=$NPM_C, High=$NPM_H, Moderate=$NPM_M, Low=$NPM_L" >> "$REPORT_FILE"
        echo "" >> "$REPORT_FILE"
        echo "Run \`cd agentguard-frontend && npm audit\` for full details." >> "$REPORT_FILE"
    else
        echo "  OK: No vulnerabilities found"
        echo "**No vulnerabilities found.**" >> "$REPORT_FILE"
        INFO=$((INFO + 1))
    fi
else
    echo "  SKIPPED: npm not available or package.json missing"
    echo "*Skipped: npm not available or package.json missing.*" >> "$REPORT_FILE"
fi
echo "" >> "$REPORT_FILE"

# ============================================================
# Check 3: Python Static Security Analysis (Bandit)
# ============================================================
echo "--- Check 3: Static Analysis (bandit) ---"
echo "## 3. Python Static Security Analysis (Bandit)" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

if command -v bandit &>/dev/null; then
    BANDIT_OUT=$(bandit -r "$BACKEND_DIR/app/" -x "$BACKEND_DIR/app/tests" -f json -q 2>/dev/null || true)
    BANDIT_ISSUES=$(echo "$BANDIT_OUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    results = data.get('results', [])
    high = [r for r in results if r['issue_severity'] == 'HIGH' and r['issue_confidence'] != 'LOW']
    med = [r for r in results if r['issue_severity'] == 'MEDIUM' and r['issue_confidence'] != 'LOW']
    low = [r for r in results if r['issue_severity'] == 'LOW']
    print(f'{len(high)},{len(med)},{len(low)}')
except:
    print('0,0,0')
" 2>/dev/null || echo "0,0,0")

    IFS=',' read -r B_H B_M B_L <<< "$BANDIT_ISSUES"
    HIGH=$((HIGH + B_H))
    MEDIUM=$((MEDIUM + B_M))
    LOW=$((LOW + B_L))
    TOTAL_B=$((B_H + B_M + B_L))

    if [ "$TOTAL_B" -gt 0 ]; then
        echo "  FOUND: $TOTAL_B issues (high=$B_H, medium=$B_M, low=$B_L)"
        echo "**$TOTAL_B issues found:** High=$B_H, Medium=$B_M, Low=$B_L" >> "$REPORT_FILE"
        echo "" >> "$REPORT_FILE"
        echo "| Severity | Confidence | File | Line | Issue |" >> "$REPORT_FILE"
        echo "|----------|------------|------|------|-------|" >> "$REPORT_FILE"
        echo "$BANDIT_OUT" | python3 -c "
import sys, json, os
try:
    data = json.load(sys.stdin)
    for r in sorted(data.get('results', []), key=lambda x: x['issue_severity'], reverse=True):
        if r['issue_confidence'] == 'LOW':
            continue
        f = os.path.basename(r['filename'])
        print(f\"| {r['issue_severity']} | {r['issue_confidence']} | {f} | {r['line_number']} | {r['issue_text']} |\")
except:
    pass
" >> "$REPORT_FILE" 2>/dev/null
    else
        echo "  OK: No issues found"
        echo "**No issues found.**" >> "$REPORT_FILE"
        INFO=$((INFO + 1))
    fi
else
    echo "  SKIPPED: bandit not installed (pip install bandit)"
    echo "*Skipped: bandit not installed.*" >> "$REPORT_FILE"
fi
echo "" >> "$REPORT_FILE"

# ============================================================
# Check 4: Dockerfile Security
# ============================================================
echo "--- Check 4: Dockerfile Security ---"
echo "## 4. Container Security (Dockerfile)" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

DOCKERFILE="$BACKEND_DIR/Dockerfile"
if [ -f "$DOCKERFILE" ]; then
    DOCKER_ISSUES=0

    if ! grep -q "^USER " "$DOCKERFILE"; then
        MEDIUM=$((MEDIUM + 1))
        DOCKER_ISSUES=$((DOCKER_ISSUES + 1))
        echo "  MEDIUM: Container runs as root (no USER directive)"
        echo "- **MEDIUM:** Container runs as root — no \`USER\` directive found. Add a non-root user." >> "$REPORT_FILE"
    fi

    if ! grep -q "HEALTHCHECK" "$DOCKERFILE"; then
        LOW=$((LOW + 1))
        DOCKER_ISSUES=$((DOCKER_ISSUES + 1))
        echo "  LOW: No HEALTHCHECK in Dockerfile"
        echo "- **LOW:** No \`HEALTHCHECK\` instruction in Dockerfile (handled by docker-compose, but good practice to include)." >> "$REPORT_FILE"
    fi

    if [ "$DOCKER_ISSUES" -eq 0 ]; then
        echo "  OK: Dockerfile passes checks"
        echo "**All checks passed.**" >> "$REPORT_FILE"
        INFO=$((INFO + 1))
    fi
else
    echo "  SKIPPED: Dockerfile not found at $DOCKERFILE"
    echo "*Skipped: Dockerfile not found.*" >> "$REPORT_FILE"
fi
echo "" >> "$REPORT_FILE"

# ============================================================
# Check 5: Hardcoded Secrets Scan
# ============================================================
echo "--- Check 5: Hardcoded Secrets Scan ---"
echo "## 5. Hardcoded Secrets Scan" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

SECRETS_FOUND=0
SECRETS_TMP=$(mktemp)

# Scan Python source (excluding known false positives)
grep -rn \
    --include="*.py" \
    --exclude="conftest.py" \
    --exclude="config.py" \
    --exclude="test_*.py" \
    -E '(sk-[a-zA-Z0-9]{20,}|sk_live_[a-zA-Z0-9]{20,}|ag_live_[a-f0-9]{32,}|AKIA[0-9A-Z]{16})' \
    "$BACKEND_DIR/app/" >> "$SECRETS_TMP" 2>/dev/null || true

# Scan TypeScript source
grep -rn \
    --include="*.ts" \
    --include="*.tsx" \
    --exclude-dir="node_modules" \
    --exclude-dir=".next" \
    -E '(sk-[a-zA-Z0-9]{20,}|sk_live_[a-zA-Z0-9]{20,}|ag_live_[a-f0-9]{32,}|AKIA[0-9A-Z]{16})' \
    "$FRONTEND_DIR/src/" >> "$SECRETS_TMP" 2>/dev/null || true

SECRETS_FOUND=$(wc -l < "$SECRETS_TMP" | tr -d ' ')

if [ "$SECRETS_FOUND" -gt 0 ]; then
    HIGH=$((HIGH + SECRETS_FOUND))
    echo "  HIGH: $SECRETS_FOUND potential hardcoded secrets found"
    echo "**HIGH: $SECRETS_FOUND potential hardcoded secret(s) found**" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    echo '```' >> "$REPORT_FILE"
    cat "$SECRETS_TMP" >> "$REPORT_FILE"
    echo '```' >> "$REPORT_FILE"
else
    echo "  OK: No hardcoded secrets found"
    echo "**No hardcoded secrets found.**" >> "$REPORT_FILE"
    INFO=$((INFO + 1))
fi
rm -f "$SECRETS_TMP"
echo "" >> "$REPORT_FILE"

# ============================================================
# Check 6: Security Headers Validation
# ============================================================
echo "--- Check 6: Security Headers ---"
echo "## 6. Security Headers Validation" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

HEADERS_TMP=$(mktemp)
if curl -sf -o /dev/null "$API_URL/health" 2>/dev/null; then
    curl -sI "$API_URL/health" > "$HEADERS_TMP" 2>/dev/null

    echo "| Header | Expected | Status |" >> "$REPORT_FILE"
    echo "|--------|----------|--------|" >> "$REPORT_FILE"

    EXPECTED_HEADERS=(
        "x-content-type-options:nosniff"
        "x-frame-options:DENY"
        "x-xss-protection:1; mode=block"
        "referrer-policy:strict-origin-when-cross-origin"
        "content-security-policy:default-src"
        "cache-control:no-store"
        "permissions-policy:camera=()"
    )

    MISSING_HEADERS=0
    for entry in "${EXPECTED_HEADERS[@]}"; do
        HEADER_NAME="${entry%%:*}"
        HEADER_VALUE="${entry#*:}"
        if grep -qi "$HEADER_NAME.*$HEADER_VALUE" "$HEADERS_TMP"; then
            echo "| $HEADER_NAME | $HEADER_VALUE | Present |" >> "$REPORT_FILE"
            INFO=$((INFO + 1))
        else
            echo "| $HEADER_NAME | $HEADER_VALUE | **MISSING** |" >> "$REPORT_FILE"
            LOW=$((LOW + 1))
            MISSING_HEADERS=$((MISSING_HEADERS + 1))
        fi
    done

    if [ "$MISSING_HEADERS" -gt 0 ]; then
        echo "  LOW: $MISSING_HEADERS expected security headers missing"
    else
        echo "  OK: All security headers present"
    fi
else
    echo "  SKIPPED: API not reachable at $API_URL"
    echo "*Skipped: API not reachable at $API_URL. Start Docker Compose first.*" >> "$REPORT_FILE"
fi
rm -f "$HEADERS_TMP"
echo "" >> "$REPORT_FILE"

# ============================================================
# Summary
# ============================================================
echo ""
echo "=== Summary ==="
echo "  Critical: $CRITICAL"
echo "  High:     $HIGH"
echo "  Medium:   $MEDIUM"
echo "  Low:      $LOW"
echo "  Info:     $INFO"

# Insert summary after header (line 7)
SUMMARY=$(cat << EOF
## Summary

| Severity | Count |
|----------|-------|
| Critical | $CRITICAL |
| High | $HIGH |
| Medium | $MEDIUM |
| Low | $LOW |
| Info | $INFO |

EOF
)

# Use python to insert summary after the horizontal rule
python3 -c "
import sys
with open('$REPORT_FILE', 'r') as f:
    content = f.read()
parts = content.split('---\n\n', 1)
if len(parts) == 2:
    new_content = parts[0] + '---\n\n' + '''$SUMMARY''' + '\n---\n\n' + parts[1]
    with open('$REPORT_FILE', 'w') as f:
        f.write(new_content)
"

# Append recommendations
cat >> "$REPORT_FILE" << 'EOF'
## Recommendations

1. **Fix all Critical/High dependency vulnerabilities** — update affected packages or pin to patched versions
2. **Add non-root USER to Dockerfile** — `RUN adduser --system --no-create-home appuser && USER appuser`
3. **Run `pip-audit` and `npm audit` in CI** — catch vulnerabilities before they reach production
4. **Add `bandit` to pre-commit hooks** — catch security issues at commit time
5. **Review any hardcoded secrets** — rotate compromised keys, move to environment variables
EOF

echo ""
echo "Report written to: $REPORT_FILE"

# Exit code
if [ "$CRITICAL" -gt 0 ] || [ "$HIGH" -gt 0 ]; then
    echo "RESULT: FAIL (Critical/High findings detected)"
    exit 1
fi
echo "RESULT: PASS"
exit 0
