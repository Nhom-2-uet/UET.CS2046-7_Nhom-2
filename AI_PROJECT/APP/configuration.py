"""Read application settings from local environment or Streamlit secrets."""

import os
from typing import Any


def get_setting(name: str, default: Any = None) -> Any:
    """Prefer environment variables, then Streamlit-managed secrets."""
    value = os.getenv(name)
    if value:
        return value

    try:
        import streamlit as st

        value = st.secrets.get(name)
    except Exception:
        # Streamlit is not initialized in standalone scripts and local tests.
        value = None

    return value if value not in (None, "") else default
