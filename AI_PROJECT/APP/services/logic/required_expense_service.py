"""Các thao tác dữ liệu cho những khoản chi bắt buộc."""

# ---- (1. IMPORT VÀ CẤU HÌNH CÁC CỘT) ----
from contextlib import contextmanager
from datetime import date
from typing import Any, Iterator

from APP.models.required_expense import ExpenseStatus, RequiredExpense
from database.connection import get_connection


_SELECT_COLUMNS = """
    SELECT
        expense_id, user_id, name, amount_vnd,
        due_date, status, paid_transaction_id
    FROM required_expenses
"""

_ALLOWED_STATUSES = {"unpaid", "paid", "cancelled"}


# ---- (2. MỞ KẾT NỐI VÀ CURSOR) ----
@contextmanager
def _open_cursor() -> Iterator[Any]:
    """Commit nếu thao tác thành công; rollback nếu lỗi; luôn đóng kết nối."""
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


# ---- (3. ĐỔI DÒNG DATABASE THÀNH MODEL PYTHON) ----
def _row_to_required_expense(row: dict[str, Any]) -> RequiredExpense:
    return RequiredExpense(
        expense_id=row["expense_id"],
        user_id=row["user_id"],
        name=row["name"],
        amount_vnd=row["amount_vnd"],
        due_date=row["due_date"],
        status=row["status"],
        paid_transaction_id=row["paid_transaction_id"],
    )


