import os

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS services (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT    NOT NULL,
    duration_min INTEGER NOT NULL,
    price        INTEGER NOT NULL DEFAULT 0,
    active       INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS working_hours (
    weekday    INTEGER PRIMARY KEY,   -- 0 = Monday ... 6 = Sunday
    start_time TEXT NOT NULL,         -- "09:00"
    end_time   TEXT NOT NULL          -- "18:00"
);

CREATE TABLE IF NOT EXISTS bookings (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    user_name  TEXT    NOT NULL,
    service_id INTEGER NOT NULL REFERENCES services(id),
    starts_at  TEXT    NOT NULL,      -- ISO 8601 with offset
    ends_at    TEXT    NOT NULL,
    status     TEXT    NOT NULL DEFAULT 'active',  -- active | cancelled
    reminded   INTEGER NOT NULL DEFAULT 0,
    created_at TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_bookings_starts_at ON bookings(starts_at);
CREATE INDEX IF NOT EXISTS idx_bookings_user ON bookings(user_id, starts_at);
"""


async def connect(path: str) -> aiosqlite.Connection:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    db = await aiosqlite.connect(path)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    await db.executescript(SCHEMA)
    await db.commit()
    return db
