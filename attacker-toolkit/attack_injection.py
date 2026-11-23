"""
attacker-toolkit/attack_injection.py

Threat being tested: docs/threat-model.md NFR-6 (input validation).

IMPORTANT DESIGN NOTE -- read this before "fixing" a failure here:

This script deliberately does NOT expect every attack-looking payload to be
REJECTED. Two categories of payload are tested, with different correct
outcomes:

  1. STRUCTURAL violations (wrong type, oversized, negative, malformed JSON)
     -- these MUST be rejected (400/422). They violate the schema itself,
     regardless of content.

  2. CONTENT patterns that only matter in a specific execution context
     (SQLi-looking strings, XSS-looking strings, path traversal, format
     strings) -- these are EXPECTED TO BE ACCEPTED as opaque string data by
     this API, and that is CORRECT, not a bug. This service builds no SQL
     queries (in-memory store, no DB) and renders no HTML (no templating
     engine touches this data). Blocklisting "<script>" or "DROP TABLE" at
     the input layer is a well-known anti-pattern: it's trivially bypassed
     (different casing/encoding/whitespace), and it breaks legitimate data
     (a product genuinely named "O'Brien's Widget"). The real defenses are
     parameterized queries (when a DB is added) and output encoding (when a
     renderer is added) -- see docs/attack-report.md for the full reasoning
     and docs/threat-model.md's residual risk section, which flags this as
     something to revisit when either of those is added.

  3. Null bytes ARE rejected (see resource-service/main.py's
     reject_null_bytes validator) -- this is the one narrow, content-based
     rule in the codebase, justified because null bytes have no legitimate
     use in a text field and are a known source of real bugs in downstream
     C-string-based systems, independent of SQL/HTML context.

This split is the point of the test: naive "does it 400" checking on every
payload would have pushed toward adding a blocklist, which is a worse fix
than no fix at all.

SPRINT 10 UPDATE -- a real database now exists (PostgreSQL, see
resource-service/db.py), so the "content patterns are inert" claims above are
no longer just "there's nothing to inject into." They're now verified against
a real SQL engine: the last section of this script attacks the three places
user input actually reaches a SQL query (the item field on INSERT, the order
id in the URL path, and the admin ?owner_id= filter) and confirms parameterized
queries hold in each. The reasoning for NOT blocklisting is unchanged -- the
reason it holds has shifted from "no database" to "every query is parameterized."

Run: python3 attack_injection.py
"""
import sys
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).parent))
from toolkit_common import CA_CERT, GATEWAY_URL, Result, exit_code_for, login, login_or_skip, print_header, print_summary

import requests

# (label, payload, expected_outcome) where expected_outcome is "rejected" or "inert"
STRUCTURAL_PAYLOADS = [
    ("NoSQL injection operator ($gt) sent as item value", {"$gt": ""}, "rejected"),
    ("NoSQL injection operator ($ne) sent as item value", {"$ne": None}, "rejected"),
    ("Oversized string (10000 chars)", "A" * 10000, "rejected"),
]

CONTENT_PAYLOADS = [
    ("SQLi-looking string (classic)", "'; DROP TABLE orders; --", "inert"),
    ("SQLi-looking string (union)", "' UNION SELECT * FROM users --", "inert"),
    ("XSS-looking string (script tag)", "<script>alert('xss')</script>", "inert"),
    ("XSS-looking string (img onerror)", "<img src=x onerror=alert(1)>", "inert"),
    ("Path traversal-looking string", "../../../../etc/passwd", "inert"),
    ("Format string", "%s%s%s%s%s%s%s%s", "inert"),
]

NULL_BYTE_PAYLOAD = ("Null byte injection", "item\x00.txt", "rejected")


def try_create_order(token, item_value):
    try:
        resp = requests.post(
            f"{GATEWAY_URL}/orders",
            json={"item": item_value, "quantity": 1},
            headers={"Authorization": f"Bearer {token}"},
            verify=CA_CERT,
            timeout=10,
        )
    except requests.exceptions.RequestException as e:
        return None, str(e)
    return resp.status_code, resp.text[:250]


