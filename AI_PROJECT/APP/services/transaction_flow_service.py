#----1.IMPORT----
"""Chuẩn bị giao dịch để xem trước và chỉ lưu sau khi xác nhận."""

from APP.models.transaction import Transaction, TransactionDraft
from datetime import date

from services.logic.repositories.transaction_repository import (
    create_transactions,
    create_transaction,
    get_categories,
    get_category_id,
)

#----3.TẠO BẢN NHÁP, CHƯA LƯU----
def prepare_transaction_draft(data: dict) -> TransactionDraft:
    """Kiểm tra dữ liệu AI và chuyển thành bản nháp giao dịch."""

    required_fields = {"amount", "category", "type", "description", "date"}
    missing_fields = required_fields - data.keys()

    if missing_fields:
        raise ValueError(
            "Thiếu thông tin: " + ", ".join(sorted(missing_fields))
        )

    amount = data["amount"]
    category_name = data["category"]
    transaction_type = data["type"]
    description = data["description"]

    if not isinstance(amount, int) or isinstance(amount, bool) or amount <= 0:
        raise ValueError("Số tiền phải là số nguyên dương.")

    if transaction_type not in {"income", "expense"}:
        raise ValueError("Loại giao dịch phải là income hoặc expense.")

    if not isinstance(category_name, str) or not category_name.strip():
        raise ValueError("Tên danh mục không được để trống.")

    if not isinstance(description, str) or not description.strip():
        raise ValueError("Mô tả không được để trống.")

    try:
        transaction_date = date.fromisoformat(data["date"])
    except (TypeError, ValueError) as error:
        raise ValueError("Ngày phải có dạng YYYY-MM-DD.") from error

    category_id = get_category_id(
        category_name.strip(),
        transaction_type,
    )

    return TransactionDraft(
        category_id=category_id,
        transaction_type=transaction_type,
        amount_vnd=amount,
        description=description.strip(),
        transaction_date=transaction_date,
        input_source="natural_language",
        exclude_from_saving=bool(data.get("exclude_from_saving", False)),
    )

#----4.CHỈ LƯU KHI XÁC NHẬN----
def confirm_and_save_transaction(
    user_id: int,
    draft: TransactionDraft,
    confirmed: bool,
) -> Transaction | None:
    """Chưa xác nhận thì không lưu; xác nhận rồi mới gọi CRUD."""

    if not confirmed:
        return None

    return create_transaction(user_id=user_id, draft=draft)


def get_transaction_categories(transaction_type: str) -> list[str]:
    """Return categories available for the selected transaction type."""
    return get_categories(transaction_type)


def confirm_and_save_transactions(
    user_id: int,
    drafts: list[TransactionDraft],
    confirmed: bool,
) -> list[Transaction]:
    """Save all reviewed drafts together only after explicit confirmation."""
    if not confirmed:
        return []
    return create_transactions(user_id=user_id, drafts=drafts)
