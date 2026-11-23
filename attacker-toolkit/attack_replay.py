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

from toolkit_common import CA_CERT, GATEWAY_CLIENT_CERT, GATEWAY_CLIENT_KEY, RESOURCE_URL, Result, exit_code_for, load_secret, login_or_skip, print_header, print_summary

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

    # A "captured" request that passes signature verification needs the real HMAC
    # secret -- the "leaked secret" worst case described above. load_secret()
    # looks in the environment, then the certs folder, then Vault itself when
    # VAULT_TOKEN is set (an attacker who had obtained Vault access). If none is
    # available the check is reported as SKIPPED, never as a pass.
    secret, source = load_secret("HMAC_KEY_OVERRIDE", "hmac-signing.key", "hmac-signing", "key")
    if not secret:
        print(f"NOTE: the HMAC key is {source}")
        print_summary([Result("Replay of a captured signed request is rejected", False, f"could not run: {source}", skipped=True)])
        sys.exit(2)
    print(f"(HMAC key obtained from {source})")

    access_token = login_or_skip("naytik", "password123", "attack_replay.py")

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
            status2 == 401 and "replay" in body2.lower(),  # a 401 for any OTHER reason (bad token, bad signature) must not count
            f"HTTP {status2}: {body2[:150]}",
        ),
    ]

    print_summary(results)
    sys.exit(exit_code_for(results))


if __name__ == "__main__":
    main()
