// Demo user store. In a real system this is a database -- kept in-memory here
// so the security engineering (auth flow, scopes, rotation) stays the focus,
// not user management CRUD.
//
// Password hashes are bcrypt (cost 10). Plaintext passwords below are for the
// README/demo only -- never do this in a real system, obviously.
import bcrypt from "bcryptjs";

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

export function verifyPassword(user, password) {
  return bcrypt.compareSync(password, user.passwordHash);
}
