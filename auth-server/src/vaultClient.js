// Fetches the JWT PRIVATE signing key from Vault at startup. This is the only
// service that ever holds the private key -- see docs/signing-scheme.md and
// docs/threat-model.md for why that matters (Gateway/Resource Service only
// ever get the public key, from their own vaultClient.js).
//
// NOTE: intentionally duplicated from gateway/src/vaultClient.js -- see that
// file's comment for why (independent deployability of each service).
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
  return json.data.data;
}

/**
 * @returns {Promise<{ jwtPrivateKey: string }>}
 */
export async function fetchSecrets() {
  if (!VAULT_TOKEN) {
    throw new Error("VAULT_TOKEN is not set -- cannot authenticate to Vault.");
  }

  const jwtSigning = await readSecret("jwt-signing");
  return { jwtPrivateKey: jwtSigning.private_key };
}