# ---- (4. KIỂM TRA DỮ LIỆU ĐẦU VÀO) ----
def _check_positive(value: int, name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{name} phải là số nguyên dương.")


def _check_expense_details(name: str, amount_vnd: int, due_date: date) -> None:
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Tên khoản chi không được để trống.")
    _check_positive(amount_vnd, "amount_vnd")
    # datetime cũng là một kiểu date trong Python; chỉ nhận ngày thuần.
    if not isinstance(due_date, date) or hasattr(due_date, "hour"):
        raise ValueError("due_date phải là ngày hợp lệ.")


def _get_expense_row(cursor: Any, user_id: int, expense_id: int) -> dict[str, Any] | None:
    cursor.execute(
        _SELECT_COLUMNS + " WHERE user_id = %s AND expense_id = %s",
        (user_id, expense_id),
    )
    return cursor.fetchone()


# ---- (5. CREATE: TẠO KHOẢN CHI BẮT BUỘC) ----
def create_required_expense(
    user_id: int,
    name: str,
    amount_vnd: int,
    due_date: date,
) -> RequiredExpense:
    """Tạo một khoản chi mới với trạng thái ban đầu là unpaid."""
    _check_positive(user_id, "user_id")
    _check_expense_details(name, amount_vnd, due_date)

    with _open_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO required_expenses (user_id, name, amount_vnd, due_date)
            VALUES (%s, %s, %s, %s)
            """,
            (user_id, name.strip(), amount_vnd, due_date),
        )
        expense_id = cursor.lastrowid
        row = _get_expense_row(cursor, user_id, expense_id)
        if row is None:
            raise RuntimeError("Không đọc lại được khoản chi vừa tạo.")
        return _row_to_required_expense(row)


# ---- (6. READ: ĐỌC MỘT KHOẢN CHI) ----
def get_required_expense(user_id: int, expense_id: int) -> RequiredExpense | None:
    """Đọc một khoản chi thuộc về user; không tìm thấy thì trả None."""
    _check_positive(user_id, "user_id")
    _check_positive(expense_id, "expense_id")

    with _open_cursor() as cursor:
        row = _get_expense_row(cursor, user_id, expense_id)
    return _row_to_required_expense(row) if row is not None else None


# ---- (7. READ: ĐỌC DANH SÁCH KHOẢN CHI) ----
def get_required_expenses(
    user_id: int,
    status: ExpenseStatus | None = None,
) -> list[RequiredExpense]:
    """Đọc các khoản chi của user, có thể lọc theo unpaid/paid/cancelled."""
    _check_positive(user_id, "user_id")
    if status is not None and status not in _ALLOWED_STATUSES:
        raise ValueError("status phải là unpaid, paid hoặc cancelled.")

    query = _SELECT_COLUMNS + " WHERE user_id = %s"
    parameters: list[Any] = [user_id]
    if status is not None:
        query += " AND status = %s"
        parameters.append(status)
    query += " ORDER BY due_date, expense_id"

    with _open_cursor() as cursor:
        cursor.execute(query, tuple(parameters))
        rows = cursor.fetchall()
    return [_row_to_required_expense(row) for row in rows]


# ---- (8. UPDATE: SỬA KHOẢN CHI CHƯA THANH TOÁN) ----
def update_required_expense(
    user_id: int,
    expense_id: int,
    name: str,
    amount_vnd: int,
    due_date: date,
) -> RequiredExpense | None:
    """Sửa tên, số tiền, ngày đến hạn; chỉ sửa khoản còn unpaid."""
    _check_positive(user_id, "user_id")
    _check_positive(expense_id, "expense_id")
    _check_expense_details(name, amount_vnd, due_date)

    with _open_cursor() as cursor:
        cursor.execute(
            """
            UPDATE required_expenses
            SET name = %s, amount_vnd = %s, due_date = %s
            WHERE user_id = %s AND expense_id = %s AND status = 'unpaid'
            """,
            (name.strip(), amount_vnd, due_date, user_id, expense_id),
        )
        row = _get_expense_row(cursor, user_id, expense_id)

    if row is None or row["status"] != "unpaid":
        return None
    return _row_to_required_expense(row)


# ---- (9. DELETE: XÓA KHOẢN CHI CHƯA THANH TOÁN) ----
def delete_required_expense(user_id: int, expense_id: int) -> bool:
    """Xóa khoản unpaid; không xóa bản ghi đã thanh toán hoặc đã hủy."""
    _check_positive(user_id, "user_id")
    _check_positive(expense_id, "expense_id")

    with _open_cursor() as cursor:
        cursor.execute(
            """
            DELETE FROM required_expenses
            WHERE user_id = %s AND expense_id = %s AND status = 'unpaid'
            """,
            (user_id, expense_id),
        )
        return cursor.rowcount == 1


# ---- (10. ĐÁNH DẤU ĐÃ THANH TOÁN) ----
def mark_required_expense_paid(
    user_id: int,
    expense_id: int,
    paid_transaction_id: int,
) -> RequiredExpense | None:
    """Gắn khoản bắt buộc với transaction chi đã lưu; không tạo transaction."""
    _check_positive(user_id, "user_id")
    _check_positive(expense_id, "expense_id")
    _check_positive(paid_transaction_id, "paid_transaction_id")

    with _open_cursor() as cursor:
        # Chặn liên kết nhầm transaction của user khác hoặc transaction thu.
        cursor.execute(
            """
            SELECT transaction_id
            FROM transactions
            WHERE transaction_id = %s
              AND user_id = %s
              AND transaction_type = 'expense'
            """,
            (paid_transaction_id, user_id),
        )
        if cursor.fetchone() is None:
            raise ValueError("Không tìm thấy giao dịch chi này của user.")

        cursor.execute(
            """
            SELECT expense_id
            FROM required_expenses
            WHERE paid_transaction_id = %s AND expense_id <> %s
            LIMIT 1
            FOR UPDATE
            """,
            (paid_transaction_id, expense_id),
        )
        if cursor.fetchone() is not None:
            raise ValueError("Giao dịch này đã được gắn với khoản chi bắt buộc khác.")

        cursor.execute(
            """
            UPDATE required_expenses
            SET status = 'paid', paid_transaction_id = %s
            WHERE user_id = %s AND expense_id = %s AND status = 'unpaid'
            """,
            (paid_transaction_id, user_id, expense_id),
        )
        row = _get_expense_row(cursor, user_id, expense_id)

    if row is None or row["status"] != "paid":
        return None
    return _row_to_required_expense(row)
