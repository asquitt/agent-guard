#!/bin/bash

INPUT=$(cat)
PROMPT=$(echo "$INPUT" | jq -r '.user_prompt // .message // empty' 2>/dev/null)

if [ -z "$PROMPT" ]; then
    exit 0
fi

if echo "$PROMPT" | grep -qiE '(implement|add|create|build|fix|refactor|modify|update|review).*(feature|service|agent|task|handler|model|component|module|endpoint|workflow|architecture|codebase)'; then
    cat << 'EOF'
{"additionalContext":"AGENTGUARD ARCHITECTURE: Read AGENTS.md, CLAUDE.md, and .github/ai-review/senior-review.md. Search existing proxy, detection, model, task, alert, WebSocket, and frontend concern homes. Preserve org_id isolation, PII and secret redaction, async API versus sync Celery contracts, detector registration, and the request -> detection -> persistence -> consumer -> dashboard path."}
EOF
fi

exit 0
