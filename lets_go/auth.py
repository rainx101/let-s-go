"""Simple password gate. Not multi-user auth — just keeps the deployed app
private to the owner (PRD: single user, password login)."""

import hmac

import streamlit as st


def _password_correct(entered: str) -> bool:
    """Constant-time compare against the password in secrets."""
    expected = st.secrets.get("app", {}).get("password", "")
    return bool(expected) and hmac.compare_digest(entered, expected)


def require_login() -> None:
    """Block the app until the correct password is entered. Call once at the
    top of the app; it stops the script (st.stop) while logged out."""
    if st.session_state.get("authenticated"):
        return

    st.title("let's go")
    entered = st.text_input("Password", type="password")
    if entered:
        if _password_correct(entered):
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    st.stop()
