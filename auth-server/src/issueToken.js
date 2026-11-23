import jwt from "jsonwebtoken";

const ISSUER = "secure-api-platform-auth";
const AUDIENCE = "secure-api-platform";
const ACCESS_TOKEN_TTL = "15m";

// Week 5: no longer read from a local file at import time -- injected once at
// startup after being fetched from Vault (see index.js and vaultClient.js).
let privateKey = null;

export function setPrivateKey(key) {
  privateKey = key;
}

export function issueAccessToken(sub, scopes) {
  if (!privateKey) {
    throw new Error("JWT private key not loaded yet -- Vault fetch may have failed at startup.");
  }

  return jwt.sign({ scopes }, privateKey, {
    algorithm: "RS256",
    subject: sub,
    issuer: ISSUER,
    audience: AUDIENCE,
    expiresIn: ACCESS_TOKEN_TTL,
  });
}

export const ACCESS_TOKEN_TTL_SECONDS = 15 * 60;
