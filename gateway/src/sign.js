// HMAC request signing -- see docs/signing-scheme.md for the exact canonical
// string format. resource-service/signing.py implements the verification side
// using the IDENTICAL format; if these two ever drift, requests fail closed
// (rejected), not open.
import crypto from "crypto";

/**
 * @returns {{ signature: string, timestamp: string, nonce: string }}
 */
export function signRequest(secret, method, path, bodyString) {
  const timestamp = Math.floor(Date.now() / 1000).toString();
  const nonce = crypto.randomBytes(16).toString("hex"); // 128 bits -- collision-infeasible

  const canonical = `${method.toUpperCase()}\n${path}\n${bodyString}\n${timestamp}\n${nonce}`;
  const signature = crypto.createHmac("sha256", secret).update(canonical).digest("hex");

  return { signature, timestamp, nonce };
}
