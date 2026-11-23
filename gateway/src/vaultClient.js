// Fetches secrets from Vault's KV v2 HTTP API at startup. This replaces
// reading jwt-signing.pub and hmac-signing.key as local files (Weeks 3-4) --
// as of Week 5, those secrets exist ONLY in Vault (see infra/scripts/vault-init.sh,
// which shreds the local copies after pushing them here).
//
// Uses Node's built-in fetch (Node 20+) -- no extra HTTP client dependency needed.
//
// NOTE: this file is intentionally duplicated (not shared) with
// auth-server/src/vaultClient.js. Each service is independently deployable in
// this architecture, so a shared internal package would add build complexity
// disproportionate to ~20 lines of code. In a larger system this would likely
// become a published internal npm package.
const VAULT_ADDR = process.env.VAULT_ADDR || "http://vault:8200";
const VAULT_TOKEN = process.env.VAULT_TOKEN;

async function readSecret(path) {
  const res = await fetch(`${VAULT_ADDR}/v1/secret/data/${path}`, {
    headers: { "X-Vault-Token": VAULT_TOKEN },
  });

  if (!res.ok) {
    throw new Error(`Vault read failed for secret/${path}: HTTP ${res.status}`);
  }

  const json = await res.json();
  return json.data.data; // KV v2 wraps the actual fields under data.data
}

/**
 * Fetch everything the Gateway needs from Vault at startup.
 * @returns {Promise<{ jwtPublicKey: string, hmacSecret: string }>}
 */
export async function fetchSecrets() {
  if (!VAULT_TOKEN) {
    throw new Error("VAULT_TOKEN is not set -- cannot authenticate to Vault.");
  }

  const jwtSigning = await readSecret("jwt-signing");
  const hmacSigning = await readSecret("hmac-signing");

  return {
    jwtPublicKey: jwtSigning.public_key,
    hmacSecret: hmacSigning.key,
  };
}
