## 4.5 Results

Sections 4.5.1 to 4.5.6 report the first round of testing, before any fix. The re-test is in Section 4.7.1.

### 4.5.1 Unit tests (U)

The Resource Service has a pytest suite of 17 tests for the signature and nonce logic ({tab:unit}). All 17 passed in 1.15 seconds, as shown in {fig:pytest}. The tests cover valid signatures with and without a body or query string; tampering with the body, path and method and the use of a wrong secret; timestamps that are fresh, stale, in the future or malformed; and the nonce store. One test records a design choice: the signature function deliberately does not reject a reused nonce, because replay is a separate layer handled by the nonce store after the signature has been proved genuine.

@table unit | Unit tests by group | 2.4,0.6,4.6
| Group | Tests | What is checked |
| --- | --- | --- |
| Valid signature | 3 | Accepts a correct signature for a GET, a POST with a body, and a GET with a query string |
| Tampering | 4 | Rejects a changed body, a changed path, a changed method and a signature made with the wrong secret |
| Timestamp | 4 | Accepts a 30-second-old request; rejects one 91 seconds old, one 91 seconds in the future and a malformed value |
| Nonce and signature layers | 1 | The signature check alone does not reject a reused nonce, because the nonce store does |
| Nonce store | 5 | First use accepted; replay rejected, including immediately; different nonces independent; an expired nonce can be used again |
| **Total** | **17** | **17 passed** |

@figure pytest | screens/T7-pytest.png | 15 | Captured output of the unit-test run: 17 passed

In the first round the suite did not cover the Redis-backed nonce store, the HTTP middleware, the Gateway or the Auth Server. Those parts were exercised only by the live stages that follow, which is a gap in automated regression protection (D-14). Nine tests for the Auth Server's login and lockout logic were added together with the fixes (Section 4.7.1); the Gateway still has none.

### 4.5.2 Live functional flows (F)

Nineteen flows were run against the live stack and are listed in {tab:flows}; excerpts of the captured output are in {fig:flowa}, {fig:flowb}, {fig:flowc} and {fig:flowd}. Every flow behaved as designed.

@table flows | Live functional flows and results | 0.5,2.5,2.6,3.3,0.6
| ID | Objective | Expected | Observed | Result |
| --- | --- | --- | --- | --- |
| F-01 | Health endpoints over TLS, certificate verified against the project CA | 200 from Gateway and Auth Server | Both answered with a status of ok | Pass |
| F-02 | Plaintext HTTP to the HTTPS port | No valid HTTP answer | HTTP status 000 (no HTTP response) | Pass |
| F-03 | Resource Service reached with no client certificate | Handshake refused | No HTTP response; curl reported an empty reply (exit 52). With the Gateway's client certificate the health call returned 200 | Pass |
| F-04 | Log in as the three demonstration users | Tokens with the right scopes | Read and write; read only; read, write and admin; access token valid for 900 seconds | Pass |
| F-05 | Inspect the access token | RS256, expected claims | Header RS256; issuer, audience, subject and scopes as designed; 900-second lifetime | Pass |
| F-06 | Standard user creates an order | 201 with owner from the token | 201; owner is the user's own subject | Pass |
| F-07 | Standard user lists orders | Own orders only | One order returned | Pass |
| F-08 | Read-only user tries to create an order | 403 insufficient scope | 403, message names the missing scope | Pass |
| F-09 | Read-only user reads another user's order by identifier | 403 | 403 from the Resource Service | Pass |
| F-10 | Read-only user asks for another owner's list | 403 | 403 from the Gateway: needs admin scope | Pass |
| F-11 | Administrator reads that order | 200 | 200 with the order | Pass |
| F-12 | No token, garbage token, tampered token | 401 each | 401, 401, 401 | Pass |
| F-13 | Standard user and administrator call the admin API | 403 and 200 | 403 and 200 | Pass |
| F-14 | Valid client certificate but no signature, straight to the Resource Service | 401 | 401, "Missing request signature" | Pass |
| F-15 | Store a SQL-injection string and inspect the database | Stored verbatim; table intact | String stored as text; psql shows both rows; list still works | Pass |
| F-16 | Oversized quantity, wrong type, missing field | 4xx | 422, 422, 422 | Pass |
| F-17 | Use a refresh token twice | First works, second fails | New pair issued; reuse returned 401 | Pass |
| F-18 | Security response headers | Present | HSTS, nosniff, frame, content-security, referrer and cross-origin headers present | Pass |
| F-19 | Negotiated TLS | Verified chain, modern TLS | TLS 1.3, TLS_AES_256_GCM_SHA384, verification OK | Pass |

