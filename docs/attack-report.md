# Attack Report — Week 6

This report documents the results of running `attacker-toolkit/` against the
full running stack (Gateway, Auth Server, Resource Service, Redis, Vault).
Every result below reflects an actual run, not a prediction — see the
"Evidence" line under each finding for the real HTTP responses observed.

**Final result: 22/22 checks passed across 5 scripts, after 2 real issues
were found and fixed during this week's work.** This report covers both
fixes in full, because the finding-and-fixing process is the actual point of
this exercise — not just the final green run.

## Summary table

| Script | Threat (docs/threat-model.md) | Checks | Result |
| :--- | :--- | :--- | :--- |
| `attack_replay.py` | Spoofing/Replay (5.3) | 2/2 | ✅ Pass |
| `attack_token_forgery.py` | Spoofing (Section 4) | 3/3 | ✅ Pass |
| `attack_bruteforce.py` | DoS / credential guessing (5.1) | 2/2 | ✅ Pass |
| `attack_injection.py` | Input validation (NFR-6) | 12/12 | ✅ Pass |
| `attack_mitm_downgrade.py` | Tampering / TLS (NFR-1) | 3/3 | ✅ Pass |

## Finding 1: Toolkit self-interference via the auth rate limiter

**Not a security vulnerability — an operational finding about the toolkit itself.**

**What happened:** running `attack_bruteforce.py` immediately followed by
`attack_injection.py` (both need to log in as `naytik`) caused the *second*
script's legitimate login to fail with `429`. The brute-force script's own
flood correctly tripped the per-IP rate limiter on `/auth/login` — but that
limiter state persisted in Redis for its full 60-second window, so the next
script's first login attempt landed inside that same window and got blocked
too.

**Evidence (first run, before the fix):**
```
attack_bruteforce.py: ... attempt 7 (password='welcome'): HTTP 429 <-- BLOCKED
...
attack_injection.py: ERROR: could not log in as naytik -- is the stack running?
```

**Why this matters anyway:** a toolkit that can't tell "I'm being blocked
because I'm attacking" from "I'm being blocked because a sibling script just
got blocked two seconds ago" isn't very useful for CI or repeat runs. Real
API clients should also handle `429` gracefully (back off, respect
`Retry-After`), not treat it as fatal.

**Fix:** `toolkit_common.py`'s `login()` now retries on `429` with backoff,
respecting the `Retry-After` header. `run_all.py` also inserts a 15-second
pause after `attack_bruteforce.py` specifically, so the common case doesn't
rely on retry logic alone.

**Evidence (after fix):**
```
attack_injection.py: (login rate-limited, waiting 41s before retry 2/3...)
--- STRUCTURAL violations (must be rejected, 400/422) ---
[... proceeds normally ...]
```

## Finding 2: Injection payloads accepted as `item` values — and why the obvious fix would have been wrong

**This one is worth reading in full — the naive fix here would have made the
codebase worse, not better.**

**What happened:** `attack_injection.py`'s first version sent SQLi-looking,
XSS-looking, path-traversal-looking, and format-string payloads as the
`item` field and expected all of them to be rejected (422). Six of them were
instead accepted (201):

```
SQLi (classic):        HTTP 201  {"item":"'; DROP TABLE orders; --", ...}
SQLi (union):           HTTP 201  {"item":"' UNION SELECT * FROM users --", ...}
XSS (script tag):       HTTP 201  {"item":"<script>alert('xss')</script>", ...}
XSS (img onerror):      HTTP 201  {"item":"<img src=x onerror=alert(1)>", ...}
Null byte injection:    HTTP 201  {"item":"item\u0000.txt", ...}
Path traversal:         HTTP 201  {"item":"../../../../etc/passwd", ...}
Format string:          HTTP 201  {"item":"%s%s%s%s%s%s%s%s", ...}
```

**Investigation before fixing anything:** the question that actually
matters isn't "does this string look dangerous" — it's "does anything in
this system ever *interpret* this string as code." Walking through it:
- SQL injection requires a SQL query built from this string. This service has no
  database — orders live in an in-memory dict. There is no query to inject into.
- XSS requires this string being rendered as HTML somewhere. There is no
  templating engine or frontend rendering this data (yet — see Residual Risk below).
- Path traversal requires this string being used to construct a filesystem
  path. It's never used that way here.
