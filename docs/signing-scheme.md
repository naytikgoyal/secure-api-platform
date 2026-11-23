# HMAC Request Signing Scheme

This document is the single source of truth for how Gateway → Resource Service
requests are signed and verified. `gateway/src/sign.js` (signing side) and
`resource-service/signing.py` (verification side) both implement this exact
scheme independently, in two different languages — if they ever drift, every
request fails **closed** (rejected), never open.

## Why this exists

TLS/mTLS proves *who* is talking to *whom* and encrypts the channel. It does
**not** prove that a specific request wasn't captured and replayed later by
someone who can also complete a valid mTLS handshake (e.g. anyone who steals
a certificate from a compromised container, or a network path that terminates
and re-establishes mTLS). HMAC signing + nonce protection is a second,
independent layer that binds the signature to the *exact contents and moment*
of one specific request.

## The canonical string

Every signed request builds this exact string before hashing:

```
{METHOD}\n{PATH}\n{BODY}\n{TIMESTAMP}\n{NONCE}
```

| Field | Details |
| :--- | :--- |
| `METHOD` | Uppercase HTTP method, e.g. `GET`, `POST`, `DELETE` |
| `PATH` | The full request target **including the query string** if present, e.g. `/orders?owner_id=user-1`. Using only the path (dropping query params) is a real bug we hit and fixed during Week 4 build/test — see the note below. |
| `BODY` | The exact raw request body as a string. Empty string `""` for GET/DELETE with no body. Must be byte-for-byte what's actually sent — not a re-serialized version, since JSON key ordering/whitespace differences would break verification. |
| `TIMESTAMP` | Unix seconds (not milliseconds), as a string, at signing time. |
| `NONCE` | 128-bit random value, hex-encoded (32 hex characters). Generated fresh for every single request — never reused by the signer. |

Fields are joined with `\n` (newline), not concatenated directly — this
prevents ambiguity attacks where, e.g., `path="/a"` + `body="b"` could
otherwise collide with `path="/ab"` + `body=""`.

## Signing (Gateway side — `gateway/src/sign.js`)

```js
const canonical = `${method}\n${path}\n${bodyString}\n${timestamp}\n${nonce}`;
const signature = crypto.createHmac("sha256", secret).update(canonical).digest("hex");
```

The signature, timestamp, and nonce are sent as headers:
- `X-Signature` — hex-encoded HMAC-SHA256 output
- `X-Timestamp` — Unix seconds
- `X-Nonce` — the random nonce used

## Verification (Resource Service side — `resource-service/signing.py`)

Verification happens in `main.py`'s `verify_request_signature` middleware,
which runs **before** any route's JWT/scope check — a request with an invalid
signature never reaches auth logic at all. Order of checks:

1. **Timestamp window** — reject if `abs(now - timestamp) > 60 seconds`. Checked *before* recomputing the signature, since there's no reason to do the (marginally more expensive) HMAC computation for something already outside the freshness window.
2. **Signature match** — recompute the expected HMAC over the same canonical string and compare using `hmac.compare_digest` (constant-time — a naive `==` comparison leaks timing information about how many leading bytes matched, which is a real side-channel attackers can exploit).
3. **Nonce uniqueness** — *only after* the signature is confirmed genuine, check the nonce against the Redis-backed `NonceStore`. If it's been seen before, reject as a replay. If not, atomically reserve it (`SET NX EX`) so a race of two requests with the same nonce can't both slip through.

## Why the query-string bug is worth understanding

During Week 4 build/test, `GET /orders?owner_id=user-1` initially failed
signature verification even with correct code on both sides. The cause:
the Gateway signs the **full request target as sent on the wire**
(`/orders?owner_id=user-1`), but FastAPI/Starlette's `request.url.path`
**excludes the query string** by design. The fix reconstructs the full
target on the verification side:

```python
path_for_signing = request.url.path
if request.url.query:
    path_for_signing += f"?{request.url.query}"
```

This is a real, common class of HMAC-signing bug — the signer and verifier
must agree on *exactly* which bytes were signed, and web frameworks often
give you a "cleaned up" or "parsed" version of the request by default that
silently doesn't match. Any time signature verification is failing on
requests that "should" be identical, this mismatch is the first thing to check.

## Why the nonce TTL (5 min) exceeds the timestamp window (60s)

The timestamp window alone already rejects anything older than 60 seconds, so
in principle a nonce only needs to be remembered for 60 seconds too. The nonce
TTL is set longer (5 minutes) as defense in depth against clock skew between
services — if the Resource Service's clock is briefly off, a slightly-outside-
window-by-the-timestamp-check request might still arrive; keeping nonces
around longer than strictly necessary costs a small amount of Redis memory but
closes that edge case.

## Why error messages are generic

Both signature and timestamp failures return the identical
`{"error": "unauthorized", "message": "Invalid request signature."}` response.
The *specific* reason (`signature_mismatch` vs `timestamp_outside_window` vs
`malformed_timestamp`) is logged server-side only. Returning the specific
reason to the client would let an attacker distinguish "your signature was
wrong" from "your timestamp was stale," which helps them iterate toward a
forged request faster — the same information-disclosure reasoning as the
identical login error message from Week 3.
