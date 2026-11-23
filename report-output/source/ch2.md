@chapter 2 | LITERATURE SURVEY

## 2.1 Timeline of the Reported Problem

The problems that this project deals with were not discovered in one year. Each one was noticed, named and answered separately over about three decades, and the answers were gradually collected into the checklists and standards that practitioners use today. {fig:timeline} shows the sources that mark the main steps; every event in it is a document listed in the references of this report.

@figure timeline | diagrams/fig-standards-timeline.png | 16 | Timeline of the sources that shaped the controls used in this project

**Foundations (1990s to 2000s).** Syverson classified replay attacks on cryptographic protocols by the origin and destination of the replayed message, which gave later designers a vocabulary for the problem that nonces and timestamps solve [@syverson1994]. Bellare, Canetti and Krawczyk proposed message-authentication constructions built from ordinary hash functions, including HMAC, and showed that they inherit the strength of the underlying hash [@bellare1996]; the IETF published HMAC as RFC 2104 the following year [@rfc2104]. Provos and Mazières argued that a password scheme must become more expensive to attack as hardware improves, and introduced bcrypt with an adjustable cost for that reason [@provos1999]. Brumley and Boneh showed that timing differences can be measured over a network precisely enough to attack a real web server [@brumley2003], which turned timing from a laboratory curiosity into a practical concern. In 2006 Halfond, Viegas and Orso classified SQL injection attacks by route and by attacker intent and reviewed the defences available at that time [@halfond2006], and NIST published its guide to log management [@kent2006].

**The web-API era (2012 to 2017).** The OAuth 2.0 framework and its bearer-token usage rules were published in 2012 [@rfc6749; @rfc6750]. Two years later Google described BeyondCorp, a model in which access depends on the user and device rather than on position inside a network [@ward2014], and Lewis and Fowler gave the widely used definition of a microservice architecture [@lewis2014]. The JSON Web Token format followed in 2015 [@rfc7519], and a survey by Dragoni and colleagues summarised the history, open problems and challenges of microservices [@dragoni2017].

**Transport and zero trust (2018 to 2021).** TLS 1.3 became RFC 8446 in 2018 [@rfc8446]. NIST published its security strategies for microservices in 2019 and a service-mesh companion in 2020 [@chandramouli2019; @chandramouli2020]; in the same year it released the zero trust architecture publication [@nist207], and the IETF issued its JWT best-current-practice document [@rfc8725]. In 2021 TLS 1.0 and 1.1 were formally deprecated [@rfc8996], the NSA issued its zero trust information sheet [@nsa2021], and two systematic reviews of microservice security appeared [@pereira2021; @hannousse2021].

**Codification (2023 to 2026).** The OWASP API Security Top 10 was revised in 2023 [@owaspapi2023]. In 2025 the IETF published its OAuth 2.0 security best current practice [@rfc9700], OWASP released version 5.0.0 of the Application Security Verification Standard on 30 May [@asvs], and NIST published revision 4 of its digital identity guidance on authentication [@nist63b]. In 2026 the TLS 1.3 specification was reissued as RFC 9846, which obsoletes both RFC 8446 and the TLS 1.2 specification, RFC 5246 [@rfc9846].

Reading the timeline from left to right, the same pattern repeats: a weakness is demonstrated, a control is proposed, the control is standardised, and later documents warn about common mistakes in applying it. The platform in this report applies the controls from every period and then tests them against the mistakes the later documents warn about.

## 2.2 Proposed Solutions in the Literature

This section groups the surveyed sources by the seven problems identified in Chapter 1. For each group it states what the literature proposes, and what this project took from it.

### 2.2.1 Identity and token security (problem P1)

OAuth 2.0 lets a service accept a short-lived access token instead of a user's password, and bearer tokens travel in the HTTP Authorization header [@rfc6749; @rfc6750]. A JWT is a compact, signed set of claims such as issuer, subject, audience and expiry [@rfc7519]. The JWT best-current-practice document records the recurring mistakes in using them and recommends, among other things, verifying the algorithm and validating the issuer and audience [@rfc8725]. The OAuth security best current practice updates the advice for OAuth deployments and advises against the resource-owner password-credentials grant [@rfc9700]. This project issues tokens through a password-style login for simplicity; Chapter 3 treats that as a documented simplification, not as a recommendation.

### 2.2.2 Request integrity and replay protection (problem P1)

A bearer token proves who is calling, but it does not prove that a particular request body has not been changed or that the request is not a copy. HMAC gives integrity and authenticity for a message under a shared key [@bellare1996; @rfc2104], and replay attacks are defeated by making each message usable only once, which in practice means a fresh nonce and a limited time window [@syverson1994]. The Gateway-to-Resource-Service signing scheme described in Chapter 3 is built from exactly these ideas.

### 2.2.3 Transport security between services (problem P3)

