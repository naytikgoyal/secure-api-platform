"""
attacker-toolkit/attack_bruteforce.py

Threat being tested: docs/threat-model.md section 5.1 --
"Attacker brute-forces credentials to exhaust database connections" / guess
a password. Control under test: auth-server/src/middleware/rateLimiter.js
(10 requests/min per IP on /auth/login).

Also verifies the account-enumeration fix: wrong password vs. nonexistent
username must return an IDENTICAL error, or an attacker can use the
difference to build a list of valid usernames before even trying passwords.

Run: python3 attack_bruteforce.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from toolkit_common import AUTH_URL, CA_CERT, Result, print_header, print_summary

import requests

COMMON_PASSWORDS = [
    "password", "123456", "password123", "admin", "letmein",
    "qwerty", "welcome", "monkey", "dragon", "master",
    "naytik2023", "Password1!", "changeme",
]


def attack_enumeration():
    print("\n1. Account enumeration check: wrong password vs. nonexistent user")
    resp_wrong_pw = requests.post(
        f"{AUTH_URL}/auth/login", json={"username": "naytik", "password": "definitely-wrong"},
        verify=CA_CERT, timeout=10,
    )
    resp_no_user = requests.post(
        f"{AUTH_URL}/auth/login", json={"username": "no-such-user-xyz", "password": "whatever"},
        verify=CA_CERT, timeout=10,
    )
    same_status = resp_wrong_pw.status_code == resp_no_user.status_code
    same_body = resp_wrong_pw.json() == resp_no_user.json()
    print(f"   wrong password: HTTP {resp_wrong_pw.status_code} {resp_wrong_pw.json()}")
    print(f"   no such user:   HTTP {resp_no_user.status_code} {resp_no_user.json()}")

    return Result(
        "Wrong password and nonexistent user return identical responses (no enumeration)",
        same_status and same_body,
        f"status match={same_status}, body match={same_body}",
    )


def attack_bruteforce_login():
    print(f"\n2. Brute-forcing 'naytik' with {len(COMMON_PASSWORDS)} common passwords, rapid-fire")
    statuses = []
    first_429_at = None

    for i, pw in enumerate(COMMON_PASSWORDS, start=1):
        resp = requests.post(
            f"{AUTH_URL}/auth/login", json={"username": "naytik", "password": pw},
            verify=CA_CERT, timeout=10,
        )
        statuses.append(resp.status_code)
        marker = " <-- BLOCKED" if resp.status_code == 429 else ""
        print(f"   attempt {i:2d} (password={pw!r}): HTTP {resp.status_code}{marker}")
        if resp.status_code == 429 and first_429_at is None:
            first_429_at = i

    got_rate_limited = first_429_at is not None
    return Result(
        "Rapid-fire login attempts trigger rate limiting before exhausting the password list",
        got_rate_limited,
        f"First 429 at attempt #{first_429_at}" if got_rate_limited else "Never rate-limited across all attempts -- VULNERABLE to unlimited guessing",
    )


def main():
    print_header("attack_bruteforce.py -- Credential brute-forcing + enumeration")

    results = [attack_enumeration()]

    print("\n   (waiting 2s to avoid cross-contaminating with the enumeration check above)")
    time.sleep(2)

    results.append(attack_bruteforce_login())

    ok = print_summary(results)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
