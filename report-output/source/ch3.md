@chapter 3 | DESIGN FLOW AND PROCESS

## 3.1 Concept Generation and Requirement Analysis

The design started from the seven problems in Chapter 1 and the threat actors identified in the project's threat model: an unauthenticated outsider who can reach only the public gateway, an authenticated user with limited permissions who tries to reach other users' data, a compromised dependency or container, and an insider or leaked credential with access to infrastructure. Host-operating-system compromise, physical access and social engineering were declared out of scope.

From these actors the following requirements were written. Functional requirements describe what the platform does for its users; security requirements describe what it must refuse to do. {tab:requirements} lists them. The requirement identifiers are used again in Chapter 4 and in Appendix 2 to show which test covers which requirement.

@table requirements | Functional and security requirements | 0.6,4.8,2.2
| ID | Requirement | Addressed by |
| --- | --- | --- |
| FR1 | Authenticate a user and issue a short-lived access token and a rotating refresh token | Auth Server |
| FR2 | Provide create, list, read and delete operations on orders | Gateway, Resource Service |
| FR3 | Allow reading, writing and administration to be granted separately as scopes | Auth Server, Gateway, Resource Service |
| FR4 | Let a user see and change only their own orders; allow an administrator to see any | Resource Service |
| FR5 | Give administrators an audit log, metrics, a live event stream and an attack-report store | Gateway |
| FR6 | Offer a customer view and an administrator security dashboard in a browser | Dashboard |
| SR1 | Accept only HTTPS, with TLS 1.2 or higher | Gateway, Auth Server, Resource Service |
| SR2 | Verify every access token for algorithm, signature, issuer, audience and expiry | Gateway and Resource Service |
| SR3 | Repeat the token and scope checks inside the internal service | Resource Service |
| SR4 | Require mutual TLS on the internal hop | Resource Service, Gateway |
| SR5 | Sign each internal request and reject tampered, stale and replayed requests | Gateway signs, Resource Service verifies |
| SR6 | Keep signing keys and database credentials in a secrets manager | Vault |
| SR7 | Limit login attempts and request rates, and lock out repeatedly failing accounts | Auth Server, Gateway |
| SR8 | Use only parameterised database queries, as a database role with minimum privileges | Resource Service, PostgreSQL |
| SR9 | Return generic error messages and log the real reason on the server | All services |
| SR10 | Write structured logs with a request identifier for every allow or deny decision | All services |
| SR11 | Be reproducible on a laptop and testable by an automated attacker | Docker Compose, attacker toolkit |

## 3.2 Evaluation and Selection of Specifications and Features

Not every feature that could be added was worth adding. Each candidate was judged by the problem it solves, the effort it needs and the risk it adds. {tab:features} records the decisions. Features marked deferred are discussed again as future work in Chapter 5.

@table features | Feature selection | 2.4,1.1,4.4
| Feature | Decision | Reason |
| --- | --- | --- |
| RS256 JWT access tokens, 15 minutes | Selected | The private key stays in one service; the others hold only a public key and cannot mint tokens |
| Opaque rotating refresh tokens | Selected | A refresh token can be revoked by deleting it and cannot be used twice |
| Scope-based authorisation at two layers | Selected | A flaw in one layer does not give a full bypass |
| Mutual TLS between Gateway and Resource Service | Selected | The internal service can verify who is calling, not only encrypt the channel |
| HMAC signature, timestamp and nonce | Selected | Defeats tampering and replay by someone who can still make a TLS connection |
| HashiCorp Vault for secrets | Selected | Removes signing keys and database passwords from files and compose configuration |
| Redis for counters and nonces | Selected | Shared state keeps limits and replay checks correct if a service is scaled out |
| PostgreSQL with a least-privilege role | Selected | Makes SQL injection a real threat to defend against, and limits the damage of any future mistake |
| Account lockout in addition to IP rate limit | Selected | Stops one source from guessing at one account; keyed by username and address so that an outsider cannot lock out the real user |
| Structured logs, dashboard and Grafana | Selected | Allow and deny decisions must be visible to be useful |
| Attacker toolkit | Selected | Turns design claims into tested facts |
| Multi-factor authentication, OpenID Connect | Deferred | Needs an identity provider; out of scope for this project |
| Vault AppRole and PKI, auto-unseal | Deferred | Needs production Vault operation; the project uses dev mode and says so |
| Network segmentation, Kubernetes, service mesh | Deferred | Adds operational weight without changing what is being tested |
| Web application firewall | Deferred | Does not replace the application-level controls being studied |

