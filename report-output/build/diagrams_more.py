"""Second batch of original diagrams (design, data model, deployment, process)."""
from svgkit import Canvas


def graphical_abstract():
    c = Canvas(820, 440)
    c.text(410, 24, "Every API request is checked at four independent layers", 19, bold=True)
    c.box(8, 150, 100, 90, "Client", "white", bold=True, sub="HTTPS")
    xs = [140, 310, 480, 650]
    heads = ["1  API Gateway", "2  Service link", "3  Resource Service", "4  Database"]
    cols = ["yellow", "orange", "green", "blue"]
    body = [
        "TLS 1.2+\nJWT, RS256 only\nscope check\nrate limit",
        "mutual TLS\nHMAC-SHA256\nnonce, 60 s window\ngeneric 401",
        "JWT verified again\nscope again\nowner must match\ninput validation",
        "parameterised SQL\nleast-privilege role\nport not published\nsecrets from Vault",
    ]
    for x, h, col, b in zip(xs, heads, cols, body):
        c.box(x, 90, 150, 200, "", col)
        c.text(x + 75, 114, h, 15, bold=True)
        c.text(x + 75, 205, b, 14, lh=26)
    c.line([(108, 195), (140, 195)])
    for a, b in zip(xs[:-1], xs[1:]):
        c.line([(a + 150, 195), (b, 195)])
    c.box(140, 325, 200, 44, "Vault: secrets", "purple", size=15)
    c.box(360, 325, 200, 44, "Redis: limits, nonces", "blue", size=15)
    c.box(580, 325, 220, 44, "Loki + Grafana: audit logs", "grey", size=15)
    c.text(8, 347, "Supporting\nservices", 13, anchor="start")
    c.box(8, 392, 804, 36, "Validated by an attacker toolkit (28 checks), 19 live flows and 26 unit tests", "yellow", size=15, bold=True)
    return c


def checks_per_layer():
    c = Canvas(820, 470)
    cols = [
        ("1  API Gateway", "yellow", ["HTTPS only, TLS 1.2+", "helmet security headers", "JSON body limit 100 kB", "Bearer JWT, RS256 only", "issuer, audience, expiry", "scope check per route", "100 requests/min per user", "?owner_id needs admin"]),
        ("2  Service link", "orange", ["client certificate (mTLS)", "CA pinned by the Gateway", "HMAC-SHA256 over method", "target, body, time, nonce", "60 s timestamp window", "nonce kept for 300 s", "constant-time comparison", "generic 401 on any failure"]),
        ("3  Resource Service", "green", ["JWT verified again", "scope checked again", "owner_id must equal sub", "order ownership (BOLA)", "admin scope for others", "Pydantic type and size rules", "null bytes rejected", "errors reveal no detail"]),
        ("4  Data layer", "blue", ["%s placeholders only", "UUID shape checked first", "role orders_app", "no superuser, CREATEDB", "other databases closed", "database port not published", "credentials come from Vault", "one table, one index"]),
    ]
    for i, (h, col, items) in enumerate(cols):
        x = 8 + i * 204
        c.box(x, 10, 196, 40, h, col, size=16, bold=True)
        c.box(x, 56, 196, 330, "", "white", lw=1.2)
        for j, t in enumerate(items):
            c.text(x + 12, 80 + j * 40, t, 13.5, anchor="start")
    c.box(8, 400, 804, 56, "Across all layers: Vault secrets  |  Auth Server limit 10 logins/min  |  lockout after 5 failures per source\nbcrypt password hashes  |  structured JSON audit log with request IDs", "grey", size=14)
    return c


