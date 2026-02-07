#!/bin/bash
# PostToolUse hook: security pattern checks on Python and TypeScript files.
# Non-blocking (exit 0) — prints warnings on stderr.

FILE_PATH="${TOOL_INPUT_FILE_PATH:-}"
if [ -z "$FILE_PATH" ]; then
  exit 0
fi

WARNINGS=""

# Python checks
if [[ "$FILE_PATH" == *.py ]]; then
  # Hardcoded secret patterns (API keys, passwords in strings)
  if grep -nE '(password|secret|api_key|token)\s*=\s*["\x27][A-Za-z0-9]' "$FILE_PATH" 2>/dev/null | grep -vE '(settings\.|os\.environ|getenv|Field|#|test_|example)' | head -3; then
    WARNINGS+="WARNING: Possible hardcoded secret in $FILE_PATH\n"
  fi

  # f-string SQL (potential injection)
  if grep -nE 'f"(SELECT|INSERT|UPDATE|DELETE|DROP)' "$FILE_PATH" 2>/dev/null | head -3; then
    WARNINGS+="WARNING: f-string SQL detected in $FILE_PATH — use parameterized queries\n"
  fi

  # Missing org_id filter in service/api files
  if [[ "$FILE_PATH" == *services/* || "$FILE_PATH" == *api/* ]]; then
    if grep -nE '\.(query|execute|select)\(' "$FILE_PATH" 2>/dev/null | grep -vE 'org_id|org\.id|import' | head -3; then
      WARNINGS+="NOTE: Query without org_id filter in $FILE_PATH — verify tenant isolation\n"
    fi
  fi
fi

# TypeScript checks
if [[ "$FILE_PATH" == *.ts || "$FILE_PATH" == *.tsx ]]; then
  if grep -n 'dangerouslySetInnerHTML' "$FILE_PATH" 2>/dev/null | head -3; then
    WARNINGS+="WARNING: dangerouslySetInnerHTML in $FILE_PATH — verify XSS safety\n"
  fi
fi

if [ -n "$WARNINGS" ]; then
  echo -e "$WARNINGS" >&2
fi

exit 0
