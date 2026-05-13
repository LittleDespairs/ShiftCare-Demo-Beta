from __future__ import annotations

from dataclasses import dataclass
from datetime import date as Date, datetime, time, timedelta


@dataclass(frozen=True)
class Interval:
    start: int
    end: int

    def contains(self, start: int, end: int) -> bool:
        return self.start <= start and end <= self.end

    def overlaps(self, other: "Interval") -> bool:
        return self.start < other.end and other.start < self.end


def parse_time_string(value: str) -> time:
    return datetime.strptime(value, "%H:%M").time()


def parse_date_string(value: str) -> Date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def time_to_minutes(value: str) -> int:
    parsed = parse_time_string(value)
    return parsed.hour * 60 + parsed.minute


def build_interval(start_time: str, end_time: str, is_overnight: bool = False) -> Interval:
    start = time_to_minutes(start_time)
    end = time_to_minutes(end_time)
    if is_overnight or end <= start:
        end += 24 * 60
    return Interval(start=start, end=end)


def build_week_dates(week_start_date: str) -> list[str]:
    start = parse_date_string(week_start_date)
    return [(start + timedelta(days=offset)).isoformat() for offset in range(7)]


def get_week_start_for_date(date_string: str) -> str:
    current = parse_date_string(date_string)
    days_since_sunday = (current.weekday() + 1) % 7
    return (current - timedelta(days=days_since_sunday)).isoformat()


def recurring_day_of_week(date_string: str) -> int:
    # App weeks start on Sunday: Sunday=0, Monday=1, ..., Saturday=6.
    return (parse_date_string(date_string).weekday() + 1) % 7


def get_week_end_date(week_start_date: str) -> str:
    return build_week_dates(week_start_date)[-1]
