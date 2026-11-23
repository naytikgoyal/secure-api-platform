@chapter 4 | RESULTS ANALYSIS AND VALIDATION

This chapter reports what was built, how it was tested and what the tests showed. All results come from runs made on 28 October 2026 against a copy of the repository, started with freshly generated certificates and keys. Raw logs and unedited screenshots from those runs are kept with the report as evidence files. Where a result contradicts a claim in the project's own documents, the result is reported as observed. Sections 4.5 and 4.6 describe this first round of testing. Five of the findings were then fixed in the author's repository and the system was tested again the same day; Section 4.7.1 describes the fixes and their re-test.

## 4.1 Implementation Environment and Tools

### 4.1.1 Software and versions

The versions in {tab:tools} were read from the running containers and from the package managers, not copied from the dependency manifests, because the manifests allow ranges.

@table tools | Tools and versions observed in testing | 1.4,1.7,3
| Area | Tool and version | Role |
| --- | --- | --- |
| Host | macOS 26.5.2 on Apple silicon (arm64) | Development and test machine |
| Containers | Docker Engine 29.8.0, Docker Compose v5.5.1 | Runs the ten containers on one bridge network |
| Gateway, Auth Server | Node.js 20.20.2; Express 4.22.3; jsonwebtoken 9.0.3; helmet 7.2.0; express-rate-limit 7.5.1; rate-limit-redis 4.3.1; pino 9.14.0; bcryptjs 2.4.3 | HTTPS APIs, token handling, headers, rate limits, logging |
| Resource Service | Python 3.12.16; FastAPI 0.111.0; Starlette 0.37.2; Pydantic 2.14.1; PyJWT 2.8.0; uvicorn 0.30.1; structlog 24.1.0 | Internal API, validation, signature checks |
| Data stores | PostgreSQL 16.15; Redis 7.4.11 | Orders; counters and nonces |
| Secrets | HashiCorp Vault 1.17.6 (development mode) | JWT keys, HMAC key, database credentials |
| Observability | Loki 3.1.0, Promtail 3.1.0, Grafana 11.1.0 | Log storage, collection, dashboards |
| Dashboard | React 18.3.1, Vite 5.4.21 | Customer and administrator views |
| Testing | pytest 8.2.2; Python requests 2.32.3 and cryptography 42.0.8 (attack scripts); curl; openssl; psql; Node.js built-in test runner (Auth Server tests); Playwright with headless Chromium | Unit tests, attacks, probes, browser checks |

### 4.1.2 Size of the work

{tab:size} counts lines of code and configuration in the repository, excluding generated files, dependency folders and lock files. The Resource Service and Auth Server figures include 170 and 83 lines of unit tests. The counts are taken after the fixes described in Section 4.7.1. The documentation set (README, threat model, architecture, signing scheme, key-rotation runbook, attack report, SQL-injection demonstration, build log, demo script and others) adds a further 1,379 lines.

@table size | Lines of code and configuration by component | 3,1.4,3
| Component | Lines | Main languages and files |
| --- | --- | --- |
| API Gateway | 727 | JavaScript: entry point, middleware, routes, proxy client, signer, Vault client |
| Auth Server | 548 | JavaScript: login, refresh store, lockout, rate limiter; includes 83 lines of tests |
| Resource Service | 862 | Python: API, signature and nonce logic, database layer, tests |
| Dashboard | 1,149 | JavaScript (React) and CSS |
| Attacker toolkit | 998 | Python: five attack scripts, harness, runner |
| Infrastructure | 588 | Compose file, shell scripts, Grafana and Promtail configuration |
| **Total** | **4,872** | |

## 4.2 Implementation of the Solution

### 4.2.1 Deployment view

{fig:deploy} shows what actually runs. Ten containers share one bridge network. Eight of them publish a port on the host, which is convenient for development and is discussed as a weakness in Section 4.7. PostgreSQL publishes no port at all, so it can be reached only from other containers. Certificates are mounted read-only into the three services that need them.

@figure deploy | diagrams/fig-deployment.png | 16 | Containers, images, ports, volumes and mounts of the test deployment

### 4.2.2 API Gateway

The Gateway is an Express application served over HTTPS. Its middleware order is: security headers from helmet, a CORS rule that allows only the dashboard's origin, structured request logging with a generated request identifier, and a JSON body parser limited to 100 kB. Under `/orders`, every route first runs the token check, then a per-user rate limiter, and then a scope check specific to the route. Under `/admin`, every route requires a valid token and the admin scope. Administrators can list audit events, read metrics, subscribe to a live event stream, store and read the last attack report, and trigger three attack simulations that call the Gateway's own HTTPS listener so that the resulting deny events come from the real middleware.

