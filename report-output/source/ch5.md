@chapter 5 | CONCLUSION AND FUTURE WORK

## 5.1 Conclusion

This project set out to build an API platform in which no single failed check exposes protected data, and to find out by running real attacks which of its controls hold. Both parts were completed.

The platform was built as ten cooperating containers: an API Gateway and an Auth Server written in Node.js, a Resource Service written in Python, PostgreSQL, Redis, Vault, a React dashboard and a Loki, Promtail and Grafana logging pipeline. Four independent layers protect each request. The Gateway verifies an RS256 token, its scope and a per-user rate limit. The link to the Resource Service is protected by mutual TLS and an HMAC-SHA256 signature with a timestamp and single-use nonce. The Resource Service verifies the token and scope again and applies an ownership rule. The data layer uses parameterised queries under a least-privilege database role. Signing keys and database credentials are read from Vault.

The platform was then tested in five stages. All 17 Resource Service unit tests passed, all 19 live request flows behaved as designed, and the attacker toolkit passed all 28 of its checks once its own prerequisites were met. A TLS probe with a positive control confirmed that the servers, and not the attacking client, refuse TLS 1.0 and 1.1. A browser test confirmed that SQL strings and script tags stored in orders are shown as plain text. The ten objectives set in Chapter 2 were met, three of them with stated qualifications ({tab:objres}).

The more valuable result may be the list of things that testing showed to be wrong or overstated. Login timing revealed which usernames exist. Account lockout could be turned against a legitimate user. Two of three Grafana panels were broken. The shipped attacker runner could not reproduce its documented result. Several sentences in the project's own documents described more than the code does. These sixteen findings in {tab:defects} are the practical outcome of treating the platform as something to be attacked and not merely described. Five of them (D-01 to D-05) were then fixed and tested again the same day (Section 4.7.1): login time no longer depends on whether the username exists, a lockout now applies only to the source that failed, all three Grafana panels show data, and the toolkit reproduces its 28 of 28 result with a single Vault token and reports unavailable checks honestly. The other eleven findings remain open. All of this agrees with what the literature warns about: controls are mature, and the failures are in how they are applied [@rfc8725; @owaspapi2023].

## 5.2 Deviation from Expected Results

Four results differed from what was expected before testing began.

**The stock attacker run did not pass.** The documents said 22 of 22 checks passed. The runner as shipped reported two failing scripts. The causes were a key file that the secrets script deliberately removes, and an interaction between the brute-force script and the later lockout feature. The reduction in apparent success came from the test harness drifting away from the system as features were added, not from a weakness in the system. The documented count was also out of date: after the database was added the injection script grew from 12 to 18 checks, so the full suite is 28.

**Identical messages did not give identical behaviour.** The design assumed that returning the same message for a wrong password and an unknown user was enough to prevent enumeration. The timing measurement showed otherwise. The explanation is that the message was treated as the whole of the response, whereas a response also has a duration.

**A protective control became a risk.** Lockout was added to defeat guessing spread across many addresses. It does that, but it also lets an outsider lock a named user. This is the trade-off that the OWASP guidance describes [@owaspauth], and it was not appreciated until the control was tested against a legitimate user.

**The monitoring view was only partly working.** The Grafana dashboard had never been viewed with live data, and two of its three queries were wrong. This is a reminder that a configuration file that looks correct is not evidence that a dashboard works.

Each of these four deviations was traced to its cause and fixed (Section 4.7.1). The lockout fix involves a trade-off: it protects the account owner at some cost in protection against guessing from many addresses, as Section 4.7.1 explains.

## 5.3 Limitations

- **Scope of the deployment.** Everything ran on one host with Vault in development mode, a fixed root token, an unauthenticated Redis and plain connections to Vault and Redis inside the network.
- **Scope of the tests.** The attacks are a fixed list. They do not replace independent penetration testing or a code review by someone other than the author.
- **Lockout trade-off.** After the fix, an attacker with many source addresses gets five guesses per address. The login rate limit and bcrypt slow this and a warning is logged, but it is not blocked.
- **State kept in memory.** Lockout counters, refresh tokens and the audit buffer disappear on restart and cannot be shared by two instances of a service.
- **Authentication model.** The password-style login is a deliberate simplification. Current OAuth security guidance advises against that grant for production use [@rfc9700], and no multi-factor authentication is offered.
- **Not measured.** Performance overhead of the extra layers, behaviour under sustained load, and the continuous-integration pipeline were not measured.

## 5.4 Future Work

The four items that headed the first version of this list (the timing leak, the lockout, the Grafana queries and the attacker runner) were completed and are described in Section 4.7.1. {tab:future} lists what remains, ordered by how directly each item reduces risk. Effort is a rough estimate: S is a few hours, M a day or two, L a week or more.

@table future | Recommended future work | 0.5,3.4,3.2,0.6
| No. | Work | Why | Effort |
| --- | --- | --- | --- |
| 1 | Publish only the ports clients need; use a separate internal network | Makes the "single entry point" statement true (D-08) | S |
| 2 | Run containers as non-root; build the dashboard as static files | Limits damage from a compromised container (D-10) | M |
| 3 | State a minimum TLS version and a cipher list in every service | Makes transport security independent of library defaults (D-11) | S |
| 4 | Add tests for the Gateway and extend those for the Auth Server; run the toolkit in CI | Protects against regressions (D-14) | M |
| 5 | Move lockout, refresh tokens and audit events into Redis or PostgreSQL | Survives restart and supports scaling (D-13) | M |
| 6 | Vault AppRole, auto-unseal and short-lived service certificates | Removes the fixed root token and long-lived TLS keys (D-12) | L |
| 7 | Multi-factor option, access-token revocation, refresh-token families, OpenID Connect | Moves from a demonstration login to production-grade identity | L |
| 8 | Log redaction, tamper-evident logs, a circuit breaker to the Resource Service | Implements what the threat model lists but the code does not (D-07) | M |
| 9 | Alert on the "possible distributed guessing" warning and offer a recovery route for locked accounts | Turns the detection added with the lockout fix into a response | M |
| 10 | Make the dependency audit blocking in CI | Stops known-vulnerable packages from being merged quietly | S |

## 5.5 Closing Remarks

The platform shows that the well-known controls can be combined in a small, free and reproducible system, and that a purpose-built attacker is a practical way to keep the claims honest. The way ahead is to fix the findings that remain open in Section 4.7, to turn the manual verification used in this report into automated regression tests, and to replace the development-mode parts with their production equivalents.
