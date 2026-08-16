# System Architecture & Trust Boundaries

```mermaid
graph TD
    %% Trust Boundaries
    subgraph "Public / Untrusted Zone"
        Client[("External Client\n(Browser/Postman)")]
        Attacker(("Attacker Toolkit\n(Python Scripts)"))
    end

    subgraph "DMZ / API Gateway Zone"
        Gateway["API Gateway\n(Node.js/Express)"]
        Dashboard["Security Dashboard\n(React)"]
        Auth["Auth Server\n(Node.js)"]
    end

    subgraph "Secure Internal Zone (Zero Trust)"
        Resource["Resource Service\n(Python/FastAPI)"]
        Vault[("HashiCorp Vault\n(Secrets)")]
        Logs[("Loki + Grafana\n(Audit Logs)")]
        Redis[("Redis\n(Rate Limits & Nonces)")]
    end

    %% Client Interactions
    Client -->|1. POST /auth/login\n(Returns JWT)| Auth
    Client -->|2. HTTPS Request + Bearer JWT| Gateway
    Attacker -.->|Simulated Replay, MITM,\nInjection Attacks| Gateway
    Dashboard -->|Reads /admin/audit-logs| Gateway

    %% Gateway Operations
    Gateway <-->|Check Rate Limits| Redis
    Gateway -->|3. mTLS + HMAC Signature + Nonce| Resource
    
    %% Internal Service Operations
    Resource <-->|Validate Nonce cache| Redis
    
    %% Secrets & Observability
    Vault -.->|Injects Keys & Certs\nat startup| Gateway
    Vault -.->|Injects Keys & Certs\nat startup| Resource
    
    Gateway -.->|Emits Structured JSON| Logs
    Resource -.->|Emits Structured JSON| Logs
    Auth -.->|Emits Structured JSON| Logs

    %% Styling
    classDef secure fill:#d4edda,stroke:#28a745,stroke-width:2px,color:#000;
    classDef public fill:#f8d7da,stroke:#dc3545,stroke-width:2px,color:#000;
    classDef dmz fill:#fff3cd,stroke:#ffc107,stroke-width:2px,color:#000;
    
    class Client,Attacker public;
    class Gateway,Dashboard,Auth dmz;
    class Resource,Vault,Logs,Redis secure;