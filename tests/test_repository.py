from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Yerevan")


async def test_add_and_list_services(repo):
    await repo.add_service("Haircut", 30, 5000)
    hidden = await repo.add_service("Old service", 60, 1000)
    await repo.set_service_active(hidden.id, False)

    active = await repo.list_services()
    everything = await repo.list_services(active_only=False)

    assert [s.name for s in active] == ["Haircut"]
    assert len(everything) == 2


async def test_working_hours_upsert(repo):
    await repo.set_working_hours(0, time(9, 0), time(18, 0))
    await repo.set_working_hours(0, time(10, 0), time(19, 0))

    hours = await repo.get_working_hours()

    assert hours[0].start == time(10, 0)
    assert hours[0].end == time(19, 0)
    assert 1 not in hours


async def test_create_booking_rejects_overlap(repo):
    service = await repo.add_service("Massage", 60, 0)
    start = datetime(2030, 1, 7, 10, 0, tzinfo=TZ)

    first = await repo.create_booking(1, "Ann", service, start)
    overlap = await repo.create_booking(2, "Bob", service, start + timedelta(minutes=30))
    adjacent = await repo.create_booking(3, "Kim", service, start + timedelta(minutes=60))

    assert first is not None and first.service_name == "Massage"
    assert overlap is None
    assert adjacent is not None


async def test_cancel_only_own_booking(repo):
    service = await repo.add_service("Consult", 30, 0)
    booking = await repo.create_booking(1, "Ann", service, datetime(2030, 1, 7, 12, 0, tzinfo=TZ))

    assert not await repo.cancel_booking(booking.id, user_id=999)
    assert await repo.cancel_booking(booking.id, user_id=1)
    assert await repo.user_bookings(1, datetime(2030, 1, 1, tzinfo=TZ)) == []


async def test_due_reminders_once(repo):
    service = await repo.add_service("Consult", 30, 0)
    start = datetime(2030, 1, 7, 12, 0, tzinfo=TZ)
    booking = await repo.create_booking(1, "Ann", service, start)

    around_start = (start - timedelta(minutes=5), start + timedelta(minutes=5))
    too_early = (start - timedelta(minutes=65), start - timedelta(minutes=55))

    due = await repo.due_reminders(*around_start)
    assert [b.id for b in due] == [booking.id]
    assert await repo.due_reminders(*too_early) == []

    await repo.mark_reminded(booking.id)
    assert await repo.due_reminders(*around_start) == []
