// Refresh token store with rotation.
//
// Refresh tokens are OPAQUE random strings (not JWTs) stored server-side --
// this means we can revoke one instantly by deleting it, which you cannot do
// with a self-contained JWT before its natural expiry. This is the standard
// "access token = JWT, refresh token = opaque + server-tracked" split.
//
// Rotation: every time a refresh token is used, it's deleted and a brand new
// one is issued. If an attacker ever steals and replays an OLD refresh token
// after the legitimate client already rotated it, this store no longer
// recognizes it -- request is rejected. (This is "refresh token reuse
// detection" in OAuth2 terminology.)
import crypto from "crypto";

const REFRESH_TOKEN_TTL_MS = 7 * 24 * 60 * 60 * 1000; // 7 days

// Map<token, { sub, scopes, expiresAt }>
const store = new Map();

export function issueRefreshToken(sub, scopes) {
  const token = crypto.randomBytes(48).toString("hex");
  store.set(token, { sub, scopes, expiresAt: Date.now() + REFRESH_TOKEN_TTL_MS });
  return token;
}

/**
 * Consume (and invalidate) a refresh token, returning its claims if valid.
 * Returns null if the token doesn't exist or has expired.
 */
export function consumeRefreshToken(token) {
  const record = store.get(token);
  if (!record) return null;

  store.delete(token); // rotation: this token can never be used again, valid or not

  if (record.expiresAt < Date.now()) return null;

  return record;
}