def hmac_flow():
    c = Canvas(820, 650)
    c.text(140, 22, "API Gateway: sign", 17, bold=True)
    c.text(520, 22, "Resource Service: verify", 17, bold=True)
    c.titled(20, 50, 240, 140, "Build canonical string", "METHOD\nPATH?QUERY\nBODY\nTIMESTAMP\nNONCE (128-bit random)", "yellow", lh=19)
    c.box(20, 225, 240, 70, "HMAC-SHA256 with the\nshared secret from Vault", "yellow", size=15)
    c.titled(20, 330, 240, 90, "Send three headers", "X-Signature   X-Timestamp\nX-Nonce", "yellow", lh=19)
    c.line([(140, 190), (140, 225)])
    c.line([(140, 295), (140, 330)])
    ys = [70, 168, 330, 440]
    labels = ["Three headers\npresent?", "Timestamp within\n60 s of now?", "Signature equal?\n(constant time)", "Nonce unused?\n(SET NX EX 300)"]
    cx = 470
    for y, lab in zip(ys, labels):
        c.diamond(cx, y, 230, 76, lab, "yellow", size=14)
    c.box(cx - 115, 232, 230, 52, "Rebuild the string from the raw\npath, query and body", "white", size=13)
    c.box(cx - 115, 540, 230, 56, "Continue: JWT, scope,\nownership, SQL", "green", size=14, bold=True)
    for a, b in ((108, 132), (206, 232), (284, 292), (368, 402), (478, 540)):
        c.line([(cx, a), (cx, b)])
    c.line([(260, 375), (300, 375), (300, 70), (355, 70)])
    c.line([(cx + 115, 70), (640, 70)], arrow=False)
    c.line([(cx + 115, 168), (640, 168)], arrow=False)
    c.line([(cx + 115, 330), (640, 330)], arrow=False)
    c.line([(cx + 115, 440), (640, 440)], arrow=False)
    c.line([(640, 70), (640, 440)], arrow=False)
    c.line([(640, 255), (668, 255)], color="#b3261e")
    c.titled(668, 195, 144, 120, "401 Unauthorized", "generic text;\nreal reason is\nlogged only", "red", size=14, bsize=12, lh=16)
    for y in (70, 168, 330, 440):
        c.text(cx + 124, y - 12, "no", 12, anchor="start", color="#b3261e", bold=True)
    for y in (70, 168, 330, 440):
        c.text(cx + 8, y + 50, "yes", 12, anchor="start", bold=True)
    return c


def data_model():
    c = Canvas(820, 500)
    c.box(10, 56, 320, 40, "orders  (PostgreSQL)", "blue", size=16, bold=True)
    c.box(10, 96, 320, 200, "", "white", lw=1.2)
    rows = [("id", "UUID  PRIMARY KEY"), ("item", "TEXT  NOT NULL"), ("quantity", "INTEGER  NOT NULL"), ("owner_id", "TEXT  NOT NULL  (indexed)"), ("created_at", "TIMESTAMPTZ  NOT NULL")]
    for i, (a, b) in enumerate(rows):
        y = 124 + i * 36
        c.text(24, y, a, 15, anchor="start", bold=True)
        c.text(120, y, b, 14, anchor="start")
    c.box(10, 316, 320, 74, "Application role orders_app owns this\ndatabase only: no superuser, no CREATEDB,\nno CREATEROLE, no other database", "white", size=13)
    c.box(10, 410, 320, 56, "Pydantic: item 1-200 characters,\nquantity 1-1000, owner_id 1-100", "yellow", size=13)
    stores = [
        ("Users  (Auth Server memory)", "sub, username, passwordHash (bcrypt, cost 10), scopes[]", "grey"),
        ("Refresh tokens  (Auth Server memory)", "48-byte hex token  ->  sub, scopes, expiresAt (7 days)", "grey"),
        ("Failed attempts  (Auth Server memory)", "(username, address)  ->  count, lockedUntil (15 min)", "grey"),
        ("Nonces  (Redis)", "nonce:<32 hex>  ->  \"1\", expires after 300 s", "blue"),
        ("Rate-limit counters  (Redis)", "keyed by user (Gateway) or IP (Auth Server)", "blue"),
        ("Secrets  (Vault KV v2)", "jwt-signing, hmac-signing, db-creds", "purple"),
    ]
    for i, (a, b, col) in enumerate(stores):
        y = 56 + i * 68
        c.box(420, y, 390, 58, a, col, size=14, bold=True, sub=b)
    c.line([(420, 85), (375, 85), (375, 232), (330, 232)], None, dashed=True)
    c.text(375, 262, "sub = owner_id\n(logical link,\nno foreign key)", 12, lh=14.5)
    return c


