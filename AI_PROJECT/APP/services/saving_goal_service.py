"""Các thao tác database cho mục tiêu tiết kiệm và tiến trình hằng ngày.

Service này lưu kết quả do phần logic tính ra; nó không tự tính quy tắc
chi vượt, bù tiến độ hay phân bổ khoản dư.
"""

# ---- (1. IMPORT) ----
from contextlib import contextmanager
from datetime import date
from typing import Any, Iterator

from APP.models.saving_goal import GoalStatus, SavingGoal
from APP.models.saving_goal_daily_progress import (
    SavingGoalDailyProgress,
    SurplusAction,
)
from database.connection import get_connection


# ---- (2. DATABASE COLUMNS) ----
GOAL_COLUMNS = """
    SELECT
        goal_id, user_id, name, target_amount_vnd, deadline,
        status, created_at, progress_vnd, buffer_vnd
    FROM saving_goals
"""

PROGRESS_COLUMNS = """
    SELECT
        progress_id, goal_id, progress_date,
        planned_spending_limit_vnd, actual_spending_vnd,
        planned_saving_vnd, progress_change_vnd, buffer_change_vnd,
        progress_after_vnd, buffer_after_vnd, surplus_action, created_at
    FROM saving_goal_daily_progress
"""

ALLOWED_STATUSES = {"active", "paused", "finished", "failed", "cancelled"}
TERMINAL_STATUSES = {"finished", "failed", "cancelled"}
ALLOWED_SURPLUS_ACTIONS = {"to_goal", "to_buffer", "none"}


# ---- (3. OPEN CONNECTION AND CURSOR) ----
@contextmanager
def _open_cursor() -> Iterator[Any]:
    """Mở kết nối; commit nếu thành công, rollback nếu có lỗi, rồi đóng lại."""
    connection = get_connection()
    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)
        yield cursor
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()


# ---- (4. CONVERT DATABASE ROWS TO PYTHON MODELS) ----
def _row_to_goal(row: dict[str, Any]) -> SavingGoal:
    """Đổi một dòng saving_goals thành đối tượng SavingGoal."""
    return SavingGoal(
        goal_id=row["goal_id"],
        user_id=row["user_id"],
        name=row["name"],
        target_amount_vnd=row["target_amount_vnd"],
        deadline=row["deadline"],
        status=row["status"],
        created_at=row["created_at"],
        progress_vnd=row["progress_vnd"],
        buffer_vnd=row["buffer_vnd"],
    )


def _row_to_daily_progress(row: dict[str, Any]) -> SavingGoalDailyProgress:
    """Đổi một dòng lịch sử thành đối tượng SavingGoalDailyProgress."""
    return SavingGoalDailyProgress(
        progress_id=row["progress_id"],
        goal_id=row["goal_id"],
        progress_date=row["progress_date"],
        planned_spending_limit_vnd=row["planned_spending_limit_vnd"],
        actual_spending_vnd=row["actual_spending_vnd"],
        planned_saving_vnd=row["planned_saving_vnd"],
        progress_change_vnd=row["progress_change_vnd"],
        buffer_change_vnd=row["buffer_change_vnd"],
        progress_after_vnd=row["progress_after_vnd"],
        buffer_after_vnd=row["buffer_after_vnd"],
        surplus_action=row["surplus_action"],
        created_at=row["created_at"],
    )


def _check_positive(value: int, name: str) -> None:
    """Báo lỗi nếu ID không phải số nguyên dương."""
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{name} phải là số nguyên dương.")


def _check_non_negative(value: int, name: str) -> None:
    """Báo lỗi nếu số tiền không phải số nguyên không âm."""
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{name} phải là số nguyên không âm.")


