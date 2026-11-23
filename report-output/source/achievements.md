@uh ACHIEVEMENTS

No publications, patents, certifications or competition entries are claimed for this project. The achievements of the work itself, all of which can be inspected in the repository and in the evidence that accompanies this report, are the following.

- A working platform of ten containers in which every request passes four independent layers of checks: token verification at the Gateway, mutual TLS with a signed, time-limited, single-use request, repeated token and ownership checks in the Resource Service, and parameterised queries under a least-privilege database role.
- Signing keys and database credentials read from HashiCorp Vault, with a working key-rotation script and runbook.
- A purpose-built attacker toolkit of five scripts and 28 checks, a suite of 26 unit tests (17 for the Resource Service and 9 added for the Auth Server) and 19 live request flows, all passing after the fixes.
- An independent TLS probe with a positive control, a timing measurement, a rate-limit burst and a lockout check that go beyond what the toolkit reports.
- Sixteen documented findings, including weaknesses in the author's own system and statements in its documents that overstated what the code does, each with a recommendation. Five of them were fixed in the repository and re-tested, with the change recorded as a patch.
- A set of original diagrams, a threat register, a step-by-step user manual and a verified reference list of 37 sources.