def deployment():
    c = Canvas(820, 500)
    c.zone(8, 10, 804, 484, "Docker Compose network: secure-net (single bridge network)", "grey")
    X = [24, 300, 576]
    Y = [48, 158, 268, 378]
    W, H = 220, 90

    def cont(col, row, name, image, port, color):
        c.box(X[col], Y[row], W, H, name, color, size=15, bold=True, sub=image + "\n" + port)

    cont(0, 0, "vault", "hashicorp/vault:1.17 (dev mode)", "host port 8200 published", "purple")
    cont(1, 0, "redis", "redis:7-alpine", "host port 6379 published", "blue")
    cont(2, 0, "postgres", "postgres:16-alpine", "no host port (internal only)", "blue")
    cont(0, 1, "auth-server", "Node 20 / Express", "host port 4000 published", "yellow")
    cont(1, 1, "gateway", "Node 20 / Express", "host port 3000 published", "yellow")
    cont(2, 1, "resource-service", "Python 3.12 / FastAPI", "host port 8000 published", "green")
    cont(0, 2, "dashboard", "Node 20, Vite dev server", "host port 5173 published", "grey")
    cont(1, 2, "loki", "grafana/loki:3.1.0", "host port 3100 published", "grey")
    cont(2, 2, "grafana", "grafana/grafana:11.1.0", "host port 3001 -> 3000", "grey")
    cont(0, 3, "promtail", "grafana/promtail:3.1.0", "no port; reads docker.sock", "grey")
    c.box(X[1], Y[3], W, H, "certs (read-only mount)", "white", size=14, bold=True, sub="ca, gateway, auth-server,\nresource-service keys and certificates")
    c.cylinder(X[2] + 50, Y[3] - 4, 120, 100, "postgres_data", "blue", size=14, sub="named volume")
    return c


def alternatives():
    c = Canvas(820, 580)
    px = [8, 281, 554]
    names = [("A.  Perimeter trust", "grey"), ("B.  Monolith with sessions", "grey"), ("C.  Layered zero trust (built)", "green")]
    flows = [
        ["Client", "Gateway:\nTLS + JWT check", "Internal services\n(trust the Gateway)", "Database\n(one shared account)"],
        ["Client\n(session cookie)", "One application:\nsession store + roles", "Database", None],
        ["Client", "Gateway: JWT, scope,\nrate limit", "Resource Service: mTLS,\nHMAC, nonce, JWT again", "Database: parameterised,\nleast privilege"],
    ]
    notes = [
        ["+ simple, fast", "- one check only", "- a Gateway flaw exposes everything", "- no protection against replay\n  on the internal hop"],
        ["+ least moving parts", "- session lives in one process", "- no service isolation", "- every defect is in one blast radius"],
        ["+ independent checks per layer", "+ replay and tampering blocked", "- more components to run", "- more latency and set-up work"],
    ]
    for i in range(3):
        x = px[i]
        c.box(x, 8, 258, 38, names[i][0], names[i][1], size=15, bold=True)
        y = 70
        for j, f in enumerate(flows[i]):
            if f is None:
                continue
            col = ["white", "yellow", "green", "blue"][j] if i == 2 else ["white", "yellow", "yellow", "blue"][j] if i == 0 else ["white", "yellow", "blue"][j]
            c.box(x + 14, y, 230, 56, f, col, size=13)
            if j < 3 and flows[i][j + 1] is not None:
                c.line([(x + 129, y + 56), (x + 129, y + 78)])
            y += 78
        c.box(x, 400, 258, 170, "", "white", lw=1.2)
        for k, t in enumerate(notes[i]):
            c.text(x + 10, 420 + k * 38 + (6 if "\n" in t else 0), t, 13, anchor="start", lh=16)
    return c