@figure flowa | screens/T1-functional-a.png | 15 | Captured output, flows F-01 to F-05: health, plaintext, mTLS and login

@figure flowb | screens/T2-functional-b.png | 15 | Captured output, flows F-06 to F-13: orders, scope and ownership checks, admin API

@figure flowc | screens/T3-functional-c.png | 15 | Captured output, flows F-14 to F-16: signature check, injection data and validation

@figure flowd | screens/T3b-functional-d.png | 15 | Captured output, flows F-17 to F-19: refresh rotation, response headers and TLS

Three details deserve comment. In F-09 the 403 body has a different shape ({"detail": ...}) from the Gateway's ({"error", "message"}) because it comes from FastAPI's default error response; this is harmless but inconsistent. In F-18 the Gateway sent the frame header with the value SAMEORIGIN, while a comment in its source says DENY, because that is the default of the helmet library version in use. And F-03 shows why mutual TLS needs a test of its own: the refusal happens in the handshake, before any HTTP code runs, so an application-level test could never see it.

### 4.5.3 Attacker toolkit (A)

The toolkit was run twice: once exactly as shipped, and once with its prerequisites supplied and its scripts run in a safe order. Both results matter.

**The stock runner.** Running `run_all.py` as shipped reported three scripts passing and two failing ({fig:stock}). Neither failure was a successful attack. The replay script needs the HMAC key as a local file, and that file no longer exists after the secrets script has moved it into Vault and deleted it. The script's message mentions an override variable that the code does not read. The injection script cannot log in because the brute-force script, which runs just before it, has by then triggered the 15-minute account lockout on the same user; the toolkit's login helper retries on rate-limit responses (429) but not on lockout responses (423). The forgery script also quietly skipped its algorithm-confusion test because the public-key file was missing, and still reported its two remaining checks as a pass. The dashboard's attack-history panel therefore displayed two red results ({fig:s04}).

@figure stock | screens/T4-stock-runner.png | 15 | Captured output of the stock runner showing two scripts that could not complete

**The corrected run.** The HMAC key and the public key were read from the development Vault and placed in the test copy, which is exactly the scenario the replay script describes, namely an attacker who has obtained the key. The Auth Server was restarted to clear the in-memory lockout, and the brute-force script was run last. Under those conditions all 28 checks passed ({tab:attacks} and {fig:results}).

@table attacks | Attacker-toolkit checks and outcomes (corrected run) | 0.7,2.2,4.4,1.4
| Script | Checks | Outcome observed | Result |
| --- | --- | --- | --- |
| A-RP replay | 2 | Original signed request accepted (200); identical request sent again rejected (401, "replay detected") | 2 of 2 |
| A-TF token forgery | 3 | Token signed with the attacker's own key, an unsigned `alg: none` token, and an HS256 token built with the public key as the secret: all rejected with 401 | 3 of 3 |
| A-BF brute force | 2 | Wrong password and unknown user gave identical status and body; the rate limiter first answered 429 at attempt 9 of 13 | 2 of 2 |
| A-IN injection and malformed input | 18 | See {tab:injection} | 18 of 18 |
| A-TL downgrade | 3 | Plaintext request to the HTTPS port refused; TLS 1.0 and TLS 1.1 handshakes failed (but see P-01 below) | 3 of 3 |
| **Total** | **28** | | **28 of 28** |

@figure results | diagrams/fig-chart-results.png | 14 | Checks executed against the running system, by stage

