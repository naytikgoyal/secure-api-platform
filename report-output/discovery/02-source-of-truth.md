# Source-of-truth map (claim to evidence)

Status key
- **CODE** = read in the source during discovery
- **TEST** = I executed it and saw the output
- **RUN-PENDING** = needs the live Docker stack; not yet observed
- **DOC-ONLY** = only the project's own docs say so
- **OVERSTATED** = a project doc claims more than the code does; the report must use the code's version

| # | Claim in project docs | Evidence inspected | Status |
|---|---|---|---|
| 1 | Gateway and Auth Server serve HTTPS only | `gateway/src/index.js`, `auth-server/src/index.js` use `https.createServer`; no HTTP listener | CODE; plaintext refusal RUN-PENDING |
| 2 | "TLS 1.2+ only" | No explicit `minVersion` in any service; depends on Node 20 / Python+OpenSSL defaults | RUN-PENDING (`attack_mitm_downgrade.py`) |
| 3 | mTLS Gateway to Resource Service | `gateway/src/proxyClient.js` presents `gateway.crt/key`, pins CA; uvicorn started with `--ssl-cert-reqs 2` | CODE; RUN-PENDING |
| 4 | HMAC-SHA256 over `METHOD\nPATH\nBODY\nTS\nNONCE`, constant-time compare | `gateway/src/sign.js`, `resource-service/signing.py` identical format; `hmac.compare_digest` | CODE |
| 5 | 17 unit tests pass | `resource-service/tests/*` run with pytest 8.2.2 on Python 3.14.7 in a scratch venv: **17 passed in 1.15 s** | TEST |
| 6 | Timestamp window 60 s, both directions | `signing.py` `abs(now-ts) > 60`; tests cover past, future, malformed | CODE + TEST |
| 7 | Replay protection via Redis nonce, 5-min TTL, atomic | `nonce_store.py` `SET NX EX 300`; only the in-memory variant is unit-tested | CODE; Redis path RUN-PENDING |
| 8 | JWT RS256 pinned, issuer + audience checked, 15-min access token | `auth-server/src/issueToken.js`, `gateway/src/middleware/auth.js`, `resource-service/main.py` | CODE |
| 9 | Scopes enforced independently at Gateway and Resource Service | `requireScope()` in gateway, `require_scope()` in resource service | CODE |
| 10 | BOLA enforced "independently at both services" | Resource Service checks owner on get/delete/list. Gateway checks only the `?owner_id=` list filter; per-object ownership is **Resource Service only** | CODE; **OVERSTATED** (README table) |
| 11 | Refresh-token rotation with reuse detection | `refreshTokenStore.js`: opaque 48-byte token, single use, 7 days, in-memory Map. No token-family revocation, lost on restart | CODE; "reuse detection" is single-use only |
| 12 | Account lockout (5 failures, 15 min, also for unknown usernames) | `accountLockout.js`, in-memory Map, unbounded keys, per-instance. Lets an attacker lock a known username | CODE |
| 13 | Rate limits: Gateway 100/min per `sub`, Auth 10/min per IP, Redis-backed | both `rateLimiter.js` files | CODE; RUN-PENDING |
| 14 | Identical 401 for wrong password and unknown user (anti-enumeration) | `auth-server/src/index.js`. Unknown user skips bcrypt, so a **timing difference** is plausible | CODE; timing = hypothesis, measure under RUN |
| 15 | Passwords bcrypt cost 10 | `users.js`; demo users hard-coded in memory, hashed at startup | CODE |
| 16 | Secrets from Vault, local copies shredded | Vault clients in all three services; `vault-init.sh`. Build log admits Vault was **tested only against a mock** | CODE; RUN-PENDING |
| 17 | Vault production-readiness | Dev mode, fixed root token in `docker-compose.yml`, plaintext HTTP to Vault, port 8200 published | CODE (limitation, report as such) |
| 18 | Key rotation runbook and script | `rotate-hmac-key.sh`; runbook says DB creds are "not consumed by any service yet" which is **stale** (they are, since Sprint 10) | CODE; stale doc |
| 19 | SQL injection fully prevented | `db.py`: every query uses `%s` placeholders; UUID shape validated; Pydantic limits on `item`/`quantity`; null-byte rejection | CODE; live proof RUN-PENDING |
| 20 | Least-privilege DB role | `infra/postgres-init/01-create-app-role.sh`: NOSUPERUSER/NOCREATEDB/NOCREATEROLE, REVOKE CONNECT on `postgres`; Postgres port not published | CODE; RUN-PENDING |
| 21 | XSS-safe dashboard | `grep` for `dangerouslySetInnerHTML`, `innerHTML`, `eval(` over `dashboard/src`: no matches | CODE |
| 22 | Token handling in browser | `grep` for `localStorage`/`sessionStorage`: no matches; token lives in React state only (lost on refresh) | CODE |
| 23 | Security headers (helmet) | `app.use(helmet())` in Gateway and Auth Server | CODE; RUN-PENDING |
| 24 | CORS restricted | Hard-coded `http://localhost:5173` in both Node services | CODE |
| 25 | Structured logs with request IDs | pino-http (`genReqId`), structlog JSON, `X-Request-Id` header on Resource Service | CODE |
| 26 | "Log redaction" and "tamper-evident audit logs" (threat model) | No pino `redact` config, no structlog redaction, no log signing or hash chain | **OVERSTATED** (not implemented) |
| 27 | "Circuit breakers" (threat model, DoS row) | No circuit-breaker code anywhere | **OVERSTATED** (not implemented) |
| 28 | "OIDC/JWT" (threat model, spoofing row) | Custom OAuth2-style password grant; no OIDC discovery/ID tokens | **OVERSTATED** (README correctly says OAuth2-style) |
| 29 | "Vault injects keys & certs at startup" (architecture diagram) | TLS certs and keys are local files mounted read-only from `infra/certs/`; only JWT, HMAC, DB creds are in Vault | **OVERSTATED** (diagram) |
| 30 | Attacker has "exactly one entry point" | Compose publishes Resource Service (8000), Redis (6379), Vault (8200) to the host; all containers share one flat network `secure-net`. Zones are logical, not network-enforced. Resource Service is still mTLS-gated | CODE; **OVERSTATED** for host-level exposure |
| 31 | Attacker toolkit 22/22 | `attack-report.md` says 22/22 (Week 6); build log says injection suite grew to 18 checks in Sprint 10, so totals differ | DOC-ONLY; RUN-PENDING |
| 32 | Dashboard "Attack Simulation" is real | `admin.js` makes real self-requests. But the `insufficient-scope` button sends a tampered token (401), not a scope failure (403): **name is a misnomer** | CODE |
| 33 | Grafana "Security Overview" with 3 panels | `grafana-dashboard.json` has the 3 panels (request volume, deny reasons, rate-limit hits). Build log says never rendered | CODE; RUN-PENDING |
| 34 | CI: gitleaks, pytest, node syntax check, npm audit | `.github/workflows/ci.yml`. Audit steps use `|| true` (non-blocking). Repo is not a git repository here, so no CI run evidence | CODE; CI results NOT VERIFIED |
| 35 | Test coverage | Automated tests exist only for `signing.py` and `nonce_store.py`. Gateway and Auth Server have no unit tests (syntax check only). Everything else is covered by the live attacker toolkit | CODE |
| 36 | Containers hardened | Gateway/Auth/Resource images run as root (no `USER`); dashboard container runs the Vite **dev server**; Promtail mounts `docker.sock` read-only | CODE (limitation) |
| 37 | Admin `/admin/attack-report` | Accepts any JSON body, stored in memory, admin-only (documented in code comment) | CODE (limitation) |

