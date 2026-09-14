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

# Public README wording is independent of the machine-readable runtime controls.
grep -Fxq '# AgentGuard' README.md
grep -Fq 'Historical standalone-product material' docs/historical/STANDALONE_PRODUCT_README.md
grep -Fxq '# AgentGuard Archive and Asset Map' docs/ARCHIVE_AND_ASSET_MAP.md

active_workflow_count=$(find .github/workflows -maxdepth 1 -type f \( -name '*.yml' -o -name '*.yaml' \) | wc -l | tr -d ' ')
active_workflow=$(find .github/workflows -maxdepth 1 -type f \( -name '*.yml' -o -name '*.yaml' \) | sort)
test "$active_workflow_count" -eq 1
test "$active_workflow" = ".github/workflows/mothball-verification.yml"
test "$(sha256_file "$active_workflow")" = "6ad7cd2f7079f2bc4f4b29170f55419a55a4a644a69043234f618e6bb9430068"

historical_dir="docs/historical/workflows"
historical_workflow_count=$(find "$historical_dir" -maxdepth 1 -type f \( -name '*.yml' -o -name '*.yaml' \) | wc -l | tr -d ' ')
test "$historical_workflow_count" -eq 5
test "$(sha256_file "$historical_dir/SHA256SUMS")" = "14ed1b10771ca999bf4958a6a7fde11bfea3c5d787d92b287976869a7741678d"
test "$(sha256_file "$historical_dir/build.yml")" = "5377c0404480baa0f7e630e2fd8663054660175b94653daa111978dc5192e3df"
test "$(sha256_file "$historical_dir/ci.yml")" = "3d5d89ed5ffcff20ad8b87aef8810b668b7b5a7132a212882fc6b1f371c4b754"
test "$(sha256_file "$historical_dir/deploy-production.yml")" = "b9a33b1789cbc7ef1028bfeb5a96e601dc48bca05ac3df07bcb551e342df4ef3"
test "$(sha256_file "$historical_dir/deploy-staging.yml")" = "31c2b233e9cc148f77f0c3e29ca734efd4f6037fd2f6184e9153992aad7f08ec"
test "$(sha256_file "$historical_dir/release.yml")" = "9353717ab1beadf363cb9002799b8c9dec54d1a7790c7affcfe5628b325496e2"

echo "AgentGuard mothball contract verified"
