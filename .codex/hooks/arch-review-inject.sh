#!/bin/bash

INPUT=$(cat)
PROMPT=$(printf '%s' "$INPUT" | jq -r '.prompt // empty' 2>/dev/null || true)

if [ -z "$PROMPT" ]; then
    exit 0
fi

if echo "$PROMPT" | grep -qiE '(implement|add|create|build|fix|refactor|modify|update|review).*(feature|service|agent|task|handler|model|component|module|endpoint|workflow|architecture|codebase)'; then
    cat << 'EOF'
{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"AGENTGUARD ARCHITECTURE: Read AGENTS.md, CLAUDE.md, and .github/ai-review/senior-review.md. Search existing proxy, detection, model, task, alert, WebSocket, and frontend concern homes. Preserve org_id isolation, PII and secret redaction, async API versus sync Celery contracts, detector registration, and the request -> detection -> persistence -> consumer -> dashboard path."}}
EOF
fi

exit 0
