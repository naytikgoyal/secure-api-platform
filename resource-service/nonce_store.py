# Nonce store: tracks which (nonce) values have already been used, so a
# captured valid request can never be replayed -- see docs/signing-scheme.md.
#
# RedisNonceStore is what actually runs in docker-compose (shared across
# multiple Resource Service instances if you ever scale horizontally --
# an in-memory dict would NOT catch a replay against a different instance).
# InMemoryNonceStore exists purely so unit tests don't need a live Redis.
from __future__ import annotations

import time
from abc import ABC, abstractmethod


class NonceStore(ABC):
    @abstractmethod
    def check_and_reserve(self, nonce: str, ttl_seconds: int) -> bool:
        """Returns True if the nonce was NOT seen before (and reserves it).
        Returns False if it WAS already seen (i.e. this is a replay)."""
        raise NotImplementedError


class RedisNonceStore(NonceStore):
    def __init__(self, host: str, port: int = 6379):
        import redis  # imported lazily so tests never need the package installed as a hard dep

        self._client = redis.Redis(host=host, port=port, decode_responses=True)

    def check_and_reserve(self, nonce: str, ttl_seconds: int) -> bool:
        # SET key value NX EX ttl -- atomic "set if not exists" with expiry.
        # This atomicity matters: two requests racing on the same nonce must not
        # both succeed just because of a check-then-set gap.
        was_set = self._client.set(f"nonce:{nonce}", "1", nx=True, ex=ttl_seconds)
        return bool(was_set)


class InMemoryNonceStore(NonceStore):
    """Test-only. Not safe across multiple processes/instances -- that's the
    exact gap RedisNonceStore exists to close in real deployments."""

    def __init__(self):
        self._seen: dict[str, float] = {}

    def check_and_reserve(self, nonce: str, ttl_seconds: int) -> bool:
        now = time.time()
        # lazy cleanup of expired entries
        expired = [n for n, exp in self._seen.items() if exp < now]
        for n in expired:
            del self._seen[n]

        if nonce in self._seen:
            return False

        self._seen[nonce] = now + ttl_seconds
        return True
