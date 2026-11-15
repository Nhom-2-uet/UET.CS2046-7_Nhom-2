# ---- (1. IMPORT KIỂU DỮ LIỆU) ----
from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal


# ---- (2. CÁCH XỬ LÝ KHOẢN DƯ) ----
# Các giá trị này khớp với ENUM surplus_action trong database.
SurplusAction = Literal["to_goal", "to_buffer", "none"]


# ---- (3. MODEL TIẾN TRÌNH TIẾT KIỆM MỘT NGÀY) ----
@dataclass
class SavingGoalDailyProgress:
    """Đại diện cho bản ghi theo dõi một mục tiêu trong một ngày."""

    progress_id: int
    goal_id: int
    progress_date: date

    # Hạn mức chi và khoản chi thực tế của ngày đó.
    planned_spending_limit_vnd: int
    actual_spending_vnd: int

    # Khoản tiết kiệm cơ bản theo kế hoạch trong ngày.
    planned_saving_vnd: int

    # Mức thay đổi trong ngày; các giá trị này có thể âm.
    progress_change_vnd: int
    buffer_change_vnd: int

    # Số dư sau khi cập nhật cuối ngày.
    progress_after_vnd: int
    buffer_after_vnd: int

    # Người dùng chọn đưa khoản dư vào mục tiêu, vào quỹ đệm,
    # hoặc ngày đó không có khoản dư.
    surplus_action: SurplusAction

    created_at: datetime
