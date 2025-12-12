import aiosqlite
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_path: str = "botguette.db"):
        self.db_path = db_path

    async def initialize(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS banned_users (
                    user_id INTEGER PRIMARY KEY,
                    reason TEXT,
                    banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS announced_rooms (
                    room_id TEXT NOT NULL,
                    guild_id INTEGER NOT NULL,
                    announced_by INTEGER NOT NULL,
                    announced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    message_id INTEGER,
                    channel_id INTEGER,
                    lobby_url TEXT,
                    is_async INTEGER DEFAULT 0,
                    PRIMARY KEY (room_id, guild_id)
                )
            """)
            # Migration: add is_async column if it doesn't exist
            async with db.execute("PRAGMA table_info(announced_rooms)") as cursor:
                columns = [row[1] for row in await cursor.fetchall()]
                if "is_async" not in columns:
                    await db.execute("ALTER TABLE announced_rooms ADD COLUMN is_async INTEGER DEFAULT 0")
            await db.commit()
            logger.info("Database initialized")

    async def is_user_banned(self, user_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT 1 FROM banned_users WHERE user_id = ?", (user_id,)
            ) as cursor:
                result = await cursor.fetchone()
                return result is not None

    async def ban_user(self, user_id: int, reason: str = ""):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO banned_users (user_id, reason) VALUES (?, ?)",
                (user_id, reason),
            )
            await db.commit()
            logger.info(f"Banned user {user_id}: {reason}")

    async def unban_user(self, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM banned_users WHERE user_id = ?", (user_id,))
            await db.commit()
            logger.info(f"Unbanned user {user_id}")

    async def is_room_announced(self, room_id: str, guild_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT 1 FROM announced_rooms WHERE room_id = ? AND guild_id = ?",
                (room_id, guild_id)
            ) as cursor:
                result = await cursor.fetchone()
                return result is not None

    async def mark_room_announced(self, room_id: str, guild_id: int, user_id: int, lobby_url: str, is_async: bool, message_id: int = None, channel_id: int = None):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO announced_rooms (room_id, guild_id, announced_by, lobby_url, is_async, message_id, channel_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (room_id, guild_id, user_id, lobby_url, int(is_async), message_id, channel_id)
            )
            await db.commit()
            logger.info(f"Room {room_id} marked as announced in guild {guild_id} by user {user_id}")

    async def get_pinned_announcements(self) -> list[tuple[str, int, int, int, str, bool]]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT room_id, guild_id, message_id, channel_id, lobby_url, is_async FROM announced_rooms WHERE message_id IS NOT NULL"
            ) as cursor:
                return await cursor.fetchall()

    async def clear_message_id(self, room_id: str, guild_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE announced_rooms SET message_id = NULL, channel_id = NULL WHERE room_id = ? AND guild_id = ?",
                (room_id, guild_id)
            )
            await db.commit()

    async def get_room_announcement_info(self, room_id: str, guild_id: int) -> tuple[int, str] | None:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT announced_by, announced_at FROM announced_rooms WHERE room_id = ? AND guild_id = ?",
                (room_id, guild_id)
            ) as cursor:
                result = await cursor.fetchone()
                return result if result else None

    async def get_user_cooldown_seconds(self, user_id: int, cooldown_hours: int = 1) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                """SELECT MAX(announced_at) FROM announced_rooms
                   WHERE announced_by = ?
                   AND announced_at > datetime('now', ?)""",
                (user_id, f"-{cooldown_hours} hours")
            ) as cursor:
                result = await cursor.fetchone()
                if result and result[0]:
                    last_announcement = datetime.fromisoformat(result[0]).replace(tzinfo=timezone.utc)
                    now = datetime.now(timezone.utc)
                    cooldown_end = last_announcement + timedelta(hours=cooldown_hours)
                    remaining = (cooldown_end - now).total_seconds()
                    return max(0, int(remaining))
                return 0
