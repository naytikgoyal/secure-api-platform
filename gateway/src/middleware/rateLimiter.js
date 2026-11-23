// Per-client rate limiting (NFR-5), Redis-backed so it's correct even if the
// Gateway is ever scaled to multiple instances -- an in-memory counter would
// let each instance independently allow the full quota, defeating the limit.
//
// Applied AFTER requireAuth (see routes/orders.js) so we can key by the
// verified token's `sub` claim rather than just IP -- this means the limit
// actually follows the CLIENT, not the network path (important behind a
// shared corporate NAT or VPN where many legitimate users share one IP).
// Unauthenticated requests never reach this middleware; they're already
// rejected with 401 by requireAuth first, which is cheap enough not to need
// its own separate rate limit at this layer (auth-server's /auth/login has
// its own stricter, IP-keyed limiter -- see auth-server/src/middleware/rateLimiter.js
// -- because that's the actual pre-auth brute-force surface).
import rateLimit from "express-rate-limit";
import { RedisStore } from "rate-limit-redis";
import { redisClient } from "../redisClient.js";
import { logger } from "../logger.js";
import { recordAuditEvent } from "../auditEvents.js";

export function createOrdersRateLimiter() {
  return rateLimit({
    windowMs: 60_000, // 1 minute
    limit: 100, // NFR-5: 100 req/min per client
    standardHeaders: true, // adds RateLimit-* headers so clients can self-throttle
    legacyHeaders: false,
    keyGenerator: (req) => req.auth?.sub || req.ip,
    store: new RedisStore({
      sendCommand: (...args) => redisClient.sendCommand(args),
    }),
    handler: (req, res) => {
      const key = req.auth?.sub || req.ip;
      logger.warn({ reqId: req.id, key }, "rate limit exceeded");
      recordAuditEvent({
        type: "deny",
        category: "rate_limit",
        message: `Rate limit exceeded for ${key}`,
        meta: { key, path: req.originalUrl },
      });
      res.status(429).json({
        error: "rate_limited",
        message: "Too many requests. Please slow down and try again shortly.",
      });
    },
  });
}