TLS 1.3 is the current version of the protocol [@rfc9846; @rfc8446], and TLS 1.0 and 1.1 are deprecated [@rfc8996]. NIST gives guidance on selecting and configuring TLS implementations [@mckay2019]. Zero trust architecture adds the principle that traffic must be secured and verified whatever the network location, so internal calls are not exempt [@nist207]. Mutual TLS, in which the server also demands a client certificate, is one way to put that principle into practice, and it is what the Resource Service requires.

### 2.2.4 Authorisation and object-level access (problem P2)

The OWASP API Security Top 10 lists broken object level authorization as its first entry [@owaspapi2023], and the MITRE weakness CWE-639 describes the underlying flaw: a system fails to stop one user reaching another user's data when the attacker can change the key that identifies the data [@cwe639]. The Application Security Verification Standard provides numbered verification requirements against which such controls can be checked [@asvs]. The remedy applied here is the one the descriptions imply: the server decides who owns an object from the verified token, never from a value the client supplies.

### 2.2.5 Secrets and key management (problem P4)

HashiCorp describes Vault as a tool for centrally managing privileged access and sensitive credentials, with database secret plugins and encryption controlled by authentication and authorisation policies [@vault]. NIST's general key-management recommendation covers how keys are generated, protected and replaced over time [@barker2020]. The project moves its JWT keys, HMAC key and database credentials into Vault and writes a rotation procedure; it also records honestly that Vault runs in development mode.

### 2.2.6 Injection (problem P5)

CWE-89 describes SQL injection as a failure to neutralise special characters in input that is used to build a query [@cwe89]. Halfond and colleagues classified the techniques attackers use [@halfond2006], and the OWASP SQL Injection Prevention Cheat Sheet names prepared statements with parameterised queries as the first defence, followed by stored procedures and allow-list input validation, while describing escaping as strongly discouraged [@owaspsqli]. The project follows the first recommendation without exception and uses allow-list style type and size checks as a second layer.

### 2.2.7 Abuse of login endpoints and password handling (problem P6)

The OWASP Authentication Cheat Sheet advises returning the same generic response for valid and invalid usernames, warns that differences in processing time can reveal whether an account exists, recommends throttling failed logins tied to the account rather than only the address, and cautions that lockouts can be abused for denial of service [@owaspauth]. CWE-208 names the timing weakness [@cwe208], and Brumley and Boneh show why such timing differences cannot be dismissed as unmeasurable [@brumley2003]. For stored passwords, adaptive hashing such as bcrypt keeps guessing expensive [@provos1999]. NIST's current guidance on authentication and authenticator management covers the wider topic [@nist63b]. Chapter 4 tests the project against this advice, and some of the findings are unflattering.

### 2.2.8 Logging and monitoring (problem P7)

NIST's log-management guide describes how organisations should generate, store and analyse security logs [@kent2006]. The project emits structured JSON logs with a request identifier from all three services, ships them to Loki, shows them in Grafana, and feeds a live event stream to a dashboard.

### 2.2.9 Threat modelling and verification

Shostack's book describes threat modelling and the STRIDE categories that this project uses to organise its threat register [@shostack2014]. OWASP's verification standard and the NIST and IETF documents above supply the checklist against which the finished system is compared [@asvs]. Architectural background on microservices and their security comes from the NIST publications and the research surveys discussed next [@chandramouli2019; @chandramouli2020; @pereira2021; @hannousse2021].

## 2.3 Bibliometric Analysis

A true bibliometric study queries a citation database such as Scopus or Web of Science, which were not available for this project. The analysis below is therefore a count over the sources that were collected and verified for this report, and it should be read as a description of the evidence base of this report, not of the research field as a whole. Every one of the 37 sources was checked against an official page or a bibliographic record, as listed in the references; a few older papers were confirmed through listings that point to the venue page.

{fig:littype} counts the sources by type. Internet standards (nine IETF documents) and NIST publications (seven) dominate, which reflects the practical nature of the project: most of the controls it uses are defined by standards rather than by papers. Five conference papers supply the older foundations of replay, message authentication, password hashing, timing and injection, and two journal articles give systematic overviews of microservice security.

@figure littype | diagrams/fig-chart-lit-type.png | 13.5 | Surveyed sources by type (37 sources)

{fig:lityear} groups the same sources by publication period. The largest group, nine sources, was published between 2020 and 2023, and four were published in 2025 or 2026. Six sources are undated web pages such as the OWASP cheat sheets and the MITRE weakness entries. The spread shows that the design combines long-established cryptographic ideas with guidance that is only a few years old, and that two of the standards cited (RFC 8446 and the NIST TLS guidance) have already been revised or are under review.

@figure lityear | diagrams/fig-chart-lit-year.png | 14 | Surveyed sources by publication period (37 sources)

{tab:coverage} shows how the sources map to the seven problems of Chapter 1. Each source is counted once, under the problem it is cited for most. The counts show where this report's evidence is thick and where it is thin. Request integrity and token security (eight sources) and authentication hardening (five) are well supported; secrets (two) and visibility (one) rest on fewer documents, which is a limitation of the evidence base to keep in mind when reading the discussion of those areas.