The token check ({fig:authjs}) pins the algorithm to RS256 and validates issuer, audience and expiry. A failure returns the same 401 message whatever the reason, while the real reason is logged and sent to the audit buffer. The outbound client to the Resource Service uses an HTTPS agent that trusts only the project's certificate authority and presents the Gateway's own certificate as a client identity; it never disables certificate verification.

@codefile authjs | gateway/src/middleware/auth.js | 41 | 63 | JWT verification in the Gateway with a pinned algorithm

One start-up detail is worth recording. The orders router builds its Redis-backed rate limiter when the module is imported, so it must be imported only after the Redis connection is open. The Gateway therefore connects to Redis, fetches secrets from Vault, and only then imports the router with a dynamic import. This was a bug found during development: the limiter had been created before Redis was ready.

### 4.2.3 Auth Server

The Auth Server holds three invented users in memory with bcrypt password hashes at cost factor 10 [@provos1999]. A login is processed in a fixed order: a check that both fields are strings, the IP rate limit (ten requests a minute, counted in Redis), the lockout check for the pair of submitted username and source address, one bcrypt comparison, and finally token issue. The comparison is made even when the username does not exist, against a hash of a random value, so response time does not reveal which names are real. The lockout counts failures for any submitted username, including ones that do not exist, so that an attacker cannot tell real accounts from invented ones by watching which names get locked. Five failures from one address lock that address out of that account for fifteen minutes, and failures older than fifteen minutes are forgotten. Failures against one account from many addresses are counted together, and a warning is logged when they pass thirty; that is detection, not prevention. Refresh tokens are 48 random bytes, held in memory for seven days, and removed when used. In the first round of testing the comparison was skipped for unknown names and the lockout was keyed by username alone; Section 4.7.1 explains the change.

### 4.2.4 Resource Service

The Resource Service is a FastAPI application started under uvicorn with mutual TLS required: a connection without a certificate signed by the project's authority is refused during the handshake. An HTTP middleware verifies the signature headers before any route code runs, then reserves the nonce. Route dependencies then verify the token and scope. Pydantic models restrict the `item` field to 1 to 200 characters without null bytes, and `quantity` to whole numbers from 1 to 1000. The ownership rule is applied in each handler: a caller may read or delete an order only if the order's owner equals the token subject or the token carries the admin scope, and a listing for a non-administrator is silently narrowed to the caller's own orders. An exception handler returns a generic 500 response and keeps details in the server output.

Two ordering lessons from development are visible in the code. Starlette runs middleware in reverse registration order, so the request-identifier middleware must be registered after the signature middleware to run before it. And because the Gateway signs the request target exactly as it appears on the wire, the verifier must rebuild it from the raw path bytes and raw query string; using the framework's decoded path made every percent-encoded identifier fail verification until this was fixed.

### 4.2.5 Data layer

All four database operations (create, list, read, delete) use `%s` placeholders and pass values separately to the driver, which is the first defence the OWASP guidance recommends [@owaspsqli]. Order identifiers are UUIDs, and a value that is not a valid UUID is treated as "not found" before the query is run. {fig:dbpy} shows the code. The database role used by the service is created by an initialisation script, owns only the `orders` database, has no superuser, create-database or create-role rights, and has its right to connect to the default database revoked. Connections are opened per request, which is simple but would be replaced by a pool under load.

@codefile dbpy | resource-service/db.py | 128 | 160 | Parameterised queries for listing and reading orders

### 4.2.6 Secrets handling

At start-up each service fetches the secrets it needs from Vault's key-value API using a token supplied through its environment. The Gateway receives the public key and the HMAC key; the Auth Server receives only the private key; the Resource Service receives the public key, the HMAC key and the database username and password. A script writes the secrets into Vault and removes the local files. A second script rotates the HMAC key by writing a new version. In this test deployment Vault runs in development mode, so the root token is a fixed string in the Compose file and storage is in memory. This is a deliberate demonstration setting and is listed as a limitation, not as a recommended practice [@vault].

### 4.2.7 Dashboard

The React dashboard decodes the token's scopes only to decide which view to show: administrators see the Security Operations Dashboard with a metrics row, a live request feed, a denies-only list, attack-simulation buttons and an attack-history panel; other users see a customer orders view, which for a read-only user explains that creation and deletion are unavailable. The decoded scopes are never used for a security decision, since the backend repeats every check. A search of the dashboard source found no use of `dangerouslySetInnerHTML`, `innerHTML`, `eval`, `localStorage` or `sessionStorage`: order text is shown through ordinary React text nodes, and the access token lives only in component state, so it disappears when the page is reloaded.