def _ensure_no_other_active_goal(
    cursor: Any,
    user_id: int,
    exclude_goal_id: int | None = None,
) -> None:
    """Chặn tạo/kích hoạt mục tiêu nếu user đã có mục tiêu active khác."""
    query = """
        SELECT goal_id
        FROM saving_goals
        WHERE user_id = %s AND status = 'active'
    """
    parameters: list[Any] = [user_id]

    if exclude_goal_id is not None:
        query += " AND goal_id <> %s"
        parameters.append(exclude_goal_id)

    query += " LIMIT 1 FOR UPDATE"
    cursor.execute(query, tuple(parameters))
    if cursor.fetchone() is not None:
        raise ValueError("Bạn đã có một kế hoạch tiết kiệm đang chạy.")


# ---- (5. CREATE: CREATE A SAVING GOAL) ----
def create_saving_goal(
    user_id: int,
    name: str,
    target_amount_vnd: int,
    deadline: date,
) -> SavingGoal:
    """Tạo mục tiêu mới, ban đầu tiến độ và quỹ đệm đều bằng 0."""
    _check_positive(user_id, "user_id")
    _check_positive(target_amount_vnd, "target_amount_vnd")

    if not isinstance(name, str) or not name.strip():
        raise ValueError("Tên mục tiêu không được để trống.")
    if not isinstance(deadline, date):
        raise ValueError("deadline phải là ngày hợp lệ.")

    with _open_cursor() as cursor:
        # Mỗi người dùng chỉ được có một mục tiêu đang chạy tại một thời điểm.
        _ensure_no_other_active_goal(cursor, user_id)
        cursor.execute(
            """
            INSERT INTO saving_goals (
                user_id, name, target_amount_vnd, deadline,
                status, progress_vnd, buffer_vnd
            )
            VALUES (%s, %s, %s, %s, 'active', 0, 0)
            """,
            (user_id, name.strip(), target_amount_vnd, deadline),
        )
        goal_id = cursor.lastrowid
        cursor.execute(
            GOAL_COLUMNS + " WHERE goal_id = %s AND user_id = %s",
            (goal_id, user_id),
        )
        row = cursor.fetchone()

        if row is None:
            raise RuntimeError("Không đọc lại được mục tiêu vừa tạo.")
        return _row_to_goal(row)


# ---- (6. READ: READ ONE GOAL OR A USER'S GOALS) ----
def get_saving_goal(user_id: int, goal_id: int) -> SavingGoal | None:
    """Đọc một mục tiêu; trả None nếu không tìm thấy hoặc không thuộc user."""
    _check_positive(user_id, "user_id")
    _check_positive(goal_id, "goal_id")

    with _open_cursor() as cursor:
        cursor.execute(
            GOAL_COLUMNS + " WHERE goal_id = %s AND user_id = %s",
            (goal_id, user_id),
        )
        row = cursor.fetchone()
        return _row_to_goal(row) if row is not None else None


def get_saving_goals(
    user_id: int,
    status: GoalStatus | None = None,
) -> list[SavingGoal]:
    """Đọc các mục tiêu của user; có thể lọc theo trạng thái."""
    _check_positive(user_id, "user_id")
    if status is not None and status not in ALLOWED_STATUSES:
        raise ValueError("Trạng thái mục tiêu không hợp lệ.")

    query = GOAL_COLUMNS + " WHERE user_id = %s"
    parameters: list[Any] = [user_id]
    if status is not None:
        query += " AND status = %s"
        parameters.append(status)
    query += " ORDER BY created_at DESC, goal_id DESC"

    with _open_cursor() as cursor:
        cursor.execute(query, tuple(parameters))
        return [_row_to_goal(row) for row in cursor.fetchall()]


# ---- (7. UPDATE: UPDATE GOAL DETAILS OR STATUS) ----
def update_saving_goal_details(
    user_id: int,
    goal_id: int,
    target_amount_vnd: int,
    deadline: date,
) -> SavingGoal | None:
    """Chỉ sửa số tiền mục tiêu và kỳ hạn; giữ nguyên tiến độ/quỹ đệm."""
    _check_positive(user_id, "user_id")
    _check_positive(goal_id, "goal_id")
    _check_positive(target_amount_vnd, "target_amount_vnd")
    if not isinstance(deadline, date):
        raise ValueError("deadline phải là ngày hợp lệ.")

    with _open_cursor() as cursor:
        cursor.execute(
            """
            UPDATE saving_goals
            SET target_amount_vnd = %s, deadline = %s
            WHERE goal_id = %s AND user_id = %s
              AND status IN ('active', 'paused')
            """,
            (target_amount_vnd, deadline, goal_id, user_id),
        )
        cursor.execute(
            GOAL_COLUMNS + " WHERE goal_id = %s AND user_id = %s",
            (goal_id, user_id),
        )
        row = cursor.fetchone()
        return _row_to_goal(row) if row is not None else None


