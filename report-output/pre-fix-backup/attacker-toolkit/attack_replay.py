"""
attacker-toolkit/attack_replay.py

Threat being tested: docs/threat-model.md section 5.3 (Spoofing/Replay) --
"Attacker captures a valid order-creation request and resends it N times."

ATTACKER MODEL / ASSUMPTION: this script assumes a worst-case position --
the attacker holds a copy of a legitimately-signed Gateway->Resource Service
request (e.g. via a compromised log, a misconfigured debug proxy, or a prior
network capture) AND the Gateway's mTLS client certificate. This is a
deliberately pessimistic assumption: even if BOTH of those leaked, nonce-based
replay protection should still hold. That's what this script proves.

Run: python3 attack_replay.py
"""
import http.client
import secrets
import ssl
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "resource-service"))

from toolkit_common import CA_CERT, GATEWAY_CLIENT_CERT, GATEWAY_CLIENT_KEY, RESOURCE_URL, Result, login, print_header, print_summary

try:
    from signing import build_canonical_string, compute_signature
except ImportError:
    print("ERROR: could not import resource-service/signing.py. Run this from the repo with")
    print("the resource-service directory intact.")
    sys.exit(1)


def _parse_host_port(url):
    url = url.replace("https://", "")
    host, _, port = url.partition(":")
    return host, int(port) if port else 8000


def send_direct_to_resource_service(method, path, headers, body=None):
    """Bypasses the Gateway entirely -- talks straight to the Resource Service
    using the Gateway's mTLS identity, exactly as an attacker holding that
    identity would."""
    host, port = _parse_host_port(RESOURCE_URL)
    ctx = ssl.create_default_context(cafile=CA_CERT)
    ctx.load_cert_chain(GATEWAY_CLIENT_CERT, GATEWAY_CLIENT_KEY)
    conn = http.client.HTTPSConnection(host, port, context=ctx, timeout=10)
    conn.request(method, path, body=body, headers=headers)
    resp = conn.getresponse()
    return resp.status, resp.read().decode()


def main():
    print_header("attack_replay.py -- Replay a captured, validly-signed request")

    # We need a real, currently-valid HMAC secret to construct a "captured"
    # request that would actually pass signature verification -- this script
    # can only run meaningfully with access to it (the "leaked secret" worst
    # case described above). Read it the same way the toolkit operator would
    # need to have obtained it in a real compromise: from the local certs dir,
    # which in THIS demo is populated by infra/scripts/vault-init.sh before it
    # shreds the local copy. If it's already been shredded (Week 5+), this
    # script documents that it can't run without simulating deeper compromise.
    hmac_key_path = Path(__file__).parent.parent / "infra" / "certs" / "hmac-signing.key"
    if not hmac_key_path.exists():
        print("NOTE: hmac-signing.key is not present locally (expected after Week 5's")
        print("vault-init.sh shreds it). This script demonstrates the replay attack")
        print("using a copy of the key obtained the same way a real attacker who'd")
        print("compromised Vault access would -- for this demo, set HMAC_KEY_OVERRIDE")
        print("or re-run vault-init.sh's push step without the shred step to test this.")
        sys.exit(1)

    secret = hmac_key_path.read_text().strip()

    access_token, _ = login("naytik", "password123")
    if not access_token:
        print("ERROR: could not log in as naytik -- is the stack running?")
        sys.exit(1)

    method, path, body = "GET", "/orders", ""
    timestamp = str(int(time.time()))
    nonce = secrets.token_hex(16)
    signature = compute_signature(secret, build_canonical_string(method, path, body, timestamp, nonce))

    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Signature": signature,
        "X-Timestamp": timestamp,
        "X-Nonce": nonce,
    }

    print(f"\n1. Sending ORIGINAL request (fresh nonce {nonce[:12]}...)")
    status1, body1 = send_direct_to_resource_service(method, path, headers)
    print(f"   -> HTTP {status1}")

    print(f"\n2. IMMEDIATELY replaying the IDENTICAL request (same signature, same nonce)")
    status2, body2 = send_direct_to_resource_service(method, path, headers)
    print(f"   -> HTTP {status2}: {body2[:150]}")

    results = [
        Result(
            "Original request succeeds (sanity check -- proves the signature itself was valid)",
            status1 == 200,
            f"HTTP {status1}",
        ),
        Result(
            "Immediate replay of identical signed request is rejected",
            status2 == 401 and "replay" in body2.lower() or status2 == 401,
            f"HTTP {status2}: {body2[:150]}",
        ),
    ]

    ok = print_summary(results)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
