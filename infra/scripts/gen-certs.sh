#!/usr/bin/env bash
# infra/scripts/gen-certs.sh
#
# Generates a local Certificate Authority (CA) and signs a server cert for
# each service. This is what makes "HTTPS" real instead of decorative:
# the Gateway and Resource Service will only trust certs signed by THIS CA,
# so anything not holding these exact private keys cannot impersonate them.
#
# Week 4 reuses this same CA to also issue CLIENT certs for mTLS.
#
# Usage: ./gen-certs.sh
set -euo pipefail

CERT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/certs"
mkdir -p "$CERT_DIR"
cd "$CERT_DIR"

DAYS_VALID=825   # ~2.25 years -- browsers cap trusted certs around here; good habit even locally

echo "==> Cleaning old certs (if any)"
rm -f *.key *.crt *.csr *.srl

echo "==> 1. Generating CA private key + self-signed CA certificate"
openssl genrsa -out ca.key 4096
# -addext authorityKeyIdentifier: newer OpenSSL/Python TLS stacks (e.g. OpenSSL 3.2+)
# reject a CA cert that's missing an Authority Key Identifier, even on a
# self-signed root. Without this, cert verification fails with
# "Missing Authority Key Identifier" on newer systems.
openssl req -x509 -new -nodes -key ca.key -sha256 -days "$DAYS_VALID" \
  -subj "/C=US/O=SecureAPIPlatform/CN=SecureAPIPlatform-Local-CA" \
  -addext "basicConstraints=critical,CA:TRUE" \
  -addext "keyUsage=critical,keyCertSign,cRLSign" \
  -addext "authorityKeyIdentifier=keyid:always,issuer:always" \
  -addext "subjectKeyIdentifier=hash" \
  -out ca.crt

gen_service_cert () {
  local name="$1"
  echo "==> Generating cert for service: $name"

  # Private key
  openssl genrsa -out "${name}.key" 2048

  # Certificate Signing Request
  openssl req -new -key "${name}.key" \
    -subj "/C=US/O=SecureAPIPlatform/CN=${name}" \
    -out "${name}.csr"

  # SAN config so the cert is valid for both the Docker service name AND localhost
  # (you'll hit this service both from inside Docker's network and from your host machine)
  # authorityKeyIdentifier here too: newer OpenSSL/Python TLS stacks reject a
  # leaf cert whose issuer lacks an Authority Key Identifier, same reason as
  # the CA cert above.
  cat > "${name}.ext" <<EOF
subjectAltName = DNS:${name}, DNS:localhost, IP:127.0.0.1
extendedKeyUsage = serverAuth, clientAuth
authorityKeyIdentifier = keyid:always,issuer:always
subjectKeyIdentifier = hash
EOF

  # Sign the CSR with our CA -> this is what makes it trusted
  openssl x509 -req -in "${name}.csr" -CA ca.crt -CAkey ca.key -CAcreateserial \
    -out "${name}.crt" -days "$DAYS_VALID" -sha256 -extfile "${name}.ext"

  rm -f "${name}.csr" "${name}.ext"
}

gen_service_cert "gateway"
gen_service_cert "resource-service"
gen_service_cert "auth-server"

echo "==> Generating JWT signing keypair (RS256)"
# This is SEPARATE from the TLS certs above. TLS certs prove "who is this service."
# This keypair proves "who issued this token." Only auth-server gets the private key --
# Gateway and Resource Service only ever see the public key, so a compromised Gateway
# still cannot forge a valid token. Week 5 moves jwt-signing.key into Vault.
openssl genrsa -out jwt-signing.key 2048
openssl rsa -in jwt-signing.key -pubout -out jwt-signing.pub

echo "==> Generating HMAC signing secret (Gateway <-> Resource Service request signing)"
# Symmetric secret -- both sides need the SAME bytes, unlike the TLS/JWT keys above.
# Used to sign method+path+body+timestamp+nonce on every Gateway->Resource Service
# request (docs/signing-scheme.md has the exact canonical format). Week 5 moves this
# into Vault too, with a rotation runbook.
openssl rand -hex 32 > hmac-signing.key
tr -d '\n' < hmac-signing.key > hmac-signing.key.tmp && mv hmac-signing.key.tmp hmac-signing.key

chmod 600 ./*.key
chmod 644 ./*.crt ./*.pub

# Database bootstrap passwords (Sprint 10). Written to infra/.env, which
# docker-compose reads automatically and which is gitignored.
#
# IMPORTANT: only created if it doesn't already exist. Postgres sets its
# passwords ONCE, the first time its data volume is initialized -- if this
# script regenerated new passwords on every run, they'd stop matching the
# already-initialized database and the Resource Service would fail with
# "password authentication failed". To deliberately reset everything:
#   docker compose down -v && rm ../.env && ./gen-certs.sh
ENV_FILE="$CERT_DIR/../.env"
if [ ! -f "$ENV_FILE" ]; then
  echo "==> Generating database bootstrap passwords -> infra/.env"
  # Two DIFFERENT passwords on purpose: PG_ADMIN_PASSWORD is the Postgres
  # superuser (only the postgres container ever sees it); DB_PASSWORD is the
  # limited role the Resource Service connects as (pushed into Vault by
  # vault-init.sh -- the service never sees the admin password at all).
  {
    echo "PG_ADMIN_PASSWORD=$(openssl rand -hex 16)"
    echo "DB_PASSWORD=$(openssl rand -hex 16)"
  } > "$ENV_FILE"
  chmod 600 "$ENV_FILE"
else
  echo "==> infra/.env already exists -- keeping existing DB passwords (see comment in this script for why)"
fi
echo ""
echo "==> Done. Certs written to: $CERT_DIR"
echo "    ca.crt                  <- trust this to verify any service cert"
echo "    gateway.key/.crt        <- Gateway's server identity"
echo "    resource-service.key/.crt"
echo "    auth-server.key/.crt"
echo "    jwt-signing.key         <- auth-server ONLY (signs tokens)"
echo "    jwt-signing.pub         <- gateway + resource-service (verifies tokens)"
echo "    hmac-signing.key        <- gateway + resource-service (signs/verifies requests)"
echo "    (gateway.crt also serves as the mTLS CLIENT cert -- see docs/signing-scheme.md)"
echo ""
echo "These are gitignored (infra/certs/) -- regenerate any time with this script."
