"""Đăng ký, xác thực và quản lý hồ sơ tài khoản người dùng."""

# ---- (1. IMPORT VÀ THIẾT LẬP BẢO MẬT MẬT KHẨU) ----
import hashlib
import hmac
import secrets
from typing import Any

from APP.models.user import User
from services.logic.repositories import user_repository


_PASSWORD_HASH_ALGORITHM = "pbkdf2_sha256"
_PASSWORD_HASH_ITERATIONS = 600_000


# ---- (3. CHUYỂN DÒNG DATABASE THÀNH MODEL) ----
def _row_to_user(row: dict[str, Any]) -> User:
    """Chuyển một dòng database thành model User, không đưa password hash ra ngoài."""
    return User(
        user_id=row["user_id"],
        display_name=row["display_name"],
        created_at=row["created_at"],
        username=row["username"],
    )


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
    row = user_repository.create_user_record(
        display_name.strip(), username, password_hash
    )
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

    row = user_repository.add_login_to_user_record(
        user_id, username, _hash_password(password)
    )
    return _row_to_user(row) if row is not None and row["username"] else None


# ---- (6. READ: ĐỌC HỒ SƠ USER) ----
def get_user(user_id: int) -> User | None:
    _check_positive_id(user_id)
    row = user_repository.get_user_record(user_id)
    return _row_to_user(row) if row is not None else None


# ---- (7. READ: KIỂM TRA ĐĂNG NHẬP) ----
def authenticate_user(username: str, password: str) -> User | None:
    """Trả hồ sơ nếu tên đăng nhập/mật khẩu đúng; sai thì trả None."""
    username = _clean_username(username)
    if not isinstance(password, str):
        return None

    row = user_repository.get_user_auth_record(username)

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

    row = user_repository.update_user_display_name(user_id, display_name.strip())
    return _row_to_user(row) if row is not None else None


# ---- (9. UPDATE: ĐỔI MẬT KHẨU) ----
def change_password(user_id: int, old_password: str, new_password: str) -> bool:
    """Đổi mật khẩu nếu mật khẩu cũ khớp; không trả/lộ chuỗi mật khẩu."""
    _check_positive_id(user_id)
    if not isinstance(old_password, str):
        return False
    _check_password(new_password)

    current_hash = user_repository.get_user_password_hash(user_id)
    if current_hash is None or not _password_matches(old_password, current_hash):
        return False

    return user_repository.update_user_password_hash(
        user_id,
        expected_password_hash=current_hash,
        new_password_hash=_hash_password(new_password),
    )
