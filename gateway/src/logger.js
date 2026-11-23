// Structured JSON logging (NFR-7: "Structured JSON logs for every auth
// decision (allow/deny) with a request ID"). Uses pino -- the standard
// structured logger for Node, chosen over console.log because every log line
// needs to be machine-parseable (by Loki, by the dashboard's SSE feed, by a
// human grepping it) rather than free-text.
import pino from "pino";

export const logger = pino({
  level: process.env.LOG_LEVEL || "info",
  formatters: {
    level: (label) => ({ level: label }), // "info" not 30 -- readable in raw JSON
  },
  timestamp: pino.stdTimeFunctions.isoTime,
  base: { service: "gateway" },
});
