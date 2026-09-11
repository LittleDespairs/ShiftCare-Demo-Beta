"""Services: common for ShiftCare."""
from __future__ import annotations

from datetime import UTC
from datetime import datetime
from fastapi import HTTPException
import schedule_time

def is_weekend(date_string: str) -> bool:
    # Python: Monday=0. The app week starts on Sunday, but this still catches Friday/Saturday.
    weekday = schedule_time.parse_date_string(date_string).weekday()
    return weekday in (4, 5)


def fetch_one_or_404(cursor, query: str, params: tuple, message: str):
    cursor.execute(query, params)
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=message)
    return row


def fetch_count(cursor, query: str, params: tuple = ()) -> int:
    cursor.execute(query, params)
    return int(cursor.fetchone()[0])


def current_utc_timestamp() -> str:
    return datetime.now(UTC).replace(tzinfo=None).isoformat(timespec="seconds")
