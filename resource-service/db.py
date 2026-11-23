# Real persistence layer, replacing the in-memory dict from Weeks 2-8.
#
# THE SINGLE MOST IMPORTANT RULE IN THIS FILE: every query uses a %s
# placeholder and passes user-controlled values as a SEPARATE parameters
# tuple to cursor.execute(). NEVER f-string, .format(), or % user input
# directly into a SQL string -- that is exactly the SQL injection
# vulnerability class demonstrated live during this project's build (see
# docs/attack-report.md and docs/sql-injection-demo.md for the proof: the
# identical malicious payload that stole every row via string-formatted SQL
# returns an empty, harmless result here).
#
# This distinction is not a style preference -- it changes what the database
# driver actually does. With a placeholder, the driver sends the query
# structure and the data as two separate things over the wire; the database
# cannot confuse "this is SQL syntax" with "this is just a value to compare"
# no matter what characters the value contains.
from __future__ import annotations

import os
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional

import psycopg2
import psycopg2.extras

# Host/port/name are not secrets and come from the environment. The username
# and password are injected once at startup via configure(), after main.py
# fetches them from Vault -- same "set once after the Vault fetch" pattern the
# Node services use (setPublicKey / setHmacSecret / setPrivateKey).
DB_HOST = os.environ.get("DB_HOST", "postgres")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "orders")

_db_user: Optional[str] = None
_db_password: Optional[str] = None


def configure(user: str, password: str) -> None:
    global _db_user, _db_password
    _db_user, _db_password = user, password


def _connect():
    if _db_user is None or _db_password is None:
        # Fail loudly and early rather than attempting an anonymous connection.
        raise RuntimeError("db.configure() must be called with Vault-provided credentials first")
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=_db_user, password=_db_password,
    )


@contextmanager
def get_cursor():
    """Yields a cursor inside a transaction; commits on success, rolls back on
    any exception. Connections are opened per-request rather than pooled --
    fine at this project's scale, and simpler to reason about; a real
    production service under load would use a connection pool (e.g. psycopg2's
    own pool, or SQLAlchemy) instead of a fresh TCP connection per request."""
    conn = _connect()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def wait_for_database(max_attempts: int = 30, delay_seconds: float = 1.0) -> None:
    """Postgres and the Resource Service start at roughly the same time in
    docker-compose; this retries the connection instead of crashing on the
    first attempt if the database isn't ready yet."""
    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            conn = _connect()
            conn.close()
            return
        except psycopg2.OperationalError as e:
            last_error = e
            time.sleep(delay_seconds)
    raise RuntimeError(f"Could not connect to database after {max_attempts} attempts: {last_error}")


def init_schema() -> None:
    """Creates the orders table if it doesn't already exist. Idempotent --
    safe to call on every startup, not just the first time."""
    with get_cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                id UUID PRIMARY KEY,
                item TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                owner_id TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL
            )
            """
        )
        # Orders are almost always looked up by owner_id (list_orders) --
        # an index here is a real, if small, performance consideration now
        # that this is an actual queryable database rather than a Python dict.
        cur.execute("CREATE INDEX IF NOT EXISTS idx_orders_owner_id ON orders (owner_id)")


def create_order(item: str, quantity: int, owner_id: str) -> dict:
    order_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc)
    with get_cursor() as cur:
        cur.execute(
            "INSERT INTO orders (id, item, quantity, owner_id, created_at) VALUES (%s, %s, %s, %s, %s)",
            (order_id, item, quantity, owner_id, created_at),
        )
    return {
        "id": order_id,
        "item": item,
        "quantity": quantity,
        "owner_id": owner_id,
        "created_at": created_at.isoformat(),
    }


def list_orders(owner_id: Optional[str]) -> list[dict]:
    with get_cursor() as cur:
        if owner_id:
            cur.execute("SELECT * FROM orders WHERE owner_id = %s ORDER BY created_at DESC", (owner_id,))
        else:
            cur.execute("SELECT * FROM orders ORDER BY created_at DESC")
        rows = cur.fetchall()
    return [_serialize(row) for row in rows]


def _valid_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except (ValueError, AttributeError, TypeError):
        return False


def get_order(order_id: str) -> Optional[dict]:
    # The id column is a UUID. Handing Postgres a string that isn't one
    # (e.g. "does-not-exist", or an injection attempt like "' OR '1'='1")
    # doesn't run anything dangerous -- the parameterized query still treats
    # it purely as data -- but Postgres rejects it with a type error, which
    # would surface as a 500. A malformed ID can't match any order, so the
    # correct answer is the same as for any unknown ID: not found (404).
    # Validating the TYPE up front is input validation, not a blocklist:
    # it accepts exactly the shape the column requires and nothing else.
    if not _valid_uuid(order_id):
        return None
    with get_cursor() as cur:
        cur.execute("SELECT * FROM orders WHERE id = %s", (order_id,))
        row = cur.fetchone()
    return _serialize(row) if row else None


def delete_order(order_id: str) -> bool:
    """Returns True if a row was actually deleted, False if the ID didn't exist."""
    if not _valid_uuid(order_id):
        return False
    with get_cursor() as cur:
        cur.execute("DELETE FROM orders WHERE id = %s", (order_id,))
        deleted_count = cur.rowcount
    return deleted_count > 0


def _serialize(row: dict) -> dict:
    """psycopg2 returns TIMESTAMPTZ as a Python datetime; convert to an ISO
    string so it matches the shape the API has always returned."""
    row = dict(row)
    row["id"] = str(row["id"])
    row["created_at"] = row["created_at"].isoformat()
    return row
