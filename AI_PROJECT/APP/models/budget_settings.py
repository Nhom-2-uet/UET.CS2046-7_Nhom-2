from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass
class BudgetSettings:
    setting_id: int
    user_id: int
    monthly_budget_vnd: int
    weekday_daily_limit_vnd: int
    weekend_daily_limit_vnd: int
    payday: int | None
    reserve_rate: Decimal
    updated_at: datetime

    def __post_init__(self) -> None:
        if not 0 <= self.reserve_rate <= 1:
            raise ValueError("reserve_rate phải nằm trong khoảng từ 0 đến 1.")

        if self.payday is not None and not 1 <= self.payday <= 31:
            raise ValueError("payday phải nằm trong khoảng từ 1 đến 31.")
