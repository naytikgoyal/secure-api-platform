@chapter 1 | INTRODUCTION

## 1.1 Identification of Client and Need

Almost every modern web or mobile product talks to its back end through an application programming interface (API). A browser dashboard, a mobile app and a partner's server all send the same kind of request: a signed-in person asks a service to read or change something that belongs to them. Because the API is the place where identity, permissions and data meet, it is also the place an attacker studies first.

The client for this project is a development team that has to publish an orders-style API to browsers and external callers and needs to know that it is secure by design, not secure by luck. Typical examples are the engineering group of a small software company, a student team building a service for a department, or a security trainer who wants a working system on which attacks can be demonstrated and measured. No outside sponsor or industry partner is involved; the project was carried out as an academic exercise in applying security engineering to a realistic multi-service system.

The need is easy to state and hard to meet. The team wants an API platform in which a stolen token, a captured request, a mistake in one service or a hostile string typed into a form does not lead to a data breach. It also wants evidence: attacks that are really run against the system, results that are really recorded, and an honest list of what is still weak. Writing a README that says "secure" does not meet this need; running an attacker against the platform and publishing the outcome does.

## 1.2 Relevant Contemporary Issues

**APIs are the main attack surface.** The OWASP API Security project ranks the most serious API risks in a public list that was last revised in 2023. Its first entry is broken object level authorization, where a caller changes an identifier in a request and receives another user's data, and the second is broken authentication [@owaspapi2023]. A systematic review of microservice security research found the same pattern from the research side: authentication and authorization were the mechanisms discussed most often in the 70 academic and grey-literature works that were finally selected [@pereira2021]. A second mapping study that began with 1,067 candidate studies selected 47 and reported that attention was concentrated on external attacks and on authentication and authorization, with less work on internal attacks [@hannousse2021].

**Microservices multiply the number of trust decisions.** A microservice architecture builds one application from small, independently deployable services that talk to each other over lightweight protocols, often HTTP [@lewis2014; @dragoni2017]. Each extra network hop is a place where a request can be intercepted, replayed or forged, and each service must decide whether to trust the caller. The NIST guidance on microservices security discusses strategies for exactly this setting [@chandramouli2019], and a companion publication looks at how a service mesh can carry some of the controls [@chandramouli2020].

**The network perimeter is no longer enough.** Traditional designs treat everything inside a firewall as trusted. Google's BeyondCorp paper describes moving away from that model because a breached perimeter gives an attacker easy access to the internal network [@ward2014]. NIST Special Publication 800-207 defines zero trust and describes an architecture for it, and the United States National Security Agency published a short information sheet recommending that critical networks consider the model [@nist207; @nsa2021]. The design in this report follows the same thinking at a small scale: the Resource Service does not assume that a request is safe merely because it arrived from the Gateway.

**Token-based authentication is easy to get subtly wrong.** The OAuth 2.0 framework and the JSON Web Token (JWT) format are used almost everywhere [@rfc6749; @rfc7519], but implementations repeatedly go wrong in the same ways. The IETF therefore published best-current-practice documents for JWT use and for OAuth 2.0 security [@rfc8725; @rfc9700]. Pinning the allowed signature algorithm and validating the issuer and audience are practices recommended in the JWT document [@rfc8725], and both appear in this project.

**Secrets leak, and rules are tightening.** Keys committed to a repository, database passwords placed in environment files and long-lived tokens in logs are routine causes of breaches. Regulation is also moving: India's Digital Personal Data Protection Act, 2023, which Parliament passed in August 2023, requires organisations that decide how personal data is processed to build reasonable security safeguards against data breaches [@prs2023]. A system that handles personal data must be able to show what those safeguards are.

## 1.3 Problem Identification

A common weakness in student and small-team systems is that security rests on one check at the edge. The gateway validates a token and every service behind it believes whatever the gateway says. If that single check has a bug, is bypassed, or the internal network is reached some other way, the whole system is exposed. Other weaknesses sit next to it: shared secrets stored in plain files, queries assembled by string concatenation, login endpoints without throttling, and test suites that never attempt a real attack.

Seven concrete problems were identified at the start of the project and are listed in {tab:problems}. They were taken from the OWASP API list, from the replay, forgery and downgrade attacks that the IETF and NIST documents warn about, and from the author's own threat model for the platform.