def implementation_flow():
    c = Canvas(820, 880)
    steps = [
        ("g", "TLS handshake (TLS 1.2 or 1.3)", "no connection"),
        ("g", "Authorization header holds a Bearer token?", "401"),
        ("g", "JWT valid: RS256, issuer, audience, expiry?", "401"),
        ("g", "Within 100 requests per minute for this user?", "429"),
        ("g", "Route scope present in the token?", "403"),
        ("g", "Sign the request (HMAC, timestamp, nonce) and call over mTLS", "502 if upstream fails"),
        ("r", "Client certificate valid for the mTLS handshake?", "handshake fails"),
        ("r", "HMAC signature and 60-second window correct?", "401"),
        ("r", "Nonce not seen before (Redis SET NX EX 300)?", "401 replay"),
        ("r", "JWT valid again, scope present?", "401 / 403"),
        ("r", "owner_id equals token subject, or admin scope?", "403"),
        ("r", "Parameterised SQL runs; row found?", "404"),
        ("r", "Return 200, 201 or 204 with JSON", ""),
    ]
    c.box(8, 10, 120, 6 * 66 - 12, "API\nGateway", "yellow", bold=True, size=16)
    c.box(8, 10 + 6 * 66, 120, 7 * 66 - 12, "Resource\nService", "green", bold=True, size=16)
    for i, (z, t, fail) in enumerate(steps):
        y = 10 + i * 66
        col = "yellow" if z == "g" else "green"
        c.box(150, y, 470, 54, t, col, size=14, bold=(i == len(steps) - 1))
        if fail:
            c.line([(620, y + 27), (660, y + 27)], arrow=True, color="#b3261e")
            c.box(660, y + 7, 150, 40, fail, "red", size=13)
        if i < len(steps) - 1:
            c.line([(385, y + 54), (385, y + 66)])
    return c


def gantt():
    c = Canvas(820, 470)
    x0, wk = 260, 46.5  # pixels per week (12 weeks -> 558 px)
    phases = [
        ("P1  Threat model, scaffolding", 0.0, 0.8, "yellow"),
        ("P2  Core APIs and TLS", 0.8, 1.6, "yellow"),
        ("P3  Authentication, authorisation", 1.6, 2.6, "yellow"),
        ("P4  mTLS, HMAC, replay protection", 2.6, 3.5, "orange"),
        ("P5  Vault, rate limits, CI", 3.5, 4.3, "orange"),
        ("P6  Attacker toolkit", 4.3, 4.9, "red"),
        ("P7  Logging, monitoring, dashboard", 4.9, 5.6, "green"),
        ("P8  Role-based UI, headers, lockout", 5.6, 6.1, "green"),
        ("P9  PostgreSQL, SQL-injection proof", 6.1, 6.6, "blue"),
        ("P10 Verification and report writing", 6.6, 12.0, "grey"),
    ]
    ticks = [(0, "1 Sep"), (2.1, "15 Sep"), (4.3, "1 Oct"), (6.4, "15 Oct"), (8.7, "1 Nov"), (10.8, "15 Nov")]
    for w, lab in ticks:
        x = x0 + w * wk
        c.line([(x, 40), (x, 410)], None, arrow=False, color="#bbbbbb", lw=1)
        c.text(x, 24, lab, 13)
    for i, (n, a, b, col) in enumerate(phases):
        y = 50 + i * 36
        c.text(8, y + 14, n, 14, anchor="start")
        c.box(x0 + a * wk, y, max((b - a) * wk, 6), 28, "", col, rx=4, lw=1.4)
    c.text(8, 440, "Phase boundaries are approximate. Build period stated by the author: September to mid-October 2026.", 13, anchor="start")
    return c


def observability():
    c = Canvas(820, 380)
    c.box(8, 20, 170, 130, "Gateway\nAuth Server\nResource Service", "yellow", size=15, bold=True)
    c.box(230, 20, 130, 56, "stdout\nJSON lines", "white", size=14)
    c.box(400, 20, 130, 56, "Promtail\n(docker_sd)", "grey", size=14)
    c.box(570, 20, 110, 56, "Loki", "grey", size=15, bold=True)
    c.box(710, 20, 100, 56, "Grafana", "grey", size=15, bold=True)
    c.line([(178, 48), (230, 48)])
    c.line([(360, 48), (400, 48)])
    c.line([(530, 48), (570, 48)])
    c.line([(680, 48), (710, 48)])
    c.text(760, 108, "3 panels:\nrequest volume\ndeny reasons\nrate-limit hits", 13, lh=16)
    c.box(220, 230, 160, 60, "Audit event buffer\n(200 events, in memory)", "yellow", size=13)
    c.box(420, 230, 160, 60, "/admin/audit-logs\n/admin/metrics\n/admin/audit-stream", "yellow", size=12)
    c.box(640, 230, 170, 60, "React dashboard\n(admin only)", "white", size=14, bold=True)
    c.line([(93, 150), (93, 260), (220, 260)], "allow / deny\nevents", loff=(0, -24), size=12)
    c.line([(380, 260), (420, 260)])
    c.line([(580, 260), (640, 260)], "fetch + SSE", loff=(0, -22), size=12)
    c.text(410, 330, "Two paths: durable, queryable history in Loki (top) and a live in-memory feed for the dashboard (bottom)", 13)
    return c


