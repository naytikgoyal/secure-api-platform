#!/usr/bin/env bash
# infra/scripts/vault-init.sh
#
# Run this ONCE after `docker compose up -d vault` and BEFORE starting the
# other services. It:
#   1. Waits for Vault to be reachable
#   2. Enables the KV v2 secrets engine (if not already enabled)
#   3. Pushes the JWT signing keypair, HMAC secret, and a placeholder DB
#      credential (for a future persistence layer) into Vault
#   4. Shreds the local plaintext copies of jwt-signing.key, jwt-signing.pub,
#      and hmac-signing.key -- after this script runs, those secrets exist
#      ONLY inside Vault, never as files on disk. TLS certs/keys are
#      deliberately left alone (see docs/key-rotation-runbook.md for why
#      mTLS material isn't in Vault yet -- documented scope boundary, not
#      an oversight).
#
# Usage: ./vault-init.sh
set -euo pipefail

VAULT_ADDR="${VAULT_ADDR:-http://localhost:8200}"
VAULT_TOKEN="${VAULT_TOKEN:-dev-only-root-token-do-not-use-in-prod}"
CERT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/certs"

export VAULT_ADDR VAULT_TOKEN

echo "==> Waiting for Vault at $VAULT_ADDR ..."
for i in $(seq 1 30); do
  if curl -s -o /dev/null -w "%{http_code}" "$VAULT_ADDR/v1/sys/health" | grep -qE "200|429|472|473"; then
    echo "    Vault is up."
    break
  fi
  sleep 1
  if [ "$i" -eq 30 ]; then
    echo "ERROR: Vault did not become ready in time." >&2
    exit 1
  fi
done

vault_put () {
  local path="$1"
  local json_body="$2"
  curl -s -o /dev/null -w "%{http_code}" \
    --header "X-Vault-Token: $VAULT_TOKEN" \
    --request POST \
    --data "$json_body" \
    "$VAULT_ADDR/v1/secret/data/$path"
}

echo "==> Pushing JWT signing keypair to secret/jwt-signing"
JWT_PRIVATE=$(python3 -c "import json,sys; print(json.dumps(open('$CERT_DIR/jwt-signing.key').read()))")
JWT_PUBLIC=$(python3 -c "import json,sys; print(json.dumps(open('$CERT_DIR/jwt-signing.pub').read()))")
vault_put "jwt-signing" "{\"data\": {\"private_key\": $JWT_PRIVATE, \"public_key\": $JWT_PUBLIC}}"

echo "==> Pushing HMAC signing secret to secret/hmac-signing"
HMAC_KEY=$(python3 -c "import json,sys; print(json.dumps(open('$CERT_DIR/hmac-signing.key').read().strip()))")
vault_put "hmac-signing" "{\"data\": {\"key\": $HMAC_KEY}}"

echo "==> Pushing database credentials to secret/db-creds"
echo "    (the Resource Service fetches these at startup and connects to Postgres as this"
echo "     limited, non-superuser role -- it never sees the Postgres admin password)"
ENV_FILE="$CERT_DIR/../.env"
if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: $ENV_FILE not found. Run ./gen-certs.sh first (it creates the DB passwords)." >&2
  exit 1
fi
DB_PASSWORD=$(grep '^DB_PASSWORD=' "$ENV_FILE" | cut -d= -f2-)
if [ -z "$DB_PASSWORD" ]; then
  echo "ERROR: DB_PASSWORD missing from $ENV_FILE" >&2
  exit 1
fi
vault_put "db-creds" "{\"data\": {\"username\": \"orders_app\", \"password\": \"$DB_PASSWORD\"}}"

echo ""
echo "==> Shredding local plaintext copies (they now live ONLY in Vault)"
shred -u "$CERT_DIR/jwt-signing.key" "$CERT_DIR/jwt-signing.pub" "$CERT_DIR/hmac-signing.key" 2>/dev/null \
  || rm -f "$CERT_DIR/jwt-signing.key" "$CERT_DIR/jwt-signing.pub" "$CERT_DIR/hmac-signing.key"

echo ""
echo "==> Done. Verify: 'grep -r \"BEGIN PRIVATE KEY\" $CERT_DIR' should now return nothing"
echo "    (TLS certs/keys remain in $CERT_DIR -- see docs/key-rotation-runbook.md)"
echo ""
echo "You can now run: docker compose up --build"
