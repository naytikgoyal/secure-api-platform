// Week 3: every route now requires a valid JWT (requireAuth) and the correct
// scope (requireScope). owner_id no longer comes from the client -- it comes
// from req.auth.sub, the verified token subject. This closes the BOLA gap
// flagged with TODO(Week 3) comments in resource-service/main.py during Week 2.
//
// IMPORTANT: this Gateway-level scope check is only HALF the story. The
// Resource Service (see resource-service/main.py) enforces the exact same
// scopes again, independently, using its own JWT verification. A bug here
// does not equal a full bypass -- that's what "defense in depth" (NFR-8) means
// in practice, not just as a PRD bullet point.
import { Router } from "express";
import { callResourceService } from "../proxyClient.js";
import { requireAuth, requireScope } from "../middleware/auth.js";
import { createOrdersRateLimiter } from "../middleware/rateLimiter.js";

const router = Router();

router.use(requireAuth); // every /orders/* route requires a valid token, no exceptions
router.use(createOrdersRateLimiter()); // AFTER requireAuth so we can key by req.auth.sub

router.post("/", requireScope("orders:write"), async (req, res, next) => {
  try {
    const payload = { item: req.body?.item, quantity: req.body?.quantity, owner_id: req.auth.sub };
    const { status, body } = await callResourceService("POST", "/orders", payload, req.rawToken);
    res.status(status).json(body);
  } catch (err) {
    next(err);
  }
});

router.get("/", requireScope("orders:read"), async (req, res, next) => {
  try {
    // Admins can pass ?owner_id=... to inspect any user's orders; everyone else
    // only ever sees their own -- Resource Service enforces this independently too.
    const wantsOtherOwner = req.query.owner_id && req.query.owner_id !== req.auth.sub;
    if (wantsOtherOwner && !req.auth.scopes.includes("admin")) {
      return res.status(403).json({ error: "insufficient_scope", message: "Requires 'admin' scope to view another user's orders." });
    }
    const ownerId = req.query.owner_id || req.auth.sub;
    const { status, body } = await callResourceService("GET", `/orders?owner_id=${encodeURIComponent(ownerId)}`, null, req.rawToken);
    res.status(status).json(body);
  } catch (err) {
    next(err);
  }
});

router.get("/:id", requireScope("orders:read"), async (req, res, next) => {
  try {
    const { status, body } = await callResourceService("GET", `/orders/${encodeURIComponent(req.params.id)}`, null, req.rawToken);
    res.status(status).json(body);
  } catch (err) {
    next(err);
  }
});

router.delete("/:id", requireScope("orders:write"), async (req, res, next) => {
  try {
    const { status, body } = await callResourceService("DELETE", `/orders/${encodeURIComponent(req.params.id)}`, null, req.rawToken);
    res.status(status).json(body ?? {});
  } catch (err) {
    next(err);
  }
});

export default router;