## 3.3 Design Constraints

The university format asks that regulations, economic, environmental, health, manufacturability, safety, professional, ethical, social and political issues be considered in the design. Each is treated below in terms of this project and not in general terms.

### 3.3.1 Regulations

An orders service holds personal data as soon as an owner identifier or name appears in it. India's Digital Personal Data Protection Act, 2023 requires those who decide how personal data is processed to build reasonable security safeguards against breaches [@prs2023]. This project does not claim legal compliance, which depends on organisational measures that a software prototype cannot supply. It does supply technical safeguards that a compliance programme could point to, and it keeps real personal data out of the demonstration by using invented users and orders.

### 3.3.2 Economic

Every component is free software: Node.js, Python, PostgreSQL, Redis, Vault (the free container image), Loki, Grafana and Docker. The whole system runs on one laptop, so the cost of the project is the author's time. The same low cost is a design constraint: a design that needs commercial gateways, hardware security modules or managed identity services would not be reproducible by a student team.

### 3.3.3 Environmental

The platform runs as ten containers on one development laptop, so its environmental footprint is that of ordinary development work. The relevant design choice was to avoid always-on cloud resources for a prototype, and to make the stack start and stop from the command line with a short documented sequence so that it need not stay running.

### 3.3.4 Health

The software has no direct health impact. The indirect link is that leaked personal data can harm people, which is one reason the project treats authorisation and data exposure as its first priorities.

### 3.3.5 Manufacturability and reproducibility

For software, manufacturability means that someone else can build and run the same thing. The platform is therefore defined entirely by files: Dockerfiles, a Compose file, scripts that generate certificates and initialise Vault, and pinned dependency manifests. For this report the stack was built and run from a copy of the repository with freshly generated certificates and keys, and all ten containers reached a healthy state.

### 3.3.6 Safety

The platform controls no physical process, so safety here means safe failure. The design rule is to fail closed: if the Gateway cannot read the public key it answers 503, if the signing secret is missing it refuses to call the internal service, and if the two sides disagree on the signed text every request is rejected, not accepted.

### 3.3.7 Professional

The work follows published practice: the OWASP API Security list and verification standard, the NIST and IETF documents surveyed in Chapter 2, secret scanning with gitleaks, dependency auditing, and an explicit threat model. Decisions and failures are written down in a build log and in this report, in the way a professional team would record an engineering decision.

### 3.3.8 Ethical

The attacker toolkit is aimed only at the author's own local deployment, uses invented accounts and never touches a third-party system. Demonstration credentials are labelled as demonstration values and are never used for anything else. Weaknesses that were found, including ones that contradict earlier claims in the project's own documents, are reported in Chapter 4, because reporting only the successes would mislead the reader.

### 3.3.9 Social

APIs underpin services that people rely on every day. A platform that shows how to resist common attacks without commercial tools makes those practices accessible to small teams and students. The report is written to be understandable by a reader who is not already a security specialist.

### 3.3.10 Political

Data protection law, export rules for cryptography and national guidance on zero trust differ between countries, and they change. The design uses widely published open algorithms (RSA, SHA-256, TLS) and refers to international standards, so that it is not tied to the rules of one country. Where a national rule applies, as with the Indian data protection law above, it is named instead of assumed.

## 3.4 Analysis and Feature Finalisation Subject to Constraints

{tab:constraints} shows how the constraints changed the design. It is the link between Sections 3.2 and 3.3 and the architecture described later in this chapter.

@table constraints | Effect of the constraints on the final design | 1.5,4.5
| Constraint | Effect on the design |
| --- | --- |
| Regulation | Use invented data only; keep personal data out of logs; document safeguards; do not claim legal compliance |
| Economic | Free and open components only; one-machine deployment; no managed services |
| Environmental | Ten containers on one machine; short scripted start and stop |
| Manufacturability | Everything defined as code and scripts; certificates and keys generated, never committed |
| Safety | Fail closed; generic errors to clients, real reasons to logs |
| Professional | Follow OWASP, NIST and IETF guidance; threat model first; test with an attacker |
| Ethical | Attack only the local system; invented accounts; report failures honestly |
| Social and political | Plain-language documentation; open standards and algorithms |

