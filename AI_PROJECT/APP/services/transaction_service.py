"""Application services for transaction queries and operations."""

from datetime import date

from APP.models.transaction import Transaction
from APP.models.transaction import TransactionDraft
from services.logic.repositories.transaction_repository import (
    create_transaction,
    delete_transaction,
    get_category_id,
    get_transactions,
    update_transaction,
)


def list_transactions(
    user_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[Transaction]:
    """Return a user's transactions, optionally filtered by date."""
    return get_transactions(
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
    )


def save_transaction(user_id: int, data: dict, transaction_id: int | None = None):
    """Validate a UI payload and create or update a persisted transaction."""
    description = data.get("description")
    if not isinstance(description, str) or not description.strip():
        raise ValueError("Tên giao dịch không được để trống.")
    category_id = get_category_id(data["category_name"], data["transaction_type"])
    draft = TransactionDraft(
        category_id=category_id,
        transaction_type=data["transaction_type"],
        amount_vnd=int(data["amount_vnd"]),
        description=description.strip(),
        transaction_date=data["transaction_date"],
        input_source=data.get("input_source", "manual"),
        exclude_from_saving=bool(data.get("exclude_from_saving", False)),
    )
    if transaction_id is None:
        return create_transaction(user_id, draft)
    return update_transaction(user_id, transaction_id, draft)


def remove_transaction(user_id: int, transaction_id: int) -> bool:
    return delete_transaction(user_id, transaction_id)
