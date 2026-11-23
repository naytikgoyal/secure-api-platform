// Week 5: secrets (JWT public key, HMAC secret) are fetched from Vault ONCE
// at startup, before the HTTPS server starts listening -- see vaultClient.js.
// This is why main() is async and everything downstream (auth middleware,
// proxy client) uses a setter pattern (setPublicKey/setHmacSecret) instead of
// reading a file at import time. TLS certs (mTLS identity) remain local files
// mounted read-only from infra/certs/ -- see docs/key-rotation-runbook.md for
// why that boundary exists.
import fs from "fs";
import https from "https";
import express from "express";
import pinoHttp from "pino-http";
import { randomUUID } from "crypto";
import { errorHandler, notFoundHandler } from "./middleware/errorHandler.js";
import { fetchSecrets } from "./vaultClient.js";
import { setPublicKey } from "./middleware/auth.js";
import { setHmacSecret } from "./proxyClient.js";
import { connectRedis } from "./redisClient.js";
import { logger } from "./logger.js";
import adminRouter from "./routes/admin.js";
import cors from "cors";
import helmet from "helmet";
const PORT = process.env.PORT || 3000;
const CERT_DIR = process.env.CERT_DIR || "/certs";

async function main() {
  console.log("[gateway] connecting to Redis...");
  await connectRedis(); // MUST resolve before importing orders.js -- its rate
  // limiter constructs a RedisStore at module-import time, which needs an
  // already-open Redis connection. Using a dynamic import() here (instead of
  // a static top-level import) is what lets us guarantee that ordering.

  console.log("[gateway] fetching secrets from Vault...");
  const { jwtPublicKey, hmacSecret } = await fetchSecrets();
  setPublicKey(jwtPublicKey);
  setHmacSecret(hmacSecret);
  console.log("[gateway] secrets loaded from Vault -- no local secret files needed at runtime.");

  const { default: ordersRouter } = await import("./routes/orders.js");

  const app = express();

  // Security headers (Sprint 9). helmet sets a bundle of defensive HTTP
  // response headers in one call -- the most relevant ones for an API like
  // this: X-Content-Type-Options: nosniff (stops a browser from guessing a
  // response is HTML/JS when we said it's JSON), X-Frame-Options: DENY (this
  // API can't be embedded in an <iframe>, which matters if it were ever
  // fronted by a browser client vulnerable to clickjacking), and
  // Strict-Transport-Security (tells a browser to only ever speak HTTPS to
  // this host from now on, once it's seen this header once). None of these
  // replace the deeper controls elsewhere in this project (mTLS, JWT, HMAC
  // signing) -- they're a cheap, standard baseline that costs one line and
  // is one of the first things a real AppSec review checks for.
  app.use(helmet());

  app.use(cors({
    origin: "http://localhost:5173",
    credentials: true,
  }));
  // Assigns req.id (a correlation ID -- NFR-7) and logs every request's
  // completion as structured JSON: method, path, status, response time.
  // This is the "access log" layer; auth.js/rateLimiter.js add the more
  // specific allow/deny semantic events on top of it.
  app.use(
    pinoHttp({
      logger,
      genReqId: () => randomUUID(),
      customLogLevel: (req, res) => (res.statusCode >= 500 ? "error" : res.statusCode >= 400 ? "warn" : "info"),
    })
  );

  app.use(express.json({ limit: "100kb" })); // cap body size -- cheap DoS guard

  app.get("/health", (req, res) => {
    res.status(200).json({ status: "ok", service: "gateway", ts: new Date().toISOString() });
  });

  app.use("/orders", ordersRouter);
  app.use("/admin", adminRouter);

  app.use(notFoundHandler);
  app.use(errorHandler); // must be registered LAST -- Express error middleware convention

  const httpsOptions = {
    key: fs.readFileSync(`${CERT_DIR}/gateway.key`),
    cert: fs.readFileSync(`${CERT_DIR}/gateway.crt`),
  };

  https.createServer(httpsOptions, app).listen(PORT, () => {
    console.log(`[gateway] listening on https://0.0.0.0:${PORT}`);
  });
}

main().catch((err) => {
  console.error("[gateway] FATAL: failed to start:", err);
  process.exit(1);
});
