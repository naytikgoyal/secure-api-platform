# HMAC request signing verification. See docs/signing-scheme.md for the exact
# canonical string format -- gateway/src/sign.js implements the signing side
# using the IDENTICAL format. If the two ever drift, every request fails
# closed (signature mismatch), not open -- that's the safe failure direction.
from __future__ import annotations

import hashlib
import hmac as hmac_lib
import time


class SignatureError(Exception):
    """Raised for any signature/timestamp/nonce verification failure.
    Deliberately a single exception type with a generic message -- see
    docs/signing-scheme.md 'Why errors are generic' for the reasoning."""

    def __init__(self, reason: str):
        self.reason = reason  # logged server-side only, never returned to the client
        super().__init__(reason)


def build_canonical_string(method: str, path: str, body: str, timestamp: str, nonce: str) -> str:
    """MUST exactly match gateway/src/sign.js's canonical string construction."""
    return f"{method.upper()}\n{path}\n{body}\n{timestamp}\n{nonce}"


def compute_signature(secret: str, canonical_string: str) -> str:
    return hmac_lib.new(secret.encode("utf-8"), canonical_string.encode("utf-8"), hashlib.sha256).hexdigest()


def verify_signature(
    secret: str,
    method: str,
    path: str,
    body: str,
    timestamp: str,
    nonce: str,
    provided_signature: str,
    timestamp_window_seconds: int = 60,
) -> None:
    """Raises SignatureError on any failure. Returns None (success) otherwise.

    Checks, in order:
    1. Timestamp is a valid number and within the allowed window (catches both
       stale replays AND clock-skew nonsense).
    2. Signature matches, using a constant-time comparison (hmac.compare_digest)
       to avoid leaking timing information about how close a guess was.

    Nonce uniqueness is checked SEPARATELY by the caller via NonceStore, after
    this function confirms the signature is genuine -- no point burning a
    nonce-store write on a request that was forged anyway.
    """
    try:
        ts = float(timestamp)
    except (TypeError, ValueError):
        raise SignatureError("malformed_timestamp")

    now = time.time()
    if abs(now - ts) > timestamp_window_seconds:
        raise SignatureError("timestamp_outside_window")

    canonical = build_canonical_string(method, path, body, timestamp, nonce)
    expected_signature = compute_signature(secret, canonical)

    if not hmac_lib.compare_digest(expected_signature, provided_signature or ""):
        raise SignatureError("signature_mismatch")
