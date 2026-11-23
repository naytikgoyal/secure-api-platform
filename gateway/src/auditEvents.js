// Audit event bus: every allow/deny decision gets recorded here, in addition
// to being logged via pino (logger.js). This is a SEPARATE concern from
// logging -- logs are for humans/Loki querying history; this is for the
// dashboard's live feed (PRD Section 8.1, Panel 1 & 2), which needs recent
// events in memory, pushed out over SSE as they happen, not queried from a
// log store per request.
//
// Deliberately in-memory and single-instance: this is a demo dashboard
// feature, not a durability guarantee. If the Gateway restarts, the feed
// resets. Loki (docs/architecture-diagram.md) is the durable, queryable
// version of the same data -- see infra/grafana-dashboard.json.
import { randomUUID } from "crypto";

const MAX_EVENTS = 200; // ring buffer size -- enough for a demo, not a data warehouse
const events = [];
const sseClients = new Set();

/**
 * @param {object} event - { type: "allow"|"deny", category: string, message: string, meta?: object }
 */
export function recordAuditEvent(event) {
  const enriched = {
    id: randomUUID(),
    ts: new Date().toISOString(),
    ...event,
  };

  events.push(enriched);
  if (events.length > MAX_EVENTS) {
    events.shift();
  }

  const payload = `data: ${JSON.stringify(enriched)}\n\n`;
  for (const res of sseClients) {
    res.write(payload);
  }

  return enriched;
}

export function getRecentEvents(limit = 100) {
  return events.slice(-limit).reverse(); // newest first
}

export function getMetrics() {
  const now = Date.now();
  const oneMinuteAgo = now - 60_000;
  const recentEvents = events.filter((e) => new Date(e.ts).getTime() >= oneMinuteAgo);

  return {
    requestsPerMinute: recentEvents.length,
    denyRate:
      recentEvents.length > 0
        ? Math.round((recentEvents.filter((e) => e.type === "deny").length / recentEvents.length) * 100)
        : 0,
    rateLimitedCount: recentEvents.filter((e) => e.category === "rate_limit").length,
    totalTracked: events.length,
  };
}

/** Registers an SSE client connection to receive events as they happen. */
export function subscribeSSE(res) {
  sseClients.add(res);
  return () => sseClients.delete(res);
}
