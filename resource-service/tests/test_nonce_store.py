# Unit tests for nonce replay protection (resource-service/nonce_store.py).
# Uses InMemoryNonceStore -- no live Redis required to run these.
import time

from nonce_store import InMemoryNonceStore


class TestInMemoryNonceStore:
    def test_first_use_of_nonce_succeeds(self):
        store = InMemoryNonceStore()
        assert store.check_and_reserve("nonce-1", ttl_seconds=300) is True

    def test_replayed_nonce_is_rejected(self):
        store = InMemoryNonceStore()
        assert store.check_and_reserve("nonce-2", ttl_seconds=300) is True
        # Second use of the SAME nonce -- this is exactly what a captured/replayed
        # request looks like, even if the signature itself is perfectly valid.
        assert store.check_and_reserve("nonce-2", ttl_seconds=300) is False

    def test_replay_rejected_even_immediately(self):
        """Acceptance criteria from the PRD: 'A captured valid request replayed
        even 1 second later is rejected due to nonce reuse.' No grace period."""
        store = InMemoryNonceStore()
        store.check_and_reserve("nonce-3", ttl_seconds=300)
        assert store.check_and_reserve("nonce-3", ttl_seconds=300) is False

    def test_different_nonces_are_independent(self):
        store = InMemoryNonceStore()
        assert store.check_and_reserve("nonce-a", ttl_seconds=300) is True
        assert store.check_and_reserve("nonce-b", ttl_seconds=300) is True

    def test_expired_nonce_can_be_reused(self):
        """After the TTL window passes, the nonce is evicted -- this bounds
        memory growth. TTL should exceed the signature timestamp window (60s)
        so a nonce can never expire from the store before its signature would
        have expired anyway."""
        store = InMemoryNonceStore()
        store.check_and_reserve("nonce-expiring", ttl_seconds=1)
        time.sleep(1.1)
        # Now allowed again -- this is expected and safe, because a timestamp
        # this old would ALREADY be rejected by verify_signature()'s window
        # check before the nonce store is ever consulted (see main.py ordering).
        assert store.check_and_reserve("nonce-expiring", ttl_seconds=1) is True