@table coverage | Coverage of the seven problems by the surveyed sources | 3,1.2,3
| Topic | Sources | Which |
| --- | --- | --- |
| P1 Credentials and requests | 8 | RFC 6749, RFC 6750, RFC 7519, RFC 8725, RFC 9700, RFC 2104, Bellare et al. 1996, Syverson 1994 |
| P2 Authorisation | 3 | OWASP API Top 10 2023, CWE-639, OWASP ASVS 5.0.0 |
| P3 Transport | 4 | RFC 8446, RFC 9846, RFC 8996, NIST SP 800-52 Rev. 2 |
| P4 Secrets | 2 | HashiCorp Vault documentation, NIST SP 800-57 Part 1 Rev. 5 |
| P5 Injection | 3 | CWE-89, OWASP SQL Injection Prevention Cheat Sheet, Halfond et al. 2006 |
| P6 Abuse and authentication | 5 | OWASP Authentication Cheat Sheet, Provos and Mazières 1999, Brumley and Boneh 2003, CWE-208, NIST SP 800-63B-4 |
| P7 Visibility | 1 | NIST SP 800-92 |
| Architecture, zero trust, method, law | 11 | Lewis and Fowler, Dragoni et al., NIST SP 800-204 and 800-204A, NIST SP 800-207, NSA 2021, Ward and Beyer, Pereira-Vale et al., Hannousse and Yahiouche, Shostack, PRS India |

## 2.4 Review Summary

Four points follow from the literature and shape the rest of the report.

First, the controls themselves are mature. Signed tokens, HMAC, nonces, TLS, parameterised queries, adaptive password hashing and centralised secrets are all documented in standards or well-cited papers, so the project did not need to invent any new mechanism.

Second, the literature repeatedly stresses mistakes in applying known controls, not the absence of controls. The JWT and OAuth best-current-practice documents exist for that reason [@rfc8725; @rfc9700], and the first two entries of the OWASP API list are about authorisation and authentication errors [@owaspapi2023]. A design should therefore be judged by whether it avoids those mistakes in practice.

Third, the two systematic reviews report that research attention concentrates on authentication, authorisation and external attacks [@pereira2021; @hannousse2021]. Pereira-Vale and colleagues also found that about two-thirds of the proposed solutions aim to mitigate or stop attacks, and none addressed reacting to or recovering from them [@pereira2021]. This project follows the same bias: it has detection and logging, but no automated response.

Fourth, the mapping study found that proposals are most often validated through performance analysis and case studies [@hannousse2021]. Running a purpose-built attacker against the finished system, and reporting the failures along with the passes, is a more demanding form of validation, and it is the approach this project takes.

## 2.5 Problem Definition

The problem addressed by this project is to design, implement and verify an API platform for an orders-style service in which no single failed or bypassed check exposes protected data, and to establish by running real attacks, not by assertion, which of its controls hold and which do not.

The scope is as follows.

- **In scope:** token-based authentication and authorisation; request signing and replay protection between the gateway and an internal service; protection of secrets and of the database; rate limiting, lockout and logging; and an attacker toolkit and test campaign that exercise these controls on a local deployment.
- **Out of scope:** a production identity provider, federation with external identity systems, multi-factor authentication, host or container-runtime hardening, high availability, and penetration testing of any system other than the author's own local deployment.

## 2.6 Goals and Objectives

The overall goal is a working, tested platform together with an honest assessment of its security. It is broken into the objectives in {tab:objectives}, each with a way of checking whether it was reached. Chapter 4 reports the result for every row.

@table objectives | Objectives and acceptance criteria | 0.7,3.2,3.6
| ID | Objective | Acceptance criterion |
| --- | --- | --- |
| O1 | Verify identity independently in two places | A request with a bad token is rejected at the Gateway, and a request sent straight to the Resource Service with no valid signature is rejected there |
| O2 | Enforce scopes and object ownership | A read-only user cannot write; one user cannot read another user's order by identifier |
| O3 | Stop forged and confused tokens | Wrong-key, unsigned and RS256-to-HS256 tokens are all rejected |
| O4 | Stop replay and tampering on the internal hop | A captured signed request replayed immediately is rejected; a request without a client certificate fails at the TLS handshake |
| O5 | Keep secrets out of files and source | JWT private key, HMAC key and database credentials are read from Vault at start-up and the local copies are removed |
| O6 | Neutralise injection | SQL-looking and script-looking input is stored and shown as plain text, and no table is changed |
| O7 | Slow abuse | Repeated failed logins and request floods are limited |
| O8 | Make events visible | Allow and deny decisions appear in structured logs, a live dashboard and Grafana |
| O9 | Validate with an attacker | Five attack scripts run against the live system and their results are recorded |
| O10 | Report weaknesses honestly | Every defect, limitation and overstated claim found during testing is listed with a recommendation |
