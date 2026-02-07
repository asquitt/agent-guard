#!/bin/bash
# PostToolUse hook: dead code pattern checks on Python files.
# Non-blocking (exit 0) — prints warnings on stderr.

FILE_PATH="${TOOL_INPUT_FILE_PATH:-}"
if [ -z "$FILE_PATH" ] || [[ "$FILE_PATH" != *.py ]]; then
  exit 0
fi

WARNINGS=""

# Commented-out imports
if grep -nE '^\s*#\s*(from |import )' "$FILE_PATH" 2>/dev/null | head -3; then
  WARNINGS+="WARNING: Commented-out import in $FILE_PATH — remove or restore\n"
fi

# TODO without ticket reference
if grep -nE 'TODO(?!\(|: [A-Z]+-[0-9])' "$FILE_PATH" 2>/dev/null | head -3; then
  WARNINGS+="NOTE: TODO without ticket ref in $FILE_PATH\n"
fi

if [ -n "$WARNINGS" ]; then
  echo -e "$WARNINGS" >&2
fi

exit 0
