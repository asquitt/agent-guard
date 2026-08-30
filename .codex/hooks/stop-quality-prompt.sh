#!/bin/bash

INPUT=$(cat)
STOP_HOOK_ACTIVE=$(printf '%s' "$INPUT" | jq -r 'if .stop_hook_active == true then "true" else "false" end' 2>/dev/null || printf 'false')

if [ "$STOP_HOOK_ACTIVE" = "true" ]; then
    exit 0
fi

cat << 'EOF'
{"decision":"block","reason":"Before completing: preserve unrelated work. Run focused and changed-stack gates; prove the real organization-scoped detector, persistence, consumer, and UI outcome when product behavior changed; test auth and tenant negatives where applicable; require exact-commit review for material changes; label every unavailable gate or unverified claim. At an authorized shipping boundary, commit the coherent checkpoint, push once, and report the exact PR state: absent, draft, ready, merged, or closed. Never call an unmerged candidate shipped."}
EOF

exit 0
