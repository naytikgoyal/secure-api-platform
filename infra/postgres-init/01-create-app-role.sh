#!/bin/bash
# Runs automatically ONCE, the first time the Postgres container initializes
# an empty data volume (anything in /docker-entrypoint-initdb.d is executed by
# the official image's entrypoint). It does NOT re-run on later restarts.
#
# Creates the role the Resource Service actually connects as. The point is
# LEAST PRIVILEGE: the Postgres superuser (POSTGRES_USER, pgadmin) exists
# only for bootstrapping and is never given to any application. orders_app:
#   - cannot create other databases or roles
#   - is not a superuser (cannot touch server config, create roles, load
#     extensions, or run OS commands via COPY ... PROGRAM -- each of these was
#     verified to be denied, see docs/sql-injection-demo.md)
#   - owns ONLY the "orders" database
#   - has CONNECT revoked on the default "postgres" database (see below)
#
# NOTE ON A CORRECTION: an earlier draft of this comment claimed the role
# "cannot read other databases." Testing disproved that -- by default
# Postgres grants CONNECT on every database to PUBLIC (i.e. everyone), so the
# role COULD connect to "postgres". It couldn't do anything dangerous there,
# but the claim was wrong, so the REVOKE below now makes it true.
#
# Why this matters for SQL injection specifically: parameterized queries
# (see resource-service/db.py) are the real defense. But defense in depth
# means asking "if some future code change DID introduce an injectable
# query, how bad would it be?" With a superuser connection: catastrophic
# (read files off the DB server, execute commands, destroy every database).
# With this role: limited to that one database's data. A blast-radius limit,
# not a substitute for the real fix.
#
# Note the password is passed to psql as a *variable* (-v) and referenced as
# :'app_pw' -- psql quotes it properly as a SQL literal. Building this
# statement by pasting $APP_DB_PASSWORD into the SQL text with shell string
# interpolation would be the exact bug class this whole sprint is about.
set -e

psql -v ON_ERROR_STOP=1 -v app_pw="$APP_DB_PASSWORD" \
     --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<'EOSQL'
CREATE ROLE orders_app LOGIN PASSWORD :'app_pw'
    NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;
ALTER DATABASE orders OWNER TO orders_app;
REVOKE CONNECT ON DATABASE postgres FROM PUBLIC;
EOSQL
