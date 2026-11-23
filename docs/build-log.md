# Build Log (Week-by-Week Development Record)

This document is the detailed, chronological record of how this project was built — every week's deliverables, every bug found and fixed, every acceptance-criteria verification with real command output. It's kept as evidence for anything summarized elsewhere (the top-level README, `docs/attack-report.md`, `docs/resume-bullets.md`) — if you want to check a claim, the receipts are here.

---

## Week 1 — Threat Model & Scaffolding
- [x] `docs/threat-model.md` — STRIDE threat model with assets, trust boundaries, risk ratings
- [x] `docs/architecture-diagram.md` — Mermaid diagram with legend + numbered data flow
- [x] Monorepo structure, all services boot with real health endpoints

## Week 2 — Core APIs + TLS
- [x] Resource Service: real `/orders` CRUD (in-memory store), Pydantic validation, centralized error handling
- [x] Gateway: HTTPS pass-through proxy routes to Resource Service, centralized error handling
- [x] `infra/scripts/gen-certs.sh` — generates a local CA + signs a server cert per service
- [x] Both Gateway and Resource Service serve HTTPS only; plaintext HTTP is refused
- [x] `docs/postman-collection.json` — importable collection covering CRUD + validation + 404 cases

### First-time setup: generate certificates
**You must do this before `docker compose up`, and any time you want fresh certs:**
```bash
cd infra/scripts
./gen-certs.sh
```
This creates `infra/certs/` (gitignored — every developer generates their own local CA; never commit these).

## How to verify this yourself (run this on your own machine, not here)

```bash
cd infra
./scripts/gen-certs.sh     # if you haven't already
docker compose up --build
```

Then in another terminal:
```bash
# --cacert makes curl actually validate the cert chain against our local CA
# (as opposed to -k, which would just skip verification entirely and prove nothing)
curl --cacert infra/certs/ca.crt https://localhost:3000/health   # gateway
curl --cacert infra/certs/ca.crt https://localhost:8000/health   # resource-service
curl http://localhost:4000/health                                # auth-server (still HTTP until Week 3)

# Full CRUD through the Gateway (which proxies to Resource Service over verified HTTPS):
curl --cacert infra/certs/ca.crt -X POST https://localhost:3000/orders \
  -H "Content-Type: application/json" \
  -d '{"item":"Mechanical Keyboard","quantity":1,"owner_id":"user-123"}'

curl --cacert infra/certs/ca.crt https://localhost:3000/orders

# Prove plaintext HTTP is refused (this should fail to connect):
curl http://localhost:3000/health

docker compose ps   # all should show "healthy"
```

Or import `docs/postman-collection.json` into Postman and run the whole collection.

**Definition of Done for Week 2 (from the PRD):** `curl` over HTTP is refused; `curl` over HTTPS with the CA trusted succeeds end-to-end Gateway → Resource Service.

## Week 3 — Authentication & Authorization
- [x] Auth Server: real `/auth/login` (password grant) issuing RS256 JWT access tokens (15 min) + rotating refresh tokens
- [x] Gateway: JWT validation middleware (`gateway/src/middleware/auth.js`) — signature, expiry, issuer, audience, scope
- [x] Resource Service: **independent** JWT verification (`resource-service/main.py`) — never trusts the Gateway already checked it
- [x] BOLA/IDOR fix landed: `owner_id` now comes from the verified token's `sub` claim, never from client input (closes the `TODO(Week 3)` from Week 2)
- [x] Refresh token rotation: reusing an old refresh token after it's been rotated is rejected
- [x] `docs/postman-collection.json` updated with 12 requests proving auth, scopes, BOLA blocking, and defense-in-depth

### Demo users (see `auth-server/src/users.js`)
| Username | Password | Scopes |
| :--- | :--- | :--- |
| `naytik` | `password123` | `orders:read`, `orders:write` |
| `rishi` | `password123` | `orders:read` (read-only — used to prove scope enforcement) |
| `admin` | `adminpass456` | `orders:read`, `orders:write`, `admin` |