The injection script is the largest. {tab:injection} lists its 18 checks. Structural violations such as wrong types, oversized strings, negative numbers and malformed JSON must be rejected. Strings that merely look dangerous, such as SQL fragments, script tags, path traversal and format strings, are correctly accepted and stored unchanged, because nothing in the system interprets them as code; the script verifies that they come back byte for byte. Three payloads placed in the order identifier in the URL and one in the administrator's owner filter reach the database layer and match nothing, and a final check confirms that the row count did not change.

@table injection | The 18 injection and malformed-input checks | 0.5,4.2,2.4,0.9
| No. | Input | Expected behaviour | Observed |
| --- | --- | --- | --- |
| 1 | NoSQL-style operator `$gt` sent as the item | Rejected | 422 |
| 2 | NoSQL-style operator `$ne` sent as the item | Rejected | 422 |
| 3 | 10,000-character item | Rejected | 422 |
| 4 | Classic SQL injection string as item | Stored as inert text | 201, verbatim |
| 5 | SQL UNION string as item | Stored as inert text | 201, verbatim |
| 6 | Script-tag string as item | Stored as inert text | 201, verbatim |
| 7 | Image-tag with onerror as item | Stored as inert text | 201, verbatim |
| 8 | Path-traversal-looking string as item | Stored as inert text | 201, verbatim |
| 9 | Format-string characters as item | Stored as inert text | 201, verbatim |
| 10 | Null byte inside the item | Rejected | 422 |
| 11 | Negative quantity | Rejected | 422 |
| 12 | Malformed JSON body | Clean error, not a 500 | 400 |
| 13 | SQL tautology as order identifier in the URL | 404, reaches the database layer | 404 |
| 14 | DROP TABLE string as order identifier | 404 | 404 |
| 15 | DELETE FROM string as order identifier | 404 | 404 |
| 16 | Delete request with an injected identifier | Nothing deleted | 404 |
| 17 | SQL tautology as the administrator's owner filter | Zero rows (control query returned 8) | 0 rows |
| 18 | Row count before and after all attacks | Unchanged | 8 before, 8 after |

### 4.5.4 Independent probes (P)

**P-01: which TLS versions are accepted.** The toolkit reported that TLS 1.0 and 1.1 handshakes were refused, but its error text, "[SSL] internal error", could equally have come from the attacker's own Python library declining to speak an old protocol. To settle this, a probe was run from inside the Gateway container with a positive control: a deliberately permissive test server that accepted TLS 1.0 to 1.3 handshakes from the same client. The control succeeded at every version, which proves that the client can speak the old protocols. The real services then refused TLS 1.0 and 1.1 and accepted 1.2 and 1.3 ({tab:tls} and {fig:tlsprobe}). The refusal is therefore a property of the servers, and it comes from library defaults and not from any setting in the project: Node 20 sets a minimum of TLS 1.2, and Python's server context reports a minimum of 771, the code for TLS 1.2. In line with the IETF deprecation of TLS 1.0 and 1.1 [@rfc8996], this is the desired behaviour, but a stated minimum version and cipher list would make it explicit and independent of the runtime. One further observation: when the probing client offered every cipher suite, the Resource Service chose a CBC mode suite with SHA-1 (ECDHE-RSA-AES256-SHA) for TLS 1.2, whereas the Gateway and Auth Server chose AES-GCM. NIST guidance on selecting and configuring TLS implementations covers the choice of cipher suites [@mckay2019].

@table tls | TLS versions accepted by each service | 3.1,0.9,0.9,0.9,0.9
| Target | TLS 1.0 | TLS 1.1 | TLS 1.2 | TLS 1.3 |
| --- | --- | --- | --- | --- |
| Control: permissive test server | Handshake ok | Handshake ok | Handshake ok | Handshake ok |
| Gateway (port 3000) | Refused (protocol-version alert) | Refused (protocol-version alert) | Handshake ok | Handshake ok |
| Resource Service (port 8000, client certificate presented) | Refused (connection reset) | Refused (connection reset) | Handshake ok | Handshake ok |
| Auth Server (port 4000) | Not tested | Refused (protocol-version alert) | Handshake ok | Not tested |

@figure tlsprobe | screens/T5-tls-probe.png | 15 | Captured output of the TLS version probe, including the control server

