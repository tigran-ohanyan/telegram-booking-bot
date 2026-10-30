from collections.abc import Iterable
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from bot.models import WorkingHours


def free_slots(
    day: date,
    hours: WorkingHours | None,
    duration_min: int,
    step_min: int,
    busy: Iterable[tuple[datetime, datetime]],
    now: datetime,
    tz: ZoneInfo,
) -> list[datetime]:
    """Return slot start times on `day` that fit `duration_min` and do not overlap `busy`.

    Slots start at `step_min` intervals from the opening time and must end before closing.
    Slots in the past (relative to `now`) are skipped.
    """
    if hours is None:
        return []

    opening = datetime.combine(day, hours.start, tzinfo=tz)
    closing = datetime.combine(day, hours.end, tzinfo=tz)
    duration = timedelta(minutes=duration_min)
    step = timedelta(minutes=step_min)
    busy = list(busy)

    slots: list[datetime] = []
    start = opening
    while start + duration <= closing:
        end = start + duration
        if start > now and not any(b_start < end and b_end > start for b_start, b_end in busy):
            slots.append(start)
        start += step
    return slots


def upcoming_days(today: date, hours: dict[int, WorkingHours], days_ahead: int) -> list[date]:
    """Dates from today that have working hours configured."""
    result = []
    for offset in range(days_ahead):
        day = today + timedelta(days=offset)
        if day.weekday() in hours:
            result.append(day)
    return result
