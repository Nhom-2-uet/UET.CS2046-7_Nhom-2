"""Helpers for temporary, per-session frontend state."""

import streamlit as st


USER_ID_KEY = "current_user_id"
DISPLAY_NAME_KEY = "current_user_display_name"


def get_user_id() -> int | None:
    """Return the current session's user ID, if one has been set."""
    user_id = st.session_state.get(USER_ID_KEY)
    return int(user_id) if user_id is not None else None


def set_user_id(user_id: int | None) -> None:
    """Set or clear the current session's user ID."""
    if user_id is None:
        st.session_state.pop(USER_ID_KEY, None)
        return
    if isinstance(user_id, bool) or int(user_id) <= 0:
        raise ValueError("user_id phải là số nguyên dương.")
    st.session_state[USER_ID_KEY] = int(user_id)


def set_user(user) -> None:
    set_user_id(user.user_id if user is not None else None)
    if user is None:
        st.session_state.pop(DISPLAY_NAME_KEY, None)
    else:
        st.session_state[DISPLAY_NAME_KEY] = user.display_name


def get_display_name() -> str | None:
    return st.session_state.get(DISPLAY_NAME_KEY)


def get_value(key: str, default=None):
    """Read an arbitrary temporary value from this Streamlit session."""
    return st.session_state.get(key, default)


def set_value(key: str, value) -> None:
    """Store an arbitrary temporary value in this Streamlit session."""
    st.session_state[key] = value