**P-02: login timing.** The project's documents rely on identical error messages to prevent username enumeration, and the toolkit confirms that the status code and body are identical. The OWASP Authentication Cheat Sheet, however, warns that differences in processing time can reveal whether an account exists [@owaspauth], and CWE-208 describes the weakness [@cwe208]. Four wrong-password logins were timed for an existing user and four for names that do not exist, alternating between them to share conditions. Existing-user requests took 131.5 ms on average and unknown-user requests 10.7 ms ({fig:timing}). The cause is visible in the code: when the user is not found, the password comparison, which is deliberately slow with bcrypt, is skipped. An attacker who can time responses can therefore list valid usernames even though the messages match. Brumley and Boneh showed that network timing differences of this kind are measurable in practice [@brumley2003]. Four samples per user are too few to describe a distribution, but a twelve-fold difference with no overlap between the two groups is enough to show the effect.

@figure timing | diagrams/fig-chart-timing.png | 13.5 | Login latency for existing and unknown usernames

**P-03: rate limit.** One user sent 130 authenticated list requests inside a minute. Exactly 100 returned 200 and 30 returned 429, which matches the configured limit of 100 per minute ({fig:ratelimit}). The Loki query for rate-limit events then counted the same 30 events, which links the observed behaviour to the log pipeline.

@figure ratelimit | diagrams/fig-chart-ratelimit.png | 14 | Outcome of a 130-request burst against a limit of 100 per minute

**P-04: account lockout.** After the brute-force script, a login as the targeted user with the correct password returned HTTP 423 and a message to try again in 14 minutes ({fig:lockout}). The control therefore works as designed and also exposes its cost: anyone who knows a username can lock that person out by sending five wrong passwords, and the per-address rate limit does not prevent it. The OWASP guidance on authentication names this trade-off and suggests that other recovery routes remain available for a locked account [@owaspauth]. The lock lived in the Auth Server's memory, so restarting the container removed it, which is itself a limitation.

@figure lockout | screens/T6-timing-lockout.png | 15 | Captured output of the timing measurement and of the lockout check

### 4.5.5 Browser checks (S and P-05)

An automated browser drove the real dashboard. {fig:s01} shows the sign-in page after a failed attempt with an unknown username. The message is the same one shown for a wrong password.

@figure s01 | screens/S02-login-failed-generic-error.png | 10 | S-02: sign-in page after a failed login, with the credential note cropped out

{fig:s04} shows the administrator's Security Operations Dashboard after the three attack-simulation buttons were clicked in the browser. The live feed shows allowed requests, the denies-only list shows rejected tokens, and the attack-history panel shows the two failed scripts from the stock run described in Section 4.5.3. The "metrics" row shows 32 requests per minute, a 6% deny rate and 75 events tracked at the moment of capture.

@figure s04 | screens/S04-admin-dashboard-after-attacks.png | 15.5 | S-04: administrator view after three real attack simulations

A read-only user sees a different page ({fig:s05}), and the text explains that the restriction comes from the token's scopes and not from the page.

@figure s05 | screens/S05-readonly-user-orders-view.png | 14 | S-05: orders view for the read-only user

The most important browser check concerns stored text. A standard user created four orders through the form whose item names were an ordinary product, a script tag with an alert call, an image tag with an onerror handler, and a SQL string with a DROP TABLE statement. {fig:s07} shows that all four appear as plain text. The browser raised no JavaScript dialog at any point, and a count of script and image elements inside the orders list found none, so the stored text was not interpreted as markup (P-05).

@figure s07 | screens/S07-orders-with-hostile-strings-rendered-as-text.png | 15 | S-07: hostile strings shown as plain text in the orders list

### 4.5.6 Observability checks (P-06)

Grafana loaded the provisioned dashboard but only one of its three panels worked as provisioned ({fig:s08}). The rate-limit panel showed the burst of 30 denied requests. The request-volume panel displayed an error, and the deny-reasons panel displayed no data. Querying Loki directly with each panel's expression explained both cases ({fig:loki}). The request-volume query applies a JSON parser to every line from the Resource Service, but that service also prints plain-text server lines, which makes Loki reject the whole query. The deny-reasons query filters on a `level` label that Loki does not index, so nothing matches. Adding an error filter to the first and moving the level filter after the JSON parser in the second made both return data when tested directly. These queries are defects in the shipped configuration and were not changed during this work. A smaller point is that the two logging libraries use different words for the same level, `warn` and `warning`.

