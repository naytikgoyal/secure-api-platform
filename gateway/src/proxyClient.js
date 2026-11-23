// Outbound client from Gateway -> Resource Service.
//
// Key security point: this uses an https.Agent with `ca` set to OUR local CA
// certificate, so Node will only trust a Resource Service presenting a cert
// signed by that exact CA. This is real certificate validation, not
// `rejectUnauthorized: false` (which would silently defeat the entire point
// of TLS and is a common student-project mistake).
//
// Week 4 adds: client cert (mTLS) + HMAC signature headers on every call here.
// Week 5: the HMAC secret is no longer a local file -- it's injected via
// setHmacSecret() once, at startup, after being fetched from Vault. TLS certs
// (mTLS identity) remain local files; see docs/key-rotation-runbook.md for
// why that boundary exists.
import fs from "fs";
import https from "https";
import { signRequest } from "./sign.js";

const CERT_DIR = process.env.CERT_DIR || "/certs";
const RESOURCE_SERVICE_HOST = process.env.RESOURCE_SERVICE_HOST || "resource-service";
const RESOURCE_SERVICE_PORT = process.env.RESOURCE_SERVICE_PORT || "8000";

let hmacSecret = null;

export function setHmacSecret(secret) {
  hmacSecret = secret;
}

const agent = new https.Agent({
  ca: fs.readFileSync(`${CERT_DIR}/ca.crt`),
  // mTLS: present OUR OWN cert/key so the Resource Service can verify who's
  // calling, not just encrypt the channel. gateway.crt was issued with
  // extendedKeyUsage = serverAuth, clientAuth (see gen-certs.sh) specifically
  // so it can double as this client identity.
  key: fs.readFileSync(`${CERT_DIR}/gateway.key`),
  cert: fs.readFileSync(`${CERT_DIR}/gateway.crt`),
  // rejectUnauthorized defaults to true when `ca` is set -- this is intentional
  // and must NEVER be overridden to false, even "temporarily."
});

/**
 * Forward a JSON request to the Resource Service over mTLS, with the request
 * signed via HMAC (method+path+body+timestamp+nonce -- see docs/signing-scheme.md).
 * @param {"GET"|"POST"|"DELETE"} method
 * @param {string} path e.g. "/orders" or "/orders/abc-123"
 * @param {object|null} body
 * @param {string|null} bearerToken - forwarded as-is so the Resource Service can
 *        INDEPENDENTLY verify it (defense in depth, NFR-8) -- the Gateway's own
 *        requireAuth() check does not substitute for this.
 */
export function callResourceService(method, path, body = null, bearerToken = null) {
  return new Promise((resolve, reject) => {
    if (!hmacSecret) {
      return reject(Object.assign(new Error("HMAC secret not loaded yet"), { status: 503 }));
    }

    const payload = body ? JSON.stringify(body) : null;
    const bodyForSigning = payload || ""; // MUST match resource-service's body decoding exactly

    const { signature, timestamp, nonce } = signRequest(hmacSecret, method, path, bodyForSigning);

    const req = https.request(
      {
        hostname: RESOURCE_SERVICE_HOST,
        port: RESOURCE_SERVICE_PORT,
        path,
        method,
        agent,
        headers: {
          "Content-Type": "application/json",
          ...(bearerToken ? { Authorization: `Bearer ${bearerToken}` } : {}),
          ...(payload ? { "Content-Length": Buffer.byteLength(payload) } : {}),
          "X-Signature": signature,
          "X-Timestamp": timestamp,
          "X-Nonce": nonce,
        },
      },
      (res) => {
        let raw = "";
        res.on("data", (chunk) => (raw += chunk));
        res.on("end", () => {
          const status = res.statusCode;
          let parsed = null;
          try {
            parsed = raw ? JSON.parse(raw) : null;
          } catch {
            // Non-JSON response from upstream -- treat as an upstream failure.
            return reject(Object.assign(new Error("Invalid upstream response"), { status: 502 }));
          }
          resolve({ status, body: parsed });
        });
      }
    );

    req.on("error", (err) => {
      // Connection refused, cert validation failure, etc. -- surfaced as 502 Bad Gateway.
      reject(Object.assign(new Error(`Upstream request failed: ${err.message}`), { status: 502 }));
    });

    if (payload) req.write(payload);
    req.end();
  });
}
