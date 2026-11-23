# Fetches secrets from Vault's KV v2 HTTP API at import time (module-level,
# synchronous -- this runs once when the FastAPI app boots, before it accepts
# any traffic). Replaces reading jwt-signing.pub and hmac-signing.key as local
# files (Weeks 3-4); as of Week 5 those secrets exist ONLY in Vault.
#
# NOTE: same shape as gateway/src/vaultClient.js and auth-server/src/vaultClient.js
# by design, but not shared code -- see those files' comments for why.
from __future__ import annotations

import os

import requests


def _read_secret(path: str) -> dict:
    vault_addr = os.environ.get("VAULT_ADDR", "http://vault:8200")
    vault_token = os.environ.get("VAULT_TOKEN")

    if not vault_token:
        raise RuntimeError("VAULT_TOKEN is not set -- cannot authenticate to Vault.")

    resp = requests.get(
        f"{vault_addr}/v1/secret/data/{path}",
        headers={"X-Vault-Token": vault_token},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["data"]["data"]  # KV v2 wraps fields under data.data


def fetch_secrets() -> dict:
    """Returns the JWT public key, HMAC secret, and the database credentials
    (Sprint 10 -- the Postgres username/password never appear in
    docker-compose.yml's resource-service environment; only Vault has them)."""
    jwt_signing = _read_secret("jwt-signing")
    hmac_signing = _read_secret("hmac-signing")
    db_creds = _read_secret("db-creds")
    return {
        "jwt_public_key": jwt_signing["public_key"],
        "hmac_secret": hmac_signing["key"],
        "db_user": db_creds["username"],
        "db_password": db_creds["password"],
    }