## 3.5 Alternative Designs

Three architectures were analysed. They are described below, drawn side by side in {fig:alternatives}, and then compared with the weighted criteria in {tab:matrix}. The analysis is the author's engineering assessment of each design's properties; it is not a measurement.

@figure alternatives | diagrams/fig-alternatives.png | 16 | Three alternative designs compared: perimeter trust, session-based monolith and layered zero trust

### 3.5.1 Alternative A: perimeter trust

An internet-facing gateway terminates TLS and validates a JSON Web Token. Behind it, internal services accept any request that comes from the gateway and share one database account. This is the simplest way to put an API in front of several services and a common pattern in small systems. Its strength is speed of construction. Its weakness is that all security rests on one check: a gateway bug, a stolen internal address or a container with network access gives an attacker the same power as the gateway has. There is also no protection against a captured request being repeated on the internal hop.

### 3.5.2 Alternative B: monolith with server-side sessions

One application authenticates users with a session cookie held in server memory, checks roles in the same process, and talks to its database directly. It has the fewest moving parts and is easy to test. It does not have an internal network hop to protect, but it also has no isolation: a flaw anywhere in the application, such as an injection, runs with the permissions of the whole application. Session state held in one process also makes horizontal scaling and token-style verification by other services awkward.

### 3.5.3 Alternative C: layered zero trust

The gateway verifies the token, scope and rate limit. It then signs the internal request and sends it over mutual TLS. The internal service verifies the client certificate, the signature, the time window and a single-use nonce, checks the token and scope again, enforces ownership, and queries a database through parameterised statements under a role with minimal privileges. Secrets come from a secrets manager. This design has several independent barriers, at the price of more components, more start-up steps and extra latency per request.

### 3.5.4 Comparison

The criteria in {tab:matrix} were weighted by how directly they relate to the problems of Chapter 1. Resistance to token theft and replay and containment of a compromised component each carry weight 20, because they correspond to the two largest risks in the threat model. Scores run from 1 (poor) to 5 (strong). For the two cost criteria, complexity and performance, a higher score means a lower cost.

@table matrix | Weighted comparison of the three alternatives | 3.4,0.7,0.6,0.6,0.6
| Criterion | Weight | A | B | C |
| --- | --- | --- | --- | --- |
| Resistance to token theft, forgery and replay | 20 | 2 | 2 | 4 |
| Containment if one component is compromised | 20 | 1 | 1 | 4 |
| Protection of the data layer (injection, over-privilege) | 15 | 2 | 3 | 5 |
| Secrets and key management | 10 | 2 | 2 | 3 |
| Auditability and observability | 10 | 3 | 3 | 4 |
| Simplicity of build and operation | 10 | 5 | 5 | 2 |
| Low performance overhead | 5 | 5 | 5 | 3 |
| Testability and verifiability | 10 | 3 | 4 | 5 |
| **Weighted score (maximum 500)** | 100 | **245** | **270** | **390** |
| **Percentage of maximum** | | **49%** | **54%** | **78%** |

## 3.6 Best Design Selection

Alternative C scores 390 of 500, ahead of B at 270 and A at 245. The margin comes from the two heaviest criteria, containment and resistance to token and replay attacks, and from the data layer, where only C combines parameterised queries with a limited database role. Alternative C does lose on simplicity and on performance cost, and the scores say so honestly. The reasons for choosing it are the following.

- The purpose of the project is to study defence in depth. Only C has more than one independent barrier to study.
- Each barrier can be attacked on its own, which makes the design testable. The Resource Service can be called directly, bypassing the Gateway, to show that it refuses the request by itself.
- Its costs are acceptable for a prototype: extra start-up steps are scripted, and the added latency is small compared with the human-scale operations the API serves (this was not measured, and Chapter 4 does not claim a figure).
- The weaknesses of C are the places where the design is still incomplete (development-mode Vault, a flat Docker network, in-memory lockout state), and they are recorded as limitations.

### 3.6.1 How sensitive is the choice?

A weighted score depends on the weights, so the comparison was repeated with two other weightings ({tab:sensitivity}). In the first, all eight criteria carry equal weight. In the second, a team that values speed of delivery above everything is imagined: simplicity of build and operation carries weight 30 and low performance overhead 20, token and replay resistance, containment and the data layer carry 10 each, secrets and auditability 5 each, and testability 10.