def testing_workflow():
    c = Canvas(820, 340)
    c.box(8, 10, 804, 44, "GitHub Actions workflow (defined, not run for this report): gitleaks, pytest, Node syntax check, npm audit", "grey", size=13, dashed=True)
    steps = [
        ("Unit tests", "pytest and node:test\n26 tests\nsigning, nonce,\nlockout, login", "blue"),
        ("Live functional flows", "curl, psql\n19 flows\nlogin to SQL", "yellow"),
        ("Attacker toolkit", "5 scripts\n28 checks\nreplay, forgery,\nbrute force, SQLi,\nTLS downgrade", "red"),
        ("Independent probes", "TLS version probe\nlogin timing\nrate-limit burst\nLoki queries", "orange"),
        ("Browser checks", "Playwright\nlogin, dashboard,\nXSS strings,\nGrafana", "green"),
    ]
    for i, (h, b, col) in enumerate(steps):
        x = 8 + i * 164
        c.box(x, 90, 150, 200, "", col)
        c.text(x + 75, 112, h, 14, bold=True)
        c.text(x + 75, 202, b, 13, lh=21)
        if i < 4:
            c.line([(x + 150, 190), (x + 164, 190)])
    c.text(410, 318, "Every figure and result in Chapter 4 comes from one of these five stages", 13)
    return c


def standards_timeline():
    c = Canvas(820, 470)
    ev = [
        ("1994", "Syverson:\nreplay-attack\ntaxonomy"), ("1997", "RFC 2104\nHMAC"), ("1999", "bcrypt\npassword\nscheme"),
        ("2003", "Remote\ntiming attacks"), ("2012", "RFC 6749, 6750\nOAuth 2.0"), ("2014", "BeyondCorp;\nmicroservices\ndefinition"),
        ("2015", "RFC 7519\nJWT"), ("2018", "RFC 8446\nTLS 1.3"), ("2019", "NIST SP\n800-204"),
        ("2020", "NIST SP 800-207\nZero Trust;\nRFC 8725"), ("2021", "RFC 8996;\nNSA Zero\nTrust sheet"), ("2023", "OWASP API\nSecurity\nTop 10"),
        ("2025", "RFC 9700;\nASVS 5.0;\nSP 800-63B-4"), ("2026", "RFC 9846\nTLS 1.3"),
    ]
    n = len(ev)
    x0, x1 = 50, 770
    ymid = 235
    c.line([(20, ymid), (800, ymid)], arrow=True, lw=2.4)
    for i, (yr, t) in enumerate(ev):
        x = x0 + (x1 - x0) * i / (n - 1)
        lvl = [-1, 1][i % 2]
        far = (i // 2) % 2
        ty = ymid + lvl * (62 + far * 84)
        c.line([(x, ymid), (x, ty - lvl * 34)], None, arrow=False, color="#888888", lw=1.2)
        c.circle(x, ymid, 7, "", "blue")
        c.text(x, ymid + (-18 if lvl < 0 else 20) * 0.0 + (lvl * 0), "", 1)
        c.text(x, ty - lvl * 22, yr, 14, bold=True, color="#2a5d9f", bg=True)
        c.text(x, ty + lvl * 12, t, 12, lh=14.5, bg=True)
    c.text(410, 455, "Events are spaced evenly, not to scale. Each is a source cited in this report.", 12, italic=True)
    return c


JOBS = {
    "fig-graphical-abstract": graphical_abstract,
    "fig-checks-per-layer": checks_per_layer,
    "fig-hmac-flow": hmac_flow,
    "fig-data-model": data_model,
    "fig-deployment": deployment,
    "fig-alternatives": alternatives,
    "fig-implementation-flow": implementation_flow,
    "fig-gantt": gantt,
    "fig-observability": observability,
    "fig-testing-workflow": testing_workflow,
    "fig-standards-timeline": standards_timeline,
}
