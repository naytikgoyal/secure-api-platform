# System Architecture & Trust Boundaries

```mermaid
graph TD
    %% Trust Boundaries
    subgraph "Public / Untrusted Zone"
        Client[("External Client<br>(Browser/Postman)")]
        Attacker(("Attacker Toolkit<br>(Python Scripts)"))
    end

    subgraph "DMZ / API Gateway Zone"
        Gateway["API Gateway<br>(Node.js/Express)"]
        Dashboard["Security Dashboard<br>(React)"]
        Auth["Auth Server<br>(Node.js)"]
    end

    subgraph "Secure Internal Zone (Zero Trust)"
        Resource["Resource Service<br>(Python/FastAPI)"]
        Vault[("HashiCorp Vault<br>(Secrets)")]
        Logs[("Loki + Grafana<br>(Audit Logs)")]
        Redis[("Redis<br>(Rate Limits & Nonces)")]
    end

    %% Client Interactions
    Client -->|1. POST /auth/login (Returns JWT)| Auth
    Client -->|2. HTTPS Request + Bearer JWT| Gateway
    Attacker -.->|Simulated Replay, MITM, Injection Attacks| Gateway
    Dashboard -->|Reads /admin/audit-logs| Gateway

    %% Gateway Operations
    Gateway <-->|Check Rate Limits| Redis
    Gateway -->|3. mTLS + HMAC Signature + Nonce| Resource
    
    %% Internal Service Operations
    Resource <-->|Validate Nonce cache| Redis
    
    %% Secrets & Observability
    Vault -.->|Injects Keys & Certs at startup| Gateway
    Vault -.->|Injects Keys & Certs at startup| Resource
    
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