from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from bot.models import WorkingHours
from bot.services.slots import free_slots, upcoming_days

TZ = ZoneInfo("Asia/Yerevan")
DAY = date(2030, 1, 7)  # Monday
HOURS = WorkingHours(0, time(10, 0), time(12, 0))
EARLY = datetime(2030, 1, 1, tzinfo=TZ)


def at(hour: int, minute: int = 0) -> datetime:
    return datetime.combine(DAY, time(hour, minute), tzinfo=TZ)


def test_slots_follow_step_and_fit_before_closing():
    slots = free_slots(DAY, HOURS, duration_min=60, step_min=30, busy=[], now=EARLY, tz=TZ)
    assert slots == [at(10), at(10, 30), at(11)]


def test_busy_interval_removes_overlapping_slots():
    busy = [(at(10, 30), at(11, 0))]
    slots = free_slots(DAY, HOURS, duration_min=30, step_min=30, busy=busy, now=EARLY, tz=TZ)
    assert slots == [at(10), at(11), at(11, 30)]


def test_past_slots_are_skipped():
    now = at(10, 45)
    slots = free_slots(DAY, HOURS, duration_min=30, step_min=30, busy=[], now=now, tz=TZ)
    assert slots == [at(11), at(11, 30)]


def test_no_working_hours_means_no_slots():
    assert free_slots(DAY, None, 30, 30, [], EARLY, TZ) == []


def test_upcoming_days_respects_schedule():
    hours = {0: HOURS, 2: HOURS}  # Monday and Wednesday only
    days = upcoming_days(DAY, hours, days_ahead=7)
    assert days == [DAY, DAY + timedelta(days=2)]
