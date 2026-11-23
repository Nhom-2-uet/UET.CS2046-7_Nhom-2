"""Shared database cursor lifecycle for repository modules."""

from contextlib import contextmanager
from typing import Any, Iterator

from database.connection import get_connection


@contextmanager
def open_cursor() -> Iterator[Any]:
    """Open a dictionary cursor; commit on success and rollback on failure."""
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
