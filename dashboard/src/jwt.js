// Decodes a JWT's payload WITHOUT verifying its signature. This is safe and
// normal to do client-side, for one specific reason: we are not trusting
// this data for any security decision. The Gateway and Resource Service
// independently re-verify the token's signature on every single request
// (see gateway/src/middleware/auth.js and resource-service/main.py) -- that
// is the ONLY place a scope check actually matters for security.
//
// Here, we only use the decoded scopes to decide what UI to SHOW (e.g. hide
// the "Create Order" button for a read-only user). If someone tampered with
// their own token to fake an extra scope and trick this code into showing
// a button, clicking it would still hit the real backend, which would
// independently verify the (still-invalid) signature and reject the request
// with a real 401/403. Client-side UI logic is a convenience, never a
// security boundary -- see docs/threat-model.md's "defense in depth" framing.
export function decodeJwtPayload(token) {
  try {
    const payloadB64 = token.split(".")[1];
    const json = atob(payloadB64.replace(/-/g, "+").replace(/_/g, "/"));
    return JSON.parse(json);
  } catch {
    return null;
  }
}
