#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

jq -e '
  .project == "AgentGuard" and
  .status == "mothballed" and
  .standalone_product.development == "frozen" and
  .standalone_product.deployments == "not_authorized" and
  .standalone_product.runtime_state == "unverified" and
  (.reactivation_gates | length == 4)
' PROJECT_STATUS.json >/dev/null

grep -Fq 'Status: mothballed as a standalone product' README.md
grep -Fq 'Historical standalone-product material' docs/historical/STANDALONE_PRODUCT_README.md
grep -Fxq '# AgentGuard Archive and Asset Map' docs/ARCHIVE_AND_ASSET_MAP.md

active_workflow_count=$(find .github/workflows -maxdepth 1 -type f \( -name '*.yml' -o -name '*.yaml' \) | wc -l | tr -d ' ')
active_workflow=$(find .github/workflows -maxdepth 1 -type f \( -name '*.yml' -o -name '*.yaml' \) | sort)
test "$active_workflow_count" -eq 1
test "$active_workflow" = ".github/workflows/mothball-verification.yml"
grep -Eq '^[[:space:]]+workflow_dispatch:' "$active_workflow"
if grep -REn '^[[:space:]]+(push|pull_request|pull_request_target|schedule|workflow_run|repository_dispatch|merge_group):' .github/workflows; then
  echo "Automatic GitHub Actions trigger found in mothballed repository" >&2
  exit 1
fi

for workflow in build.yml ci.yml deploy-production.yml deploy-staging.yml release.yml; do
  test -f "docs/historical/workflows/$workflow"
done

echo "AgentGuard mothball contract verified"
