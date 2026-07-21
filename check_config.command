#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

check_key() {
  local key="$1"
  if awk -F= -v k="$key" '$1==k && length(substr($0,index($0,"=")+1))>0 {found=1} END{exit !found}' .env; then
    printf '✓ %s is configured\n' "$key"
  else
    printf '✗ %s is missing\n' "$key"
  fi
}

echo "BNZ Customer Intelligence Lab configuration"
echo
check_key BEDROCK_EVALUATION_MODEL_ID
check_key AWS_PROFILE
check_key AWS_REGION
check_key LEX_BOT_ID
check_key LEX_BOT_ALIAS_ID
check_key LEX_LOCALE_ID
echo
echo "AWS session:"
aws sts get-caller-identity --profile bnz-demo --output table 2>&1 || true
echo
read -r -p "Press Return to close..." _
