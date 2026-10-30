import os
from dataclasses import dataclass
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class Settings:
    bot_token: str
    admin_ids: frozenset[int]
    db_path: str
    tz: ZoneInfo
    slot_step_min: int
    days_ahead: int


def _parse_ids(raw: str) -> frozenset[int]:
    ids = set()
    for part in raw.replace(";", ",").split(","):
        part = part.strip()
        if part:
            ids.add(int(part))
    return frozenset(ids)


def load_settings() -> Settings:
    token = os.environ.get("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("BOT_TOKEN is not set, see .env.example")

    return Settings(
        bot_token=token,
        admin_ids=_parse_ids(os.environ.get("ADMIN_IDS", "")),
        db_path=os.environ.get("DB_PATH", "data/bookings.db"),
        tz=ZoneInfo(os.environ.get("TZ", "UTC")),
        slot_step_min=int(os.environ.get("SLOT_STEP_MIN", "30")),
        days_ahead=int(os.environ.get("DAYS_AHEAD", "7")),
    )
