# Secure API Communication Platform: Threat Model

## 1. Introduction
This document defines the threat model for the Secure API Communication Platform, a defense-in-depth microservices architecture where external client traffic is routed through a Node.js API Gateway to a trusted Python FastAPI Resource Service.

We use the **STRIDE** methodology (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege) applied at each trust boundary, and rate every threat by **Likelihood × Impact** so engineering effort is provably prioritized rather than applied evenly everywhere.

## 2. Assets & Actors

### 2.1 Protected Assets
| Asset | Why it matters |
| :--- | :--- |
| JWT signing key (Auth Server) | Compromise = attacker can forge valid access tokens for any client/scope |
| HMAC shared/derived signing key | Compromise = attacker can forge trusted Gateway→Resource requests |
| TLS/mTLS private keys & certs | Compromise = attacker can impersonate a service or decrypt traffic |
| Order data (PII: names, addresses) | Confidentiality/integrity obligation to end users |
| Audit logs | Evidence of who did what — must be tamper-evident for repudiation defense |
| Vault root/unseal tokens | Compromise = attacker gets every other secret above |

### 2.2 Threat Actors
| Actor | Capability | Motivation |
| :--- | :--- | :--- |
| External unauthenticated attacker | Network access to public Gateway only | Data theft, service disruption |
| Malicious authenticated client | Valid but limited-scope token | Privilege escalation, access other users' data (BOLA) |
| Compromised dependency / supply-chain | Code execution inside a service | Persistence, secret exfiltration |
| Insider / leaked credential | Direct access to infra (Vault, DB) | Data theft |

*Out of scope for this project (assumption): host OS compromise, Docker daemon compromise, physical access, and social engineering. These are acknowledged but not defended against — a real production system would need additional controls (OS hardening, EDR, etc.) beyond this project's scope.*

## 3. Trust Boundaries

The architecture has **three explicit trust boundary crossings**. Every threat below is tied to one of these.

| # | Boundary | Crossing | Trust change |
| :--- | :--- | :--- | :--- |
| TB-1 | Internet → DMZ | Client → API Gateway | Untrusted → semi-trusted (authenticated but external) |
| TB-2 | DMZ → Internal Zone | Gateway → Resource Service | Semi-trusted → fully trusted (internal-only, mTLS-gated) |
| TB-3 | Internal Zone → Secrets | Any service → Vault | Service identity → secret material |

## 4. High-Level STRIDE Analysis

| STRIDE Category | Example Threat | Boundary | Primary Control | Likelihood | Impact | Risk |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Spoofing | Attacker forges identity / replays a stolen JWT | TB-1 | OIDC/JWT, ≤15 min expiry, mTLS on TB-2 | Medium | High | **High** |
| Tampering | Attacker modifies request body/params in transit | TB-1, TB-2 | TLS 1.2+ (TB-1); HMAC signing + mTLS (TB-2) | Low | High | Medium |
| Repudiation | Client denies making a malicious/erroneous request | — | Tamper-evident JSON audit logs, correlation IDs | Medium | Medium | Medium |
| Information Disclosure | Secrets leak via env vars, logs, or error responses | TB-3 | Vault-managed secrets, log redaction, generic errors | Medium | High | **High** |
| Denial of Service | Flooding the public API to exhaust resources | TB-1 | Per-client rate limiting (Redis) + circuit breakers | High | Medium | **High** |
| Elevation of Privilege | Client with `read` scope calls a `write` endpoint | TB-1, TB-2 | Scope/RBAC enforced independently at both layers | Medium | High | **High** |

*Risk = Likelihood × Impact, rated qualitatively (Low/Medium/High). The four **High** rows get built and attacked first (Weeks 3-6); Medium rows still get controls but aren't the priority for the attacker toolkit if time runs short.*

## 5. Per-Endpoint Threat Analysis

### 5.1 Authentication Endpoints (`POST /auth/login`, `POST /auth/refresh`) — TB-1
- **Threat (DoS):** Attacker brute-forces credentials to exhaust database/connection resources.
  **Mitigation:** Gateway-level strict rate limiting on `/auth/*` (tighter limit than general API). **Risk: High → Medium after control.**
