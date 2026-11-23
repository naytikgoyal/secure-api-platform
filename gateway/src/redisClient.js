// Shared Redis client for the Gateway -- used by the rate limiter (this week)
// and could back other cross-instance state later (e.g. a token blocklist).
import { createClient } from "redis";

const REDIS_HOST = process.env.REDIS_HOST || "redis";

export const redisClient = createClient({ url: `redis://${REDIS_HOST}:6379` });

redisClient.on("error", (err) => {
  console.error("[gateway] Redis client error:", err.message);
});

export async function connectRedis() {
  if (!redisClient.isOpen) {
    await redisClient.connect();
  }
}
