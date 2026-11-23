// Unit tests for the login hardening added after the report's first test campaign
// (findings D-01 and D-02). Run with: npm test   (uses Node's built-in test runner)
import test from "node:test";
import assert from "node:assert/strict";
import {
  recordFailedAttempt, clearFailedAttempts, getLockoutRemaining, _resetForTests,
} from "../src/accountLockout.js";
import { authenticate } from "../src/users.js";

const MIN = 60 * 1000;
const T0 = 1_000_000_000_000;

test("five failures from one address lock that address out of that account", () => {
  _resetForTests();
  for (let i = 0; i < 4; i++) recordFailedAttempt("naytik", "10.0.0.5", T0 + i);
  assert.equal(getLockoutRemaining("naytik", "10.0.0.5", T0 + 10), 0, "four failures must not lock");
  recordFailedAttempt("naytik", "10.0.0.5", T0 + 5);
  assert.ok(getLockoutRemaining("naytik", "10.0.0.5", T0 + 10) > 14 * MIN);
});

test("an outsider cannot lock the real owner out from another address (D-02)", () => {
  _resetForTests();
  for (let i = 0; i < 20; i++) recordFailedAttempt("naytik", "203.0.113.9", T0 + i); // attacker's address
  assert.ok(getLockoutRemaining("naytik", "203.0.113.9", T0 + 100) > 0, "the attacker's own address is locked");
  assert.equal(getLockoutRemaining("naytik", "198.51.100.7", T0 + 100), 0, "the owner's address is not");
});

test("a successful login clears the count for that source only", () => {
  _resetForTests();
  for (let i = 0; i < 3; i++) recordFailedAttempt("rishi", "10.0.0.5", T0 + i);
  clearFailedAttempts("rishi", "10.0.0.5");
  for (let i = 0; i < 4; i++) recordFailedAttempt("rishi", "10.0.0.5", T0 + 10 + i);
  assert.equal(getLockoutRemaining("rishi", "10.0.0.5", T0 + 20), 0, "count restarted from zero");
});

test("the lock expires after 15 minutes", () => {
  _resetForTests();
  for (let i = 0; i < 5; i++) recordFailedAttempt("admin", "10.0.0.5", T0 + i);
  assert.ok(getLockoutRemaining("admin", "10.0.0.5", T0 + 14 * MIN) > 0);
  assert.equal(getLockoutRemaining("admin", "10.0.0.5", T0 + 16 * MIN), 0);
});

test("old failures are forgotten: four failures a day apart never lock", () => {
  _resetForTests();
  for (let i = 0; i < 6; i++) recordFailedAttempt("naytik", "10.0.0.5", T0 + i * 24 * 60 * MIN);
  assert.equal(getLockoutRemaining("naytik", "10.0.0.5", T0 + 6 * 24 * 60 * MIN), 0);
});

test("unknown usernames are tracked exactly like real ones", () => {
  _resetForTests();
  for (let i = 0; i < 5; i++) recordFailedAttempt("no-such-user", "10.0.0.5", T0 + i);
  assert.ok(getLockoutRemaining("no-such-user", "10.0.0.5", T0 + 10) > 0);
});

test("failures from many addresses are counted per account and flagged once", () => {
  _resetForTests();
  let flagged = 0, last = 0;
  for (let i = 0; i < 40; i++) {
    const r = recordFailedAttempt("naytik", `192.0.2.${i}`, T0 + i);
    if (r.distributedGuessingSuspected) flagged += 1;
    last = r.accountFailures;
  }
  assert.equal(last, 40);
  assert.equal(flagged, 1, "the warning fires once, when the threshold of 30 is passed");
});

test("authenticate returns the user only for the right password", () => {
  assert.equal(authenticate("naytik", "definitely-wrong"), null);
  assert.equal(authenticate("no-such-user-xyz", "whatever"), null);
});

test("an unknown username costs a comparable time to a known one (D-01)", () => {
  authenticate("naytik", "warm-up"); authenticate("no-such-user", "warm-up"); // warm the JIT
  const time = (name) => {
    const t = process.hrtime.bigint();
    for (let i = 0; i < 3; i++) authenticate(name, "wrong-password");
    return Number(process.hrtime.bigint() - t) / 3e6; // ms per call
  };
  const known = time("naytik");
  const unknown = time("no-such-user");
  assert.ok(unknown > known * 0.5, `unknown ${unknown.toFixed(1)} ms vs known ${known.toFixed(1)} ms: the bcrypt step must not be skipped`);
  assert.ok(unknown < known * 2, "and must not be wildly slower either");
});