### Why RS256 instead of a shared secret (HS256)
The Auth Server holds the **private** signing key. The Gateway and Resource Service only ever get the **public** key (`infra/certs/jwt-signing.pub`). A compromised Gateway can verify tokens but can never forge one — only the Auth Server can sign. Week 5 moves the private key into Vault.

## First-time setup: generate certificates + JWT signing keypair
**Do this before `docker compose up`, and any time you want fresh keys:**
```bash
cd infra/scripts
./gen-certs.sh
```
This now generates both the TLS certs (Week 2) and the JWT RS256 keypair (Week 3) into `infra/certs/` (gitignored).

## How to verify this yourself (run this on your own machine, not here)

```bash
cd infra
./scripts/gen-certs.sh     # if you haven't already
docker compose up --build
```

```bash
CA=infra/certs/ca.crt

# 1. Log in
curl --cacert $CA -X POST https://localhost:4000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"naytik","password":"password123"}'
# copy the access_token from the response into $TOKEN below

# 2. Create an order (owner_id comes from the token now, not the request body)
curl --cacert $CA -X POST https://localhost:3000/orders \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"item":"Keyboard","quantity":1}'

# 3. Prove BOLA is fixed: log in as rishi, try to read naytik's order by ID -> 403
# 4. Prove scope enforcement: rishi (read-only) tries POST /orders -> 403
# 5. Prove defense-in-depth: hit https://localhost:8000/orders DIRECTLY (skip the
#    Gateway entirely) with rishi's token and try to write -> still 403
```

Or import `docs/postman-collection.json` — it runs all of the above as an ordered, assertable test suite.

**Definition of Done for Week 3 (from the PRD):** a valid token with `orders:read` cannot call `POST /orders` anywhere in the chain; expired/forged tokens are rejected everywhere; a user cannot read another user's order by ID even with a valid token.

## Week 4 — mTLS + HMAC Request Signing + Replay Protection
- [x] mTLS: Resource Service **requires** a valid client certificate for every connection (enforced at the TLS handshake, before any application code runs) — Gateway presents `gateway.crt` as its client identity
- [x] HMAC request signing: every Gateway → Resource Service request is signed over `method+path+body+timestamp+nonce` (see `docs/signing-scheme.md` for the exact scheme)
- [x] Nonce replay protection: Redis-backed, 5-minute TTL — a captured request replayed even 1 second later is rejected
- [x] Timestamp window (±60s) rejects both stale AND suspiciously-future requests
- [x] 17 passing unit tests (`resource-service/tests/`) covering valid signatures, tampered body/path/method, wrong secret, expired/future/malformed timestamps, and nonce reuse
- [x] Found and fixed a real bug during build: signing must include the query string, not just the path — documented in `docs/signing-scheme.md`

### Run the unit tests yourself
```bash
cd resource-service
pip install -r requirements.txt --break-system-packages
pytest tests/ -v
```

## First-time setup: generate certificates + JWT + HMAC keys
**Do this before `docker compose up`, and any time you want fresh keys:**
```bash
cd infra/scripts
./gen-certs.sh
```
This now generates TLS certs (Week 2), the JWT RS256 keypair (Week 3), AND the HMAC signing secret (Week 4) — all into `infra/certs/` (gitignored).

## How to verify this yourself (run this on your own machine, not here)

```bash
cd infra
./scripts/gen-certs.sh
docker compose up --build
```

