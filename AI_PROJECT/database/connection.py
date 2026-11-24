"""Tạo kết nối Python tới MySQL Server."""

from pathlib import Path

import mysql.connector
from dotenv import load_dotenv
from mysql.connector import Error

from APP.configuration import get_setting


# connection.py nằm trong AI_PROJECT/database, nên parents[1] là AI_PROJECT.
PROJECT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_DIR / ".env")


def get_connection():
    """Mở và trả về một kết nối tới database của ứng dụng."""

    required_settings = ("DB_USER", "DB_PASSWORD")
    missing_settings = [name for name in required_settings if not get_setting(name)]

    if missing_settings:
        names = ", ".join(missing_settings)
        raise RuntimeError(
            f"Thiếu cấu hình {names}. Hãy tạo AI_PROJECT/.env "
            "dựa trên AI_PROJECT/.env.example."
        )

    try:
        return mysql.connector.connect(
            host=get_setting("DB_HOST", "127.0.0.1"),
            port=int(get_setting("DB_PORT", "3306")),
            user=get_setting("DB_USER"),
            password=get_setting("DB_PASSWORD"),
            database=get_setting("DB_NAME", "chi_tieu_sinh_vien"),
            connection_timeout=5,
        )
    except Error as exc:
        raise RuntimeError(
            "Không kết nối được MySQL. Hãy kiểm tra MySQL Server đang chạy, "
            "địa chỉ host/port, tài khoản và tên database trong AI_PROJECT/.env. "
            f"Chi tiết lỗi: {exc}"
        ) from exc
