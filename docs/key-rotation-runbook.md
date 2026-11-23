# Key Rotation Runbook

This runbook covers rotating the two secrets Vault manages for this platform:
the HMAC signing key and the JWT RS256 keypair. It also documents what's
**deliberately not yet automated**, and why.

## Secrets inventory (what's in Vault, and what isn't)

| Secret | Location | Rotation covered here? |
| :--- | :--- | :--- |
| JWT signing keypair (`jwt-signing.key`/`.pub`) | Vault `secret/jwt-signing` | Yes (below) |
| HMAC signing key (`hmac-signing.key`) | Vault `secret/hmac-signing` | Yes (below) — this is the one with a working script |
| Placeholder DB credentials | Vault `secret/db-creds` | N/A — not consumed by any service yet |
| TLS certs/keys (mTLS identity, CA) | Local files in `infra/certs/`, gitignored | **Not in Vault yet** — see "Residual scope" below |

## Why secrets are fetched once at startup, not per-request

Every service (`gateway`, `auth-server`, `resource-service`) reads its secrets
from Vault exactly once, at process startup, and holds them in memory for the
life of the process. This is simpler than a per-request or leased/TTL-based
fetch, but it has one direct consequence you need to know:

> **Rotating a secret in Vault does NOT retroactively affect a running
> process.** The new value only takes effect after that service restarts.

This is why `infra/scripts/rotate-hmac-key.sh` ends with an explicit reminder
to run `docker compose restart gateway resource-service` — rotation isn't
"done" until both sides have actually reloaded.

**Production alternative (not implemented here, documented as a stretch
goal):** short-lived Vault leases with a periodic background re-fetch, or a
`SIGHUP`-triggered reload, so rotation takes effect without a restart. This
project uses the simpler restart-based model deliberately, to keep the
security *properties* (secrets never touch disk in plaintext, rotation
provably invalidates old signatures) demonstrable without the added
complexity of a live-reload system.

## Rotating the HMAC signing key

**When to do this:** on a fixed schedule (e.g. quarterly) as a hygiene
practice, or immediately if you suspect the key has leaked (e.g. it appeared
in a log, a screen share, or a compromised container).

```bash
cd infra/scripts
./rotate-hmac-key.sh
```

What it does:
1. Reads the current key's version number from Vault (KV v2 keeps full version history — nothing is destroyed).
2. Generates a new 256-bit random key.
3. Writes it to Vault as a new version at the same path.
4. Prints the restart command you need to run next.

```bash
docker compose restart gateway resource-service
```

**Verification procedure** (this is the exact test that proves rotation worked):
1. Before restarting, capture a validly-signed request (or note the current HMAC key value).
2. Restart both services as instructed.
3. Replay the pre-rotation signed request against the Resource Service.
4. Expected result: `401 {"error": "unauthorized", "message": "Invalid request signature."}` — the old key no longer verifies anything, because the Resource Service only holds the new key in memory.

This exact procedure was run and verified during Week 5 development — see the
project's build notes / commit history for the before/after HTTP responses.

## Rotating the JWT signing keypair

More disruptive than HMAC rotation, because **every access token issued under
the old key becomes unverifiable the moment the Gateway/Resource Service
restart with the new public key** — including tokens that haven't expired yet.
There's no overlap/grace period in the current implementation.

```bash
cd infra/scripts
openssl genrsa -out /tmp/new-jwt-signing.key 2048
openssl rsa -in /tmp/new-jwt-signing.key -pubout -out /tmp/new-jwt-signing.pub

curl --header "X-Vault-Token: $VAULT_TOKEN" \
  --request POST \
  --data "{\"data\": {\"private_key\": \"$(cat /tmp/new-jwt-signing.key)\", \"public_key\": \"$(cat /tmp/new-jwt-signing.pub)\"}}" \
  "$VAULT_ADDR/v1/secret/data/jwt-signing"

rm /tmp/new-jwt-signing.key /tmp/new-jwt-signing.pub  # never leave these on disk
docker compose restart auth-server gateway resource-service
```

**Production alternative (documented, not implemented):** issue the new
keypair under a new `kid` (key ID), publish both old and new public keys
simultaneously (a JWKS endpoint with multiple keys), and only retire the old
key after its longest-lived outstanding token has naturally expired (≤15
minutes here, since access tokens are short-lived by design — see
`docs/threat-model.md` NFR-2). This project's single-key model is simpler and
appropriate for a 15-minute token lifetime, but wouldn't scale to a system
with longer-lived tokens.

## Residual scope: why TLS/mTLS certs aren't in Vault (yet)

Vault has a PKI secrets engine specifically for issuing and rotating
short-lived TLS certificates, which would be the "correct" production answer
here. It's deliberately out of scope for this project: it requires standing
up Vault as an intermediate CA, configuring cert issuance roles, and having
every service request a fresh cert on a schedule — meaningfully more
infrastructure than the KV-based secret storage this week covers. Documented
as a stretch goal (see the PRD, Section 12) rather than treated as an
oversight.

## What a real incident response would add on top of this runbook

This runbook covers *planned* rotation. A real *suspected compromise* would
also require, at minimum: revoking the compromised secret's Vault lease
immediately (not waiting for a scheduled rotation), auditing Vault's access
log for what was read using the old token, and checking
`docs/threat-model.md`'s residual risk section for what else that secret
could have touched.
