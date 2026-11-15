from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal


GoalStatus = Literal[
    "active",
    "completed",
    "paused",
    "cancelled",
    "failed",
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

    # Tiến độ có thể âm nếu chi vượt cả quỹ đệm.
    progress_vnd: int = 0

    # Quỹ đệm không âm; chi vượt sẽ dùng quỹ này trước.
    buffer_vnd: int = 0