### 4.2.8 Observability

{fig:obs} shows the two paths by which events reach people. The Gateway, Auth Server and Resource Service print JSON lines; Promtail reads container output through the Docker socket and ships it to Loki; Grafana provisions a three-panel "Security Overview" dashboard. Separately, the Gateway records allow and deny decisions in a 200-entry ring buffer and serves them to administrators through the dashboard.

@figure obs | diagrams/fig-observability.png | 16 | Two event paths: Loki and Grafana for history, a live buffer for the dashboard

### 4.2.9 Attacker toolkit and CI

The attacker toolkit contains five scripts: replay of a captured signed request, token forgery (wrong key, `alg: none`, algorithm confusion), credential brute force with an enumeration check, injection and malformed-input probes against three places where user input reaches a query, and plaintext and TLS-downgrade attempts. A runner executes them in sequence, prints a combined result and posts it to the Gateway for the dashboard's attack-history panel. After the fixes described in Section 4.7.1 the runner runs the brute-force script last, the scripts fetch the keys they need from Vault when given a read token, and a check that cannot run is reported as SKIP, which the dashboard shows separately from PASS and FAIL. The repository also contains a GitHub Actions workflow that runs gitleaks, the unit tests, a Node syntax check and a non-blocking dependency audit. The workflow was not executed for this report, because the repository used here is a plain folder and not a connected Git repository, so no pipeline results exist to report.

### 4.2.10 Layers of checks

{fig:checks} summarises, by layer, the checks that the code performs. It is the implementation-side counterpart of the graphical abstract at the start of this report.

@figure checks | diagrams/fig-checks-per-layer.png | 16 | Checks performed at each of the four layers

## 4.3 Threat Register and Security Analysis

### 4.3.1 Threat register

The STRIDE categories are Spoofing, Tampering, Repudiation, Information disclosure, Denial of service and Elevation of privilege [@shostack2014]. {tab:threats} lists the threats that apply to the implemented architecture, with the mitigation found in the code, the test that exercised it and the risk that remains. The identifiers of the tests are explained in Section 4.4: U for unit tests, F for live flows, A for attacker-toolkit checks and P for independent probes. Residual risk is the author's judgement.

@table threats | Threat register for the implemented system | 0.5,2.2,0.9,2.4,1.5,2.6
| ID | Threat | STRIDE | Mitigation implemented | Evidence | Residual risk |
| --- | --- | --- | --- | --- | --- |
| T-01 | Forged or stolen access token | S | RS256 only; issuer, audience, expiry checked in two services; 15-minute life | F-12, A-TF | A stolen valid token works until it expires; no access-token revocation |
| T-02 | Replay of a captured internal request | S, T | HMAC, 60-second window, single-use nonce in Redis | U, A-RP | Redis is unauthenticated inside the network |
| T-03 | Tampering with an internal request | T | mTLS and HMAC over method, target, body | U, F-03, F-14 | Anyone holding the HMAC key can sign |
| T-04 | Plaintext or downgraded connection | T, I | TLS 1.2 minimum by runtime defaults | F-02, F-19, A-TL, P-01 | No explicit version or cipher policy; a CBC suite was accepted by the Resource Service |
| T-05 | Privilege escalation through scopes | E | Scope checks at Gateway and Resource Service | F-08, F-13 | Scopes are fixed in a demo user store |
| T-06 | Reading another user's order (BOLA) | E | Owner taken from the token; ownership check per object | F-09, F-10, A-IN | Object ownership is enforced only by the Resource Service |
| T-07 | SQL injection | T, E | Parameterised queries; UUID check; least-privilege role | F-15, A-IN | Every future query must follow the same rule |
| T-08 | Stored script injection in the browser | T, I | React text nodes; no unsafe HTML APIs | P-05 | Holds only while unsafe APIs stay absent |
| T-09 | Password guessing | S, D | 10 logins per minute per IP; lockout after 5 failures per username and address; bcrypt; warning when many addresses fail against one account | A-BF, P-04, R-03 | Guessing from many addresses is slowed and logged but not blocked; state is in memory |
| T-10 | Finding valid usernames | I | Identical 401 body and one bcrypt comparison for every attempt | A-BF, P-02, R-02 | Timing difference removed in the re-test (medians 56.5 and 56.0 ms); other side channels not examined |
| T-11 | Secrets leaking from files or images | I | Vault; local copies removed; secret scanning in CI definition | V-01 | Dev-mode Vault, fixed token, TLS keys on disk, bootstrap passwords in an environment file |
| T-12 | Request flooding | D | 100 requests per minute per user in Redis | P-03 | No global limit, no circuit breaker |
| T-13 | Actions that cannot be traced | R | JSON logs with request IDs; audit buffer | S-04, P-06 | Logs not tamper-evident, not redacted; buffer lost on restart |
| T-14 | Compromised container or dependency | E | Pinned CA; limited database role | V-02 | Containers run as root; Promtail reads the Docker socket; dependency audit is non-blocking |

