# Unit tests for the pure signing/verification logic (resource-service/signing.py).
#
# These test the CRYPTOGRAPHIC logic in isolation -- no HTTP, no TLS, no mTLS.
# mTLS enforcement can't be meaningfully unit tested this way (it's a transport-
# layer property of the TLS handshake, not application code) -- that's proven
# separately via the live curl tests in README.md and the attacker toolkit (Week 6).
#
# Run: cd resource-service && pytest tests/ -v
import time

import pytest

from signing import SignatureError, build_canonical_string, compute_signature, verify_signature

SECRET = "test-secret-do-not-use-in-real-deployment"


def _sign(method, path, body, timestamp, nonce, secret=SECRET):
    return compute_signature(secret, build_canonical_string(method, path, body, timestamp, nonce))


class TestValidSignature:
    def test_valid_signature_passes(self):
        ts = str(int(time.time()))
        sig = _sign("GET", "/orders", "", ts, "nonce-abc123")
        # Should not raise
        verify_signature(SECRET, "GET", "/orders", "", ts, "nonce-abc123", sig)

    def test_valid_signature_with_body_passes(self):
        ts = str(int(time.time()))
        body = '{"item":"Widget","quantity":2,"owner_id":"user-1"}'
        sig = _sign("POST", "/orders", body, ts, "nonce-xyz789")
        verify_signature(SECRET, "POST", "/orders", body, ts, "nonce-xyz789", sig)

    def test_valid_signature_with_query_string_passes(self):
        ts = str(int(time.time()))
        sig = _sign("GET", "/orders?owner_id=user-1", "", ts, "nonce-q1")
        verify_signature(SECRET, "GET", "/orders?owner_id=user-1", "", ts, "nonce-q1", sig)


class TestTamperedBody:
    def test_tampered_body_is_rejected(self):
        ts = str(int(time.time()))
        signed_body = '{"item":"Widget","quantity":1}'
        tampered_body = '{"item":"Widget","quantity":9999}'  # changed after signing
        sig = _sign("POST", "/orders", signed_body, ts, "nonce-tamper1")

        with pytest.raises(SignatureError) as exc_info:
            verify_signature(SECRET, "POST", "/orders", tampered_body, ts, "nonce-tamper1", sig)
        assert exc_info.value.reason == "signature_mismatch"

    def test_tampered_path_is_rejected(self):
        """Signature is over the FULL request target -- changing the path after
        signing (e.g. an attacker redirecting the same signed body to a
        different endpoint) must also fail."""
        ts = str(int(time.time()))
        sig = _sign("DELETE", "/orders/order-1", "", ts, "nonce-path1")

        with pytest.raises(SignatureError):
            verify_signature(SECRET, "DELETE", "/orders/order-2", "", ts, "nonce-path1", sig)

    def test_tampered_method_is_rejected(self):
        ts = str(int(time.time()))
        sig = _sign("GET", "/orders/order-1", "", ts, "nonce-method1")

        with pytest.raises(SignatureError):
            verify_signature(SECRET, "DELETE", "/orders/order-1", "", ts, "nonce-method1", sig)

    def test_wrong_secret_is_rejected(self):
        """Simulates an attacker who doesn't hold the real HMAC key guessing a
        plausible-looking signature."""
        ts = str(int(time.time()))
        sig = _sign("GET", "/orders", "", ts, "nonce-wrongkey", secret="attacker-guessed-secret")

        with pytest.raises(SignatureError) as exc_info:
            verify_signature(SECRET, "GET", "/orders", "", ts, "nonce-wrongkey", sig)
        assert exc_info.value.reason == "signature_mismatch"


class TestExpiredTimestamp:
    def test_timestamp_within_window_passes(self):
        ts = str(int(time.time()) - 30)  # 30s old, window is 60s
        sig = _sign("GET", "/orders", "", ts, "nonce-fresh1")
        verify_signature(SECRET, "GET", "/orders", "", ts, "nonce-fresh1", sig)

    def test_timestamp_outside_window_is_rejected(self):
        ts = str(int(time.time()) - 91)  # 91s old, window is 60s
        sig = _sign("GET", "/orders", "", ts, "nonce-stale1")

        with pytest.raises(SignatureError) as exc_info:
            verify_signature(SECRET, "GET", "/orders", "", ts, "nonce-stale1", sig)
        assert exc_info.value.reason == "timestamp_outside_window"

    def test_future_timestamp_is_rejected(self):
        """A timestamp too far in the FUTURE is just as suspicious as one too
        far in the past -- catches clock manipulation, not just replay."""
        ts = str(int(time.time()) + 91)
        sig = _sign("GET", "/orders", "", ts, "nonce-future1")

        with pytest.raises(SignatureError) as exc_info:
            verify_signature(SECRET, "GET", "/orders", "", ts, "nonce-future1", sig)
        assert exc_info.value.reason == "timestamp_outside_window"

    def test_malformed_timestamp_is_rejected(self):
        sig = _sign("GET", "/orders", "", "not-a-number", "nonce-bad-ts")

        with pytest.raises(SignatureError) as exc_info:
            verify_signature(SECRET, "GET", "/orders", "", "not-a-number", "nonce-bad-ts", sig)
        assert exc_info.value.reason == "malformed_timestamp"


class TestNonceReplay:
    """Nonce UNIQUENESS is enforced by NonceStore, not verify_signature() --
    see test_nonce_store.py for those tests. This class just confirms
    verify_signature() doesn't care about nonce reuse by itself (that's a
    separate, deliberate layer)."""

    def test_same_nonce_reused_still_passes_signature_check(self):
        """This is intentional: verify_signature() only checks the signature is
        genuine. Replay detection is a SEPARATE check (NonceStore) that runs
        after signature verification succeeds -- see main.py's middleware."""
        ts = str(int(time.time()))
        sig = _sign("GET", "/orders", "", ts, "reused-nonce")
        verify_signature(SECRET, "GET", "/orders", "", ts, "reused-nonce", sig)
        # Calling again with the identical, still-valid signature -- still
        # passes at THIS layer. The nonce store is what blocks the replay.
        verify_signature(SECRET, "GET", "/orders", "", ts, "reused-nonce", sig)
