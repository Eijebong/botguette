import pytest
import os
import tempfile
from botguette.database import Database


@pytest.fixture
async def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    db = Database(path)
    await db.initialize()

    yield db

    if os.path.exists(path):
        os.unlink(path)


async def test_user_ban(temp_db):
    user_id = 123456789

    assert not await temp_db.is_user_banned(user_id)
    await temp_db.ban_user(user_id, "Test reason")
    assert await temp_db.is_user_banned(user_id)
    await temp_db.unban_user(user_id)
    assert not await temp_db.is_user_banned(user_id)


async def test_room_announcement_tracking(temp_db):
    room_id = "0755761d-bca9-46c2-8dd6-a6d03200ef66"
    guild_id = 999888777
    user_id = 123456789
    lobby_url = "https://ap-lobby.bananium.fr"

    assert not await temp_db.is_room_announced(room_id, guild_id)
    await temp_db.mark_room_announced(room_id, guild_id, user_id, lobby_url)
    assert await temp_db.is_room_announced(room_id, guild_id)

    info = await temp_db.get_room_announcement_info(room_id, guild_id)
    assert info is not None
    announced_by, announced_at = info
    assert announced_by == user_id
    assert announced_at is not None


async def test_room_announcement_per_guild(temp_db):
    room_id = "0755761d-bca9-46c2-8dd6-a6d03200ef66"
    guild1_id = 111111111
    guild2_id = 222222222
    user_id = 123456789
    lobby_url = "https://ap-lobby.bananium.fr"

    await temp_db.mark_room_announced(room_id, guild1_id, user_id, lobby_url)
    assert await temp_db.is_room_announced(room_id, guild1_id)
    assert not await temp_db.is_room_announced(room_id, guild2_id)

    await temp_db.mark_room_announced(room_id, guild2_id, user_id, lobby_url)
    assert await temp_db.is_room_announced(room_id, guild1_id)
    assert await temp_db.is_room_announced(room_id, guild2_id)


async def test_duplicate_announcement_prevention(temp_db):
    room_id = "0755761d-bca9-46c2-8dd6-a6d03200ef66"
    guild_id = 999888777
    user1_id = 123456789
    user2_id = 987654321
    lobby_url = "https://ap-lobby.bananium.fr"

    await temp_db.mark_room_announced(room_id, guild_id, user1_id, lobby_url)
    info = await temp_db.get_room_announcement_info(room_id, guild_id)
    assert info[0] == user1_id

    await temp_db.mark_room_announced(room_id, guild_id, user2_id, lobby_url)
    info = await temp_db.get_room_announcement_info(room_id, guild_id)
    assert info[0] == user1_id
