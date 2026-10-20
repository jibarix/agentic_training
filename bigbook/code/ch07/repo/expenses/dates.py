"""Dates of travel: ISO dates, nights, days and quarters."""
from datetime import date


def parse_date(text):
    """'2026-03-04' -> date(2026, 3, 4). Only YYYY-MM-DD is accepted; anything else raises ValueError."""
    s = str(text).strip()
    if len(s) != 10 or s[4] != "-" or s[7] != "-":
        raise ValueError(f"not a YYYY-MM-DD date: {text!r}")
    return date.fromisoformat(s)


def nights(check_in, check_out):
    """Nights of lodging between two dates; 0 if they are the same day. ValueError if check_out
    comes before check_in."""
    n = (check_out - check_in).days
    if n < 0:
        raise ValueError("check-out is before check-in")
    return n


def travel_days(start, end):
    """Days of travel, counting both the first and the last day. ValueError if end is before start."""
    if end < start:
        raise ValueError("the trip ends before it starts")
    return (end - start).days + 1


def is_weekend(day):
    """True on Saturday and Sunday."""
    return day.weekday() >= 5


def quarter(day):
    """1 for January to March, ..., 4 for October to December."""
    return (day.month - 1) // 3 + 1
