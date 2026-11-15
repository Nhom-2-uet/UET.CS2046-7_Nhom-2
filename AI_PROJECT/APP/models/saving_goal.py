from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal


GoalStatus = Literal[
    "active",
    "finished",
    "failed",
    "cancelled",
]


@dataclass
class SavingGoal:
    goal_id: int
    user_id: int
    name: str
    target_amount_vnd: int
    deadline: date
    status: GoalStatus
    created_at: datetime

    def __post_init__(self) -> None:
        if self.target_amount_vnd <= 0:
            raise ValueError("target_amount_vnd phải lớn hơn 0.")

    # Tiến độ có thể âm nếu chi vượt cả quỹ đệm.
    progress_vnd: int = 0

    # Quỹ đệm không âm; chi vượt sẽ dùng quỹ này trước.
    buffer_vnd: int = 0