## Sensitive material present in the working tree (never to appear in the report or screenshots)
- `infra/.env` (database bootstrap passwords)
- `infra/certs/*.key`, `ca.key` (TLS private keys)
- Vault dev root token string in `docker-compose.yml` and scripts; I will refer to it only as "a fixed development-only root token"
- Demo user passwords in `users.js`, README and docs: local seed data. Default: usernames may appear; passwords masked in screenshots and omitted from the text

---

# Live verification results (observed 2026-10-28)

Method: a copy of the repository (certificates and `.env` freshly generated, nothing of yours reused) was built and run with Docker Compose under a separate project name (`reportrun`) so your original containers, images and the `infra_postgres_data` volume were not touched. The stack was torn down afterwards. Raw logs and screenshots are in `report-output/evidence/`.

| ID | What was observed | Evidence file | Effect on the table above |
|---|---|---|---|
| V1 | All 10 containers started and went healthy. Gateway, Auth Server and Resource Service loaded their secrets from a **real** Vault 1.17.6; all three `vault-init.sh` writes returned HTTP 200 | `environment.txt`, compose output | Row 16: mock-only caveat is resolved. Vault dev-mode limits (row 17) remain |
| V2 | 19 functional flows behaved as designed: TLS 1.3 negotiated; plaintext HTTP refused; Resource Service without client cert fails at handshake (curl exit 52); read-only user gets 403 on write; BOLA read gets 403; non-admin gets 403 on admin API; valid client cert but no HMAC gets 401; stored `'; DROP TABLE orders; --` is kept verbatim and the table survives; 3 invalid inputs get 422; refresh token reuse gets 401 | `functional-flows.log` | Rows 1, 3, 8, 9, 10, 11, 19 confirmed by execution |
| V3 | Gateway sends `X-Frame-Options: SAMEORIGIN` and a Content-Security-Policy; code comment says "DENY" | `functional-flows.log` F-18 | Row 23 confirmed; comment is inaccurate |
| V4 | Stock `run_all.py`: 3 PASS, 2 FAIL. `attack_replay.py` fails because it needs `hmac-signing.key`, which `vault-init.sh` shreds (its message mentions an `HMAC_KEY_OVERRIDE` variable the code never reads). `attack_injection.py` fails because `attack_bruteforce.py` just locked `naytik` (HTTP 423) and `login()` retries only on 429. The forgery script silently skipped algorithm confusion yet reported 2/2 | `attacker-toolkit-run1.log` | Row 31: documented 22/22 is not reproducible with the stock runner. FAIL here means "could not run", not "attack succeeded" |
| V5 | With the HMAC key and public key fetched from the dev Vault into the copy (the scenario the script's own note describes), the lockout cleared by restarting the Auth Server, and brute-force run last: replay 2/2, forgery 3/3, injection **18/18**, TLS downgrade 3/3, brute-force 2/2 = **28/28** | `attacker-toolkit-run2-part1/2/3.log` | Row 31: 22 was the pre-database count (2+3+2+12+3); current suite is 28 |
| V6 | Independent TLS probe from inside the Gateway container with a permissive control server (control completed TLS 1.0, 1.1, 1.2, 1.3). Gateway and Auth Server refuse 1.0/1.1 with a protocol-version alert; Resource Service resets the connection; 1.2 and 1.3 accepted. Defaults are Node `DEFAULT_MIN_VERSION=TLSv1.2` and Python `minimum_version=771` (TLS 1.2). The Resource Service negotiated a CBC/SHA-1 cipher suite (`ECDHE-RSA-AES256-SHA`) when the client offered one, so no explicit cipher policy exists | `tls-version-check.log` | Row 2 confirmed by a valid method. The toolkit's own "TLS 1.0/1.1 refused" result alone was not conclusive (generic client-side `[SSL] internal error`) |
| V7 | After the brute-force script, a login as `naytik` with the **correct** password returned 423 "Try again in 14 minute(s)". An attacker can lock out a known user. Lockout is in memory, so an Auth Server restart cleared it | `lockout-after-bruteforce.log` | Row 12: confirms the control and its denial-of-service side effect |
| V8 | Wrong-password login latency: existing user mean 131.5 ms (n=4), unknown user mean 10.7 ms (n=4), about 12x. Response bodies are identical but timing is not | `login-timing.log` | Row 14: anti-enumeration claim holds for responses, **fails for timing** |
| V9 | 130 authenticated requests in under a minute: exactly 100 x HTTP 200 then 30 x HTTP 429. The toolkit's auth limiter first returned 429 at attempt 9 | functional logs, Loki check | Row 13 confirmed |
| V10 | In a real browser, stored `<script>` and `<img onerror>` item names rendered as plain text; 0 JavaScript dialogs fired; 0 injected script/img elements in the DOM | `screenshots/S07...png`, `browser-run-log.json` | Row 21 confirmed by execution |
| V11 | Grafana: provisioned "Security Overview" loads. Panel 3 (rate-limit hits) works and showed the 30 x 429 burst. **Panel 1 errors** (Loki rejects `\| json` because the Resource Service also emits plain-text Uvicorn lines). **Panel 2 shows no data** (`level` is not an indexed stream label). Queries with `\| __error__=""` and `\| json \| level="warn"` returned data when tested directly against Loki (repo not modified). Also: structlog writes level `warning` while pino writes `warn` | `screenshots/S08...png`, `grafana-loki-diagnosis.log` | Row 33: 1 of 3 panels works as provisioned |
| V12 | Versions: Node 20.20.2, Python 3.12.16, PostgreSQL 16.15, Redis 7.4.11, Vault 1.17.6, Grafana 11.1.0, Loki/Promtail 3.1.0, Express 4.22.3, helmet 7.2.0, jsonwebtoken 9.0.3, FastAPI 0.111.0, PyJWT 2.8.0, React 18.3.1, Vite 5.4.21 | `environment.txt` | New |
| V13 | App containers run as root; the dashboard container runs the Vite dev server; 8 ports are published to the host (3000, 3001, 3100, 4000, 5173, 6379, 8000, 8200) | `environment.txt` | Rows 30, 36 confirmed |
| V14 | The login page itself prints the demo usernames **and passwords** in a footer | `screenshots/S01`, `S02` | New finding (demo convenience; must not exist outside a demo) |
| V15 | The Attack History panel shows whatever the last `run_all.py` posted, including the two FAILs from V4 | `screenshots/S04...png` | Report shows it as-is and explains it |
| V16 | Resource Service error bodies use `{"detail": ...}`; Gateway uses `{"error","message"}` | `functional-flows.log` F-09 | Minor inconsistency |

## Screenshots index (raw, unedited, in `evidence/screenshots/`)
S01 login, S02 failed login, S03 admin dashboard before attacks, S04 admin dashboard after three real attack simulations (full page), S05 read-only user view, S06 read-write user view, S07 hostile strings rendered as text, S08 Grafana. **S01/S02 contain the demo-credential footer: use cropped copies in the report.**
