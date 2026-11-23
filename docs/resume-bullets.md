# Resume Bullets & Interview Walkthrough

## Resume bullets (pick 4-6 based on the role)

- Designed and implemented a zero-trust microservices architecture (Node.js/Express + Python/FastAPI) with mutual TLS, HMAC-signed request integrity, and nonce-based replay protection between all internal services — verified via a custom attacker toolkit simulating captured-request replay, request tampering, and MITM/TLS-downgrade attempts.

- Implemented OAuth2/JWT authentication (RS256, short-lived access tokens with rotating refresh tokens) with scope-based authorization enforced independently at two service layers, closing a Broken Object-Level Authorization (BOLA/IDOR) vulnerability class identified during the project's own threat-modeling phase.

- Integrated HashiCorp Vault for centralized secrets management, eliminating plaintext signing keys from disk at runtime, and authored a key-rotation runbook with a verified before/after test proving rotated keys immediately invalidate previously-valid signatures.

- Built and ran a 5-script offensive test suite (JWT forgery including `alg:none` and algorithm-confusion attacks, credential brute-forcing, replay attacks, input validation probing, TLS downgrade attempts) against the live system, finding and fixing 2 real issues — including correctly identifying that blocklisting SQLi/XSS-looking input would have been security theater given the system's actual architecture, rather than applying a superficial fix.

- Authored a STRIDE-based threat model with risk-rated findings that directly drove implementation priority across an 8-week build, and a real-time Security Operations Dashboard (React, SSE) surfacing live authentication/authorization decisions and attack telemetry.

- Established a CI pipeline with gitleaks secret scanning, automated unit tests (17 tests covering cryptographic signing/replay logic), and dependency auditing — validated by running the real gitleaks binary against the repository and confirming zero secrets in tracked source.

## 60-second verbal walkthrough (for "tell me about a project")

> "I built a defense-in-depth API platform to practice the security patterns real companies actually use — not just 'add HTTPS and a JWT.' It's a Gateway and an internal Resource Service that only trust each other through mutual TLS *and* HMAC-signed, nonce-protected requests — so even if someone captured a valid request off the wire, replaying it a second later gets rejected. Auth is OAuth2/JWT with scopes checked independently at both services, which is what actually caught a BOLA vulnerability during my own threat-modeling — a user could originally read anyone's order by guessing the ID.
>
> The part I'm most proud of is the attacker toolkit — five scripts that actually attack the running system: JWT forgery, brute-forcing, replay, injection, TLS downgrade. Running it found two real issues. One was a genuine bug — my rate limiter's Redis connection wasn't ready before the middleware that used it. The other was more interesting: I almost added a blocklist for SQL-injection-looking strings, then realized that's actually a well-known anti-pattern — my system has no database and no HTML renderer, so there's nothing for those strings to exploit, and blocking them would've broken legitimate data like an apostrophe in a name. I fixed the one thing that *was* a real issue — null bytes — and documented why the rest were correctly left alone.
>
> Secrets live in Vault, not on disk, and I've got a working rotation procedure I verified end-to-end: rotate the key, restart the services, and the old key immediately stops working. Everything's backed by a STRIDE threat model that actually drove what I built each week, not a document I wrote after the fact."

## If asked "what would you do differently in production"

- Replace the password-grant OAuth2 flow with Authorization Code + PKCE (or a real IdP like Keycloak) — documented as a stretch goal, not implemented, because the simpler flow was clearer for demonstrating the token/scope mechanics that were the actual point of the project.
- Move TLS certificate issuance into Vault's PKI secrets engine instead of a locally-generated CA, so certs rotate automatically instead of via a manual script.
- Add short-lived Vault leases with automatic re-fetch, so secret rotation doesn't require a service restart to take effect (current implementation is restart-based, documented in `docs/key-rotation-runbook.md`).
- Move from an in-memory data store to a real database — and the moment that happens, revisit `docs/attack-report.md`'s injection findings, since parameterized queries become a hard requirement at that point, not a "someday" note.

## If asked "what was the hardest bug"

The HMAC signature verification failing on `GET /orders?owner_id=x` requests specifically. The Gateway signs the full request target as sent on the wire, including the query string — but FastAPI's `request.url.path` strips query strings by design. Two completely correct-looking implementations of the same signing scheme disagreed on what bytes were actually being signed. Full writeup with the fix in `docs/signing-scheme.md`.