def main():
    print_header("attack_injection.py -- Structural validation + content-pattern handling")

    access_token = login_or_skip("naytik", "password123", "attack_injection.py")

    results = []

    print("\n--- STRUCTURAL violations (must be rejected, 400/422) ---")
    for label, payload, expected in STRUCTURAL_PAYLOADS:
        status, body = try_create_order(access_token, payload)
        print(f"\n{label}\n   -> HTTP {status}: {body}")
        results.append(Result(f"{label} is rejected (structural violation)", status in (400, 422), f"HTTP {status}"))

    print("\n--- CONTENT patterns (correctly accepted as opaque data -- see script docstring) ---")
    for label, payload, expected in CONTENT_PAYLOADS:
        status, body = try_create_order(access_token, payload)
        print(f"\n{label}\n   -> HTTP {status}: {body}")
        # Correct outcome: 201 (accepted) AND the value comes back byte-for-byte
        # identical -- proving it was stored as inert data, not interpreted,
        # transformed, or (worse) silently mangled in a way that could itself
        # be a bug.
        stored_correctly = status == 201 and payload in body
        results.append(
            Result(
                f"{label} is correctly accepted as inert string data (not executed, stored verbatim)",
                stored_correctly,
                f"HTTP {status} -- {'stored verbatim as expected' if stored_correctly else 'unexpected handling, investigate'}",
            )
        )

    print("\n--- Null byte (the one legitimate content-based rejection rule) ---")
    label, payload, _ = NULL_BYTE_PAYLOAD
    status, body = try_create_order(access_token, payload)
    print(f"\n{label}\n   -> HTTP {status}: {body}")
    results.append(Result(f"{label} is rejected", status == 422, f"HTTP {status}"))

    print("\n--- Other structural checks ---")
    resp = requests.post(
        f"{GATEWAY_URL}/orders", json={"item": "Legit Item", "quantity": -999},
        headers={"Authorization": f"Bearer {access_token}"}, verify=CA_CERT, timeout=10,
    )
    print(f"\nNegative quantity\n   -> HTTP {resp.status_code}: {resp.text[:150]}")
    results.append(Result("Negative quantity is rejected (ge=1 constraint)", resp.status_code == 422, f"HTTP {resp.status_code}"))

    resp = requests.post(
        f"{GATEWAY_URL}/orders", data="{not valid json!!!",
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        verify=CA_CERT, timeout=10,
    )
    print(f"\nMalformed JSON body\n   -> HTTP {resp.status_code}: {resp.text[:150]}")
    results.append(Result("Malformed JSON body is rejected cleanly, not a 500", resp.status_code != 500, f"HTTP {resp.status_code}"))

    # ------------------------------------------------------------------
    # Sprint 10: database-layer checks. Each targets a place where user
    # input genuinely reaches a SQL query in resource-service/db.py.
    # ------------------------------------------------------------------
    print("\n--- DATABASE LAYER (Sprint 10): does user input ever become SQL? ---")
    auth = {"Authorization": f"Bearer {access_token}"}

    # Baseline: naytik's orders BEFORE the attacks below, so we can prove
    # nothing was deleted or altered afterward. (The content-pattern section
    # above already stored several orders, including a DROP TABLE payload.)
    before = requests.get(f"{GATEWAY_URL}/orders", headers=auth, verify=CA_CERT, timeout=10)
    before_count = len(before.json()) if before.status_code == 200 else -1
    print(f"\nBaseline: naytik has {before_count} order(s) stored")

    # (a) SQL injection through the URL path -- the id goes into WHERE id = %s
    injected_ids = ["' OR '1'='1", "'; DROP TABLE orders; --", "1; DELETE FROM orders"]
    for bad_id in injected_ids:
        url = f"{GATEWAY_URL}/orders/{quote(bad_id, safe='')}"
        resp = requests.get(url, headers=auth, verify=CA_CERT, timeout=10)
        print(f"\nGET  /orders/<{bad_id!r}>\n   -> HTTP {resp.status_code}: {resp.text[:100]}")
        results.append(Result(
            f"Path-parameter injection {bad_id!r} returns a clean 404 (reaches the DB layer, matches nothing)",
            resp.status_code == 404,
            f"HTTP {resp.status_code} (401 would mean the request was stopped by signature verification "
            f"instead of the layer under test -- that exact mismatch was a real bug found in Sprint 10)",
        ))

    resp = requests.delete(f"{GATEWAY_URL}/orders/{quote(chr(39) + ' OR ' + chr(39) + '1' + chr(39) + '=' + chr(39) + '1', safe='')}",
                           headers=auth, verify=CA_CERT, timeout=10)
    print(f"\nDELETE /orders/<' OR '1'='1>\n   -> HTTP {resp.status_code}: {resp.text[:100]}")
    results.append(Result("DELETE with an injected id deletes nothing (404)", resp.status_code == 404, f"HTTP {resp.status_code}"))

    # (b) SQL injection through the admin ?owner_id= filter -- the classic
    # "give me everyone's rows" attack. Needs an admin token because
    # non-admins are stopped at the Gateway before this parameter is used.
    admin_token, _ = login("admin", "adminpass456")
    if not admin_token:
        print("\n(Could not log in as admin -- skipping the owner_id injection check.)")
    else:
        admin_auth = {"Authorization": f"Bearer {admin_token}"}
        control = requests.get(f"{GATEWAY_URL}/orders?owner_id=user-naytik", headers=admin_auth, verify=CA_CERT, timeout=10)
        control_rows = control.json() if control.status_code == 200 else []
        print(f"\nPositive control: admin filtering owner_id=user-naytik -> {len(control_rows)} row(s)")

        attack = requests.get(
            f"{GATEWAY_URL}/orders?owner_id={quote(chr(39) + ' OR ' + chr(39) + '1' + chr(39) + '=' + chr(39) + '1', safe='')}",
            headers=admin_auth, verify=CA_CERT, timeout=10,
        )
        attack_rows = attack.json() if attack.status_code == 200 else None
        print(f"Attack: owner_id=' OR '1'='1 -> HTTP {attack.status_code}, {len(attack_rows) if attack_rows is not None else '?'} row(s)")
        results.append(Result(
            "Admin owner_id=' OR '1'='1 returns NO rows (treated as a literal owner name, not SQL)",
            attack.status_code == 200 and attack_rows == [] and len(control_rows) > 0,
            f"control returned {len(control_rows)} row(s) (proves the table isn't just empty); "
            f"attack returned {len(attack_rows) if attack_rows is not None else 'error'}",
        ))

    # (c) After ALL of the above -- including three DROP/DELETE payloads --
    # is every order still there? This is the check that would catch a
    # payload that quietly executed.
    after = requests.get(f"{GATEWAY_URL}/orders", headers=auth, verify=CA_CERT, timeout=10)
    after_count = len(after.json()) if after.status_code == 200 else -2
    print(f"\nAfter attacks: naytik has {after_count} order(s) stored (was {before_count})")
    results.append(Result(
        "No order was deleted or altered by any injection attempt (table + rows intact)",
        after.status_code == 200 and after_count == before_count and before_count > 0,
        f"before={before_count}, after={after_count}",
    ))

    print_summary(results)
    sys.exit(exit_code_for(results))


if __name__ == "__main__":
    main()
