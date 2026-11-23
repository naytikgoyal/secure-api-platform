// Account lockout, keyed by (username, source address).
//
// This is deliberately a DIFFERENT control from the IP rate limiter in
// middleware/rateLimiter.js: the rate limiter caps how fast ANY client may call
// /auth/login; this lock stops ONE SOURCE from going on guessing passwords for
// ONE ACCOUNT once it has failed too often.
//
// WHY THE KEY INCLUDES THE ADDRESS. The first version kept one counter per
// username, whatever the source. Testing (report finding D-02) showed the
// price: anyone who knew a username could lock that person out for 15 minutes
// with five wrong passwords, even though the real owner had done nothing. With
// the address in the key, an outsider can only lock their OWN address out of
// the account. The OWASP Authentication Cheat Sheet describes this trade-off.
//
// WHAT WE GIVE UP, AND WHAT REPLACES IT. A guesser with many addresses now
// gets five tries per address, not five in total. Two things make that
// acceptable: the per-address login rate limit (10 per minute) and bcrypt's
// cost still make each guess expensive, and every failure is also counted per
// ACCOUNT across all addresses. When that count passes a threshold we log a
// warning ("possible distributed guessing") so an operator can react. That is
// detection, not prevention, and is recorded as a residual risk.
//
// Unknown usernames are tracked exactly like real ones, so lockout cannot be
// used to tell real accounts from invented ones (see docs/threat-model.md 5.1).
//
// State is in memory and per instance (see nonce_store.py's InMemoryNonceStore
// for the same trade-off): a restart clears it and two instances would not
// share it. Every function takes an optional `now` so the rules can be tested.
const FAILED_ATTEMPT_LIMIT = 5;
const LOCKOUT_DURATION_MS = 15 * 60 * 1000; // 15 minutes
const FAILURE_WINDOW_MS = 15 * 60 * 1000; // failures older than this are forgotten
const DISTRIBUTED_GUESS_THRESHOLD = 30; // failures against one account, all sources, inside the window
const MAX_TRACKED = 5000; // bound on map sizes; expired entries are pruned past this

const pairs = new Map(); // `${ip}|${username}` -> { count, lockedUntil, lastFailure }
const accounts = new Map(); // username -> { count, windowStart, alerted }

const keyOf = (username, ip) => `${ip}|${username}`;

function prune(now) {
  if (pairs.size > MAX_TRACKED) {
    for (const [k, r] of pairs) {
      const expired = r.lockedUntil ? r.lockedUntil <= now : now - r.lastFailure > FAILURE_WINDOW_MS;
      if (expired) pairs.delete(k);
    }
  }
  if (accounts.size > MAX_TRACKED) {
    for (const [k, r] of accounts) if (now - r.windowStart > FAILURE_WINDOW_MS) accounts.delete(k);
  }
}

/**
 * Records one failed login. Returns { accountFailures, distributedGuessingSuspected }.
 * The second flag is true only once per window, the moment the threshold is passed.
 */
export function recordFailedAttempt(username, ip, now = Date.now()) {
  prune(now);

  const k = keyOf(username, ip);
  let rec = pairs.get(k);
  if (!rec || (rec.lockedUntil && rec.lockedUntil <= now) || now - rec.lastFailure > FAILURE_WINDOW_MS) {
    rec = { count: 0, lockedUntil: null, lastFailure: now };
  }
  rec.count += 1;
  rec.lastFailure = now;
  if (rec.count >= FAILED_ATTEMPT_LIMIT) rec.lockedUntil = now + LOCKOUT_DURATION_MS;
  pairs.set(k, rec);

  let acc = accounts.get(username);
  if (!acc || now - acc.windowStart > FAILURE_WINDOW_MS) acc = { count: 0, windowStart: now, alerted: false };
  acc.count += 1;
  const suspected = acc.count >= DISTRIBUTED_GUESS_THRESHOLD && !acc.alerted;
  if (suspected) acc.alerted = true;
  accounts.set(username, acc);

  return { accountFailures: acc.count, distributedGuessingSuspected: suspected };
}

/** A successful login clears the failure count for that source only. */
export function clearFailedAttempts(username, ip) {
  pairs.delete(keyOf(username, ip));
}

/** Returns the number of milliseconds remaining if this source is locked out of this account, or 0. */
export function getLockoutRemaining(username, ip, now = Date.now()) {
  const rec = pairs.get(keyOf(username, ip));
  if (!rec || !rec.lockedUntil) return 0;

  const remaining = rec.lockedUntil - now;
  if (remaining <= 0) {
    // The lock has run out: forget it so the next attempt starts fresh.
    pairs.delete(keyOf(username, ip));
    return 0;
  }
  return remaining;
}

/** Test helper: forget everything. */
export function _resetForTests() {
  pairs.clear();
  accounts.clear();
}
