from datetime import datetime, time, timedelta

import aiosqlite

from bot.models import Booking, Service, WorkingHours


def _parse_time(value: str) -> time:
    hours, minutes = value.split(":")
    return time(int(hours), int(minutes))


def _row_to_service(row: aiosqlite.Row) -> Service:
    return Service(
        id=row["id"],
        name=row["name"],
        duration_min=row["duration_min"],
        price=row["price"],
        active=bool(row["active"]),
    )


def _row_to_booking(row: aiosqlite.Row) -> Booking:
    return Booking(
        id=row["id"],
        user_id=row["user_id"],
        user_name=row["user_name"],
        service_id=row["service_id"],
        service_name=row["service_name"],
        starts_at=datetime.fromisoformat(row["starts_at"]),
        ends_at=datetime.fromisoformat(row["ends_at"]),
        status=row["status"],
        reminded=bool(row["reminded"]),
    )


BOOKING_SELECT = """
SELECT b.*, s.name AS service_name
FROM bookings b
JOIN services s ON s.id = b.service_id
"""


class Repository:
    def __init__(self, db: aiosqlite.Connection):
        self.db = db

    # --- services -----------------------------------------------------

    async def list_services(self, active_only: bool = True) -> list[Service]:
        sql = "SELECT * FROM services"
        if active_only:
            sql += " WHERE active = 1"
        sql += " ORDER BY id"
        async with self.db.execute(sql) as cur:
            return [_row_to_service(r) for r in await cur.fetchall()]

    async def get_service(self, service_id: int) -> Service | None:
        async with self.db.execute("SELECT * FROM services WHERE id = ?", (service_id,)) as cur:
            row = await cur.fetchone()
        return _row_to_service(row) if row else None

    async def add_service(self, name: str, duration_min: int, price: int) -> Service:
        cur = await self.db.execute(
            "INSERT INTO services (name, duration_min, price) VALUES (?, ?, ?)",
            (name, duration_min, price),
        )
        await self.db.commit()
        return Service(cur.lastrowid, name, duration_min, price, True)

    async def set_service_active(self, service_id: int, active: bool) -> bool:
        cur = await self.db.execute(
            "UPDATE services SET active = ? WHERE id = ?", (int(active), service_id)
        )
        await self.db.commit()
        return cur.rowcount > 0

    # --- working hours ------------------------------------------------

    async def get_working_hours(self) -> dict[int, WorkingHours]:
        async with self.db.execute("SELECT * FROM working_hours") as cur:
            rows = await cur.fetchall()
        return {
            r["weekday"]: WorkingHours(
                r["weekday"], _parse_time(r["start_time"]), _parse_time(r["end_time"])
            )
            for r in rows
        }

    async def set_working_hours(self, weekday: int, start: time, end: time) -> None:
        await self.db.execute(
            """
            INSERT INTO working_hours (weekday, start_time, end_time) VALUES (?, ?, ?)
            ON CONFLICT(weekday) DO UPDATE SET start_time = excluded.start_time,
                                               end_time = excluded.end_time
            """,
            (weekday, start.strftime("%H:%M"), end.strftime("%H:%M")),
        )
        await self.db.commit()

    async def clear_working_hours(self, weekday: int) -> None:
        await self.db.execute("DELETE FROM working_hours WHERE weekday = ?", (weekday,))
        await self.db.commit()

    # --- bookings -----------------------------------------------------

    async def bookings_between(self, start: datetime, end: datetime) -> list[Booking]:
        sql = (
            BOOKING_SELECT
            + """
        WHERE b.status = 'active' AND b.starts_at < ? AND b.ends_at > ?
        ORDER BY b.starts_at
        """
        )
        async with self.db.execute(sql, (end.isoformat(), start.isoformat())) as cur:
            return [_row_to_booking(r) for r in await cur.fetchall()]

    async def create_booking(
        self,
        user_id: int,
        user_name: str,
        service: Service,
        starts_at: datetime,
    ) -> Booking | None:
        """Insert a booking unless the slot overlaps an existing active one."""
        ends_at = starts_at + timedelta(minutes=service.duration_min)
        if await self.bookings_between(starts_at, ends_at):
            return None
        now = datetime.now(starts_at.tzinfo)
        cur = await self.db.execute(
            """
            INSERT INTO bookings (user_id, user_name, service_id, starts_at, ends_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                user_name,
                service.id,
                starts_at.isoformat(),
                ends_at.isoformat(),
                now.isoformat(),
            ),
        )
        await self.db.commit()
        return await self.get_booking(cur.lastrowid)

    async def get_booking(self, booking_id: int) -> Booking | None:
        async with self.db.execute(BOOKING_SELECT + " WHERE b.id = ?", (booking_id,)) as cur:
            row = await cur.fetchone()
        return _row_to_booking(row) if row else None

    async def user_bookings(self, user_id: int, since: datetime) -> list[Booking]:
        sql = (
            BOOKING_SELECT
            + """
        WHERE b.user_id = ? AND b.status = 'active' AND b.ends_at >= ?
        ORDER BY b.starts_at
        """
        )
        async with self.db.execute(sql, (user_id, since.isoformat())) as cur:
            return [_row_to_booking(r) for r in await cur.fetchall()]

    async def cancel_booking(self, booking_id: int, user_id: int | None = None) -> bool:
        sql = "UPDATE bookings SET status = 'cancelled' WHERE id = ? AND status = 'active'"
        params: tuple = (booking_id,)
        if user_id is not None:
            sql += " AND user_id = ?"
            params += (user_id,)
        cur = await self.db.execute(sql, params)
        await self.db.commit()
        return cur.rowcount > 0

    async def due_reminders(self, window_start: datetime, window_end: datetime) -> list[Booking]:
        sql = (
            BOOKING_SELECT
            + """
        WHERE b.status = 'active' AND b.reminded = 0
          AND b.starts_at >= ? AND b.starts_at < ?
        """
        )
        async with self.db.execute(sql, (window_start.isoformat(), window_end.isoformat())) as cur:
            return [_row_to_booking(r) for r in await cur.fetchall()]

    async def mark_reminded(self, booking_id: int) -> None:
        await self.db.execute("UPDATE bookings SET reminded = 1 WHERE id = ?", (booking_id,))
        await self.db.commit()
