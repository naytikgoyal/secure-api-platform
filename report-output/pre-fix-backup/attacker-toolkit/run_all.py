"""
attacker-toolkit/run_all.py

Runs every attack_*.py script in sequence against the live stack, prints a
combined pass/fail summary, AND (Sprint 9) posts the full results to the
Gateway's /admin/attack-report endpoint so they're visible in the Security
Dashboard's "Attack History" panel, not just in your terminal scrollback.

Posting the report requires logging in as admin -- if that login fails (e.g.
you changed the demo password, or the stack isn't fully up), the local
terminal summary below still prints normally; only the dashboard panel won't
have anything new to show. This script never fails BECAUSE the report post
failed -- that would be a strange way for an attack-testing tool to behave.

Individual scripts can still be run standalone for focused debugging.

Run: python3 run_all.py
"""
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from toolkit_common import GATEWAY_URL, login

SCRIPTS = [
    "attack_replay.py",
    "attack_token_forgery.py",
    "attack_bruteforce.py",  # deliberately BEFORE injection/mitm -- see note below
    "attack_injection.py",
    "attack_mitm_downgrade.py",
]

# Same demo credentials used throughout this toolkit and documented in
# auth-server/src/users.js -- consistent with how attack_bruteforce.py etc.
# already reference naytik/rishi's known passwords directly.
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "adminpass456"


def run_script(toolkit_dir, script):
    """Runs one attack script, streaming its output live to the terminal
    (unchanged behavior) while ALSO capturing it, so we have something to
    show in the dashboard afterward -- not just an exit code."""
    proc = subprocess.Popen(
        [sys.executable, str(toolkit_dir / script)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    captured_lines = []
    for line in proc.stdout:
        print(line, end="")  # live streaming -- exactly like before
        captured_lines.append(line)
    proc.wait()
    return proc.returncode == 0, "".join(captured_lines)


def post_report_to_dashboard(results):
    """Best-effort: logs in as admin and POSTs the report. Never raises --
    a failure here should never make the attack toolkit itself report failure."""
    try:
        admin_token, _ = login(ADMIN_USERNAME, ADMIN_PASSWORD)
        if not admin_token:
            print("\n(Could not log in as admin -- skipping dashboard report upload.)")
            return

        import requests

        from toolkit_common import CA_CERT

        report = {
            "ran_at": datetime.now(timezone.utc).isoformat(),
            "scripts": [
                {"name": name, "passed": passed, "output_tail": output[-4000:]}
                for name, passed, output in results
            ],
            "all_passed": all(passed for _, passed, _ in results),
        }

        resp = requests.post(
            f"{GATEWAY_URL}/admin/attack-report",
            json=report,
            headers={"Authorization": f"Bearer {admin_token}"},
            verify=CA_CERT,
            timeout=10,
        )
        if resp.status_code == 200:
            print("\nReport uploaded to the Security Dashboard's Attack History panel.")
        else:
            print(f"\n(Report upload got HTTP {resp.status_code} -- dashboard panel won't update this run.)")
    except Exception as e:
        print(f"\n(Report upload failed: {e} -- dashboard panel won't update this run. Terminal results above are still accurate.)")


def main():
    toolkit_dir = Path(__file__).parent
    results = []  # list of (script_name, passed, captured_output)

    for script in SCRIPTS:
        print("\n" + "#" * 70)
        print(f"# Running {script}")
        print("#" * 70)
        passed, output = run_script(toolkit_dir, script)
        results.append((script, passed, output))

        if script == "attack_bruteforce.py":
            # attack_bruteforce.py deliberately trips the /auth/login rate
            # limiter as its whole point. Any script running immediately
            # after it also needs to log in -- without a pause here, that
            # next login would ALSO get 429'd, not because it's under attack
            # but because of leftover state from the previous script. login()
            # in toolkit_common.py now retries with backoff to handle this
            # gracefully regardless, but pausing here avoids relying on that
            # retry logic every single run. See docs/attack-report.md for
            # the real run where this was caught.
            print("\n(pausing 15s to let the auth rate limiter window from the")
            print(" brute-force test above clear before the next script logs in...)")
            time.sleep(15)

    print("\n" + "=" * 70)
    print("COMBINED RESULTS")
    print("=" * 70)
    for script, passed, _ in results:
        print(f"  {'PASS' if passed else 'FAIL'}  {script}")

    all_passed = all(passed for _, passed, _ in results)
    print("=" * 70)
    print("ALL ATTACKS BLOCKED" if all_passed else "SOME ATTACKS SUCCEEDED -- SEE OUTPUT ABOVE")
    print("=" * 70)

    post_report_to_dashboard(results)

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
