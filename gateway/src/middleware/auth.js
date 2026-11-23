// JWT validation middleware -- this is Trust Boundary TB-1 from docs/threat-model.md.
//
// Verifies: signature (against auth-server's PUBLIC key only -- Gateway can never
// sign tokens, only check them), expiry, issuer, and audience. On success, attaches
// req.auth = { sub, scopes } for downstream route handlers and requireScope().
//
// Week 5: the public key is no longer read from a local file at import time --
// it's injected via setPublicKey() once, at startup, after being fetched from
// Vault (see index.js and vaultClient.js). This module-level-variable-set-once
// pattern is a common way to handle "async config needed before sync middleware
// can run" in Express without restructuring every route as async.
import jwt from "jsonwebtoken";
import { logger } from "../logger.js";
import { recordAuditEvent } from "../auditEvents.js";

const ISSUER = "secure-api-platform-auth";
const AUDIENCE = "secure-api-platform";

let publicKey = null;

export function setPublicKey(key) {
  publicKey = key;
}

export function requireAuth(req, res, next) {
  if (!publicKey) {
    // Should be unreachable in practice -- index.js awaits Vault fetch before
    // the server starts listening. Fail closed if it somehow happens anyway.
    return res.status(503).json({ error: "service_unavailable", message: "Auth is not ready yet." });
  }

  const authHeader = req.headers.authorization || "";
  const [scheme, token] = authHeader.split(" ");

  if (scheme !== "Bearer" || !token) {
    logger.warn({ reqId: req.id, path: req.originalUrl }, "auth denied: missing/malformed Authorization header");
    recordAuditEvent({ type: "deny", category: "auth", message: "Missing or malformed Authorization header", meta: { path: req.originalUrl } });
    return res.status(401).json({ error: "unauthorized", message: "Missing or malformed Authorization header." });
  }

  try {
    const payload = jwt.verify(token, publicKey, {
      algorithms: ["RS256"], // pin the algorithm -- never allow "alg: none" or HS256 confusion attacks
      issuer: ISSUER,
      audience: AUDIENCE,
    });

    req.auth = { sub: payload.sub, scopes: payload.scopes || [] };
    req.rawToken = token; // forwarded to Resource Service so IT can independently verify too

    logger.info({ reqId: req.id, sub: payload.sub, path: req.originalUrl }, "auth allowed");
    recordAuditEvent({ type: "allow", category: "auth", message: `Token verified for ${payload.sub}`, meta: { sub: payload.sub, path: req.originalUrl } });
    next();
  } catch (err) {
    // TokenExpiredError, JsonWebTokenError (bad signature), etc. -- all map to 401.
    // Never tell the CLIENT why (expired vs forged) -- that's an information
    // disclosure surface for attackers probing token validity. We DO log the
    // real reason server-side, since that's exactly the kind of detail a SOC
    // dashboard should show an operator, just never the attacker.
    logger.warn({ reqId: req.id, path: req.originalUrl, reason: err.name }, "auth denied: invalid/expired token");
    recordAuditEvent({ type: "deny", category: "auth", message: `Token rejected (${err.name})`, meta: { path: req.originalUrl, reason: err.name } });
    return res.status(401).json({ error: "unauthorized", message: "Invalid or expired token." });
  }
}

/**
 * Scope-check middleware factory. Use AFTER requireAuth.
 * This is HALF of defense-in-depth (NFR-8) -- the Resource Service enforces
 * the same check independently in resource-service/main.py.
 */
export function requireScope(scope) {
  return (req, res, next) => {
    if (!req.auth?.scopes?.includes(scope)) {
      logger.warn({ reqId: req.id, sub: req.auth?.sub, scope }, "scope check denied");
      recordAuditEvent({
        type: "deny",
        category: "scope",
        message: `${req.auth?.sub || "unknown"} lacks required scope '${scope}'`,
        meta: { sub: req.auth?.sub, scope, path: req.originalUrl },
      });
      return res.status(403).json({
        error: "insufficient_scope",
        message: `This action requires the '${scope}' scope.`,
      });
    }
    next();
  };
}
