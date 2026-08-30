#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

sha256_file() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  else
    shasum -a 256 "$1" | awk '{print $1}'
  fi
}

jq -e '
  .project == "AgentGuard" and
  .status == "mothballed" and
  .standalone_product.development == "frozen" and
  .standalone_product.deployments == "not_authorized" and
  .standalone_product.runtime_state == "unverified" and
  .allowed_work == [
    "preservation",
    "archive_security_fix",
    "read_only_evaluation",
    "bounded_asset_extraction_with_named_consumer"
  ] and
  .prohibited_without_reactivation == [
    "standalone_feature_development",
    "customer_or_pilot_claims",
    "deployment",
    "provider_or_runtime_spend",
    "wholesale_workflow_restoration"
  ] and
  .asset_destination.copy_whole_application == false and
  [.reactivation_gates[].id] == [
    "design_partner",
    "differentiation",
    "security_baseline",
    "unit_economics"
  ] and
  all(.reactivation_gates[]; (.requirement | type == "string" and length > 0))
' PROJECT_STATUS.json >/dev/null

grep -Fq 'Status: mothballed as a standalone product' README.md
grep -Fq 'Historical standalone-product material' docs/historical/STANDALONE_PRODUCT_README.md
grep -Fxq '# AgentGuard Archive and Asset Map' docs/ARCHIVE_AND_ASSET_MAP.md

active_workflow_count=$(find .github/workflows -maxdepth 1 -type f \( -name '*.yml' -o -name '*.yaml' \) | wc -l | tr -d ' ')
active_workflow=$(find .github/workflows -maxdepth 1 -type f \( -name '*.yml' -o -name '*.yaml' \) | sort)
test "$active_workflow_count" -eq 1
test "$active_workflow" = ".github/workflows/mothball-verification.yml"
test "$(sha256_file "$active_workflow")" = "6ad7cd2f7079f2bc4f4b29170f55419a55a4a644a69043234f618e6bb9430068"

while read -r expected_hash workflow; do
  test -n "$expected_hash"
  test -f "docs/historical/workflows/$workflow"
  test "$(sha256_file "docs/historical/workflows/$workflow")" = "$expected_hash"
done < docs/historical/workflows/SHA256SUMS

echo "AgentGuard mothball contract verified"
