#!/bin/bash
# PostToolUse hook: Warn about tech debt after file modifications

# Get the file being modified from stdin (Claude hook format)
read -r INPUT
FILE_PATH=$(echo "$INPUT" | jq -r '.file_path // empty' 2>/dev/null)

if [ -z "$FILE_PATH" ]; then
    exit 0
fi

# Skip non-code files
if ! echo "$FILE_PATH" | grep -qE '\.(py|ts|tsx|js|jsx)$'; then
    exit 0
fi

# Check file size after edit
if [ -f "$FILE_PATH" ]; then
    LINE_COUNT=$(wc -l < "$FILE_PATH" | tr -d ' ')

    if [ "$LINE_COUNT" -gt 400 ]; then
        echo "[Tech Debt] $FILE_PATH now has $LINE_COUNT lines" >&2
    fi
fi

# Check for bare except in Python files
if echo "$FILE_PATH" | grep -qE '\.py$'; then
    if [ -f "$FILE_PATH" ]; then
        BARE_EXCEPTS=$(grep -c "except:" "$FILE_PATH" 2>/dev/null || echo 0)
        if [ "$BARE_EXCEPTS" -gt 0 ]; then
            echo "[Tech Debt Warning] $FILE_PATH has $BARE_EXCEPTS bare except clauses" >&2
            echo "[Tech Debt Warning] Fix with: except (SpecificError, TypeError) as e:" >&2
        fi

        # Check for Any type overuse
        ANY_COUNT=$(grep -c ": Any" "$FILE_PATH" 2>/dev/null || echo 0)
        if [ "$ANY_COUNT" -gt 5 ]; then
            echo "[Tech Debt Warning] $FILE_PATH has $ANY_COUNT Any types - consider specific types" >&2
        fi
    fi
fi

# Check for any type in TypeScript
if echo "$FILE_PATH" | grep -qE '\.(ts|tsx)$'; then
    if [ -f "$FILE_PATH" ]; then
        ANY_COUNT=$(grep -c ": any" "$FILE_PATH" 2>/dev/null || echo 0)
        if [ "$ANY_COUNT" -gt 0 ]; then
            echo "[Tech Debt Warning] $FILE_PATH has $ANY_COUNT 'any' types - use proper types" >&2
        fi
    fi
fi

exit 0
