@appendix 2 | API AND TEST REFERENCE: SECURE API WEB APPLICATION

## A2.1 Endpoints

{tab:endpoints} lists the endpoints. All are served over HTTPS. Scope names are those carried in the access token. The Resource Service offers the same order routes as the Gateway but is reachable only with a client certificate and a valid request signature.

@table endpoints | HTTP endpoints of the platform | 0.9,2.6,1.4,4.1
| Method | Path | Service and scope | Behaviour |
| --- | --- | --- | --- |
| POST | /auth/login | Auth Server, none | Checks username and password; returns access token, refresh token, expiry and scopes; 10 per minute per address |
| POST | /auth/refresh | Auth Server, none | Exchanges a refresh token for a new pair; the old refresh token stops working |
| GET | /health | Gateway, Auth Server, none | Returns a status line and a time stamp |
| POST | /orders | Gateway, orders:write | Creates an order; the owner is taken from the token, not the body |
| GET | /orders | Gateway, orders:read | Lists the caller's orders; another owner may be requested only with the admin scope |
| GET | /orders/{id} | Gateway, orders:read | Returns one order if the caller owns it or is an administrator |
| DELETE | /orders/{id} | Gateway, orders:write | Deletes one order under the same ownership rule |
| GET | /admin/audit-logs | Gateway, admin | Returns recent allow and deny events, newest first, up to 200 |
| GET | /admin/metrics | Gateway, admin | Requests in the last minute, deny rate, rate-limited count, total events tracked |
| GET | /admin/audit-stream | Gateway, admin | Live event stream (Server-Sent Events) |
| POST | /admin/attack-report | Gateway, admin | Stores the latest attacker-toolkit report |
| GET | /admin/attack-report | Gateway, admin | Returns the stored report, or 404 if none |
| POST | /admin/simulate-attack/{type} | Gateway, admin | Types: bad-token, insufficient-scope, rate-limit; makes real self-requests |
| GET, POST, DELETE | /orders ... | Resource Service, same scopes | Same routes as the Gateway; requires mTLS and X-Signature, X-Timestamp and X-Nonce |

## A2.2 Response codes

{tab:codes} explains the status codes and where each one comes from.

@table codes | HTTP status codes used by the platform | 0.6,2.4,5.4
| Code | Meaning here | Typical cause |
| --- | --- | --- |
| 200, 201, 204 | Success | Read or list; order created; order deleted |
| 400 | Invalid request | Missing login fields; malformed JSON body |
| 401 | Unauthorised | Missing, malformed, forged or expired token; missing, invalid or replayed request signature; wrong password |
| 403 | Forbidden | Missing scope; order owned by someone else; owner filter without admin scope |
| 404 | Not found | Unknown or malformed order identifier |
| 422 | Validation failed | Item or quantity outside the allowed type or size; null byte in the item |
| 423 | Locked | Five failed logins for that username from the same address in the last 15 minutes |
| 429 | Too many requests | Login limit of 10 per minute per address, or 100 per minute per user |
| 500 | Internal error | Unexpected failure; generic message returned |
| 502, 503 | Upstream failure; not ready | Resource Service unreachable or returned non-JSON; secrets not yet loaded |

## A2.3 Parameters and limits

{tab:params} collects the security parameters and the place where each is set.

@table params | Security parameters and where they are set | 2.6,1.4,2.6
| Parameter | Value | Where |
| --- | --- | --- |
| Access token lifetime | 15 minutes | Auth Server token issue |
| Refresh token lifetime | 7 days, single use | Auth Server refresh store |
| Signature algorithm for tokens | RS256 only | Gateway, Resource Service, Auth Server |
| Token issuer and audience | Fixed strings checked on every request | Gateway, Resource Service |
| Request body limit | 100 kB (Gateway), 10 kB (Auth Server) | Express body parsers |
| Request rate limit | 100 per minute per user (per address if unauthenticated) | Gateway, Redis |
| Login rate limit | 10 per minute per address | Auth Server, Redis |
| Account lockout | 5 failures, 15 minutes, per username and source address | Auth Server memory |
| Password hashing | bcrypt, cost factor 10 | Auth Server |
| Signature timestamp window | 60 seconds either side | Resource Service |
| Nonce retention | 300 seconds | Resource Service, Redis |
| Item and quantity limits | 1 to 200 characters; 1 to 1000 | Resource Service |
| Audit buffer | 200 events | Gateway memory |

## A2.4 Evidence files

The evidence folder that accompanies this report holds the raw outputs behind Chapter 4 ({tab:evidence}).

@table evidence | Evidence files and what they show | 2.8,5.2
| File | Contents |
| --- | --- |
| functional-flows.log | Output of the 19 live flows |
| attacker-toolkit-run1.log | The stock runner as shipped, with two failing scripts |
| attacker-toolkit-run2-part1.log, part2, part3 | Corrected run: replay and forgery; injection and downgrade; brute force |
| tls-version-check.log | TLS version probe including the control server |
| login-timing.log, lockout-after-bruteforce.log | Timing samples and the lockout response |
| grafana-loki-diagnosis.log | Loki queries behind the three Grafana panels |
| pytest-resource-service.log | The 17 unit tests |
| environment.txt | Container, runtime and package versions; users and published ports |
| screenshots S01 to S08 and browser-run-log.json | Browser screenshots and the record of dialogs and console errors |
| after-fixes/ (node-tests, pytest, functional-flows-retest, login-timing-retest, lockout-retest, grafana-panels-retest, attacker-toolkit-runA and runB) | Raw output of the re-test after the five fixes |
| after-fixes/screenshots | Grafana after the fix and the Attack History panel after runs A and B |
| after-fixes/changes-to-repo.patch | The complete change made to the author's repository, as a unified patch |

