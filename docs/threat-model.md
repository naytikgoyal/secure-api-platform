# Secure API Communication Platform: Threat Model

## 1. Introduction
This document outlines the threat model for the Secure API Communication Platform. The system utilizes a defense-in-depth architecture, routing external client traffic through a Node.js API Gateway to a trusted Python FastAPI Resource Service. 

We utilize the **STRIDE** methodology to systematically identify and mitigate threats across the trust boundaries.

## 2. High-Level STRIDE Analysis
| STRIDE Category | Example Threat in This System | Primary Control |
| :--- | :--- | :--- |
| **Spoofing** | Attacker forges a client identity or replays a stolen JWT. | OIDC/JWT with short expiry (≤ 15 min) + mTLS on internal hop. |
| **Tampering** | Attacker modifies request body/params in transit. | External TLS 1.2+; Internal HMAC request signing + mTLS. |
| **Repudiation** | Client denies having made a malicious/erroneous request. | Centralized, tamper-evident JSON audit logs with correlation IDs. |
| **Information Disclosure** | Secrets leak via env vars, logs, or error responses. | HashiCorp Vault secrets management, log redaction, generic errors. |
| **Denial of Service** | Flooding the public API to exhaust resources. | Per-client rate limiting (Redis-backed) + global circuit breakers. |
| **Elevation of Privilege** | Client with `read` scope calls a `write` endpoint. | RBAC/Scope enforcement independently at Gateway and Resource Service. |

## 3. Per-Endpoint Threat Analysis

### 3.1 Authentication Endpoints (`POST /auth/login`, `POST /auth/refresh`)
*   **Threat (DoS):** Attacker brute-forces credentials to exhaust database connections.
    *   **Mitigation:** Gateway-level strict rate limiting on `/auth` routes.
*   **Threat (Information Disclosure):** Stack traces leak during failed logins.
    *   **Mitigation:** Standardized generic error middleware returning strictly `401 Unauthorized`.
*   **Threat (Spoofing):** Attacker steals a long-lived access token.
    *   **Mitigation:** JWT lifespan restricted to 15 minutes. Refresh token rotated upon use.

### 3.2 Order Read Operations (`GET /orders`, `GET /orders/{id}`)
*   **Threat (Elevation of Privilege):** Broken Object Level Authorization (BOLA/IDOR) - User A requests User B's order ID.
    *   **Mitigation:** Resource Service explicitly validates that the `owner_id` of the requested object matches the `sub` (subject) claim in the validated JWT.
*   **Threat (Tampering):** Man-in-the-Middle (MITM) altering the returned order data.
    *   **Mitigation:** TLS termination at Gateway; mTLS enforced between Gateway and Resource Service.

### 3.3 Order Write Operations (`POST /orders`, `DELETE /orders/{id}`)
*   **Threat (Elevation of Privilege):** Token with `orders:read` scope attempts to create or delete an order.
    *   **Mitigation:** JWT scope validation middleware at the Gateway **and** Resource Service rejects requests lacking `orders:write`.
*   **Threat (Spoofing/Replay):** Attacker captures a valid order creation request and resends it 100 times.
    *   **Mitigation:** Gateway injects a timestamp and cryptographic nonce, signed via HMAC. Resource Service caches the nonce for 5 minutes and rejects duplicates.

### 3.4 Admin Endpoints (`GET /admin/audit-logs`)
*   **Threat (Elevation of Privilege):** Standard user accesses the security telemetry.
    *   **Mitigation:** Strict scope check for `admin` required at both service layers.