def set_saving_goal_status(
    user_id: int,
    goal_id: int,
    status: GoalStatus,
) -> SavingGoal | None:
    """Lưu trạng thái do luồng ứng dụng/logic quyết định."""
    _check_positive(user_id, "user_id")
    _check_positive(goal_id, "goal_id")
    if status not in ALLOWED_STATUSES:
        raise ValueError("Trạng thái mục tiêu không hợp lệ.")

    with _open_cursor() as cursor:
        # Đọc và khóa kế hoạch để không thể mở lại mục tiêu đã kết thúc.
        cursor.execute(
            """
            SELECT status
            FROM saving_goals
            WHERE goal_id = %s AND user_id = %s
            FOR UPDATE
            """,
            (goal_id, user_id),
        )
        current_goal = cursor.fetchone()
        if current_goal is None:
            return None
        if (
            current_goal["status"] in TERMINAL_STATUSES
            and status != current_goal["status"]
        ):
            raise ValueError("Kế hoạch đã kết thúc nên không thể đổi trạng thái.")

        # Khi kích hoạt lại mục tiêu, không cho chạy song song với mục tiêu khác.
        if status == "active":
            _ensure_no_other_active_goal(cursor, user_id, exclude_goal_id=goal_id)
        cursor.execute(
            """
            UPDATE saving_goals
            SET status = %s
            WHERE goal_id = %s AND user_id = %s
            """,
            (status, goal_id, user_id),
        )
        cursor.execute(
            GOAL_COLUMNS + " WHERE goal_id = %s AND user_id = %s",
            (goal_id, user_id),
        )
        row = cursor.fetchone()
        return _row_to_goal(row) if row is not None else None


def cancel_saving_goal(user_id: int, goal_id: int) -> SavingGoal | None:
    """Hủy một mục tiêu đang chạy/tạm dừng; giữ nguyên tiến độ và lịch sử."""
    return set_saving_goal_status(
        user_id=user_id,
        goal_id=goal_id,
        status="cancelled",
    )