## A2.5 Requirements traceability

{tab:trace} links each requirement from Chapter 3 to the tests that exercised it and records the outcome. "Verified" means the test passed. A finding number means the requirement was met but testing revealed a related weakness, which is described in Section 4.7.

@table trace | Requirements traceability matrix | 0.8,3.6,2.7
| Requirement | Tests that exercised it | Outcome |
| --- | --- | --- |
| FR1 Issue tokens | F-04, F-05, F-17, A-BF | Verified |
| FR2 Order operations | F-06, F-07, F-11, A-IN | Verified |
| FR3 Scopes | F-08, F-13 | Verified |
| FR4 Own orders only | F-09, F-10, F-11, A-IN-17 | Verified |
| FR5 Admin feeds | F-13, S-04, P-06, R-04 | Verified; D-03 and D-04 fixed |
| FR6 Browser views | S-01 to S-07, P-05 | Verified |
| SR1 HTTPS, TLS 1.2 or higher | F-02, F-19, A-TL, P-01 | Verified; D-11 |
| SR2 Token verification | F-12, A-TF | Verified |
| SR3 Repeat checks in the internal service | F-14, F-09 | Verified |
| SR4 Mutual TLS | F-03, F-14 | Verified |
| SR5 Signed requests, no replay | U, A-RP, F-14 | Verified |
| SR6 Secrets manager | V-01 (all three secret writes accepted; services started with secrets from Vault) | Verified in development mode; D-12 |
| SR7 Limits and lockout | A-BF, P-03, P-04, R-03 | Verified; D-02 fixed |
| SR8 Parameterised SQL, limited role | F-15, A-IN | Verified |
| SR9 Generic errors | F-12, F-14, A-BF, R-02 | Verified; D-01 (timing) fixed |
| SR10 Structured logs | S-04, P-06 | Verified |
| SR11 Reproducible and attackable | Whole campaign, R-05 | Verified; D-05 fixed |

## A2.6 The attacker scripts

{tab:scripts} summarises what each of the five scripts does and what counts as a pass. Each script exits with code 0 when every check passed, 1 when an attack succeeded, and 2 when nothing failed but a check could not run; a skipped check is never counted as a pass.

@table scripts | What each attack script does | 1.3,3.8,3
| Script | What it does | Counts as a pass when |
| --- | --- | --- |
| attack_replay.py | Logs in, builds a correctly signed request with the HMAC key, and sends it directly to the Resource Service using the Gateway's client certificate; then sends the identical request again. This is a deliberately pessimistic attacker who holds both the key and the certificate | The first request returns 200 and the second returns 401 |
| attack_token_forgery.py | Builds three tokens claiming the admin scope: signed with an attacker's own RSA key, unsigned with `alg: none`, and signed with HS256 using the public key as the secret | Each is rejected with 401 |
| attack_bruteforce.py | Compares the answers for a wrong password and an unknown user, then tries a list of 13 common passwords in quick succession | The two answers are identical and the rate limiter answers 429 before the list ends |
| attack_injection.py | Sends structurally invalid input, hostile-looking strings, injected identifiers in the URL and an injected owner filter; counts rows before and after | Invalid input is refused, hostile text is stored unchanged, no row changes |
| attack_mitm_downgrade.py | Sends plain HTTP to the HTTPS port and tries TLS 1.0 and 1.1 handshakes | Every attempt fails |

## A2.7 Defects found and fixed during development

These defects ({tab:bugs}) come from the project's build log. Each shaped the final design. They were not re-created for this report; Chapter 4 tested the final behaviour.

@table bugs | Development-time defects from the build log | 0.6,2.6,2.6,2.6
| No. | Defect | Cause | Resolution and lesson |
| --- | --- | --- | --- |
| 1 | Verifier rejected requests that had a query string | The signed text left out the query string | Sign the full request target; signer and verifier must agree on exactly which bytes were signed |
| 2 | Gateway failed at start-up when the rate limiter was created | The Redis-backed limiter was built when the module loaded, before the Redis connection was open | Import the router only after Redis is connected |
| 3 | Second attack script could not log in | The first script's flood left the login limiter active | Retry on 429 with back-off, and pause between scripts |
| 4 | Injection payloads were accepted by the API | The first test expected a blocklist; analysis showed that blocklisting would be ineffective and would reject valid data | Keep only a null-byte rule; rely on parameterised queries and output encoding; rewrite the test |
| 5 | Signature failures were logged with an unknown request identifier | Starlette runs middleware in reverse registration order | Register the identifier middleware after the signature middleware |
| 6 | Every audit entry showed the same path | Inside a mounted Express router the path is relative to the mount point | Log the original URL |
| 7 | Percent-encoded identifiers failed signature checks | The framework decoded the path, but the Gateway had signed the encoded form | Rebuild the target from the raw path bytes |
| 8 | A script comment claimed the database role could not reach other databases | By default PostgreSQL lets everyone connect to every database; the claim was false | Revoke the connect right and re-test: verify claims by testing them |
