# ---- (1. IMPORT) ----
from contextlib import contextmanager
from typing import Any, Iterator

from APP.models.budget_settings import BudgetSettings
from database.connection import get_connection


# ---- (2. MỞ KẾT NỐI DATABASE) ----
@contextmanager
def _open_cursor() -> Iterator[Any]:
    """Mở cursor; lưu thay đổi nếu thành công, hoàn tác nếu gặp lỗi."""
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


# ---- (3. CHUYỂN DÒNG DATABASE THÀNH MODEL PYTHON) ----
def _row_to_budget_settings(row: dict[str, Any]) -> BudgetSettings:
    """Chuyển một dòng trong budget_settings thành BudgetSettings."""
    return BudgetSettings(
        setting_id=row["setting_id"],
        user_id=row["user_id"],
        monthly_budget_vnd=row["monthly_budget_vnd"],
        payday=row["payday"],
        reserve_rate=row["reserve_rate"],
        updated_at=row["updated_at"],
    )


# ---- (4. KIỂM TRA DỮ LIỆU ĐẦU VÀO) ----
def _check_positive(value: int, name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{name} phải là số nguyên dương.")


def _check_non_negative(value: int, name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{name} phải là số nguyên không âm.")


# ---- (5. READ: ĐỌC THIẾT LẬP NGÂN SÁCH) ----
def get_budget_settings(user_id: int) -> BudgetSettings | None:
    """Đọc thiết lập ngân sách của user; trả None nếu chưa có."""
    _check_positive(user_id, "user_id")

    with _open_cursor() as cursor:
        cursor.execute(
            """
            SELECT
                setting_id,
                user_id,
                monthly_budget_vnd,
                payday,
                reserve_rate,
                updated_at
            FROM budget_settings
            WHERE user_id = %s
            """,
            (user_id,),
        )
        row = cursor.fetchone()

    return _row_to_budget_settings(row) if row is not None else None


# ---- (6. CREATE / UPDATE: LƯU THIẾT LẬP NGÂN SÁCH) ----
def save_budget_settings(
    user_id: int,
    monthly_budget_vnd: int,
    payday: int | None = None,
) -> BudgetSettings:
    """Tạo thiết lập lần đầu hoặc cập nhật ngân sách đã có."""

    # Kiểm tra mã người dùng và số tiền ngân sách.
    _check_positive(user_id, "user_id")
    _check_non_negative(monthly_budget_vnd, "monthly_budget_vnd")

    # payday có thể để trống; nếu nhập thì phải là ngày 1 đến 31.
    if payday is not None:
        if not isinstance(payday, int) or isinstance(payday, bool) or not 1 <= payday <= 31:
            raise ValueError("payday phải nằm trong khoảng từ 1 đến 31.")

    with _open_cursor() as cursor:
        # user_id là duy nhất trong bảng:
        # chưa có thì thêm dòng, đã có thì cập nhật ngân sách và ngày nhận tiền.
        cursor.execute(
            """
            INSERT INTO budget_settings (
                user_id,
                monthly_budget_vnd,
                payday
            )
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE
                monthly_budget_vnd = VALUES(monthly_budget_vnd),
                payday = VALUES(payday)
            """,
            (user_id, monthly_budget_vnd, payday),
        )

        # Đọc lại dòng vừa lưu để trả về model Python.
        cursor.execute(
            """
            SELECT
                setting_id,
                user_id,
                monthly_budget_vnd,
                payday,
                reserve_rate,
                updated_at
            FROM budget_settings
            WHERE user_id = %s
            """,
            (user_id,),
        )
        row = cursor.fetchone()

        if row is None:
            raise RuntimeError("Không đọc lại được thiết lập ngân sách vừa lưu.")

        return _row_to_budget_settings(row)