"""Route frontend commands to backend services and repositories."""

from datetime import date
from typing import Any

from services.application_service import execute


def dispatch(command: str, payload: dict[str, Any] | None = None) -> Any:
    """Run a supported application command and return its result.

    Keep this layer focused on routing. Business rules belong in services, while
    database access belongs in repositories.
    """
    data = payload or {}

    if command.startswith(("transaction.", "budget.", "expense.", "goal.", "finance.")):
        user_id = data.get("user_id")
        if user_id is None:
            raise ValueError("Vui lòng đăng nhập để thực hiện thao tác này.")
        data["user_id"] = int(user_id)

    if command in {"transaction.list"}:
        data["start_date"] = _optional_date(data.get("start_date"))
        data["end_date"] = _optional_date(data.get("end_date"))
    for key in ("transaction_date", "due_date", "deadline"):
        if key in data:
            data[key] = _optional_date(data[key])

    return execute(command, data)


def _optional_date(value: date | str | None) -> date | None:
    if value is None or isinstance(value, date):
        return value
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as error:
        raise ValueError("Ngày phải có dạng YYYY-MM-DD.") from error