@table sensitivity | Comparison under three weightings | 3.6,1,1,1,1.6
| Weighting | A: perimeter | B: monolith | C: layered | Highest |
| --- | --- | --- | --- | --- |
| Baseline ({tab:matrix}) | 49% | 54% | 78% | C |
| All criteria equal | 57.5% | 62.5% | 75% | C |
| Speed and simplicity first | 71% | 75% | 67% | B |

The layered design wins whenever security criteria carry at least their ordinary share of the weight, but it loses to the simple monolith when simplicity and overhead dominate. The honest reading is that the choice of Alternative C follows from the purpose of the project, which is to study and test defence in depth, and not from any claim that it is the best architecture for every team. A small team with low-value data and little time could reasonably choose B and put the saved effort into the data-layer controls that both B and C share.

## 3.7 Implementation Plan

### 3.7.1 Architecture and components

{fig:architecture} shows the components, their zones and the eight main flows. The Gateway and Auth Server face the client. The Resource Service, PostgreSQL, Redis and Vault form the internal side. Loki, Promtail and Grafana collect logs. The attacker toolkit sits with the clients because it uses the same entry point as any other caller. {tab:components} lists each component with its technology, port and responsibility.

@figure architecture | diagrams/fig-architecture.png | 16 | System architecture with zones and numbered flows

@table components | Components and responsibilities | 1.4,1.5,0.6,3.5
| Component | Technology | Port | Responsibility |
| --- | --- | --- | --- |
| API Gateway | Node.js 20, Express 4 | 3000 | HTTPS entry point; JWT, scope and rate-limit checks; signs and forwards requests; admin endpoints |
| Auth Server | Node.js 20, Express 4 | 4000 | Login, token issue, refresh rotation, login rate limit and lockout |
| Resource Service | Python 3.12, FastAPI | 8000 | mTLS and signature verification, second token check, ownership, orders in PostgreSQL |
| PostgreSQL | 16 | internal | Orders table, least-privilege role |
| Redis | 7 | 6379 | Rate-limit counters, nonces |
| Vault | 1.17, dev mode | 8200 | JWT keys, HMAC key, database credentials |
| Dashboard | React 18, Vite 5 | 5173 | Login, customer view, administrator security view |
| Loki, Promtail, Grafana | 3.1.0, 3.1.0, 11.1.0 | 3100, 3001 | Log storage, collection and visualisation |
| Attacker toolkit | Python 3 | none | Five attack scripts and a runner |

### 3.7.2 Trust boundaries

{fig:trust} divides the system by trust. Three boundary crossings carry the controls that matter most: the Internet-to-Gateway crossing, the Gateway-to-Resource-Service crossing and the services-to-Vault crossing. Every threat in the Chapter 4 register is attached to one of them.

@figure trust | diagrams/fig-trust-boundaries.png | 16 | Trust zones and the three boundary crossings

### 3.7.3 Token design

The Auth Server signs access tokens with an RSA private key that it alone holds, using the RS256 algorithm. Each token carries the standard claims issuer, audience, subject and expiry and one custom claim, the list of scopes [@rfc7519]. The access token lives for 15 minutes. A refresh token is a random 48-byte value held on the server for seven days and deleted when it is used, so each refresh returns a new pair and an old refresh token stops working. Three roles are provided for the demonstration: a standard user with read and write scopes, a restricted user with read scope only, and an administrator with read, write and admin scopes. The Gateway and the Resource Service hold only the public key, so neither can issue a token, and both pin the accepted algorithm to RS256 so that an unsigned token or an HS256 token made with the public key as the secret is not even evaluated [@rfc8725].

### 3.7.4 Login and refresh flow

@figure login | diagrams/fig-login-sequence.png | 15 | Login and refresh-token rotation

{fig:login} shows the flow. The request is first counted against a limit of ten per minute per source address. The username and source address are checked against the lockout table. One bcrypt comparison follows for every attempt, against a dummy hash when the username does not exist, and a failure of any kind returns the same 401 message. Success clears the failure count for that source and returns both tokens.

### 3.7.5 Authenticated request flow

@figure request | diagrams/fig-request-sequence.png | 15 | Path of an authenticated read request through all layers

