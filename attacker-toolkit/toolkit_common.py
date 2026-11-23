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
  VAULT_ADDR           default: http://localhost:8200 (only used to fetch keys, see load_secret)
  VAULT_TOKEN          a Vault token allowed to read secret/jwt-signing and secret/hmac-signing
  HMAC_KEY_OVERRIDE    the HMAC key itself, as an alternative to VAULT_TOKEN
  JWT_PUBLIC_KEY_OVERRIDE  the JWT public key (PEM), as an alternative to VAULT_TOKEN

Exit codes of every attack_*.py script: 0 = every check passed, 1 = at least one
attack succeeded or a check failed, 2 = nothing failed but at least one check could
not run (a SKIP: missing key, or the account is locked). A skipped check is never
reported as a pass.
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
    to catch, and the corresponding control needs fixing before shipping).
    SKIP means the check could not be run (for example a key it needs is not
    available). A skip is reported separately and never counts as a pass."""

    def __init__(self, name, passed, detail, skipped=False):
        self.name = name
        self.passed = passed and not skipped
        self.skipped = skipped
        self.detail = detail

    def __str__(self):
        if self.skipped:
            verdict = "SKIPPED (check could not run)"
        else:
            verdict = "PASS (attack blocked)" if self.passed else "FAIL (attack succeeded -- VULNERABILITY)"
        return f"[{verdict}] {self.name}\n    {self.detail}"


def exit_code_for(results):
    """0 = all passed, 1 = something failed, 2 = nothing failed but something was skipped."""
    if any(not r.passed and not r.skipped for r in results):
        return 1
    return 2 if any(r.skipped for r in results) else 0


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
    ran = [r for r in results if not r.skipped]
    passed = sum(1 for r in ran if r.passed)
    skipped = len(results) - len(ran)
    print("-" * 70)
    print(f"{passed}/{len(ran)} attacks blocked" + (f", {skipped} check(s) skipped" if skipped else ""))
    if passed < len(ran):
        print("*** ACTION REQUIRED: one or more attacks succeeded. See detail above. ***")
    print("=" * 70)
    return passed == len(ran) and not skipped


def load_secret(env_var, local_name, vault_path, vault_field):
    """Finds a key the attack scripts need to build a 'captured' request or a forged
    token. Order: an environment variable, a file in the certs directory (present
    only if vault-init.sh was run without its shred step), then Vault itself when
    VAULT_TOKEN is set -- the same position a real attacker who had obtained
    Vault access would be in. Returns (value, source) or (None, reason)."""
    import requests

    value = os.environ.get(env_var)
    if value:
        return value.strip(), f"environment variable {env_var}"
    path = CERT_DIR / local_name
    if path.exists():
        return path.read_text().strip(), f"file {local_name}"
    token = os.environ.get("VAULT_TOKEN")
    if token:
        addr = os.environ.get("VAULT_ADDR", "http://localhost:8200")
        try:
            resp = requests.get(f"{addr}/v1/secret/data/{vault_path}", headers={"X-Vault-Token": token}, timeout=10)
            resp.raise_for_status()
            return resp.json()["data"]["data"][vault_field].strip(), f"Vault secret/{vault_path}"
        except Exception as e:  # network, auth or missing-field problems all mean "cannot run"
            return None, f"Vault lookup failed ({e})"
    return None, f"not available: set VAULT_TOKEN, or {env_var}, or keep {local_name} in {CERT_DIR}"


LAST_LOGIN_STATUS = None  # HTTP status of the most recent failed login(), so callers can tell a lockout from a wrong password


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

        global LAST_LOGIN_STATUS
        LAST_LOGIN_STATUS = resp.status_code
        if resp.status_code == 423:
            print(f"   (login refused: account locked, HTTP 423 -- {resp.json().get('message', '')})")
            return None, None
        if resp.status_code == 429 and attempt < max_retries - 1:
            wait = int(resp.headers.get("Retry-After", 5))
            print(f"   (login rate-limited, waiting {wait}s before retry {attempt + 2}/{max_retries}...)")
            time.sleep(wait)
            continue

        return None, None

    return None, None


def login_or_skip(username, password, script_name):
    """Logs in, or ends the script with exit code 2 (SKIP) when the reason is the
    platform's own protection (lockout or rate limit) rather than a broken stack."""
    token, refresh = login(username, password)
    if token:
        return token
    if LAST_LOGIN_STATUS in (423, 429):
        print(f"SKIP: {script_name} could not log in as {username} (HTTP {LAST_LOGIN_STATUS}). The account is locked or rate-limited,")
        print("      probably by an earlier attack script. Restart the Auth Server or wait, then run this script again.")
        sys.exit(2)
    print(f"ERROR: could not log in as {username} -- is the stack running?")
    sys.exit(1)
