# Secure API Communication Platform

A zero-trust, defense-in-depth microservices architecture built to demonstrate real API security engineering: mutual TLS, HMAC-signed and replay-protected requests, OAuth2/JWT auth with independently-enforced scopes at two service layers, HashiCorp Vault-managed secrets with a working key-rotation procedure, Redis-backed rate limiting, structured observability, and a live-fire attacker toolkit that validates every control end-to-end.

Every claim below has been run and verified — not just written. See [`docs/build-log.md`](docs/build-log.md) for the full week-by-week record with real command output, and [`docs/attack-report.md`](docs/attack-report.md) for the adversarial test results, including two real bugs found and fixed mid-build.

## Architecture

```
Client ──HTTPS──▶ API Gateway ──mTLS + HMAC-signed──▶ Resource Service
  │              (Node/Express)                      (Python/FastAPI)
  │                    │                                    │
  └──HTTPS──▶ Auth Server                          Redis (nonces, rate limits)
             (issues RS256 JWTs)                          │
                        │                                  │
                        └──────────── HashiCorp Vault ──────┘
                              (JWT keys, HMAC secret)
```

Full diagram with trust boundaries and data flow: [`docs/architecture-diagram.md`](docs/architecture-diagram.md).

**The core security property**: the Attacker Toolkit has exactly one entry point into this system — the public Gateway. Even a fully successful attack at that boundary still has to pass mutual TLS, HMAC signature verification, nonce-based replay protection, and independent scope checks at the Resource Service before touching any data. That's proven, not asserted — see the attack report.

## What's actually defended, and how

