#!/bin/bash
# PreToolUse hook: Enforce verification before git commit

echo "[Pre-Commit Check] Verification required before commit" >&2

# Check for staged changes
STAGED=$(git diff --cached --name-only 2>/dev/null)

if [ -n "$STAGED" ]; then
    echo "[Pre-Commit] Staged files:" >&2
    echo "$STAGED" | head -10 >&2

    # Check for TypeScript files
    if echo "$STAGED" | grep -qE '\.(ts|tsx)$'; then
        echo "[Pre-Commit] TypeScript changes detected - ensure: npx tsc --noEmit passes" >&2
    fi

    # Check for Python files
    if echo "$STAGED" | grep -qE '\.py$'; then
        echo "[Pre-Commit] Python changes detected - ensure: pyright app/ passes" >&2
    fi

    # Check for model files
    if echo "$STAGED" | grep -qE 'models/.*\.py$'; then
        echo "[Pre-Commit] Model changes detected - ensure: python scripts/check_model_imports.py passes" >&2
    fi

    echo "[Pre-Commit] MANDATORY: Verify functionality before committing" >&2
fi

exit 0