- Format string attacks require this string being passed to a
  format-string function (like C's `printf`). Python's f-strings and
  `.format()` don't have this vulnerability class the way C's `printf` does,
  and nothing here passes user input as a format string anyway.

**Conclusion: blocklisting these patterns at the input layer would have been
security theater.** Blocklisting `<script>` or `DROP TABLE` is a well-known
anti-pattern in real security engineering — it's trivially bypassed (different
casing, encoding, whitespace tricks, or just not matching the specific
blocked substring), and it actively breaks legitimate data (a product
genuinely named `O'Brien's Widget` would be rejected by a naive apostrophe
filter). The correct defenses are **parameterized queries** (the moment a
real database is added) and **output encoding** (the moment a renderer
touches this data — React, which the Week 7 dashboard uses, auto-escapes by
default). Both are architectural decisions to make when those components
are actually added, not input-layer string matching today.

**The one payload that WAS a legitimate finding: null bytes.** Unlike the
others, null bytes have no execution-context dependency — almost no
legitimate text field needs one, and they're a known source of real bugs in
C-string-based libraries, some filesystems, and certain parsers, independent
of whether there's a SQL query or HTML renderer involved. This was worth
fixing narrowly.

**Fix applied:** added one Pydantic field validator to `OrderCreate.item` in
`resource-service/main.py` that rejects embedded null bytes:
```python
@field_validator("item")
@classmethod
def reject_null_bytes(cls, v: str) -> str:
    if "\x00" in v:
        raise ValueError("must not contain null bytes")
    return v
```

**The test itself was also wrong and got rewritten**, not just the code.
`attack_injection.py` now separates **structural violations** (wrong type,
oversized, negative — always rejected) from **content patterns** (SQLi/XSS/
path-traversal/format-string-looking strings — correctly accepted as inert
data, with the response verified to store the value byte-for-byte, proving
it's genuinely inert and not silently mangled). Null bytes get their own
category as the one legitimate content-based rule.

**Evidence (final run):**
```
SQLi (classic):    HTTP 201 -- stored verbatim as expected  [PASS: correctly accepted]
Null byte:         HTTP 422 "must not contain null bytes"    [PASS: correctly rejected]
```

**Residual risk — flagged, not fixed:** if a real database is added later
(PRD Section 12 stretch goals), every query touching user input MUST use
parameterized queries / an ORM, never string concatenation. If the Week 7
dashboard or any future frontend ever renders `item` values outside of
React's default auto-escaping (e.g., via `dangerouslySetInnerHTML`), that
would reintroduce a real XSS vector. Both are noted in
`docs/threat-model.md`'s residual risk section as things to re-verify when
those components land — this report doesn't mark them as closed, because
they aren't; they're currently not-yet-applicable.

## Findings that required no fix (attack correctly blocked on first run)

### Replay protection (`attack_replay.py`)
A request captured with a fully valid HMAC signature and nonce was
replayed immediately after its original use. Original: `200`. Replay:
`401 {"error":"unauthorized","message":"Request already processed (replay detected)."}`.
Nonce-based replay protection (Week 4) worked exactly as designed, including
under the pessimistic assumption that the attacker also holds the Gateway's
mTLS client identity.

### JWT forgery (`attack_token_forgery.py`)
Three forgery techniques, all rejected with `401`:
- **Wrong-key forgery** — signed with an attacker-generated RSA keypair, claiming `admin` scope.
- **`alg: none`** — a historically real JWT library vulnerability class; blocked because the Gateway pins `algorithms: ["RS256"]` in `jwt.verify()`.
- **Algorithm confusion (RS256→HS256)** — used the *known public key* as an HMAC secret; blocked for the same reason (algorithm pinning means an HS256-signed token is never even evaluated against the public key as a symmetric secret).

### Credential brute-forcing (`attack_bruteforce.py`)
- Enumeration check: wrong password and nonexistent username return byte-identical `401` responses.
- 13 rapid login attempts: rate limiter tripped at attempt #8 (limit is 10/min; the 3 successful/failed pre-limit attempts plus the correct password attempt account for the offset), all subsequent attempts `429`.

### TLS/mTLS downgrade (`attack_mitm_downgrade.py`)
- Plaintext HTTP to the HTTPS port: connection-level failure, never parsed as valid HTTP.
- TLS 1.0 and TLS 1.1 handshake attempts: both refused at the SSL layer.

## How to reproduce this report yourself

```bash
cd infra
./scripts/gen-certs.sh
docker compose up -d vault
./scripts/vault-init.sh
docker compose up --build

# in another terminal, once everything is healthy:
cd attacker-toolkit
pip install -r requirements.txt
python3 run_all.py
```
