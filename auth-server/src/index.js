// Week 3: real OAuth2-style token issuance (password grant, documented as a
// deliberate simplification -- see docs/threat-model.md).
// Week 5: JWT private key fetched from Vault at startup (no local file);
// /auth/login and /auth/refresh rate-limited (NFR-5 + threat-model 5.1).
import fs from "fs";
import https from "https";
import express from "express";
import pinoHttp from "pino-http";
import { randomUUID } from "crypto";
import { authenticate } from "./users.js";
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

    if (typeof username !== "string" || typeof password !== "string" || !username || !password) {
      return res.status(400).json({ error: "invalid_request", message: "username and password are required." });
    }

    // Lockout is keyed by (username, source address): see accountLockout.js for
    // why, and for the trade-off. It is checked BEFORE the password comparison so
    // a locked source costs us no bcrypt work. It applies to unknown usernames
    // exactly as to real ones, so lockout cannot be used to enumerate accounts
    // (docs/threat-model.md 5.1).
    const lockoutRemaining = getLockoutRemaining(username, req.ip);
    if (lockoutRemaining > 0) {
      logger.warn({ reqId: req.id, username, lockoutRemainingMs: lockoutRemaining }, "login denied: source locked out of this account");
      return res.status(423).json({
        error: "account_locked",
        message: `Too many failed attempts from this address for this account. Try again in ${Math.ceil(lockoutRemaining / 60000)} minute(s).`,
      });
    }

    // authenticate() performs exactly one bcrypt comparison whether or not the
    // username exists, so response time does not reveal which usernames are
    // real. The 401 message is also identical (docs/threat-model.md 5.1).
    const user = authenticate(username, password);

    if (!user) {
      const result = recordFailedAttempt(username, req.ip);
      if (result.distributedGuessingSuspected) {
        // Detection, not prevention: many different sources are failing against one account.
        logger.warn({ reqId: req.id, username, accountFailures: result.accountFailures }, "possible distributed password guessing against one account");
      }
      logger.warn({ reqId: req.id, username }, "login denied: invalid credentials");
      return res.status(401).json({ error: "invalid_credentials", message: "Incorrect username or password." });
    }

    clearFailedAttempts(username, req.ip); // a successful login clears the count for this source

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
