from dataclasses import dataclass
from datetime import datetime, time


@dataclass(frozen=True)
class Service:
    id: int
    name: str
    duration_min: int
    price: int
    active: bool


@dataclass(frozen=True)
class WorkingHours:
    weekday: int
    start: time
    end: time


@dataclass(frozen=True)
class Booking:
    id: int
    user_id: int
    user_name: str
    service_id: int
    service_name: str
    starts_at: datetime
    ends_at: datetime
    status: str
    reminded: bool
