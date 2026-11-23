// Week 3: real OAuth2-style token issuance (password grant, documented as a
// deliberate simplification -- see docs/threat-model.md).
// Week 5: JWT private key fetched from Vault at startup (no local file);
// /auth/login and /auth/refresh rate-limited (NFR-5 + threat-model 5.1).
import fs from "fs";
import https from "https";
import express from "express";
import pinoHttp from "pino-http";
import { randomUUID } from "crypto";
import { findUserByUsername, verifyPassword } from "./users.js";
import { issueAccessToken, setPrivateKey, ACCESS_TOKEN_TTL_SECONDS } from "./issueToken.js";
import { issueRefreshToken, consumeRefreshToken } from "./refreshTokenStore.js";
import { fetchSecrets } from "./vaultClient.js";
import { connectRedis } from "./redisClient.js";
import { createAuthRateLimiter } from "./middleware/rateLimiter.js";
import { logger } from "./logger.js";
import cors from "cors";
import helmet from "helmet";
import { recordFailedAttempt, clearFailedAttempts, getLockoutRemaining } from "./accountLockout.js";

const PORT = process.env.PORT || 4000;
const CERT_DIR = process.env.CERT_DIR || "/certs";

async function main() {
  console.log("[auth-server] connecting to Redis...");
  await connectRedis();

  console.log("[auth-server] fetching secrets from Vault...");
  const { jwtPrivateKey } = await fetchSecrets();
  setPrivateKey(jwtPrivateKey);
  console.log("[auth-server] JWT private key loaded from Vault -- no local key file needed at runtime.");

  const app = express();

  // See gateway/src/index.js for the fuller explanation of what helmet does
  // and why -- same reasoning applies here.
  app.use(helmet());

  app.use(cors({
  origin: "http://localhost:5173",  // only the dashboard is allowed to call this API from a browser
  credentials: true,
}));
  app.use(pinoHttp({ logger, genReqId: () => randomUUID() }));
  app.use(express.json({ limit: "10kb" }));

  const authLimiter = createAuthRateLimiter();

  app.get("/health", (req, res) => {
    res.status(200).json({ status: "ok", service: "auth-server", ts: new Date().toISOString() });
  });

  // POST /auth/login { username, password } -> { access_token, refresh_token, expires_in, token_type }
  app.post("/auth/login", authLimiter, (req, res) => {
    const { username, password } = req.body || {};

    if (!username || !password) {
      return res.status(400).json({ error: "invalid_request", message: "username and password are required." });
    }

    // Account lockout check runs BEFORE we even look at the password --
    // if this specific username is locked, we don't want to do a bcrypt
    // comparison at all (bcrypt is deliberately slow; skipping it here is a
    // minor efficiency win, but more importantly it keeps the "why was this
    // rejected" reasoning in one place instead of two).
    //
    // IMPORTANT: this check runs on the raw submitted username, before we
    // know if it corresponds to a real account. That's deliberate: since
    // recordFailedAttempt() below is called unconditionally (even for
    // nonexistent usernames), a nonexistent username gets "locked" after 5
    // attempts in EXACTLY the same way a real one would. If lockout only
    // applied to real accounts, an attacker could tell "real username, wrong
    // password" apart from "fake username" just by noticing which ones
    // eventually return 423 vs. always returning 401 -- reintroducing the
    // exact account-enumeration vulnerability this system already defends
    // against via the identical 401 message below (docs/threat-model.md 5.1).
    const lockoutRemaining = getLockoutRemaining(username);
    if (lockoutRemaining > 0) {
      logger.warn({ reqId: req.id, username, lockoutRemainingMs: lockoutRemaining }, "login denied: account locked");
      return res.status(423).json({
        error: "account_locked",
        message: `Too many failed attempts for this account. Try again in ${Math.ceil(lockoutRemaining / 60000)} minute(s).`,
      });
    }

    const user = findUserByUsername(username);

    // Deliberately identical error for "no such user" and "wrong password" --
    // see docs/threat-model.md 5.1: distinguishing them enables account enumeration.
    if (!user || !verifyPassword(user, password)) {
      recordFailedAttempt(username); // tracked even for nonexistent usernames -- see accountLockout.js
      logger.warn({ reqId: req.id, username }, "login denied: invalid credentials");
      return res.status(401).json({ error: "invalid_credentials", message: "Incorrect username or password." });
    }

    clearFailedAttempts(username); // a successful login resets the counter

    const access_token = issueAccessToken(user.sub, user.scopes);
    const refresh_token = issueRefreshToken(user.sub, user.scopes);

    logger.info({ reqId: req.id, sub: user.sub }, "login allowed");
    res.status(200).json({
      access_token,
      refresh_token,
      token_type: "Bearer",
      expires_in: ACCESS_TOKEN_TTL_SECONDS,
      scopes: user.scopes,
    });
  });

  // POST /auth/refresh { refresh_token } -> new access_token + new refresh_token (rotated)
  app.post("/auth/refresh", authLimiter, (req, res) => {
    const { refresh_token } = req.body || {};

    if (!refresh_token) {
      return res.status(400).json({ error: "invalid_request", message: "refresh_token is required." });
    }

    const claims = consumeRefreshToken(refresh_token); // this DELETES the old token -- rotation

    if (!claims) {
      logger.warn({ reqId: req.id }, "refresh denied: invalid, expired, or reused token");
      return res.status(401).json({ error: "invalid_grant", message: "Refresh token is invalid, expired, or already used." });
    }

    const access_token = issueAccessToken(claims.sub, claims.scopes);
    const new_refresh_token = issueRefreshToken(claims.sub, claims.scopes);

    logger.info({ reqId: req.id, sub: claims.sub }, "refresh allowed (rotated)");
    res.status(200).json({
      access_token,
      refresh_token: new_refresh_token,
      token_type: "Bearer",
      expires_in: ACCESS_TOKEN_TTL_SECONDS,
      scopes: claims.scopes,
    });
  });

  // eslint-disable-next-line no-unused-vars
  app.use((err, req, res, next) => {
    logger.error({ reqId: req.id, err }, "unhandled error");
    res.status(500).json({ error: "internal_error", message: "Something went wrong. Please try again." });
  });

  const httpsOptions = {
    key: fs.readFileSync(`${CERT_DIR}/auth-server.key`),
    cert: fs.readFileSync(`${CERT_DIR}/auth-server.crt`),
  };

  https.createServer(httpsOptions, app).listen(PORT, () => {
    console.log(`[auth-server] listening on https://0.0.0.0:${PORT}`);
  });
}

main().catch((err) => {
  console.error("[auth-server] FATAL: failed to start:", err);
  process.exit(1);
});
