#Mô tả dữ liệu giao dịch dưới 2 dạng:
#TransactionDraft: AI nhận diện nhưng người dùng chưa xác nhận
#Transaction: Giao dịch đc xác nhận và lưu vào DB
from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal


TransactionType = Literal["income", "expense"]
InputSource = Literal["manual", "natural_language"]


@dataclass
class TransactionDraft:
    """Giao dịch đang chờ người dùng xem và xác nhận."""

    category_id: int
    transaction_type: TransactionType
    amount_vnd: int
    description: str | None
    transaction_date: date
    input_source: InputSource
    exclude_from_saving: bool = False

    def __post_init__(self) -> None:
        if self.category_id <= 0:
            raise ValueError("category_id phải là số nguyên dương.")

        if self.amount_vnd <= 0:
            raise ValueError("amount_vnd phải lớn hơn 0.")

        if self.transaction_type not in {"income", "expense"}:
            raise ValueError("transaction_type phải là income hoặc expense.")

        if self.input_source not in {"manual", "natural_language"}:
            raise ValueError(
                "input_source phải là manual hoặc natural_language."
            )


@dataclass
class Transaction:
    """Giao dịch đã được lưu trong database."""

    transaction_id: int
    user_id: int
    category_id: int
    transaction_type: TransactionType
    amount_vnd: int
    description: str | None
    transaction_date: date
    input_source: InputSource
    exclude_from_saving: bool
    created_at: datetime
    updated_at: datetime