@figure s08 | screens/S08-grafana-security-overview.png | 15 | S-08: Grafana Security Overview after the rate-limit burst; one panel works, one errors, one is empty

@figure loki | screens/T8-loki.png | 15 | Captured output of the Loki queries behind the three panels

## 4.6 Objectives Against Results

{tab:objres} returns to the objectives set in Chapter 2, with the status after the fixes of Section 4.7.1. Seven were met in the first round; two more (O7 and O8) and the validation objective (O9) were met after fixes, and one (O5) is met with a qualification that is stated in the table.

@table objres | Objectives and outcomes | 0.5,2.3,0.9,4
| ID | Objective | Status | Basis |
| --- | --- | --- | --- |
| O1 | Verify identity independently in two places | Met | F-12 (Gateway rejects bad tokens); F-14 (Resource Service rejects an unsigned call by itself) |
| O2 | Enforce scopes and object ownership | Met | F-08, F-09, F-10, F-13 |
| O3 | Stop forged and confused tokens | Met | A-TF 3 of 3; algorithm pinned in both services |
| O4 | Stop replay and tampering on the internal hop | Met | A-RP 2 of 2; U (signature, timestamp and nonce tests); F-03 |
| O5 | Keep secrets out of files and source | Met with a qualification | Keys and credentials were read from Vault; but Vault ran in development mode with a fixed token, and TLS keys and bootstrap passwords remain in files |
| O6 | Neutralise injection | Met | F-15; A-IN 18 of 18; P-05 |
| O7 | Slow abuse | Met after fixes | Rate limit confirmed (P-03). In the first round lockout could be abused against a known user (P-04) and login timing leaked (P-02); both were fixed and re-tested (R-02, R-03) |
| O8 | Make events visible | Met after fixes | JSON logs and the live dashboard verified; two of three Grafana panels were defective in the first round and now return data (R-04) |
| O9 | Validate with an attacker | Met after fix | 28 of 28 in the corrected run; after the runner fixes it reproduces 28 of 28 with only a Vault token and reports unavailable checks as SKIP (R-05) |
| O10 | Report weaknesses honestly | Met | Section 4.7 |

## 4.7 Defects, Weaknesses and Overstated Claims

{tab:defects} gathers everything that testing found. Severity is the author's judgement for a platform that handled real users; for a classroom demonstration most items would rank lower. The last two columns give the recommended remedy and its status: the five code and configuration findings D-01 to D-05 were fixed and re-tested (Section 4.7.1); the others remain open.

