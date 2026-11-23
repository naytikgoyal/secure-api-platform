# Week 3: independent JWT verification + scope enforcement.
#
# CRITICAL DESIGN POINT: this service does NOT trust that the Gateway already
# checked the token. It re-verifies the signature, expiry, issuer, and audience
# itself, using only the PUBLIC key (see docs/threat-model.md NFR-8, defense in
# depth). If the Gateway had a bug and let an unscoped request through, this
# service still blocks it independently.
#
# This is also where the BOLA/IDOR fix from docs/threat-model.md section 5.2
# actually lands: owner_id now comes from the verified token's `sub` claim,
# never from client-controlled input. See the TODOs from Week 2 -- they're
# resolved below.
from __future__ import annotations

import ssl
import uuid
from datetime import datetime, timezone
from typing import Optional

import jwt
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

import os

from nonce_store import NonceStore, RedisNonceStore
from signing import SignatureError, verify_signature
from vault_client import fetch_secrets
from logger import logger

app = FastAPI(title="Resource Service", version="0.5.0")

ISSUER = "secure-api-platform-auth"
AUDIENCE = "secure-api-platform"
CERT_DIR = os.environ.get("CERT_DIR", "/certs")
NONCE_TTL_SECONDS = 300  # 5 minutes -- matches PRD NFR-3

# Week 5: JWT public key and HMAC secret now come from Vault, fetched once at
# module load (i.e. once when the app boots), not read from local files.
# TLS certs (mTLS identity) remain local files -- see docs/key-rotation-runbook.md.
print("[resource-service] fetching secrets from Vault...")
_secrets = fetch_secrets()
_PUBLIC_KEY = _secrets["jwt_public_key"].encode("utf-8")
_HMAC_SECRET = _secrets["hmac_secret"]
print("[resource-service] secrets loaded from Vault -- no local secret files needed at runtime.")

# Module-level so tests can swap it via monkeypatch (main.nonce_store = InMemoryNonceStore()).
# Production always uses Redis -- an in-memory store would miss replays against a
# different Resource Service instance if this is ever scaled horizontally.
nonce_store: NonceStore = RedisNonceStore(host=os.environ.get("REDIS_HOST", "redis"))

# ---------------------------------------------------------------------------
# PostgreSQL-backed store (replaces the Weeks 2-8 in-memory dict). See db.py
# for the actual queries -- every single one is parameterized. schema
# initialization happens once at startup, right after secrets are loaded.
# ---------------------------------------------------------------------------
import db as _db

_db.configure(_secrets["db_user"], _secrets["db_password"])  # from Vault, never from env/compose
_db.wait_for_database()
_db.init_schema()


class OrderCreate(BaseModel):
    item: str = Field(..., min_length=1, max_length=200)
    quantity: int = Field(..., ge=1, le=1000)
    # owner_id is still accepted in the body because the Gateway sets it from
    # req.auth.sub before forwarding -- but this service does NOT trust it blindly;
    # see create_order() below, which cross-checks it against the verified token.
    owner_id: str = Field(..., min_length=1, max_length=100)

    @field_validator("item")
    @classmethod
    def reject_null_bytes(cls, v: str) -> str:
        # This is the ONE input-blocklisting rule in this codebase, and it's
        # deliberately narrow. See docs/attack-report.md for the full reasoning.
        # NOTE: now that a real database exists (see db.py), SQLi-looking
        # strings like "'; DROP TABLE orders; --" are STILL not blocked here
        # -- and that's still correct. The reason has shifted, though: it's no
        # longer "there's no database to exploit" (there is one now), it's
        # "every query in db.py is parameterized, so this string is never
        # interpreted as SQL syntax no matter what it contains." See
        # docs/sql-injection-demo.md for a live proof of exactly that.
        # Blocklisting would still be redundant security theater on top of
        # the real control (parameterized queries), and would still incorrectly
        # reject legitimate data like "O'Brien's Widget".
        if "\x00" in v:
            raise ValueError("must not contain null bytes")
        return v


class Order(BaseModel):
    id: str
    item: str
    quantity: int
    owner_id: str
    created_at: str


class Claims(BaseModel):
    sub: str
    scopes: list[str]


