"""
attacker-toolkit/attack_token_forgery.py

Threats being tested: docs/threat-model.md section 4 (Spoofing) and the JWT
verification hardening in gateway/src/middleware/auth.js and
resource-service/main.py's get_current_claims().

Three forgery techniques, all classic real-world JWT attacks:
  1. Wrong-key forgery: attacker signs their own token with a self-generated
     RSA keypair (they don't have the real private key -- nobody outside
     auth-server does, per docs/signing-scheme.md's key topology).
  2. "alg: none" attack: a JWT with an unsigned header claiming no signature
     algorithm is required. Historically a real vulnerability in JWT libraries
     that didn't pin the expected algorithm.
  3. Algorithm confusion (RS256 -> HS256): attacker takes the known PUBLIC
     key and tries to use it as an HMAC secret to sign a token with HS256,
     hoping a naive verifier will accept any algorithm.

Run: python3 attack_token_forgery.py
"""
import base64
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from toolkit_common import exit_code_for, load_secret, CA_CERT, GATEWAY_URL, Result, print_header, print_summary

import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def try_request(token, label):
    resp = requests.get(
        f"{GATEWAY_URL}/orders",
        headers={"Authorization": f"Bearer {token}"},
        verify=CA_CERT,
        timeout=10,
    )
    print(f"   -> HTTP {resp.status_code}: {resp.text[:150]}")
    return resp.status_code


def attack_wrong_key_forgery():
    print("\n1. Wrong-key forgery: sign a token with an attacker-generated RSA key")
    attacker_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    header = {"alg": "RS256", "typ": "JWT"}
    payload = {
        "sub": "user-admin",  # attacker claims to be admin
        "scopes": ["orders:read", "orders:write", "admin"],
        "iss": "secure-api-platform-auth",
        "aud": "secure-api-platform",
        "iat": 9999999999,
        "exp": 9999999999,
    }
    signing_input = f"{b64url(json.dumps(header).encode())}.{b64url(json.dumps(payload).encode())}".encode()
    signature = attacker_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    forged_token = f"{signing_input.decode()}.{b64url(signature)}"

    status = try_request(forged_token, "wrong-key forgery")
    return Result(
        "Wrong-key forgery (attacker's own RSA keypair) is rejected",
        status == 401,
        f"HTTP {status} -- token claimed admin scope, signed with a key the server never trusted",
    )


def attack_alg_none():
    print("\n2. 'alg: none' attack: unsigned token claiming no signature is required")
    header = {"alg": "none", "typ": "JWT"}
    payload = {
        "sub": "user-admin",
        "scopes": ["admin"],
        "iss": "secure-api-platform-auth",
        "aud": "secure-api-platform",
        "iat": 9999999999,
        "exp": 9999999999,
    }
    forged_token = f"{b64url(json.dumps(header).encode())}.{b64url(json.dumps(payload).encode())}."  # empty signature

    status = try_request(forged_token, "alg=none")
    return Result(
        "'alg: none' token is rejected (algorithm is pinned server-side)",
        status == 401,
        f"HTTP {status} -- gateway pins algorithms=['RS256'] in jwt.verify(), so 'none' is never accepted",
    )


def attack_algorithm_confusion(public_key_pem: bytes):
    print("\n3. Algorithm confusion: use the KNOWN PUBLIC key as an HMAC secret (RS256 -> HS256)")
    import hmac
    import hashlib

    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": "user-admin",
        "scopes": ["admin"],
        "iss": "secure-api-platform-auth",
        "aud": "secure-api-platform",
        "iat": 9999999999,
        "exp": 9999999999,
    }
    signing_input = f"{b64url(json.dumps(header).encode())}.{b64url(json.dumps(payload).encode())}".encode()
    # The classic version of this attack: if a verifier is naive about which
    # algorithm to expect, it might use the RS256 PUBLIC key (which is not
    # secret -- Gateway and Resource Service both have it, and it's meant to
    # be shared) as the HMAC key for an HS256 signature, since a symmetric
    # verify() call can't tell the difference between "the real secret" and
    # "a public key being misused as a secret."
    mac = hmac.new(public_key_pem, signing_input, hashlib.sha256).digest()
    forged_token = f"{signing_input.decode()}.{b64url(mac)}"

    status = try_request(forged_token, "algorithm confusion")
    return Result(
        "Algorithm confusion (public key used as HMAC secret) is rejected",
        status == 401,
        f"HTTP {status} -- gateway pins algorithms=['RS256'], so an HS256-signed token is never even attempted against the public key as an HMAC secret",
    )


def main():
    print_header("attack_token_forgery.py -- JWT forgery techniques")

    pub_pem, source = load_secret("JWT_PUBLIC_KEY_OVERRIDE", "jwt-signing.pub", "jwt-signing", "public_key")
    results = [attack_wrong_key_forgery(), attack_alg_none()]
    if pub_pem:
        print(f"(public key obtained from {source})")
        results.append(attack_algorithm_confusion(pub_pem.encode()))
    else:
        # The public key is not secret, but the attack needs it to build the payload.
        results.append(Result("Algorithm confusion (public key used as HMAC secret) is rejected", False, f"could not run: {source}", skipped=True))

    print_summary(results)
    sys.exit(exit_code_for(results))


if __name__ == "__main__":
    main()
