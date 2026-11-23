# SQL Injection: Live Proof, the Real Fix, and What Changed

Sprint 10 replaced the in-memory order store with real PostgreSQL. This is
the single architectural change that turns SQL injection from a theoretical
concern into a real one — the earlier reasoning in `docs/attack-report.md`
("blocklisting SQLi-looking strings would be security theater, because there's
no database to exploit") stops holding the moment a database exists. This
document is the proof that the *replacement* reasoning — "every query is
parameterized, so it holds regardless" — is actually true, not just claimed.

## Part 1 — the vulnerability, live

Run against a scratch Postgres table (`item`, `quantity`, `owner_id`):

```python
def vulnerable_search(item_name_from_user):
    query = f"SELECT * FROM orders WHERE item = '{item_name_from_user}'"
    cursor.execute(query)
    return cursor.fetchall()
```

Normal input works as expected:
```
vulnerable_search("Keyboard")
-> SQL sent: SELECT * FROM orders WHERE item = 'Keyboard'
-> [(1, 'Keyboard', 1, 'user-naytik')]
```

A malicious input closes the string early, adds a condition that's always
true, and comments out the rest:
```
vulnerable_search("nonexistent' OR '1'='1' --")
-> SQL sent: SELECT * FROM orders WHERE item = 'nonexistent' OR '1'='1' --'
-> [(1, 'Keyboard', 1, 'user-naytik'), (2, 'Secret Admin Note', 999, 'user-admin')]
```

**A search for something that doesn't exist returned every row in the table,
including another user's data.** This is a real, general vulnerability class
(CWE-89), not specific to this project — it has caused real breaches
(Equifax's 2017 breach involved a related injection class; countless smaller
incidents are pure SQL injection).

## Part 2 — the fix, live, same payload

```python
def safe_search(item_name_from_user):
    query = "SELECT * FROM orders WHERE item = %s"
    cursor.execute(query, (item_name_from_user,))   # <- parameter, not string-formatting
    return cursor.fetchall()
```

```
safe_search("nonexistent' OR '1'='1' --")
-> Query template: SELECT * FROM orders WHERE item = %s
-> Parameter (kept separate): "nonexistent' OR '1'='1' --"
-> []
```

Identical malicious string. Empty result. The database searched for an item
*literally named* `nonexistent' OR '1'='1' --`, which doesn't exist.

**Why this works, precisely**: with a placeholder (`%s`), the Python driver
sends the query's fixed structure and the user's value as two separate things
over the wire to Postgres. Postgres parses the structure once; the value is
never re-parsed as SQL syntax, no matter what characters it contains. With
string formatting, there is no structure/data distinction at all by the time
Postgres sees it — it's handed one already-assembled string and has no way to
know which parts the developer intended as fixed logic versus user input.

## Part 3 — every query in this project, and its status

`resource-service/db.py` contains every SQL statement this project issues.
All five are parameterized:

| Function | Query | User input involved |
| :--- | :--- | :--- |
| `create_order` | `INSERT INTO orders (...) VALUES (%s, %s, %s, %s, %s)` | item, quantity, owner_id |
| `list_orders` | `SELECT * FROM orders WHERE owner_id = %s` | owner_id (admin-controllable query param) |
| `get_order` | `SELECT * FROM orders WHERE id = %s` | order_id (URL path) |
| `delete_order` | `DELETE FROM orders WHERE id = %s` | order_id (URL path) |
| `init_schema` | `CREATE TABLE IF NOT EXISTS ...` | none — fixed DDL, no user input reaches this |

There is no string-formatted or `%`-interpolated SQL anywhere in this
codebase. If you ever add a new query, this table is what to check against
before merging it.

## Part 4 — live verification against the real system (not the scratch demo)

Extended `attacker-toolkit/attack_injection.py` to attack the three places
user input reaches a real query, against the actual running Gateway →
Resource Service → PostgreSQL chain, not the standalone demo above:

1. **Item field on create** (already existed pre-Sprint-10, now meaningfully
   tested): `'; DROP TABLE orders; --` as an item name → `201`, stored
   verbatim, table still has all its rows afterward.
2. **Order ID in the URL path** (`GET/DELETE /orders/{id}`): `' OR '1'='1`,
   `'; DROP TABLE orders; --`, and `1; DELETE FROM orders` as path
   parameters → all return a clean `404 Order not found`, because `id` is a
   UUID column and none of these strings are valid UUIDs *or* would match any
   row even if they were.
3. **Admin `?owner_id=` filter** (the classic "give me everyone's data"
   attack): a legitimate query (`owner_id=user-naytik`) returns real rows; the
   identical endpoint with `owner_id=' OR '1'='1` returns **zero** rows —
   proof the value was compared literally as a string, not evaluated as a
   boolean condition.
4. **Final integrity check**: after every injection attempt above, including
   two `DROP TABLE` and one `DELETE FROM` payload, the order count is
   compared before and after. It's identical. Nothing was executed.

Full run: **18/18 checks passed** (see `docs/build-log.md` for the actual
captured terminal output from this run, including the two real bugs found
while building this — below).

## Two real bugs found while building this (not hypothetical)

**Bug 1 — signature verification broke on percent-encoded URLs.**
`GET /orders/' OR '1'='1` (URL-encoded to `%27%20OR...`) returned `401
Invalid request signature` instead of reaching the database layer at all.
Cause: the same class of bug as Week 4's query-string signing issue.
`request.url.path` in Starlette is **percent-decoded**, but the Gateway
signs the path **as it puts it on the wire** — percent-*encoded*. Two
correct-looking implementations, disagreeing on which bytes were actually
signed, again. Fixed by using `request.scope["raw_path"]` (the ASGI-standard
original, undecoded bytes) instead of `request.url.path` when reconstructing
what to verify. See `resource-service/main.py`'s `verify_request_signature`
for the fix and full comment.

**Bug 2 — an overclaiming comment in the database role setup.** An early
draft of `infra/postgres-init/01-create-app-role.sh` stated the app's
database role "cannot read other databases." Testing this claim directly
(`psql -U orders_app -d postgres`) showed it was **false** — Postgres grants
`CONNECT` on every database to `PUBLIC` by default, so the role could in fact
connect to the default `postgres` database (it couldn't do anything harmful
there, but the claim itself was wrong). Fixed with an explicit `REVOKE
CONNECT ON DATABASE postgres FROM PUBLIC;`, then re-verified: connection
attempt now fails with `permission denied for database "postgres"`. The
lesson generalizes: **verify security claims about a system by testing them,
not by reasoning about what "should" be true.**

## Part 5 — defense in depth: least privilege, verified

Parameterized queries are the real fix. But defense in depth means also
asking: *if a future code change somehow did introduce a raw, injectable
query, how bad would it be?* The Resource Service connects as `orders_app`,
a role created in `infra/postgres-init/01-create-app-role.sh` with the
narrowest privileges that still let the application function. Verified live,
each attempted **and denied**:

| Attempted action | Result |
| :--- | :--- |
| Connect to its own `orders` database | Succeeds (this is its job) |
| Connect to the default `postgres` database | `permission denied for database "postgres"` |
| Create a new superuser role | `permission denied to create role` |
| Run an OS command via `COPY ... TO PROGRAM` | `permission denied to COPY to or from an external program` |
| Create another database | `permission denied to create database` |

If some future bug ever did let raw SQL through, the blast radius is capped
at this one database's own rows — not the server, not other databases, not
the OS. This is a backstop, not a substitute for parameterized queries.

## What this changes in the threat model

`docs/threat-model.md`'s residual risk section previously said: *"No SQL
injection defense is implemented, because none is needed yet."* That's now
out of date — a database exists, and the defense (parameterized queries +
least-privilege role) is implemented and verified above. See the updated
entry there.
