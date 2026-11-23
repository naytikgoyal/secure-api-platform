// Rate limiting for /auth/login and /auth/refresh. This is deliberately
// STRICTER and keyed differently than the Gateway's general limiter
// (gateway/src/middleware/rateLimiter.js):
//
// - Keyed by IP, not by client identity -- there IS no verified identity yet
//   at this point, that's the whole reason this endpoint exists.
// - Much lower limit (10/min vs 100/min) -- this is the actual credential
//   brute-force surface flagged in docs/threat-model.md section 5.1, so it
//   gets tighter throttling than general API traffic.
import rateLimit from "express-rate-limit";
import { RedisStore } from "rate-limit-redis";
import { redisClient } from "../redisClient.js";

export function createAuthRateLimiter() {
  return rateLimit({
    windowMs: 60_000,
    limit: 10,
    standardHeaders: true,
    legacyHeaders: false,
    keyGenerator: (req) => req.ip,
    store: new RedisStore({
      sendCommand: (...args) => redisClient.sendCommand(args),
    }),
    handler: (req, res) => {
      res.status(429).json({
        error: "rate_limited",
        message: "Too many attempts. Please wait before trying again.",
      });
    },
  });
}