### 4.3.2 Threats by endpoint

The project's threat model also analysed threats endpoint by endpoint. {tab:endpointthreats} restates that analysis and compares it with what the code does, because two of its statements turned out to differ from the implementation.

@table endpointthreats | Per-endpoint threats and implementation | 1.5,2.6,3.1,1.1
| Endpoint group | Threat (from the threat model) | What the code does | Evidence |
| --- | --- | --- | --- |
| Login and refresh | Password guessing exhausts resources | Login limit of 10 per minute per address, enforced in the Auth Server itself (the threat model places it at the Gateway), plus lockout per username and address | A-BF, P-04, R-03 |
| Login and refresh | Different errors for unknown user and wrong password reveal accounts | One identical 401 body; after the fix the same bcrypt work for every attempt | A-BF, P-02, R-02 |
| Login and refresh | Long-lived stolen token | Access token 15 minutes; refresh token single-use and rotated | F-05, F-17 |
| Order reads | Another user's order requested by identifier | Owner compared with the token subject for each object; list narrowed for non-admins | F-09, F-10 |
| Order reads | Altered response on the wire | TLS to the client; mutual TLS and signature inside | F-19, F-03 |
| Order writes | Read-only token tries to write | Scope checked at both layers | F-08, F-14 |
| Order writes | Captured create request resent | Signature, 60-second window and single-use nonce | A-RP |
| Admin endpoints | Ordinary user reads security telemetry | Admin scope required on the whole route group | F-13 |
| Admin endpoints | Audit feed leaks personal data without redaction | No redaction layer exists; events carry the token subject and request path only | Source review, D-07 |

## 4.4 Test Methodology and Environment

### 4.4.1 Approach

Testing was organised in five stages that move from small to large and from friendly to hostile ({fig:testflow}). Each stage produced a log or screenshot that is kept as evidence.

@figure testflow | diagrams/fig-testing-workflow.png | 16 | The five test stages used to validate the platform

1. **Unit tests** exercise the signing and nonce logic in isolation. They use no network and no database.
2. **Live functional flows** run through the real stack with curl: logins, ordering, permission failures, direct calls to the internal service, validation and a database inspection.
3. **The attacker toolkit** runs its five scripts against the Gateway.
4. **Independent probes** check the claims that the toolkit's own output cannot settle: which TLS versions each service accepts, whether login timing differs, whether the rate limit sits where it is documented, and whether lockout can hurt a legitimate user.
5. **Browser checks** drive the real dashboard with an automated browser and examine what is rendered.

### 4.4.2 Identifiers used in this chapter

U denotes the 17 Resource Service unit tests of the first round; R-01 to R-06 the re-test after the fixes (R-01 unit tests, R-02 login timing, R-03 lockout, R-04 Grafana panels, R-05 attacker toolkit, R-06 repeat of the 19 flows); F-01 to F-19 the live flows; A-RP, A-TF, A-BF, A-IN and A-TL the replay, forgery, brute-force, injection and TLS-downgrade scripts; P-01 to P-06 the independent probes (P-01 TLS versions, P-02 login timing, P-03 rate-limit burst, P-04 lockout, P-05 browser rendering of hostile text, P-06 Grafana and Loki); V-01 and V-02 the deployment observations on Vault and on container settings; and S-01 to S-08 the screenshots.

### 4.4.3 Conditions and safeguards

All tests ran on one machine against services bound to the local host. Users, orders and credentials were invented for the demonstration. No traffic was sent to any external system. The test deployment was built from a copy of the repository, so certificates, keys and database passwords were generated for the run and discarded afterwards, and the author's own working copy and Docker data were left untouched. Passwords typed in the browser were entered into password fields and do not appear in the screenshots used in this report, which are cropped so that the login page's own demonstration-credential note is not shown.

### 4.4.4 What the tests cannot show

A passing test shows that one attack in one form failed. It does not show that no other attack exists. The injection checks, for example, probe three input paths with a fixed list of payloads. Timing measurements use four samples per user, which is enough to show a twelve-fold difference but not to describe its distribution. The continuous-integration workflow, the Gateway and Auth Server beyond their behaviour under attack, and the Vault configuration of a production system were not tested.
