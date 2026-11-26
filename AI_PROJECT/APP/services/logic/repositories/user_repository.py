"""Database operations for user records and authentication fields."""

from typing import Any

from mysql.connector import IntegrityError

from services.logic.repositories._db import open_cursor


_USER_COLUMNS = """
    SELECT user_id, display_name, username, created_at
    FROM users
"""


def _fetch_user_by_id(cursor: Any, user_id: int) -> dict[str, Any] | None:
    cursor.execute(_USER_COLUMNS + " WHERE user_id = %s", (user_id,))
    return cursor.fetchone()


def create_user_record(
    display_name: str,
    username: str,
    password_hash: str,
) -> dict[str, Any]:
    """Insert a user and return public fields, with a friendly duplicate error."""
    try:
        with open_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO users (display_name, username, password_hash)
                VALUES (%s, %s, %s)
                """,
                (display_name, username, password_hash),
            )
            row = _fetch_user_by_id(cursor, cursor.lastrowid)
            if row is None:
                raise RuntimeError("Không đọc lại được tài khoản vừa tạo.")
            return row
    except IntegrityError as error:
        # MySQL error 1062 means a UNIQUE value, such as username, already exists.
        if error.errno == 1062:
            raise ValueError("Tên đăng nhập đã được sử dụng.") from error
        raise


def add_login_to_user_record(
    user_id: int,
    username: str,
    password_hash: str,
) -> dict[str, Any] | None:
    """Attach login credentials to an existing user without credentials."""
    with open_cursor() as cursor:
        cursor.execute(
            """
            UPDATE users
            SET username = %s, password_hash = %s
            WHERE user_id = %s AND username IS NULL AND password_hash IS NULL
            """,
            (username, password_hash, user_id),
        )
        return _fetch_user_by_id(cursor, user_id)


def get_user_record(user_id: int) -> dict[str, Any] | None:
    with open_cursor() as cursor:
        return _fetch_user_by_id(cursor, user_id)


def get_user_auth_record(username: str) -> dict[str, Any] | None:
    with open_cursor() as cursor:
        cursor.execute(
            """
            SELECT user_id, display_name, username, password_hash, created_at
            FROM users
            WHERE username = %s
            """,
            (username,),
        )
        return cursor.fetchone()


def update_user_display_name(
    user_id: int,
    display_name: str,
) -> dict[str, Any] | None:
    with open_cursor() as cursor:
        cursor.execute(
            "UPDATE users SET display_name = %s WHERE user_id = %s",
            (display_name, user_id),
        )
        return _fetch_user_by_id(cursor, user_id)


def get_user_password_hash(user_id: int) -> str | None:
    with open_cursor() as cursor:
        cursor.execute(
            "SELECT password_hash FROM users WHERE user_id = %s",
            (user_id,),
        )
        row = cursor.fetchone()
    return row["password_hash"] if row is not None else None


def update_user_password_hash(
    user_id: int,
    expected_password_hash: str,
    new_password_hash: str,
) -> bool:
    """Update only if the stored hash still matches the one just verified."""
    with open_cursor() as cursor:
        cursor.execute(
            """
            UPDATE users
            SET password_hash = %s
            WHERE user_id = %s AND password_hash = %s
            """,
            (new_password_hash, user_id, expected_password_hash),
        )
        return cursor.rowcount == 1