{fig:request} follows a read of the user's own orders. The Gateway verifies the token, counts the request against the per-user limit of 100 per minute and checks the scope. It then calls the Resource Service over mutual TLS with a signature, timestamp and nonce. The Resource Service verifies the signature and window, reserves the nonce in Redis, verifies the token and scope itself, applies the ownership rule and runs a parameterised query. For a write, the Gateway takes the owner identifier from the verified token and ignores any owner value in the request body; the Resource Service then checks that the identifier matches its own verification of the token.

### 3.7.6 Request-signing scheme

The signing scheme has to satisfy a practical constraint: the two services are written in different languages and must agree on exactly which bytes were signed. The canonical message is five fields joined by line feeds: the upper-case method, the request target as it appears on the wire including any query string, the raw body, the Unix timestamp in seconds and a 128-bit random nonce in hexadecimal. The signature is the hexadecimal HMAC-SHA256 of that message under the shared key [@rfc2104]. In the notation of the symbol table, σ = HMAC-SHA256(K, M), and a request is accepted only if |now − t| ≤ Δ with Δ = 60 seconds, σ matches in constant time, and the nonce n has not been seen during the last T = 300 seconds. The retention time T is deliberately longer than the window Δ, so a nonce can never leave the store before its timestamp has already become invalid. {fig:hmac} shows the steps on both sides.

@figure hmac | diagrams/fig-hmac-flow.png | 15 | Signing at the Gateway and verification at the Resource Service

### 3.7.7 Data model

The only persistent business data is the orders table. Everything else is small, short-lived state kept in memory, in Redis or in Vault ({fig:model}). Owner identifiers in the table equal the subject claim of the token, but no foreign key exists because user accounts are held by the Auth Server and not in the database.

@figure model | diagrams/fig-data-model.png | 15 | Data held by the system and where it lives

### 3.7.8 Secrets and key rotation

Three secrets live in Vault: the JWT key pair, the HMAC key and the database credentials. A script writes them into Vault after the container starts and then removes the local plaintext copies. Each service reads its secrets once at start-up and keeps them in memory. For rotation, a script writes a new HMAC value as a new version of the Vault entry; both services must then be restarted to pick it up, after which requests signed with the old value are rejected. This restart requirement is a simplification that the runbook records. Key management guidance suggests replacing keys periodically and planning for the process in advance [@barker2020], and the script and runbook are the project's version of that plan.

### 3.7.9 Observability

All three services write one JSON line per event with a request identifier. Promtail collects container output, Loki stores it, and Grafana shows three panels. In parallel, the Gateway keeps its own allow and deny events in a ring buffer of 200 entries and exposes them to administrators as a list, a metrics summary and a live Server-Sent Events stream. The dashboard reads that stream with a streaming fetch call that carries the Authorization header; the browser's built-in EventSource would have forced the token into the URL, where it can leak into logs.

### 3.7.10 Request-processing algorithm

{fig:flow} gives the processing order as a flowchart, including the response a caller gets when each check fails. Algorithm 1 restates the Resource Service part in pseudo-code.

@figure flow | diagrams/fig-implementation-flow.png | 15.5 | Order of checks across the Gateway and Resource Service, with the response for each failure

@code
Algorithm 1: Resource Service request handling
1  if path is /health: accept (the TLS handshake already demanded a client certificate)
2  read X-Signature, X-Timestamp, X-Nonce; if any is missing: reply 401
3  rebuild M from method, raw path with query, raw body, timestamp and nonce
4  if |now - timestamp| > 60 s: reply 401
5  if HMAC-SHA256(K, M) differs from X-Signature (constant-time compare): reply 401
6  if SET nonce:<n> NX EX 300 in Redis fails because the key exists: reply 401 (replay)
7  verify the Bearer JWT: RS256 only, issuer, audience, expiry; on failure: reply 401
8  require the route scope; on failure: reply 403
9  for object routes: require owner = token subject, or the admin scope; else reply 403
10 run the parameterised query; reply 200, 201, 204 or 404
@endcode

### 3.7.11 Development approach and tools

The platform was built in short increments, each ending with something that could be run and attacked. Each increment started with the threat it addressed and ended with a test or an attack script. Defects found by this loop were fixed and written down. The implementation tools, their versions as observed in the running system, and the test tools are listed in Chapter 4.