```bash
CA=infra/certs/ca.crt

# Prove mTLS is enforced: connect WITHOUT a client cert -- TLS handshake itself fails
curl --cacert $CA https://localhost:8000/health
# (this should fail with an SSL/TLS error, not an HTTP error -- it never reaches app code)

# Connect WITH a client cert -- succeeds
curl --cacert $CA --cert infra/certs/gateway.crt --key infra/certs/gateway.key https://localhost:8000/health

# Full flow still works exactly as Week 3, just now mTLS+HMAC-protected under the hood:
curl --cacert $CA -X POST https://localhost:4000/auth/login \
  -H "Content-Type: application/json" -d '{"username":"naytik","password":"password123"}'
# use the access_token in $TOKEN below

curl --cacert $CA -X POST https://localhost:3000/orders \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"item":"Keyboard","quantity":1}'
```

**Definition of Done for Week 4 (from the PRD):** a captured valid request replayed even 1 second later is rejected due to nonce reuse; a request without a valid client cert is refused at the TLS handshake, before it even reaches app code. Both proven live during build — see conversation history / commit notes.

## Week 5 — Secrets Management (Vault) + Rate Limiting
- [x] HashiCorp Vault (dev mode) added to `docker-compose.yml`
- [x] `infra/scripts/vault-init.sh` — pushes JWT keypair, HMAC secret, and placeholder DB creds into Vault, then **shreds the local plaintext copies**
- [x] Gateway, Auth Server, and Resource Service all fetch their secrets from Vault at startup — no secret files read at runtime (TLS certs for mTLS remain local files; see `docs/key-rotation-runbook.md` for why)
- [x] `infra/scripts/rotate-hmac-key.sh` + `docs/key-rotation-runbook.md` — rotates the HMAC key in Vault; verified live that a request signed with the old key is rejected once services restart with the new one
- [x] Redis-backed rate limiting: Gateway (100 req/min per client, keyed by JWT `sub`) and Auth Server (10 req/min per IP on `/auth/login` and `/auth/refresh`, since that's the actual brute-force surface)
- [x] `.github/workflows/ci.yml` — gitleaks secret scanning, resource-service pytest suite, Node syntax checks, dependency audit
- [x] Real gitleaks binary run against this repo during development — found exactly the 5 expected private keys, all in the gitignored `infra/certs/` directory, nothing in tracked source

### A bug found and fixed this week
The rate limiter's `RedisStore` was being constructed at **module-import time** (when `orders.js` loaded), but the Redis connection only finished opening later, inside `main()`. Fixed by deferring the `orders.js` import with a dynamic `import()` until *after* `connectRedis()` resolves — see the comment in `gateway/src/index.js`.

### Vault caveat (read this before running)
This sandbox environment couldn't reach HashiCorp's release servers or run a Docker daemon, so Vault integration was verified against a minimal mock server that implements the same KV v2 HTTP API (not shipped in this repo — a throwaway test double). **The `hashicorp/vault` image in `docker-compose.yml` is the real thing** and is what you'll actually run. The application-side Vault client code (`vaultClient.js` / `vault_client.py`) speaks Vault's real, stable KV v2 API contract, so this distinction shouldn't matter in practice — but you should run the full sequence below yourself and confirm it end-to-end against real Vault.

## First-time setup (Week 5 sequence — order matters now)
```bash
cd infra
./scripts/gen-certs.sh              # generates TLS certs, JWT keypair, HMAC key locally
docker compose up -d vault           # start ONLY vault first
./scripts/vault-init.sh              # push secrets into vault, shred local copies
docker compose up --build            # now start everything else
```

### Rotating the HMAC key
```bash
cd infra/scripts
./rotate-hmac-key.sh
docker compose restart gateway resource-service
```
See `docs/key-rotation-runbook.md` for the full verification procedure.

## How to verify this yourself

```bash
CA=infra/certs/ca.crt

# Confirm secrets are gone from disk (grep should find nothing after vault-init.sh runs):
grep -r "BEGIN PRIVATE KEY" infra/certs/ 2>/dev/null | grep -v "\-server\.key\|gateway\.key\|resource-service\.key\|ca\.key"
# (TLS server/CA keys legitimately remain -- only jwt-signing.key and hmac-signing.key should be gone)

# Normal flow still works exactly as before:
curl --cacert $CA -X POST https://localhost:4000/auth/login \
  -H "Content-Type: application/json" -d '{"username":"naytik","password":"password123"}'

# Rate limiting: flood /auth/login past 10 requests/min from the same IP -> 429
for i in $(seq 1 12); do
  curl -s -o /dev/null -w "%{http_code}\n" --cacert $CA -X POST https://localhost:4000/auth/login \
    -H "Content-Type: application/json" -d '{"username":"naytik","password":"wrong"}'
done
```

**Definition of Done for Week 5 (from the PRD):** `grep -r 'BEGIN PRIVATE KEY\|secret' infra/certs/` (after `vault-init.sh` runs) shows only TLS server/CA keys, never the JWT or HMAC secrets; rotating the HMAC key in Vault and restarting invalidates old-key-signed requests; flooding an endpoint trips a 429 before the service is meaningfully impacted.

## Week 6 — Attacker Toolkit
- [x] `attacker-toolkit/` — 5 runnable attack scripts + shared helpers + `run_all.py`
- [x] `docs/attack-report.md` — every finding with real before/after HTTP evidence, including 2 real issues found and fixed
- [x] **22/22 checks pass** on the final run (`python3 run_all.py`)

### The scripts
| Script | Tests |
| :--- | :--- |
| `attack_replay.py` | Captured valid signed request, replayed immediately -- must be rejected via nonce reuse |
| `attack_token_forgery.py` | Wrong-key forgery, `alg: none`, RS256→HS256 algorithm confusion |
| `attack_bruteforce.py` | Account enumeration (identical errors), rapid login flooding -- must trip rate limiting |
| `attack_injection.py` | Structural validation (type/size/negative) vs. content patterns (SQLi/XSS-looking strings -- see attack report for why these are correctly ACCEPTED, not blocked) |
| `attack_mitm_downgrade.py` | Plaintext HTTP to the HTTPS port, TLS 1.0/1.1 downgrade attempts |

### Run it yourself
```bash
cd attacker-toolkit
pip install -r requirements.txt
python3 run_all.py          # runs all 5 in sequence with a combined summary
python3 attack_replay.py    # or run any single script standalone
```
Requires the full stack running (see setup above) and certs generated via `infra/scripts/gen-certs.sh`.

### Read `docs/attack-report.md` before assuming every red result needs a blocklist fix
The most important finding this week wasn't a bug — it was almost adding one.
`attack_injection.py`'s first version expected every SQLi/XSS-looking string
to be rejected; six weren't. The **correct** conclusion, after actually
checking whether this system ever interprets those strings as code (it
doesn't — no SQL queries, no HTML rendering), was that blocklisting them
would have been security theater and would have broken legitimate data. Only
null bytes got a real fix. Full reasoning in the report.

## Week 7 — Logging, Monitoring & Dashboard
- [x] Structured JSON logging (pino on Gateway/Auth Server, structlog on Resource Service) with request-ID correlation on every allow/deny decision
- [x] `GET /admin/audit-logs`, `GET /admin/metrics`, `GET /admin/audit-stream` (SSE) — real, `admin`-scope-protected endpoints (FR-7)
- [x] `POST /admin/simulate-attack/:type` — powers the dashboard's attack-trigger buttons by making **genuine self-requests** through the real middleware, not fabricated log entries
- [x] Loki + Grafana + Promtail added to `docker-compose.yml`; `infra/grafana-dashboard.json` — 3 panels (request volume, deny reasons breakdown, rate-limit hits over time)
- [x] Real React Security Operations Dashboard (`dashboard/`) — 4 panels: live feed, security events, metrics cards, attack triggers. Dark SOC theme.
- [x] Verified live: SSE stream captured a real event end-to-end during testing; `npm run build` produces a clean production bundle (37 modules, no errors)

### Two real bugs found and fixed this week
1. **Starlette middleware ordering**: `@app.middleware("http")` decorators execute in *reverse* registration order (last-registered = outermost = runs first). The request-ID assignment middleware was registered before the signature-verification middleware, so signature-verification logs showed `request_id: "unknown"` — the ID hadn't been assigned yet when that code ran. Fixed by swapping registration order; verified via a live log capture showing a real UUID afterward.
2. **Express sub-router path logging**: `req.path` inside a router mounted with `app.use("/orders", ordersRouter)` is relative to the mount point, so every audit log showed `path: "/"` instead of `/orders`. Fixed by using `req.originalUrl` instead.

### Why the dashboard uses fetch() instead of EventSource for the live feed
Browser's native `EventSource` API cannot send custom headers, so it can't carry an `Authorization: Bearer` token. The common workaround — put the token in the URL query string — leaks it into server access logs and browser history. `dashboard/src/api.js` instead uses `fetch()` with a manual `ReadableStream` reader, which supports normal headers. See that file's comments for the full reasoning.

### Run the dashboard yourself
```bash
cd dashboard
npm install
npm run dev
# visit http://localhost:5173, log in with admin / adminpass456
```
Your browser will show a certificate warning the first time it talks to `https://localhost:3000` (self-signed local CA) — either import `infra/certs/ca.crt` into your OS/browser trust store, or visit `https://localhost:3000/health` directly first and click through the warning once.

### Vault/Loki/Grafana caveat (same as Week 5)
This sandbox environment can't run a Docker daemon or reach `grafana.com`'s release servers, so Loki/Grafana/Promtail could not be started and screenshotted here. The `docker-compose.yml` entries and `infra/grafana-dashboard.json` are real, standard configuration that will run when you bring up the stack — but you should verify the Grafana panels render as expected on your own machine before treating that part as fully proven. Everything Node/Python-side (structured logging, the admin endpoints, the SSE stream, the dashboard itself) WAS run live and verified during development.

## How to verify Week 7 yourself

```bash
cd infra
./scripts/gen-certs.sh
docker compose up -d vault
./scripts/vault-init.sh
docker compose up --build

# Grafana: http://localhost:3001 (admin/admin) -- "Security Overview" dashboard should be pre-provisioned
# Dashboard: http://localhost:5173 -- log in with admin/adminpass456
```

In the dashboard, click any of the three "Attack Simulation" buttons and watch the Live Feed / Security Events panels react within about a second — that's the real `requireAuth`/rate-limiter code producing a genuine deny event, not a scripted animation.

## What's intentionally NOT here yet
- No CI-gated attacker toolkit run (still manual `python3 run_all.py`)
- Grafana dashboard panels are provisioned but not visually verified in this environment (see caveat above)
- No alerting rules (e.g. Grafana alert on deny-rate spike) — only visualization
- TLS/mTLS certs are still local files, not Vault PKI-issued (documented scope boundary — see `docs/key-rotation-runbook.md`)
- Vault is in dev mode (auto-unseal, in-memory, fixed root token) — documented as a residual limitation, not implemented for real production use

## Repo structure
```
.
├── gateway/            # Node.js/Express API Gateway
├── resource-service/   # Python/FastAPI internal service
├── auth-server/        # Token issuance service
├── dashboard/          # React security dashboard
├── attacker-toolkit/   # Python attack scripts (Week 6)
├── infra/              # docker-compose.yml, Vault/Grafana config (added Week 5/7)
└── docs/               # threat-model.md, architecture-diagram.md, etc.
```

---

## Sprint 9 — Role-based UI, Attack History panel, security headers, account lockout

Built directly against the actual uploaded repo (not from memory), after confirming zero drift from prior sessions:
- Customer-facing "My Orders" view added to the dashboard — same login page, but Naytik (read+write) and Rishi (read-only) see structurally different UIs based on their token's real scopes, decoded client-side (`dashboard/src/jwt.js`) purely for display, never trusted for security (the backend re-verifies everything, as always)
- Verified live: Naytik creates an order (`201`); Rishi's identical attempt gets a real `403` from the actual backend; a decoded token confirms exactly why
- `attacker-toolkit/run_all.py` now POSTs its results to a new `/admin/attack-report` endpoint; the dashboard's new "Attack History" panel displays them — verified the full `404` (nothing yet) → `200` (POST) → `200` (GET, same data back) → `401` (bad token) chain live
- Security headers via `helmet` — confirmed live via `curl -D -`: `Strict-Transport-Security`, `X-Content-Type-Options: nosniff`, `X-Frame-Options` all present
- Account lockout (distinct from IP-based rate limiting) — locks a specific *username* after 5 failed attempts regardless of source IP; verified live including the important subtlety that a **nonexistent** username locks identically to a real one, preserving the anti-enumeration property from Week 3

One real find during packaging: the uploaded zip included the user's local `venv/` folders from earlier troubleshooting. Removed, and `venv/` added to `.gitignore`.

## Sprint 10 — Real PostgreSQL database + live SQL injection proof

The in-memory order dict (Weeks 2-8) was replaced with real PostgreSQL, specifically to make SQL injection a genuine threat worth defending against rather than a hypothetical one.

**Taught and proven live, in that order:** a deliberately vulnerable string-formatted query was shown stealing every row in a table with a classic `' OR '1'='1' --` payload; the identical payload was then shown failing completely against a parameterized version of the same query. Both ran against a real local PostgreSQL instance, not a mock.

**Built:** `resource-service/db.py` (every query parameterized — `create_order`, `list_orders`, `get_order`, `delete_order`, plus `init_schema`), a least-privilege `orders_app` Postgres role (`infra/postgres-init/01-create-app-role.sh`), Postgres added to `docker-compose.yml` with a named volume for persistence, DB credentials flow through Vault exactly like the JWT/HMAC secrets do (`vault_client.py`, `gen-certs.sh` now also bootstraps `infra/.env` with DB passwords).

**Verified live against the real running stack (not a mock), 18/18 checks:** the extended `attacker-toolkit/attack_injection.py` now attacks the three places user input reaches a real query — the `item` field, the order ID in the URL path, and the admin `?owner_id=` filter — including two actual `DROP TABLE` and one `DELETE FROM` payload, then confirms the row count is unchanged afterward.

**Two real bugs found and fixed, not hypothetical:**
1. Percent-encoded injection payloads in the URL path (e.g. `%27%20OR...`) returned `401 Invalid request signature` instead of reaching the database layer — because `request.url.path` in Starlette is percent-*decoded*, but the Gateway signs the path as it appears percent-*encoded* on the wire. Same bug class as Week 4's query-string issue, different manifestation. Fixed using `request.scope["raw_path"]` (the true original bytes) instead.
2. A comment in the Postgres role setup script claimed the app's database role "cannot read other databases" — testing this directly showed it was **false** (Postgres grants `CONNECT` to `PUBLIC` on every database by default). Fixed with an explicit `REVOKE`, then re-verified the connection attempt now fails. Lesson: verify security claims by testing them, don't assert what "should" be true.

**Least privilege also verified live, not assumed:** the `orders_app` role was confirmed unable to connect to the default `postgres` database, create a new role, create a new database, or run an OS command via `COPY ... TO PROGRAM` — each attempted directly and denied.

Full writeup: `docs/sql-injection-demo.md`. `docs/threat-model.md`'s residual risk section updated — the SQL injection entry is now marked resolved-and-verified rather than deferred; the XSS/output-encoding entry was also checked directly (grepped the entire dashboard for `dangerouslySetInnerHTML`/`innerHTML`/`eval(` — none found) rather than left as an assumption.
