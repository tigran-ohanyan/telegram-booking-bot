import pytest

from bot.db import connect
from bot.repository import Repository


@pytest.fixture
async def repo(tmp_path):
    db = await connect(str(tmp_path / "test.db"))
    try:
        yield Repository(db)
    finally:
        await db.close()
