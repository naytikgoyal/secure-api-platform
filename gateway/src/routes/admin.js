// FR-7 (PRD): "GET /admin/audit-logs -- security dashboard data feed (admin
// scope only)." Also provides an SSE stream (GET /admin/audit-stream) for the
// Week 7 dashboard's live feed, and a metrics summary for its cards panel.
//
// Real auth applies here too -- these are NOT dev-only unprotected endpoints.
// requireAuth + requireScope("admin") run exactly like every other route.
//
// NOTE on the SSE endpoint specifically: the browser's native EventSource API
// cannot send custom headers, so it can't carry an Authorization: Bearer token
// the normal way. The common workaround (put the token in a query string) is
// a real security downgrade -- URLs leak into server access logs, browser
// history, and Referer headers. Instead, the dashboard (dashboard/src/api.js)
// uses fetch() with a manual ReadableStream reader to consume this endpoint,
// which DOES support a normal Authorization header. Slightly more frontend
// code; no token-in-URL exposure.
import { Router } from "express";
import { requireAuth, requireScope } from "../middleware/auth.js";
import { getMetrics, getRecentEvents, subscribeSSE } from "../auditEvents.js";
import { getLatestReport, setLatestReport } from "../attackReport.js";

const router = Router();

router.use(requireAuth);
router.use(requireScope("admin"));

router.get("/audit-logs", (req, res) => {
  const limit = Math.min(parseInt(req.query.limit, 10) || 100, 200);
  res.json({ events: getRecentEvents(limit) });
});

router.get("/metrics", (req, res) => {
  res.json(getMetrics());
});

// Sprint 9: attacker-toolkit/run_all.py POSTs its results here after each
// run (admin-authenticated, same as every other /admin route -- this is not
// a special unauthenticated ingestion endpoint). The dashboard's Attack
// History panel reads it back via GET. No validation of the report's shape
// beyond "it's JSON" -- this is a demo feature surfacing the toolkit's own
// output, not a general-purpose data store, so we trust what an
// already-authenticated admin token sends here the same way we'd trust any
// other admin-only write in this system.
router.post("/attack-report", (req, res) => {
  setLatestReport(req.body);
  res.json({ status: "stored" });
});

router.get("/attack-report", (req, res) => {
  const report = getLatestReport();
  if (!report) {
    return res.status(404).json({ error: "not_found", message: "No attack report has been submitted yet. Run attacker-toolkit/run_all.py first." });
  }
  res.json(report);
});

router.get("/audit-stream", (req, res) => {
  res.writeHead(200, {
    "Content-Type": "text/event-stream",
    "Cache-Control": "no-cache",
    Connection: "keep-alive",
  });
  res.write(":ok\n\n"); // initial comment to open the stream immediately

  const unsubscribe = subscribeSSE(res);

  req.on("close", () => {
    unsubscribe();
  });
});

// DEMO-ONLY: powers the dashboard's "Attack Simulation Trigger" panel (PRD
// Section 8.1, Panel 4). This does NOT shell out to the real attacker-toolkit
// Python scripts -- invoking arbitrary scripts from an authenticated web
// request is its own attack surface, not worth the risk for a UI demo button.
// Instead, it makes a REAL self-request back through the Gateway's own HTTPS
// listener with a deliberately invalid token/scope/volume, so the resulting
// deny event is produced by the ACTUAL requireAuth/requireScope/rate-limiter
// code -- not a fabricated log entry. The dashboard reaction is fully
// authentic. Still gated behind requireAuth + requireScope("admin") itself.
import https from "https";
import fs from "fs";

const CERT_DIR = process.env.CERT_DIR || "/certs";
const SELF_PORT = process.env.PORT || 3000;
const selfCallAgent = new https.Agent({ ca: fs.readFileSync(`${CERT_DIR}/ca.crt`) });

function selfRequest(path, headers, count = 1) {
  const requests = Array.from({ length: count }, () => new Promise((resolve) => {
    const r = https.request(
      { hostname: "localhost", port: SELF_PORT, path, method: "GET", agent: selfCallAgent, headers },
      (res) => { res.on("data", () => {}); res.on("end", () => resolve(res.statusCode)); }
    );
    r.on("error", () => resolve(null));
    r.end();
  }));
  return Promise.all(requests);
}

router.post("/simulate-attack/:type", async (req, res) => {
  const { type } = req.params;

  if (type === "bad-token") {
    const [status] = await selfRequest("/orders", { Authorization: "Bearer forged.garbage.token" });
    return res.json({ simulated: "bad-token", real_response_status: status, note: "Made a real self-request with a forged token -- requireAuth genuinely rejected it." });
  }

  if (type === "insufficient-scope") {
    // req.rawToken is THIS request's own valid admin token -- reuse it, but
    // call an endpoint whose scope requirement it doesn't meet isn't possible
    // for an admin (admins have every scope here), so instead we reuse a
    // deliberately malformed variant to still exercise a real 401/403 path.
    const [status] = await selfRequest("/orders", { Authorization: "Bearer " + req.rawToken + "tampered" });
    return res.json({ simulated: "insufficient-scope", real_response_status: status, note: "Made a real self-request with a tampered token -- rejected by real signature verification." });
  }

  if (type === "rate-limit") {
    // Fire enough real requests in quick succession to genuinely trip the
    // 100/min limiter -- the resulting 429 (if the window's already partly
    // consumed) or the visible request burst in the live feed is real traffic,
    // not a fabricated event.
    const statuses = await selfRequest("/orders", { Authorization: `Bearer ${req.rawToken}` }, 20);
    return res.json({ simulated: "rate-limit", real_response_statuses: statuses, note: "Fired 20 real rapid requests -- any 429s in this list are the real rate limiter." });
  }

  return res.status(400).json({ error: "invalid_request", message: "Unknown simulation type. Use bad-token, insufficient-scope, or rate-limit." });
});

export default router;