| Threat | Control | Verified in |
| :--- | :--- | :--- |
| Stolen/replayed access token | RS256 JWT, 15-min expiry, mTLS on the internal hop | `docs/build-log.md` Week 3-4 |
| Captured request replayed later | HMAC signature + nonce (Redis, 5-min TTL) + timestamp window | `attacker-toolkit/attack_replay.py` |
| JWT forgery (wrong key, `alg:none`, algorithm confusion) | Pinned algorithm (`RS256` only) in every verifier | `attacker-toolkit/attack_token_forgery.py` |
| BOLA/IDOR (reading another user's data) | Ownership check against the verified token's `sub`, enforced independently at both services | `docs/attack-report.md`, `docs/build-log.md` Week 3 |
| Credential brute-forcing | Redis-backed rate limiting (10/min on `/auth/login`), identical error for wrong-password vs. no-such-user | `attacker-toolkit/attack_bruteforce.py` |
| Plaintext MITM / TLS downgrade | TLS 1.2+ only, refused at the handshake for anything else | `attacker-toolkit/attack_mitm_downgrade.py` |
| Secret leakage (keys on disk, in logs, in git history) | Vault-managed JWT/HMAC secrets shredded from local disk after load; real `gitleaks` scan run against the repo | `docs/key-rotation-runbook.md`, `docs/build-log.md` Week 5 |
| SQL injection | Real PostgreSQL, every query parameterized (`resource-service/db.py`); a live injection demonstrated against a vulnerable version, then defeated by the real one; app DB role runs least-privilege (verified: can't create roles/databases, run OS commands, or reach other databases) | `docs/sql-injection-demo.md` |
| Injection (XSS-looking input) | React's default JSX escaping (no `dangerouslySetInnerHTML`/`innerHTML` anywhere in the dashboard — grepped, not assumed) | `docs/threat-model.md` residual risk section |

## Quickstart

```bash
git clone <this-repo> && cd secure-api-platform/infra
./scripts/gen-certs.sh              # generates TLS certs, JWT keypair, HMAC key, and infra/.env (DB passwords)
docker compose up -d vault           # start Vault first
./scripts/vault-init.sh              # push secrets into Vault (incl. DB creds), shred local copies
docker compose up --build            # bring up everything else, incl. PostgreSQL
```

Then:
- **API**: `https://localhost:3000` (Gateway) — see `docs/postman-collection.json` for a ready-to-run request suite
- **Dashboard**: `http://localhost:5173` — log in with `admin` / `adminpass456`
- **Grafana**: `http://localhost:3001` (`admin`/`admin`) — pre-provisioned "Security Overview" dashboard
- **Run the attacker toolkit**: `cd attacker-toolkit && pip install -r requirements.txt && python3 run_all.py`

Full setup detail, demo user credentials, and troubleshooting: [`docs/build-log.md`](docs/build-log.md).

## Repository structure

```
gateway/            Node.js/Express API Gateway — JWT validation, HMAC signing, rate limiting
resource-service/   Python/FastAPI internal service — independent auth enforcement, mTLS required
auth-server/        Token issuance — RS256 JWT + rotating refresh tokens
dashboard/          React Security Operations Dashboard — live feed, metrics, attack triggers
attacker-toolkit/   5 Python attack scripts + shared harness — validates every control above
infra/              docker-compose.yml, Postgres init, cert/key generation, Vault init, Grafana/Loki config
docs/               Threat model, architecture diagram, signing scheme, attack report,
                    key-rotation runbook, build log, resume bullets, demo script
.github/workflows/  CI: gitleaks secret scanning, pytest, dependency audit
```

## Documentation index

| Document | What it covers |
| :--- | :--- |
| [`docs/threat-model.md`](docs/threat-model.md) | STRIDE analysis, assets, trust boundaries, risk ratings, residual risk |
| [`docs/architecture-diagram.md`](docs/architecture-diagram.md) | Full system diagram with trust boundary legend |
| [`docs/signing-scheme.md`](docs/signing-scheme.md) | Exact HMAC canonical string format + a real bug found while implementing it |
| [`docs/key-rotation-runbook.md`](docs/key-rotation-runbook.md) | How to rotate the HMAC/JWT keys, with a verified before/after rotation test |
| [`docs/attack-report.md`](docs/attack-report.md) | Live attacker-toolkit results — 22/22 checks, including 2 real findings and fixes |
| [`docs/sql-injection-demo.md`](docs/sql-injection-demo.md) | A live SQL injection proven, then defeated by parameterized queries; least-privilege DB role verified; 2 more real bugs found and fixed |
| [`docs/build-log.md`](docs/build-log.md) | Full week-by-week development record with command-level evidence |
| [`docs/resume-bullets.md`](docs/resume-bullets.md) | Resume-ready bullets pulled from verified work, plus a 60-second verbal walkthrough |
| [`docs/demo-script.md`](docs/demo-script.md) | Shot-by-shot script for a 3-5 minute demo recording |

# ==========================================
# 1. START INFRASTRUCTURE & INJECT SECRETS
# ==========================================
## Full Terminal Command Reference

The commands below take you from a fresh clone to a running, tested system,
including logging in as each demo user and seeing their different
permissions in action. (`docs/build-log.md` has the same material with
context on *why* each step exists, plus the debugging detours taken to get
here; this section is just the commands, in order.)

```bash
cd infra/scripts
chmod +x gen-certs.sh vault-init.sh
./gen-certs.sh
docker compose up -d --build

# Wait for Vault container to fully boot before initializing
sleep 10

cd scripts
./vault-init.sh
cd ..
docker compose restart gateway auth-server resource-service

# Wait for application services to restart and fetch secrets
sleep 5

# ==========================================
# 2. TEST STANDARD USER (NAYTIK) - READ/WRITE
# ==========================================
CA=infra/certs/ca.crt

NAYTIK_TOKEN=$(curl -s --cacert $CA -X POST https://localhost:4000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"naytik","password":"password123"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl --cacert $CA -X POST https://localhost:3000/orders \
  -H "Authorization: Bearer $NAYTIK_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"item":"Mechanical Keyboard","quantity":1}'

curl --cacert $CA -X GET https://localhost:3000/orders \
  -H "Authorization: Bearer $NAYTIK_TOKEN"

# ==========================================
# 3. TEST RESTRICTED USER (RISHI) - READ ONLY
# ==========================================
RISHI_TOKEN=$(curl -s --cacert $CA -X POST https://localhost:4000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"rishi","password":"password123"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl --cacert $CA -X GET https://localhost:3000/orders \
  -H "Authorization: Bearer $RISHI_TOKEN"

# THIS COMMAND WILL FAIL (403 Forbidden) - PROVING SECURITY WORKS
curl --cacert $CA -X POST https://localhost:3000/orders \
  -H "Authorization: Bearer $RISHI_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"item":"Rishis Sneaky Order","quantity":5}'

# ==========================================
# 4. TEST THE REAL DATABASE (Sprint 10) - SQL injection is harmless here
# ==========================================
ADMIN_TOKEN=$(curl -s --cacert $CA -X POST https://localhost:4000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"adminpass456"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Store a classic SQLi payload as an item name -- it's just text now (see docs/sql-injection-demo.md)
curl --cacert $CA -X POST https://localhost:3000/orders \
  -H "Authorization: Bearer $NAYTIK_TOKEN" -H "Content-Type: application/json" \
  -d '{"item":"'"'"'; DROP TABLE orders; --","quantity":1}'

# Confirm the table is still there and has every order in it
curl --cacert $CA https://localhost:3000/orders -H "Authorization: Bearer $NAYTIK_TOKEN"

# Run the full attacker toolkit's database-layer checks specifically:
cd ../../attacker-toolkit && pip install -r requirements.txt && python3 attack_injection.py && cd ../infra

# Inspect the real database directly, as a superuser, if you want to look yourself:
docker compose exec postgres psql -U pgadmin -d orders -c "SELECT id, item, owner_id FROM orders;"

# ==========================================
# 5. SHUT DOWN THE PROJECT
# ==========================================
cd ..
docker compose down       # stops everything, keeps your data (the postgres_data volume)
# docker compose down -v  # <- add -v to ALSO wipe the database + start completely fresh next time
```