# ---- (8. SAVE DAILY RESULT: SAVE LOGIC'S CALCULATION) ----
def save_daily_progress(
    user_id: int,
    goal_id: int,
    progress_date: date,
    planned_spending_limit_vnd: int,
    actual_spending_vnd: int,
    planned_saving_vnd: int,
    progress_change_vnd: int,
    buffer_change_vnd: int,
    progress_after_vnd: int,
    buffer_after_vnd: int,
    surplus_action: SurplusAction = "none",
) -> SavingGoalDailyProgress | None:
    """Lưu kết quả đã được tính cho một ngày và đồng bộ số dư mục tiêu.

    Nếu cùng mục tiêu/ngày đã có bản ghi, bản ghi đó được cập nhật thay vì
    tạo dòng trùng. Trả None nếu mục tiêu không tồn tại hoặc không thuộc user.
    """
    _check_positive(user_id, "user_id")
    _check_positive(goal_id, "goal_id")
    for value, field in (
        (planned_spending_limit_vnd, "planned_spending_limit_vnd"),
        (actual_spending_vnd, "actual_spending_vnd"),
        (planned_saving_vnd, "planned_saving_vnd"),
        (buffer_after_vnd, "buffer_after_vnd"),
    ):
        _check_non_negative(value, field)
    if not isinstance(progress_date, date):
        raise ValueError("progress_date phải là ngày hợp lệ.")
    if not isinstance(progress_change_vnd, int) or isinstance(progress_change_vnd, bool):
        raise ValueError("progress_change_vnd phải là số nguyên.")
    if not isinstance(buffer_change_vnd, int) or isinstance(buffer_change_vnd, bool):
        raise ValueError("buffer_change_vnd phải là số nguyên.")
    if not isinstance(progress_after_vnd, int) or isinstance(progress_after_vnd, bool):
        raise ValueError("progress_after_vnd phải là số nguyên.")
    if surplus_action not in ALLOWED_SURPLUS_ACTIONS:
        raise ValueError("surplus_action không hợp lệ.")

    with _open_cursor() as cursor:
        # Khóa dòng mục tiêu trong giao dịch để tránh hai lần cập nhật đồng thời.
        cursor.execute(
            """
            SELECT goal_id
            FROM saving_goals
            WHERE goal_id = %s AND user_id = %s
            FOR UPDATE
            """,
            (goal_id, user_id),
        )
        if cursor.fetchone() is None:
            return None

        # Lưu một kết quả tổng kết cho mục tiêu/ngày; chạy lại sẽ cập nhật nó.
        cursor.execute(
            """
            INSERT INTO saving_goal_daily_progress (
                goal_id, progress_date,
                planned_spending_limit_vnd, actual_spending_vnd,
                planned_saving_vnd, progress_change_vnd, buffer_change_vnd,
                progress_after_vnd, buffer_after_vnd, surplus_action
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                planned_spending_limit_vnd = VALUES(planned_spending_limit_vnd),
                actual_spending_vnd = VALUES(actual_spending_vnd),
                planned_saving_vnd = VALUES(planned_saving_vnd),
                progress_change_vnd = VALUES(progress_change_vnd),
                buffer_change_vnd = VALUES(buffer_change_vnd),
                progress_after_vnd = VALUES(progress_after_vnd),
                buffer_after_vnd = VALUES(buffer_after_vnd),
                surplus_action = VALUES(surplus_action)
            """,
            (
                goal_id,
                progress_date,
                planned_spending_limit_vnd,
                actual_spending_vnd,
                planned_saving_vnd,
                progress_change_vnd,
                buffer_change_vnd,
                progress_after_vnd,
                buffer_after_vnd,
                surplus_action,
            ),
        )

        # Ghi số dư mới vào mục tiêu để app đọc nhanh trạng thái hiện tại.
        cursor.execute(
            """
            UPDATE saving_goals
            SET progress_vnd = %s, buffer_vnd = %s
            WHERE goal_id = %s AND user_id = %s
            """,
            (progress_after_vnd, buffer_after_vnd, goal_id, user_id),
        )

        cursor.execute(
            PROGRESS_COLUMNS + " WHERE goal_id = %s AND progress_date = %s",
            (goal_id, progress_date),
        )
        row = cursor.fetchone()
        if row is None:
            raise RuntimeError("Không đọc lại được lịch sử tiến trình vừa lưu.")
        return _row_to_daily_progress(row)


# ---- (9. READ: READ GOAL'S DAILY HISTORY) ----
def get_daily_progress_history(
    user_id: int,
    goal_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[SavingGoalDailyProgress]:
    """Đọc lịch sử theo ngày của một mục tiêu thuộc user."""
    _check_positive(user_id, "user_id")
    _check_positive(goal_id, "goal_id")
    if start_date and end_date and start_date > end_date:
        raise ValueError("start_date không được sau end_date.")

    query = (
        PROGRESS_COLUMNS
        + " WHERE goal_id = %s"
        + " AND EXISTS (SELECT 1 FROM saving_goals g"
        + " WHERE g.goal_id = saving_goal_daily_progress.goal_id"
        + " AND g.user_id = %s)"
    )
    parameters: list[Any] = [goal_id, user_id]
    if start_date is not None:
        query += " AND progress_date >= %s"
        parameters.append(start_date)
    if end_date is not None:
        query += " AND progress_date <= %s"
        parameters.append(end_date)
    query += " ORDER BY progress_date, progress_id"

    with _open_cursor() as cursor:
        cursor.execute(query, tuple(parameters))
        return [_row_to_daily_progress(row) for row in cursor.fetchall()]
