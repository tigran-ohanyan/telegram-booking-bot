from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from bot.config import Settings
from bot.services.reminders import send_due_reminders

TZ = ZoneInfo("Asia/Yerevan")


class FakeBot:
    def __init__(self):
        self.sent = []

    async def send_message(self, chat_id, text):
        self.sent.append((chat_id, text))


def make_settings(db_path: str) -> Settings:
    return Settings("x", frozenset(), db_path, TZ, 30, 7)


async def test_reminder_sent_once_for_booking_in_an_hour(repo, tmp_path):
    service = await repo.add_service("Consult", 30, 0)
    soon = datetime.now(TZ) + timedelta(hours=1)
    later = datetime.now(TZ) + timedelta(hours=3)
    await repo.create_booking(42, "Ann", service, soon)
    await repo.create_booking(43, "Bob", service, later)

    bot = FakeBot()
    settings = make_settings(str(tmp_path / "test.db"))

    assert await send_due_reminders(bot, repo, settings) == 1
    assert bot.sent[0][0] == 42
    assert "Consult" in bot.sent[0][1]
    assert await send_due_reminders(bot, repo, settings) == 0
