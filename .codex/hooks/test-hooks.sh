#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
config="$repo_root/.codex/hooks.json"
nested_dir="$repo_root/agentguard-backend/backend"

user_prompt_command=$(jq -r '.hooks.UserPromptSubmit[0].hooks[0].command' "$config")
prompt_output=$(printf '%s' '{"prompt":"Implement a new endpoint"}' | (cd "$nested_dir" && sh -c "$user_prompt_command"))
printf '%s' "$prompt_output" | jq -e '
  .hookSpecificOutput.hookEventName == "UserPromptSubmit" and
  (.hookSpecificOutput.additionalContext | contains("AGENTGUARD ARCHITECTURE"))
' >/dev/null

unmatched_output=$(printf '%s' '{"prompt":"hello"}' | (cd "$nested_dir" && sh -c "$user_prompt_command"))
test -z "$unmatched_output"

stop_command=$(jq -r '.hooks.Stop[0].hooks[0].command' "$config")
stop_output=$(printf '%s' '{"stop_hook_active":false}' | (cd "$nested_dir" && sh -c "$stop_command"))
printf '%s' "$stop_output" | jq -e '
  .decision == "block" and
  (.reason | contains("Never call an unmerged candidate shipped"))
' >/dev/null

repeat_output=$(printf '%s' '{"stop_hook_active":true}' | (cd "$nested_dir" && sh -c "$stop_command"))
test -z "$repeat_output"

echo "Codex hook contract checks passed"
