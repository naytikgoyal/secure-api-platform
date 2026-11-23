# System Architecture & Trust Boundaries

## Legend
- 🟥 **Red zone** — Untrusted / public internet
- 🟨 **Yellow zone (DMZ)** — Internet-facing, semi-trusted, TLS-terminated
- 🟩 **Green zone** — Internal only, zero-trust (mTLS required), never internet-reachable
- **Solid arrows** — synchronous request/response traffic
- **Dashed arrows** — async / startup-time / observability traffic
- **TB-1 / TB-2 / TB-3** — trust boundary crossings, matching `threat-model.md` Section 3

```mermaid
graph TD
    %% Trust Boundaries
    subgraph "🟥 Public / Untrusted Zone"
        Client[("External Client\n(Browser/Postman)")]
        Attacker(("Attacker Toolkit\n(Python Scripts)"))
    end

    subgraph "🟨 DMZ / API Gateway Zone"
        Gateway["API Gateway\n(Node.js/Express)"]
        Dashboard["Security Dashboard\n(React)"]
        Auth["Auth Server\n(Node.js)"]
    end

    subgraph "🟩 Secure Internal Zone (Zero Trust)"
        Resource["Resource Service\n(Python/FastAPI)"]
        Vault[("HashiCorp Vault\n(Secrets)")]
        Logs[("Loki + Grafana\n(Audit Logs)")]
        Redis[("Redis\n(Rate Limits & Nonces)")]
    end

    %% Client Interactions
    Client -->|"1. POST /auth/login (TB-1)"| Auth
    Auth -->|"1a. Returns JWT access+refresh"| Client
    Client -->|"2. HTTPS + Bearer JWT (TB-1)"| Gateway
    Gateway -->|"2a. JSON response"| Client
    Attacker -.->|"Simulated Replay, MITM,\nInjection Attacks (TB-1 only)"| Gateway
    Dashboard -->|"Reads /admin/audit-logs"| Gateway
    Dashboard -->|"Triggers attack simulation"| Attacker

    %% Gateway Operations
    Gateway <-->|"Check rate limits"| Redis
    Gateway -->|"3. mTLS + HMAC Signature + Nonce (TB-2)"| Resource
    Resource -->|"3a. JSON response"| Gateway

    %% Internal Service Operations
    Resource <-->|"Validate nonce cache"| Redis

    %% Secrets & Observability
    Vault -.->|"TB-3: Injects keys & certs at startup"| Gateway
    Vault -.->|"TB-3: Injects keys & certs at startup"| Resource
    Vault -.->|"TB-3"| Auth

    Gateway -.->|"Emits structured JSON"| Logs
    Resource -.->|"Emits structured JSON"| Logs
    Auth -.->|"Emits structured JSON"| Logs

    %% Styling
    classDef secure fill:#d4edda,stroke:#28a745,stroke-width:2px,color:#000;
    classDef public fill:#f8d7da,stroke:#dc3545,stroke-width:2px,color:#000;
    classDef dmz fill:#fff3cd,stroke:#ffc107,stroke-width:2px,color:#000;

    class Client,Attacker public;
    class Gateway,Dashboard,Auth dmz;
    class Resource,Vault,Logs,Redis secure;
```

## Key Design Property (say this out loud in interviews)
The Attacker node has **exactly one edge** in this diagram — into the Gateway. It cannot reach the Resource Service, Vault, Redis, or Logs directly, no matter what it sends. That single-entry-point property is the whole point of the DMZ pattern: even a fully successful attack at TB-1 still has to get through TB-2 (mTLS + HMAC + nonce + independent scope check) before touching real data. If your diagram ever grows a second arrow from Attacker into the green zone, that's a design flaw to catch before writing code, not after.

## Data Flow Summary (numbered, matches diagram labels)
1. Client authenticates → Auth Server issues short-lived JWT (access) + refresh token.
2. Client calls Gateway over HTTPS with `Authorization: Bearer <JWT>`.
3. Gateway validates JWT, checks Redis for rate-limit status, then signs the downstream request (HMAC + nonce + timestamp) and calls Resource Service over mTLS.
4. Resource Service verifies the mTLS client cert, HMAC signature, nonce (via Redis), timestamp window, and scope — independently of the Gateway's own checks — before touching data.
5. Response flows back Resource → Gateway → Client.
6. Every service emits structured logs to Loki/Grafana continuously; Vault injects secrets once at startup (not per-request).
