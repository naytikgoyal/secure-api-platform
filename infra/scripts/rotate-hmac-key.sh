#!/usr/bin/env bash
# infra/scripts/rotate-hmac-key.sh
#
# Rotates the HMAC signing secret in Vault. This is the script referenced by
# docs/key-rotation-runbook.md and by the acceptance test in the PRD:
# "rotating the HMAC key in Vault immediately invalidates old-key-signed requests."
#
# IMPORTANT: Gateway and Resource Service fetch secrets from Vault ONCE at
# startup (see gateway/src/vaultClient.js and resource-service/vault_client.py).
# Rotating the secret in Vault does NOT retroactively change what's already
# loaded in a running process -- you must restart both services after rotating
# for them to pick up the new secret. This is a deliberate simplification
# documented as a residual limitation in the runbook (a production system
# would use short-lived leases + periodic re-fetch, or a signal-triggered
# reload).
#
# Usage: ./rotate-hmac-key.sh
set -euo pipefail

VAULT_ADDR="${VAULT_ADDR:-http://localhost:8200}"
VAULT_TOKEN="${VAULT_TOKEN:-dev-only-root-token-do-not-use-in-prod}"
export VAULT_ADDR VAULT_TOKEN

echo "==> Reading current HMAC key version..."
CURRENT=$(curl -s --header "X-Vault-Token: $VAULT_TOKEN" "$VAULT_ADDR/v1/secret/data/hmac-signing")
CURRENT_VERSION=$(echo "$CURRENT" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['metadata']['version'])")
echo "    Current version: $CURRENT_VERSION"

echo "==> Generating new HMAC secret..."
NEW_KEY=$(openssl rand -hex 32)

echo "==> Writing new version to Vault (KV v2 keeps the old version in history)..."
NEW_KEY_JSON=$(python3 -c "import json; print(json.dumps('$NEW_KEY'))")
curl -s -o /dev/null -w "HTTP %{http_code}\n" \
  --header "X-Vault-Token: $VAULT_TOKEN" \
  --request POST \
  --data "{\"data\": {\"key\": $NEW_KEY_JSON}}" \
  "$VAULT_ADDR/v1/secret/data/hmac-signing"

NEW_VERSION=$((CURRENT_VERSION + 1))
echo "    New version: $NEW_VERSION"
echo ""
echo "==> Rotation written to Vault. Old requests signed with version $CURRENT_VERSION"
echo "    remain valid ONLY until both Gateway and Resource Service are restarted."
echo "    Restart now to complete the rotation:"
echo ""
echo "        docker compose restart gateway resource-service"
echo ""
echo "    After restart, any request signed with the OLD key (version $CURRENT_VERSION)"
echo "    will be rejected with 401 'Invalid request signature' -- verified in"
echo "    docs/key-rotation-runbook.md's test procedure."
