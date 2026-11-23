"""
attacker-toolkit/toolkit_common.py

Shared config and helpers for every attack_*.py script. Run each script
individually, or all of them via run_all.py.

Prerequisites: the full stack must be running (docker compose up, or the
local dev setup in the main README) with certs generated via
infra/scripts/gen-certs.sh.

Environment variables (all optional, sensible localhost defaults):
  GATEWAY_URL          default: https://localhost:3000
  AUTH_URL             default: https://localhost:4000
  RESOURCE_URL         default: https://localhost:8000
  CERT_DIR             default: ../infra/certs (relative to this file)
"""
import os
import sys
import time
from pathlib import Path

TOOLKIT_DIR = Path(__file__).parent
DEFAULT_CERT_DIR = TOOLKIT_DIR.parent / "infra" / "certs"

CERT_DIR = Path(os.environ.get("CERT_DIR", str(DEFAULT_CERT_DIR)))
GATEWAY_URL = os.environ.get("GATEWAY_URL", "https://localhost:3000")
AUTH_URL = os.environ.get("AUTH_URL", "https://localhost:4000")
RESOURCE_URL = os.environ.get("RESOURCE_URL", "https://localhost:8000")

CA_CERT = str(CERT_DIR / "ca.crt")
GATEWAY_CLIENT_CERT = str(CERT_DIR / "gateway.crt")
GATEWAY_CLIENT_KEY = str(CERT_DIR / "gateway.key")


def _check_certs_exist():
    missing = [p for p in [CA_CERT, GATEWAY_CLIENT_CERT, GATEWAY_CLIENT_KEY] if not Path(p).exists()]
    if missing:
        print(f"ERROR: missing cert files: {missing}")
        print(f"Run infra/scripts/gen-certs.sh first, or set CERT_DIR to point at your certs.")
        sys.exit(1)


class Result:
    """A single test's outcome. PASS means the ATTACK WAS BLOCKED (defense worked).
    FAIL means the attack SUCCEEDED (a real vulnerability -- this should never
    happen on a clean run; if it does, that's exactly what this toolkit exists
    to catch, and the corresponding control needs fixing before shipping)."""

    def __init__(self, name, passed, detail):
        self.name = name
        self.passed = passed
        self.detail = detail

    def __str__(self):
        verdict = "PASS (attack blocked)" if self.passed else "FAIL (attack succeeded -- VULNERABILITY)"
        return f"[{verdict}] {self.name}\n    {self.detail}"


def print_header(script_name):
    _check_certs_exist()
    print("=" * 70)
    print(f"  {script_name}")
    print(f"  Target: {GATEWAY_URL}")
    print(f"  Time:   {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)


def print_summary(results):
    print("\n" + "-" * 70)
    print("SUMMARY")
    print("-" * 70)
    for r in results:
        print(r)
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    print("-" * 70)
    print(f"{passed}/{total} attacks blocked")
    if passed < total:
        print("*** ACTION REQUIRED: one or more attacks succeeded. See detail above. ***")
    print("=" * 70)
    return passed == total


def login(username, password, max_retries=3):
    """Returns (access_token, refresh_token) or (None, None) on failure.

    Retries on 429 with backoff, respecting Retry-After when present. This
    isn't just politeness -- during toolkit development, running
    attack_bruteforce.py immediately before another script that also needs to
    log in caused a real, reproducible failure: the brute-force script's own
    flood left the per-IP rate limiter on /auth/login still active, so the
    NEXT script's legitimate login got a 429 too. That's the rate limiter
    correctly doing its job -- but a toolkit that can't tell the difference
    between "blocked because I'm the attacker" and "blocked because a sibling
    script just got blocked two seconds ago" isn't very useful. Real clients
    (and this toolkit) should back off and retry, not treat 429 as fatal.
    """
    import requests

    for attempt in range(max_retries):
        resp = requests.post(
            f"{AUTH_URL}/auth/login",
            json={"username": username, "password": password},
            verify=CA_CERT,
            timeout=10,
        )
        if resp.status_code == 200:
            body = resp.json()
            return body["access_token"], body["refresh_token"]

        if resp.status_code == 429 and attempt < max_retries - 1:
            wait = int(resp.headers.get("Retry-After", 5))
            print(f"   (login rate-limited, waiting {wait}s before retry {attempt + 2}/{max_retries}...)")
            time.sleep(wait)
            continue

        return None, None

    return None, None