- **Threat (Information Disclosure):** Stack traces or "user not found" vs "wrong password" leak account enumeration info.
  **Mitigation:** Standardized generic error middleware returning identical `401 Unauthorized` for both cases.
- **Threat (Spoofing):** Attacker steals a long-lived access token.
  **Mitigation:** JWT lifespan capped at 15 minutes; refresh token rotated on every use (old refresh token immediately invalidated).

### 5.2 Order Read Operations (`GET /orders`, `GET /orders/{id}`) — TB-1, TB-2
- **Threat (Elevation of Privilege — BOLA/IDOR, OWASP API #1):** User A requests User B's order ID.
  **Mitigation:** Resource Service validates `owner_id` of the requested object against the `sub` claim in the validated JWT — enforced server-side, never trusting a client-supplied "is mine" flag.
- **Threat (Tampering):** MITM alters returned order data.
  **Mitigation:** TLS termination at Gateway (TB-1); mTLS enforced Gateway↔Resource (TB-2).

### 5.3 Order Write Operations (`POST /orders`, `DELETE /orders/{id}`) — TB-1, TB-2
- **Threat (Elevation of Privilege):** Token with `orders:read` scope attempts to create/delete an order.
  **Mitigation:** JWT scope validation middleware at the Gateway **and** independently at the Resource Service (defense in depth — a Gateway bug alone can't cause a full bypass).
- **Threat (Spoofing/Replay):** Attacker captures a valid order-creation request and resends it N times.
  **Mitigation:** Gateway injects timestamp + cryptographic nonce, HMAC-signed. Resource Service caches nonces (Redis, 5 min TTL) and rejects duplicates within the timestamp window.

### 5.4 Admin Endpoints (`GET /admin/audit-logs`) — TB-1, TB-2, TB-3
- **Threat (Elevation of Privilege):** Standard user accesses security telemetry.
  **Mitigation:** Strict `admin` scope check at both service layers.
- **Threat (Information Disclosure):** Audit log feed itself leaks other users' PII to an admin dashboard without redaction.
  **Mitigation:** Log redaction of sensitive fields (passwords, full card numbers if ever present) before they're ever written, not filtered at read time.

## 6. Residual Risk (What We're NOT Fully Solving)
Every threat model should be honest about what's left over — this is a strong interview signal ("I know the limits of what I built"):
- **Insider threat with valid Vault access** is only partially mitigated (Vault ACLs), not eliminated.
- **Zero-day in a dependency** (e.g., a JWT library CVE) is mitigated by dependency scanning in CI but not prevented.
- **Client-side token storage** (XSS stealing a token from browser storage) is out of scope since there's no browser frontend serving untrusted content to end users in this project.
- **SQL injection defense: RESOLVED (Sprint 10).** A real PostgreSQL database now backs order storage (`resource-service/db.py`). Every query is parameterized; a live SQL injection was demonstrated against a deliberately vulnerable version of the same code, then shown to fail against the real parameterized implementation. Defense in depth: the application connects as a least-privilege role (`orders_app`) that cannot create roles/databases, run OS commands, or reach any database but its own — verified live, not assumed. Full writeup, including two real bugs found while building this: `docs/sql-injection-demo.md`.
- **Output encoding defense is implemented for the customer-facing UI (Sprint 9), and checked, not just assumed.** Order data — including the intentionally-stored SQLi/XSS-looking strings from `docs/attack-report.md` — is rendered by `dashboard/src/components/OrderList.jsx` via plain JSX interpolation (`{o.item}`), which React always renders as a text node. `dangerouslySetInnerHTML`, raw `innerHTML`, and `eval(` were grepped for across the entire dashboard source and are absent — there is no code path that could turn a stored `<script>` payload into executing HTML. This should be re-checked any time new dashboard code is added, since the guarantee depends on that absence continuing to hold, not on a one-time proof.

## 7. References
- Architecture diagram: `architecture-diagram.md` (Mermaid, trust boundaries color-coded)
- STRIDE methodology: Microsoft Threat Modeling Tool documentation
- OWASP API Security Top 10 (referenced for BOLA classification)
- Attack report: `attack-report.md` (Week 6 — live-verified results of the attacker toolkit against every control above)
