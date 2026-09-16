#!/usr/bin/env bash
# Wrapper around `terraform apply` that forces a reviewed, saved plan and adds
# an explicit extra confirmation whenever the plan would destroy or replace
# anything. See RUNBOOK.md for the policy this encodes. Shared by every
# Terraform root module in this repo (terraform/, terraform/ci/, ...) — pass
# the target module's directory as the first argument.
#
# Usage: safe-apply.sh <terraform-directory> [extra terraform plan args...]
#   e.g. terraform/scripts/safe-apply.sh terraform
#        terraform/scripts/safe-apply.sh terraform/ci
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <terraform-directory> [extra terraform plan args...]" >&2
  exit 1
fi

TARGET_DIR="$1"
shift
cd "$TARGET_DIR"

PLAN_FILE="plan.tfplan"
trap 'rm -f "$PLAN_FILE"' EXIT

echo "==> terraform plan -out=$PLAN_FILE (in $TARGET_DIR)"
set +e
terraform plan -out="$PLAN_FILE" -detailed-exitcode "$@"
PLAN_EXIT=$?
set -e

case "$PLAN_EXIT" in
  0)
    echo "No changes. Nothing to apply."
    exit 0
    ;;
  1)
    echo "terraform plan failed." >&2
    exit 1
    ;;
  2)
    ;; # changes present — fall through
  *)
    echo "Unexpected terraform plan exit code: $PLAN_EXIT" >&2
    exit 1
    ;;
esac

DESTRUCTIVE="$(terraform show "$PLAN_FILE" | grep -E "will be destroyed|must be replaced" || true)"

if [ -n "$DESTRUCTIVE" ]; then
  echo
  echo "################################################################"
  echo "  WARNING — this plan will DESTROY or REPLACE resources:"
  echo "################################################################"
  echo "$DESTRUCTIVE"
  echo
  echo "If google_cloud_run_v2_service is in this list, its public URL will"
  echo "change on recreate — check/update the Cloudflare CNAME after applying."
  echo
  read -r -p "Type 'destroy is expected' to proceed, anything else cancels: " CONFIRM
  if [ "$CONFIRM" != "destroy is expected" ]; then
    echo "Aborted — nothing applied."
    exit 1
  fi
fi

echo "==> terraform apply $PLAN_FILE"
terraform apply "$PLAN_FILE"