# ---------------------------------------------------------------------------
# HMAC signature + nonce + timestamp verification (TB-2, docs/threat-model.md).
# Runs as middleware -- BEFORE any route's JWT/scope dependency -- because a
# request that fails signature verification shouldn't even reach auth logic.
# mTLS (client cert) is enforced one layer below this, at the TLS handshake
# itself (see the __main__ block and Dockerfile), so a connection without a
# valid client cert never even reaches this middleware.
#
# NOTE ON ORDERING: this is registered FIRST (before assign_request_id below),
# which -- because Starlette runs @app.middleware("http") decorators in
# REVERSE registration order -- makes it the INNER middleware, running SECOND.
# assign_request_id, registered second, becomes the OUTER middleware and runs
# FIRST, so request.state.request_id is already set by the time this function
# runs. Getting this backwards (as an earlier version of this file did) means
# every log line in this function logs request_id="unknown" -- caught via a
# live test run during Week 7 development, not just theorized.
# ---------------------------------------------------------------------------
@app.middleware("http")
async def verify_request_signature(request: Request, call_next):
    if request.url.path == "/health":
        return await call_next(request)  # health checks aren't signed -- nothing to protect

    req_id = getattr(request.state, "request_id", "unknown")
    signature = request.headers.get("x-signature", "")
    timestamp = request.headers.get("x-timestamp", "")
    nonce = request.headers.get("x-nonce", "")

    if not (signature and timestamp and nonce):
        logger.warning("signature_denied", request_id=req_id, path=request.url.path, reason="missing_headers")
        return JSONResponse(status_code=401, content={"error": "unauthorized", "message": "Missing request signature."})

    raw_body = await request.body()  # Starlette caches this -- route handlers can still read it after
    body_str = raw_body.decode("utf-8") if raw_body else ""

    # IMPORTANT: must be the path EXACTLY as it arrived on the wire, plus the
    # raw query string -- the Gateway signs the request target as it puts it
    # on the wire (e.g. "/orders?owner_id=x", or "/orders/'%20OR%20'1'%3D'1").
    #
    # This has now bitten us twice, in the same way -- the signer and the
    # verifier must agree on EXACTLY which bytes were signed, and web
    # frameworks helpfully hand you a cleaned-up version by default:
    #   Week 4:    request.url.path drops the query string
    #   Sprint 10: request.url.path is percent-DECODED, but the Gateway
    #              signed the percent-ENCODED form (found when a SQL
    #              injection test id containing "' OR '1'='1" got a 401
    #              signature error instead of reaching the database)
    # scope["raw_path"] is the ASGI-standard "original bytes, unmodified,
    # excluding the query string", which is what was actually signed.
    raw_path = request.scope.get("raw_path")
    path_for_signing = raw_path.decode("latin-1") if raw_path else request.url.path
    if request.url.query:
        path_for_signing += f"?{request.url.query}"

    try:
        verify_signature(
            secret=_HMAC_SECRET,
            method=request.method,
            path=path_for_signing,
            body=body_str,
            timestamp=timestamp,
            nonce=nonce,
            provided_signature=signature,
        )
    except SignatureError as e:
        logger.warning("signature_denied", request_id=req_id, path=request.url.path, method=request.method, reason=e.reason)
        return JSONResponse(status_code=401, content={"error": "unauthorized", "message": "Invalid request signature."})

    # Signature is genuine -- NOW check nonce uniqueness (no point spending a
    # nonce-store write verifying a forged request first).
    is_new = nonce_store.check_and_reserve(nonce, ttl_seconds=NONCE_TTL_SECONDS)
    if not is_new:
        logger.warning("replay_blocked", request_id=req_id, path=request.url.path, nonce=nonce[:12] + "...")
        return JSONResponse(status_code=401, content={"error": "unauthorized", "message": "Request already processed (replay detected)."})

    logger.info("signature_verified", request_id=req_id, path=request.url.path, method=request.method)
    return await call_next(request)


# ---------------------------------------------------------------------------
# Request ID (correlation ID, NFR-7): assigned to every request so a single
# request's allow/deny decision can be traced across log lines. Registered
# SECOND (after verify_request_signature above) -- this makes it the OUTER
# middleware, running FIRST on the way in, so request.state.request_id is
# already set before verify_request_signature (and every route's auth
# dependency) ever reads it. See the ordering note on verify_request_signature.
# ---------------------------------------------------------------------------
@app.middleware("http")
async def assign_request_id(request: Request, call_next):
    request.state.request_id = str(uuid.uuid4())
    response = await call_next(request)
    response.headers["X-Request-Id"] = request.state.request_id
    return response


