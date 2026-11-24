"""Frontend entry point for sending commands to the application backend."""

from datetime import date
from typing import Any

try:
    from APP.router import dispatch
    from APP.frontend.user_state import get_user_id
except ModuleNotFoundError:
    # Supports the current Streamlit launch layout where APP itself is on sys.path.
    from router import dispatch
    from user_state import get_user_id


def request(command: str, payload: dict[str, Any] | None = None) -> Any:
    """Send a command through the backend router and return its result."""
    request_data = dict(payload or {})
    if command.startswith(("transaction.", "budget.", "expense.", "goal.", "finance.")):
        user_id = get_user_id()
        if user_id is None:
            raise ValueError("Vui lòng đăng nhập để thực hiện thao tác này.")
        request_data["user_id"] = user_id
    return dispatch(command, request_data)


def login(username: str, password: str):
    user = request("auth.login", {"username": username, "password": password})
    try:
        from APP.frontend.user_state import set_user
    except ModuleNotFoundError:
        from user_state import set_user
    set_user(user)
    return user


def register(username: str, password: str, display_name: str):
    user = request(
        "auth.register",
        {"username": username, "password": password, "display_name": display_name},
    )
    try:
        from APP.frontend.user_state import set_user
    except ModuleNotFoundError:
        from user_state import set_user
    set_user(user)
    return user


def get_transactions(
    start_date: date | None = None,
    end_date: date | None = None,
    *,
    user_id: int | None = None,
) -> Any:
    """Convenience call for the transaction list command."""
    payload: dict[str, Any] = {}
    if start_date is not None:
        payload["start_date"] = start_date
    if end_date is not None:
        payload["end_date"] = end_date
    if user_id is not None:
        payload["user_id"] = user_id
    return request("transaction.list", payload)