@table problems | Problems the project set out to solve | 1,3,5
| No. | Problem | Typical consequence |
| --- | --- | --- |
| P1 | Stolen, forged or replayed credentials and requests | An attacker acts as another user, or repeats a valid request many times |
| P2 | Weak authorisation: missing scope checks and object-level access flaws | A read-only user writes data, or one user reads another user's orders |
| P3 | Unprotected traffic between internal services | Requests can be read, altered or injected on the internal hop |
| P4 | Secrets kept in files, environment variables or source control | One leaked file gives an attacker the signing key or database password |
| P5 | Injection through user-supplied text | A crafted string changes a query or runs in a browser |
| P6 | Abuse of login and API endpoints | Password guessing and request flooding |
| P7 | No visibility into what the system allowed or denied | Attacks go unnoticed and cannot be investigated |

## 1.4 Identification of Tasks

To address these problems the project was divided into the tasks below. Each task produced something that can be inspected in the repository or run on a laptop.

1. Build a threat model with assets, actors, trust boundaries and a STRIDE analysis [@shostack2014].
2. Design an architecture in which every request is checked in more than one place.
3. Implement an Auth Server that issues short-lived RS256 access tokens and rotating refresh tokens.
4. Implement an API Gateway that validates tokens, checks scopes, limits request rates and forwards work to the internal service.
5. Implement a Resource Service that repeats the token and scope checks, enforces ownership of each order and stores data in PostgreSQL.
6. Protect the internal hop with mutual TLS, an HMAC-SHA256 request signature, a timestamp window and single-use nonces.
7. Move signing keys and database credentials into HashiCorp Vault and write a key-rotation procedure.
8. Add rate limiting, account lockout, security headers and a least-privilege database role.
9. Add structured logging, a React security dashboard and a Grafana view of the logs.
10. Write an attacker toolkit that tries replay, token forgery, brute force, injection and TLS downgrade against the running system.
11. Run the whole system, measure what happens, record every defect found, fix the code-level ones, test again and report all of it honestly.

## 1.5 Timeline

The author built the platform between September and mid-October 2026, and used the weeks after that for verification and for writing this report. The project's own build log records the work as seven weekly increments followed by two shorter sprints. {fig:gantt} places these phases on a calendar, and {tab:phases} lists what each phase produced. The calendar positions are approximate: they follow the order of the build log and the build period given by the author, not exact commit dates.

@figure gantt | diagrams/fig-gantt.png | 16 | Project phases between September and November 2026 (approximate boundaries)

@table phases | Project phases and main outputs | 1.1,1.6,4.6
| Phase | Period | Main outputs |
| --- | --- | --- |
| P1 Threat model and scaffolding | 1-6 Sep | STRIDE threat model, trust boundaries, repository layout, health endpoints |
| P2 Core APIs and TLS | 6-12 Sep | Orders API, Pydantic validation, local certificate authority, HTTPS only |
| P3 Authentication and authorisation | 12-19 Sep | Auth Server, RS256 tokens, scope checks, independent verification, ownership checks |
| P4 mTLS, HMAC and replay protection | 19-25 Sep | Client certificates, canonical request signing, nonce store, unit tests |
| P5 Vault, rate limits and CI | 25 Sep-1 Oct | Vault secrets, key rotation script, Redis rate limiting, CI workflow |
| P6 Attacker toolkit | 1-5 Oct | Five attack scripts and a combined runner |
| P7 Logging, monitoring, dashboard | 5-10 Oct | JSON logs, admin endpoints, live feed, Loki and Grafana |
| P8 Role-based UI, headers, lockout | 10-13 Oct | Customer view, security headers, account lockout, attack history panel |
| P9 PostgreSQL and SQL-injection proof | 13-16 Oct | Real database, parameterised queries, least-privilege role |
| P10 Verification and report | 16 Oct onward | Live test campaign, independent probes, fixes to five findings and re-test, screenshots, this report |

## 1.6 Organization of the Report

The report follows the chapter structure prescribed by the university format.

**Chapter 1** introduces the client, the need, the problems and the tasks, and gives the project timeline.

**Chapter 2** surveys the literature and standards that frame the problem, using only sources that were checked against their official pages. It ends with the problem definition and the goals and objectives.

**Chapter 3** describes the design process: requirements, selection of features, design constraints, three alternative designs, the reasons for choosing the layered zero-trust design, and the plan for implementing it.

**Chapter 4** presents the implementation and the evidence: the tools used, the threat register, the results of unit tests, live request flows, the attacker toolkit, independent probes and browser checks, and the defects that the testing uncovered.

**Chapter 5** concludes the report, discusses where results differed from what was expected, and proposes future work.

The report ends with the references, an appendix containing a step-by-step user manual, an API and test reference and key code excerpts, and a short statement of achievements.
