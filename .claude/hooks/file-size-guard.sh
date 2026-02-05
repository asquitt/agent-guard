#!/bin/bash
# PreToolUse hook: Prevent tech debt by blocking large files
# Triggers on: Write, Edit tools for .py, .ts, .tsx files

# Get the file being modified from stdin (Claude hook format)
read -r INPUT
FILE_PATH=$(echo "$INPUT" | jq -r '.file_path // empty' 2>/dev/null)

if [ -z "$FILE_PATH" ]; then
    exit 0  # No file path, allow operation
fi

# Skip non-code files
if ! echo "$FILE_PATH" | grep -qE '\.(py|ts|tsx|js|jsx)$'; then
    exit 0
fi

# Check if file exists and get line count
if [ -f "$FILE_PATH" ]; then
    LINE_COUNT=$(wc -l < "$FILE_PATH" | tr -d ' ')

    # Warning at 400 lines
    if [ "$LINE_COUNT" -gt 400 ] && [ "$LINE_COUNT" -le 600 ]; then
        echo "[Tech Debt Warning] $FILE_PATH has $LINE_COUNT lines (approaching 800 limit)" >&2
        echo "[Tech Debt Warning] Consider splitting into a package/module soon" >&2
    fi

    # Strong warning at 600 lines
    if [ "$LINE_COUNT" -gt 600 ] && [ "$LINE_COUNT" -le 800 ]; then
        echo "[Tech Debt ALERT] $FILE_PATH has $LINE_COUNT lines (near 800 limit!)" >&2
        echo "[Tech Debt ALERT] Split this file before adding more code" >&2
    fi

    # Block at 800 lines
    if [ "$LINE_COUNT" -gt 800 ]; then
        echo "[BLOCKED] $FILE_PATH exceeds 800 lines ($LINE_COUNT)" >&2
        echo "[BLOCKED] You MUST split this file before adding more code" >&2
        echo "[BLOCKED] Use package pattern: __init__.py + constants.py + utils.py + core.py" >&2
        exit 1
    fi
fi

exit 0