# ---------------------------------------------------------------------------
# Independent JWT verification -- this is TB-2 enforcement from the threat model.
# ---------------------------------------------------------------------------
def get_current_claims(request: Request) -> Claims:
    req_id = getattr(request.state, "request_id", "unknown")
    auth_header = request.headers.get("authorization", "")
    scheme, _, token = auth_header.partition(" ")

    if scheme != "Bearer" or not token:
        logger.warning("auth_denied", request_id=req_id, reason="missing_header")
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header.")

    try:
        payload = jwt.decode(
            token,
            _PUBLIC_KEY,
            algorithms=["RS256"],  # pinned -- never accept "none" or HS256 confusion
            issuer=ISSUER,
            audience=AUDIENCE,
        )
    except jwt.PyJWTError as e:
        # Deliberately generic to the CLIENT -- never reveal WHY verification
        # failed. We DO log the real reason server-side (exactly the kind of
        # detail a SOC dashboard/Grafana panel should show an operator).
        logger.warning("auth_denied", request_id=req_id, reason=type(e).__name__)
        raise HTTPException(status_code=401, detail="Invalid or expired token.")

    logger.info("auth_allowed", request_id=req_id, sub=payload["sub"])
    return Claims(sub=payload["sub"], scopes=payload.get("scopes", []))


def require_scope(scope: str):
    def _check(request: Request, claims: Claims = Depends(get_current_claims)) -> Claims:
        if scope not in claims.scopes:
            req_id = getattr(request.state, "request_id", "unknown")
            logger.warning("scope_denied", request_id=req_id, sub=claims.sub, required_scope=scope)
            raise HTTPException(status_code=403, detail=f"This action requires the '{scope}' scope.")
        return claims

    return _check


# ---------------------------------------------------------------------------
# Centralized error handling (unchanged from Week 2)
# ---------------------------------------------------------------------------
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    print(f"[resource-service] UNHANDLED ERROR on {request.method} {request.url.path}: {exc!r}")
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "message": "Something went wrong. Please try again."},
    )


@app.get("/health")
def health():
    return {"status": "ok", "service": "resource-service", "ts": datetime.now(timezone.utc).isoformat()}


@app.post("/orders", response_model=Order, status_code=201)
def create_order(payload: OrderCreate, claims: Claims = Depends(require_scope("orders:write"))):
    # Defense in depth: even though the Gateway sets owner_id = req.auth.sub,
    # this service double-checks it matches the INDEPENDENTLY verified token.
    # A forged or mismatched owner_id here means something upstream is broken
    # or bypassed -- fail closed rather than trust it.
    if payload.owner_id != claims.sub:
        raise HTTPException(status_code=403, detail="owner_id does not match authenticated subject.")

    return _db.create_order(payload.item, payload.quantity, payload.owner_id)


@app.get("/orders", response_model=list[Order])
def list_orders(owner_id: Optional[str] = None, claims: Claims = Depends(require_scope("orders:read"))):
    # BOLA fix: a non-admin can only ever list THEIR OWN orders, regardless of
    # what owner_id query param is passed. Admins may query any owner_id.
    if "admin" not in claims.scopes:
        owner_id = claims.sub

    return _db.list_orders(owner_id)


@app.get("/orders/{order_id}", response_model=Order)
def get_order(order_id: str, claims: Claims = Depends(require_scope("orders:read"))):
    order = _db.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # THE BOLA/IDOR fix (docs/threat-model.md section 5.2): a user can only
    # fetch an order they own, unless they hold the admin scope. Previously
    # (Week 2) this endpoint had no ownership check at all -- any authenticated
    # caller could read any order by guessing/enumerating IDs.
    if order["owner_id"] != claims.sub and "admin" not in claims.scopes:
        raise HTTPException(status_code=403, detail="You do not have access to this order.")

    return order


@app.delete("/orders/{order_id}", status_code=204)
def delete_order(order_id: str, claims: Claims = Depends(require_scope("orders:write"))):
    order = _db.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order["owner_id"] != claims.sub and "admin" not in claims.scopes:
        raise HTTPException(status_code=403, detail="You do not have access to this order.")

    _db.delete_order(order_id)
    return None


if __name__ == "__main__":
    # Local debugging only -- the Docker image's CMD (see Dockerfile) is authoritative.
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        ssl_keyfile="/certs/resource-service.key",
        ssl_certfile="/certs/resource-service.crt",
        ssl_ca_certs="/certs/ca.crt",
        ssl_cert_reqs=ssl.CERT_REQUIRED,  # mTLS: refuse any connection without a valid client cert
        ssl_version=ssl.PROTOCOL_TLS_SERVER,
    )
