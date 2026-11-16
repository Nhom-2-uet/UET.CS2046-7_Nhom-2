from dataclasses import dataclass
from datetime import datetime


@dataclass
class User:
    user_id: int
    display_name: str
    created_at: datetime
    # None chỉ dành cho hồ sơ cũ chưa được gắn thông tin đăng nhập.
    username: str | None = None
