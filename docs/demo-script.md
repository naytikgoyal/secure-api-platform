# Demo Script (target: 3-5 minutes)

Record your screen with terminal + browser visible. Practice once before recording — the timing below assumes you already have the stack running (start it before you hit record; don't waste demo time on `docker compose up`'s build output).

## Setup (before recording)

```bash
cd infra
./scripts/gen-certs.sh
docker compose up -d vault
./scripts/vault-init.sh
docker compose up --build -d
```

Confirm everything's healthy (`docker compose ps`) and the dashboard loads at `http://localhost:5173` before you start recording.

---

## Shot 1 (0:00-0:30) — The pitch, over the architecture diagram

Have `docs/architecture-diagram.md` rendered on screen (paste the Mermaid block into a live editor, or a screenshot).

**Say:** "This is a defense-in-depth API platform — a Gateway and an internal Resource Service that don't trust each other just because they're on the same network. Every request between them is mutually authenticated over TLS *and* individually signed with HMAC, with replay protection. I built this to actually practice the security engineering real companies do, not just add HTTPS and call it done."

Point at the diagram: "The attacker only ever has one way in — the public Gateway. Everything past that boundary requires passing multiple independent checks."

## Shot 2 (0:30-1:15) — The normal flow, fast

Terminal, split or full-screen:

```bash
CA=infra/certs/ca.crt
TOKEN=$(curl -s --cacert $CA -X POST https://localhost:4000/auth/login \
  -H "Content-Type: application/json" -d '{"username":"naytik","password":"password123"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -s --cacert $CA -X POST https://localhost:3000/orders \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"item":"Demo Widget","quantity":1}' | python3 -m json.tool
```

**Say:** "Normal flow: login gets a short-lived JWT, then I create an order through the Gateway, which internally mTLS-connects and HMAC-signs the request to the Resource Service."

## Shot 3 (1:15-2:15) — The dashboard, live

Switch to browser, `http://localhost:5173`, already logged in as admin.

**Say:** "This is the Security Operations Dashboard — it's watching the exact same traffic in real time over a server-sent-events stream."

Click **"🔓 Forge a JWT"** in the Attack Simulation panel.

**Say, as the event appears:** "That button just made a real request with a garbage token — not a fake log entry, an actual HTTP call that hit my real authentication middleware and got rejected. You can see it land in the Security Events panel within about a second."

Click **"🌊 Flood with rapid requests"**.

**Say:** "And this fires 20 real requests to trip the actual rate limiter — same thing, genuinely happening, not staged."

## Shot 4 (2:15-3:15) — The attacker toolkit

Terminal:

```bash
cd attacker-toolkit
python3 attack_replay.py
```

**Say (while it runs):** "This is the part I'm most proud of — an actual offensive test suite. This script captures a validly HMAC-signed request and replays it immediately. Watch — first send succeeds, the identical replay gets rejected because of nonce reuse."

Let the PASS/FAIL summary print.

**Say:** "I've got five of these — JWT forgery including the classic `alg:none` attack, brute-forcing, injection testing, and TLS downgrade attempts. All five are in `docs/attack-report.md` with the real HTTP evidence, including two actual bugs I found and fixed while building this."

## Shot 5 (3:15-4:00) — The interesting finding (optional, if time allows)

**Say, over `docs/attack-report.md` on screen, scrolled to Finding 2:** "The most interesting bug wasn't really a bug — my first version of the injection test expected SQL-injection-looking strings to be rejected, and they weren't. My first instinct was to add a blocklist. Then I actually checked: this system has no database and no HTML renderer, so there's nothing for those strings to exploit. Blocklisting them would've been security theater and would've broken a legitimate product name with an apostrophe in it. I fixed the one thing that actually mattered — null bytes — and documented why the rest were correctly left alone. That's the kind of judgment call I think matters more than just running a scanner and green-checking everything."

## Shot 6 (4:00-4:30) — Close

**Say:** "Everything here — the threat model, the signing scheme, the key rotation procedure, the attack report — is documented with real command output, not just descriptions. Repo's linked below."

---

## If you only have time for a 90-second cut

Use Shot 2 (normal flow) → Shot 3's first button click (forged token, live in dashboard) → Shot 4's replay attack output → close with one sentence pointing to the attack report.
