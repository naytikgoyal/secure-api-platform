// Account lockout: locks a SPECIFIC USERNAME after too many failed attempts,
// regardless of which IP the attempts came from.
//
// This is deliberately a DIFFERENT control from the existing rate limiter
// (auth-server/src/middleware/rateLimiter.js), not a replacement for it:
//
//   - Rate limiting is IP-based: it slows down ANY client hammering
//     /auth/login, protecting the SERVER from being overwhelmed and making
//     brute-forcing slow regardless of which account is being targeted.
//   - Account lockout is USERNAME-based: it protects ONE SPECIFIC ACCOUNT
//     even if an attacker spreads their guesses across many IP addresses
//     (e.g. a botnet), which the IP-based limiter alone would never catch --
//     each individual IP might only make a handful of attempts, staying
//     under the per-IP threshold, while the targeted account still gets
//     hundreds of guesses in total.
//
// Real systems use both together for exactly this reason. This is a
// deliberately simple in-memory implementation (see nonce_store.py's
// InMemoryNonceStore for the same "good enough for a single-instance demo,
// would need Redis to scale horizontally" tradeoff, documented there too).
const FAILED_ATTEMPT_LIMIT = 5;
const LOCKOUT_DURATION_MS = 15 * 60 * 1000; // 15 minutes

const failedAttempts = new Map(); // username -> { count, lockedUntil }

export function recordFailedAttempt(username) {
  const record = failedAttempts.get(username) || { count: 0, lockedUntil: null };
  record.count += 1;
  if (record.count >= FAILED_ATTEMPT_LIMIT) {
    record.lockedUntil = Date.now() + LOCKOUT_DURATION_MS;
  }
  failedAttempts.set(username, record);
}

export function clearFailedAttempts(username) {
  failedAttempts.delete(username);
}

/** Returns the number of milliseconds remaining if locked, or 0 if not locked. */
export function getLockoutRemaining(username) {
  const record = failedAttempts.get(username);
  if (!record || !record.lockedUntil) return 0;

  const remaining = record.lockedUntil - Date.now();
  if (remaining <= 0) {
    // Lockout window has passed -- clear it so the next attempt starts fresh,
    // rather than leaving stale state around forever.
    failedAttempts.delete(username);
    return 0;
  }
  return remaining;
}
