"""Database access for Neon (Postgres). One small layer — pages never open
raw connections themselves (see CLAUDE.md)."""

import psycopg
import streamlit as st


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
def get_connection() -> psycopg.Connection:
    """A cached, reused Postgres connection (autocommit for simple reads/writes)."""
    return psycopg.connect(_connection_string(), autocommit=True)


def health_check() -> bool:
    """True if the database answers a trivial query. Lets errors surface —
    the caller decides how to show them (do not hide errors, per CLAUDE.md)."""
    with get_connection().cursor() as cur:
        cur.execute("SELECT 1")
        return cur.fetchone() == (1,)