@table defects | Findings and recommendations | 0.5,2.3,0.7,2.2,2.3,0.9
| ID | Finding | Severity | Evidence | Recommendation | Status |
| --- | --- | --- | --- | --- | --- |
| D-01 | Login latency reveals whether a username exists (about 12 times slower for real users) | Medium | P-02 | Run a dummy bcrypt comparison when the user is not found | Fixed (R-02) |
| D-02 | Lockout lets anyone with a username lock that user for 15 minutes | Medium | P-04 | Add progressive delays, tie limits to account and address together, and offer a recovery route | Fixed (R-03) |
| D-03 | Grafana request-volume panel fails on non-JSON log lines | Low | P-06 | Filter parser errors, or make the service log JSON only | Fixed (R-04) |
| D-04 | Grafana deny-reasons panel filters on a label that is not indexed | Low | P-06 | Move the level filter after the JSON parser | Fixed (R-04) |
| D-05 | Stock attacker runner fails for missing key files and the lockout, reports a skipped test as a pass, accepts any 401 as proof that a replay was rejected, and the documented 22 of 22 is not reproducible | Low | Section 4.5.3 | Read keys from Vault, report SKIP separately, run brute force last, handle HTTP 423 | Fixed (R-05) |
| D-06 | The sign-in page prints the demonstration usernames and passwords | Low (demo) | S-01, S-02 | Remove from any non-demo build | Open |
| D-07 | Threat-model text lists log redaction, tamper-evident logs, circuit breakers and OpenID Connect; none is implemented | Documentation | Source search | Correct the document or implement the controls | Open |
| D-08 | Architecture text says Vault injects TLS certificates and that attackers reach the system only through the Gateway; certificates are local files and the Compose file publishes eight host ports, including Redis, Vault and the Resource Service | Medium | V-01, F-03 | Publish only the Gateway, Auth Server and dashboard; segment the network | Open |
| D-09 | README says ownership checks happen at both services; per-object checks happen only in the Resource Service (the Gateway checks the owner filter on lists) | Low | Source review | Correct the wording or add the check | Open |
| D-10 | Containers run as root, the dashboard container serves a development server, and Promtail reads the Docker socket | Medium | V-02 | Add non-root users, build a static dashboard, restrict log collection | Open |
| D-11 | The Resource Service accepted a CBC and SHA-1 cipher suite for TLS 1.2 | Low | P-01 | State a minimum version and a cipher list explicitly | Open |
| D-12 | Vault in development mode with a fixed root token; Redis without a password; internal traffic to Vault and Redis is plain | High for production, accepted for demo | V-01 | AppRole or similar, auto-unseal, TLS and passwords for Redis | Open |
| D-13 | Lockout, refresh tokens and the audit buffer live in memory: lost on restart and not shared between instances | Medium when scaled | Source review, P-04 | Move to Redis or the database | Open |
| D-14 | Only the Resource Service signing and nonce code has automated tests; the Gateway and Auth Server are checked for syntax only | Medium | Section 4.5.1 | Add unit and integration tests; run the attacker toolkit in CI | Open |
| D-15 | The "insufficient scope" simulation button sends a tampered token and receives 401, not a scope failure (403) | Info | Source review | Rename the button or add a real scope test | Open |
| D-16 | Gateway comment states the frame header is DENY; the library sends SAMEORIGIN. Error body shape differs between services | Info | F-18, F-09 | Align comment and error format | Open |

### 4.7.1 Fixes applied and re-test

After the first round, the five findings that were errors in code or configuration (D-01 to D-05) were fixed in the author's repository on the same day. The files to be changed were copied to a backup folder first, and the complete change is recorded as a patch that accompanies this report. {tab:fixes} states what was changed. Because the Auth Server had no automated tests (D-14), nine unit tests were written with the fixes, so the unit tests now total 26.

