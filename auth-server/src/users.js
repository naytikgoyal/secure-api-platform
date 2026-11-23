// Demo user store. In a real system this is a database -- kept in-memory here
// so the security engineering (auth flow, scopes, rotation) stays the focus,
// not user management CRUD.
//
// Password hashes are bcrypt (cost 10). Plaintext passwords below are for the
// README/demo only -- never do this in a real system, obviously.
import bcrypt from "bcryptjs";
import crypto from "crypto";

function hash(pw) {
  return bcrypt.hashSync(pw, 10);
}

// sub = the JWT "subject" claim -- the stable identifier for "who is this token about."
export const users = [
  {
    sub: "user-naytik",
    username: "naytik",
    passwordHash: hash("password123"),
    scopes: ["orders:read", "orders:write"],
  },
  {
    sub: "user-rishi",
    username: "rishi",
    passwordHash: hash("password123"),
    scopes: ["orders:read"], // read-only user -- used to prove scope enforcement works
  },
  {
    sub: "user-admin",
    username: "admin",
    passwordHash: hash("adminpass456"),
    scopes: ["orders:read", "orders:write", "admin"],
  },
];

export function findUserByUsername(username) {
  return users.find((u) => u.username === username);
}

// A real bcrypt hash of a random value nobody knows. When the username does not
// exist we still compare the submitted password against this, so an unknown user
// costs the same ~100 ms as a known one. Without it, the slow bcrypt step was
// skipped for unknown usernames, and the response-time difference (about 12x in
// testing) let an attacker list valid usernames even though the error messages
// were identical (OWASP Authentication Cheat Sheet, CWE-208).
const DUMMY_HASH = bcrypt.hashSync(crypto.randomBytes(16).toString("hex"), 10);

/**
 * Returns the user if the credentials are valid, otherwise null. Always performs
 * exactly one bcrypt comparison, whatever the username.
 */
export function authenticate(username, password) {
  const user = findUserByUsername(username);
  const matches = bcrypt.compareSync(password, user ? user.passwordHash : DUMMY_HASH);
  return user && matches ? user : null;
}
