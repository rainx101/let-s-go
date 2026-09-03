"""Database access for Neon (Postgres). One small layer — pages never open
raw connections themselves (see CLAUDE.md)."""

from pathlib import Path
from typing import LiteralString, cast

import psycopg
import streamlit as st

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def _connection_string() -> str:
    """Neon connection string from Streamlit secrets.

    Raises KeyError with a clear message if it hasn't been configured yet.
    """
    try:
        return st.secrets["neon"]["url"]
    except KeyError as exc:
        raise KeyError(
            'Neon URL missing. Add [neon] url = "..." to .streamlit/secrets.toml '
            "(see .streamlit/secrets.toml.example)."
        ) from exc


@st.cache_resource
def _cached_connection() -> psycopg.Connection:
    """The cached Postgres connection (autocommit for simple reads/writes)."""
    return psycopg.connect(_connection_string(), autocommit=True)


def get_connection() -> psycopg.Connection:
    """The Neon connection, reconnecting if the cached one went stale.

    Neon's scale-to-zero / idle timeout can close the connection server-side; the
    cached object then reports `closed`, so we drop it and open a fresh one.
    """
    conn = _cached_connection()
    if conn.closed:
        _cached_connection.clear()
        conn = _cached_connection()
    return conn


def health_check() -> bool:
    """True if the database answers a trivial query. Lets errors surface —
    the caller decides how to show them (do not hide errors, per CLAUDE.md)."""
    with get_connection().cursor() as cur:
        cur.execute("SELECT 1")
        return cur.fetchone() == (1,)


@st.cache_resource
def init_db() -> None:
    """Create tables if they don't exist. Idempotent; cached so it runs once
    per deploy."""
    # Our own trusted schema file (not user input); cast for the SQL-literal type.
    schema = cast(LiteralString, _SCHEMA_PATH.read_text())
    with get_connection().cursor() as cur:
        cur.execute(schema)
