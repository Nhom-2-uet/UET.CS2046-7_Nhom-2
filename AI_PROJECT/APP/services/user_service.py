"""Đăng ký, xác thực và quản lý hồ sơ tài khoản người dùng."""

# ---- (1. IMPORT VÀ THIẾT LẬP BẢO MẬT MẬT KHẨU) ----
import hashlib
import hmac
import secrets
from contextlib import contextmanager
from typing import Any, Iterator

from APP.models.user import User
from database.connection import get_connection


_PASSWORD_HASH_ALGORITHM = "pbkdf2_sha256"
_PASSWORD_HASH_ITERATIONS = 600_000


# ---- (2. MỞ KẾT NỐI VÀ CURSOR) ----
@contextmanager
def _open_cursor() -> Iterator[Any]:
    """Commit khi thành công, rollback khi lỗi, rồi luôn đóng kết nối."""
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


# ---- (3. CHUYỂN DÒNG DATABASE THÀNH MODEL) ----
def _row_to_user(row: dict[str, Any]) -> User:
    """Chuyển một dòng database thành model User, không đưa password hash ra ngoài."""
    return User(
        user_id=row["user_id"],
        display_name=row["display_name"],
        created_at=row["created_at"],
        username=row["username"],
    )


def _fetch_user_by_id(cursor: Any, user_id: int) -> dict[str, Any] | None:
    cursor.execute(
        """
        SELECT user_id, display_name, username, created_at
        FROM users
        WHERE user_id = %s
        """,
        (user_id,),
    )
    return cursor.fetchone()


# ---- (4. KIỂM TRA VÀ BĂM MẬT KHẨU) ----
def _check_positive_id(user_id: int) -> None:
    if not isinstance(user_id, int) or isinstance(user_id, bool) or user_id <= 0:
        raise ValueError("user_id phải là số nguyên dương.")


def _clean_username(username: str) -> str:
    if not isinstance(username, str):
        raise ValueError("Tên đăng nhập phải là chữ.")
    username = username.strip().lower()
    if not 3 <= len(username) <= 100:
        raise ValueError("Tên đăng nhập phải dài từ 3 đến 100 ký tự.")
    return username


def _check_password(password: str) -> None:
    if not isinstance(password, str) or len(password) < 8:
        raise ValueError("Mật khẩu phải có ít nhất 8 ký tự.")


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, _PASSWORD_HASH_ITERATIONS
    )
    # Lưu thuật toán, số vòng lặp, muối ngẫu nhiên và kết quả băm.
    return "$".join(
        (
            _PASSWORD_HASH_ALGORITHM,
            str(_PASSWORD_HASH_ITERATIONS),
            salt.hex(),
            password_hash.hex(),
        )
    )


def _password_matches(password: str, stored_hash: str) -> bool:
    if not isinstance(stored_hash, str):
        return False
    try:
        algorithm, iterations_text, salt_hex, expected_hash = stored_hash.split("$")
        if algorithm != _PASSWORD_HASH_ALGORITHM:
            return False
        actual_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(iterations_text),
        ).hex()
        return hmac.compare_digest(actual_hash, expected_hash)
    except (ValueError, TypeError):
        return False


# ---- (5. CREATE: ĐĂNG KÝ TÀI KHOẢN) ----
def create_user(username: str, password: str, display_name: str) -> User:
    """Tạo user mới; mật khẩu chỉ được lưu dưới dạng băm."""
    username = _clean_username(username)
    _check_password(password)
    if not isinstance(display_name, str) or not display_name.strip():
        raise ValueError("Tên hiển thị không được để trống.")
    if len(display_name.strip()) > 100:
        raise ValueError("Tên hiển thị không được dài quá 100 ký tự.")

    password_hash = _hash_password(password)
    with _open_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO users (display_name, username, password_hash)
            VALUES (%s, %s, %s)
            """,
            (display_name.strip(), username, password_hash),
        )
        row = _fetch_user_by_id(cursor, cursor.lastrowid)
        if row is None:
            raise RuntimeError("Không đọc lại được tài khoản vừa tạo.")
        return _row_to_user(row)


# ---- (5B. GẮN THÔNG TIN ĐĂNG NHẬP VÀO HỒ SƠ CŨ) ----
def add_login_to_existing_user(
    user_id: int,
    username: str,
    password: str,
) -> User | None:
    """Gắn username/mật khẩu cho hồ sơ mẫu cũ chưa có thông tin đăng nhập."""
    _check_positive_id(user_id)
    username = _clean_username(username)
    _check_password(password)

    with _open_cursor() as cursor:
        cursor.execute(
            """
            UPDATE users
            SET username = %s, password_hash = %s
            WHERE user_id = %s AND username IS NULL AND password_hash IS NULL
            """,
            (username, _hash_password(password), user_id),
        )
        row = _fetch_user_by_id(cursor, user_id)
    return _row_to_user(row) if row is not None and row["username"] else None


# ---- (6. READ: ĐỌC HỒ SƠ USER) ----
def get_user(user_id: int) -> User | None:
    _check_positive_id(user_id)
    with _open_cursor() as cursor:
        row = _fetch_user_by_id(cursor, user_id)
    return _row_to_user(row) if row is not None else None


# ---- (7. READ: KIỂM TRA ĐĂNG NHẬP) ----
def authenticate_user(username: str, password: str) -> User | None:
    """Trả hồ sơ nếu tên đăng nhập/mật khẩu đúng; sai thì trả None."""
    username = _clean_username(username)
    if not isinstance(password, str):
        return None

    with _open_cursor() as cursor:
        cursor.execute(
            """
            SELECT user_id, display_name, username, password_hash, created_at
            FROM users
            WHERE username = %s
            """,
            (username,),
        )
        row = cursor.fetchone()

    if row is None or not _password_matches(password, row["password_hash"]):
        return None
    return _row_to_user(row)


# ---- (8. UPDATE: SỬA TÊN HIỂN THỊ) ----
def update_display_name(user_id: int, display_name: str) -> User | None:
    _check_positive_id(user_id)
    if not isinstance(display_name, str) or not display_name.strip():
        raise ValueError("Tên hiển thị không được để trống.")
    if len(display_name.strip()) > 100:
        raise ValueError("Tên hiển thị không được dài quá 100 ký tự.")

    with _open_cursor() as cursor:
        cursor.execute(
            "UPDATE users SET display_name = %s WHERE user_id = %s",
            (display_name.strip(), user_id),
        )
        row = _fetch_user_by_id(cursor, user_id)
    return _row_to_user(row) if row is not None else None


# ---- (9. UPDATE: ĐỔI MẬT KHẨU) ----
def change_password(user_id: int, old_password: str, new_password: str) -> bool:
    """Đổi mật khẩu nếu mật khẩu cũ khớp; không trả/lộ chuỗi mật khẩu."""
    _check_positive_id(user_id)
    if not isinstance(old_password, str):
        return False
    _check_password(new_password)

    with _open_cursor() as cursor:
        cursor.execute(
            "SELECT password_hash FROM users WHERE user_id = %s",
            (user_id,),
        )
        row = cursor.fetchone()
        if row is None or not _password_matches(old_password, row["password_hash"]):
            return False

        cursor.execute(
            "UPDATE users SET password_hash = %s WHERE user_id = %s",
            (_hash_password(new_password), user_id),
        )
        return cursor.rowcount == 1