@table fixes | Changes made to fix the five findings | 0.5,4.7,2.4
| ID | Change | Files |
| --- | --- | --- |
| D-01 | Every login now performs exactly one bcrypt comparison. When the username does not exist, the submitted password is compared with a hash of a random value, so the slow step is no longer skipped. Both login fields must be strings | auth-server/src/users.js, index.js |
| D-02 | The lockout is keyed by username and source address. Five failures from one address lock that address out of that account, so an outsider can no longer lock out the real owner. Failures older than 15 minutes are forgotten. Failures against one account from many addresses are counted together and a warning is logged when they pass thirty | auth-server/src/accountLockout.js, index.js |
| D-03 | The request-volume query skips log lines that are not JSON | infra/grafana-dashboard.json |
| D-04 | The deny-reasons query applies the level filter after the JSON parser | infra/grafana-dashboard.json |
| D-05 | The runner runs the brute-force script last. The replay and forgery scripts take the keys from the environment, the certs folder or Vault when a read token is given. A check that cannot run is reported as SKIP with exit code 2, never as a pass. A login blocked by lockout or rate limit ends a script with SKIP. The replay check now requires a 401 that names a replay. The dashboard shows SKIP | attacker-toolkit/*.py, dashboard/src/components/AttackHistory.jsx |

The system was rebuilt from the changed files in a fresh test deployment and tested again ({tab:retest}). The re-test identifiers R-01 to R-06 are used in the rest of the report.

@table retest | Before and after for each fixed finding | 0.5,2.6,3.2,0.8
| ID | Before the fix | After the fix | Evidence |
| --- | --- | --- | --- |
| D-01 | Real user 131.5 ms, unknown user 10.7 ms (about 12 times slower) | Medians 56.5 ms and 56.0 ms over 8 samples each (1.01 times); the ranges overlap | R-02 |
| D-02 | Five wrong passwords sent by an attacker made the real user's correct login fail (HTTP 423) | Attacker's own address locked after five failures (423); real user from another address logs in (200); one source stays locked out of the account it attacked; other accounts unaffected | R-03 |
| D-03 | Request-volume panel showed an error | Panel query returns 3 series (info, warn, warning) and 595 events | R-04 |
| D-04 | Deny-reasons panel showed no data | Panel query returns 5 series and 171 events | R-04 |
| D-05 | Stock run: 3 pass, 2 fail; documented 22 of 22 not reproducible | Run A without keys: 3 pass, 2 SKIP, exit code 2. Run B with only a Vault token: 5 of 5 scripts pass, 28 of 28 checks, exit code 0 | R-05 |

**R-01 and R-06: unit tests and regression check.** The nine new Auth Server tests passed inside the real container image, using the real bcrypt library ({fig:nodetests}), and the 17 Resource Service tests passed again. The 19 live flows were repeated. The result lines of the repeated run were compared with the first run, and all 48 comparable lines were identical, so the changes to the login path did not break any earlier behaviour.

@figure nodetests | screens/T10-node-tests.png | 15 | Captured output of the new Auth Server tests: 9 passed

**R-02: login timing.** The measurement was repeated in the same way, with wrong-password logins that alternated between a real user and invented names. Each name received four attempts, below the lockout threshold, and two rounds were run with different real users. The medians were 56.5 ms for real users and 56.0 ms for unknown names, a ratio of 1.01 where it had been 12.3 ({fig:timingfix}, {fig:timingretest}). The means differ more (66.2 ms and 56.2 ms) because two real-user requests took 95 ms. Both were the first request of a round, after a minute without traffic. A control round that sent an unknown name first confirmed the explanation: that first request was the slow one (67.6 ms against about 55 ms). The result shows that the large, systematic difference is gone. It does not prove that no timing channel exists, and eight samples per group is a small sample.

@figure timingfix | diagrams/fig-chart-timing-fix.png | 14 | Login time for existing and unknown usernames, before and after the fix

@figure timingretest | screens/T13-timing-retest.png | 15 | Captured output of the timing re-test, including the control round

**R-03: lockout.** The test needed two different source addresses, which a single laptop does not provide, so the attacker was a second container on the same Docker network ({fig:lockretest}). It sent six wrong passwords for one user and was locked out on the sixth request (423). The real user, logging in from the host machine with the correct password, received 200, where the first round had produced 423. The lock still works against a single source: five wrong passwords from the host for a second user followed by the correct password gave 423, while a different account from the same host was unaffected. Unit tests also check that failures spread over many addresses are counted per account and flagged once.

@figure lockretest | screens/T11-lockout-retest.png | 15 | Captured output of the lockout re-test with an attacker on a different address

The fix has a cost that should be stated plainly. An attacker with many source addresses now gets five guesses per address, not five in total. Three things limit this: the login limit of ten requests a minute per address, the cost of each bcrypt comparison, and the warning that is logged when failures against one account pass thirty. The warning is detection, not prevention. Users who share one public address, for example behind a company network gateway, can also still be locked out by someone who shares that address. The OWASP guidance describes this tension between protecting the account and protecting its owner [@owaspauth], and no setting removes it entirely.

**R-04: Grafana.** The three queries were read from the corrected dashboard file and run against Loki after a burst of traffic, and all three returned data. The panels were then viewed in Grafana ({fig:grafanafix}). The request-volume panel shows separate series for `info`, `warn` and `warning`, because the two logging libraries still use different words for the same level.

@figure grafanafix | screens/S08-grafana-after-fix.png | 15 | Grafana Security Overview after the fix: all three panels show data

**R-05: attacker toolkit.** The runner was run twice, with no manual steps. In run A there were no key files and no Vault token. Replay and the algorithm-confusion check were reported as SKIP, the other checks passed, the combined result said that no attack succeeded but some checks could not run, and the exit code was 2. In run B only a Vault read token was supplied. The scripts fetched the keys themselves, all five scripts passed, 28 of 28 checks were blocked and the exit code was 0 ({fig:toolkitretest}). The dashboard shows both outcomes ({fig:historyfix}).

@figure toolkitretest | screens/T12-toolkit-retest.png | 15 | Excerpts of the two re-run toolkit logs: without keys (run A) and with a Vault token (run B)

@figure historyfix | screens/S04bc-attack-history-after-fix.png | 12 | Attack History panel after run A (above, with SKIP) and run B (below, all pass)

**A mistake made while fixing.** The first re-run of the toolkit failed. While the injection script's first login was being replaced by the new helper, an import that the same script still needed for its administrator step was removed, and the script stopped with a name error. The re-test caught it, the import was restored, and a static check for undefined names was then run over every file that had been edited. Nothing else was found.

**What was not changed.** Findings D-06 to D-16 remain open. The results in Sections 4.5 and 4.6 describe the system as first tested, and this section describes what was changed afterwards.

## 4.8 Discussion

### 4.8.1 What the results establish

The results support the central design claim. Every layer behaved independently: the Gateway rejected bad tokens, the Resource Service rejected an unsigned call even with a valid client certificate, a captured request could not be replayed, forged tokens of three kinds failed, ownership and scope rules held, and hostile text stayed text. The attacker toolkit passed 28 of 28 checks once its own prerequisites were met, and after the fixes it does so without manual steps.

The results also show that the claims of the project's documents need to be read with care. Several statements in its documents were broader than the behaviour found: a "single entry point" that is not enforced at the network level, log redaction and circuit breakers that are not present, a Vault that "injects" TLS certificates, and a toolkit result that cannot be reproduced as shipped. None of these is a failure of a control. Each is a gap between a sentence and the system, and the testing was what exposed it.

### 4.8.2 Deviation from expected results

The expected result was a clean pass of every attack and a working monitoring dashboard. What happened differed in four ways: the stock toolkit run showed two failures that were not attacks; login timing leaked information that the identical messages were meant to hide; lockout worked but harmed the legitimate user; and two of three Grafana panels were broken. All four were fixed and re-tested (Section 4.7.1). Chapter 5 returns to them.

### 4.8.3 Threats to validity

- **Coverage.** The attacks are a fixed list. A different payload, or an attack on a part not exercised, might succeed.
- **Environment.** Everything ran on one machine with Vault in development mode. A networked or production deployment would have different timing, and different failure modes.
- **Sample size.** Timing used four samples per group. The direction and size of the difference are clear, but no statistical test was run.
- **Self-assessment.** The author built the system and designed the tests, so independent review would add confidence. The probes in Section 4.5.4 were added specifically to check conclusions that the toolkit's own output could not settle.
- **Re-test.** The fixes were tested by the author, on the same machine, on the day they were made. Timing used eight samples per group, and the lockout test used a second container as the attacker's address. A different network would give different timings.
- **Judgement.** The comparison scores in Chapter 3 and the severity ratings in {tab:defects} are judgements, not measurements.

## 4.9 Project Management and Communication

The work was organised as short increments, each ending with a runnable result, as shown in the timeline in Chapter 1. A threat model was written first, and every later increment named the threat it addressed. Decisions, bugs and verification steps were written into a dated build log as they happened. Six bugs found during the build were recorded with their causes: a limiter created before Redis was ready, a query string left out of the signed text, a path that was decoded before signing, a middleware that ran in the wrong order, a log path that was relative to a router mount, and a database-role comment that claimed more than the role did. After the first test campaign, five findings were fixed and tested again the same day; the changed files were backed up first and the change is kept as a patch.

Communication artefacts were produced alongside the code: a README with a quick start, a threat model, an architecture diagram, a signing-scheme document, a key-rotation runbook, an attack report, a SQL-injection demonstration, a Postman collection for the API and a script for a short demonstration video. This report adds the verification campaign described in this chapter, with its evidence. The supervisor's guidance during the work is acknowledged at the front of the report.
