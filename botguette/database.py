import aiosqlite
import logging
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
                    PRIMARY KEY (room_id, guild_id)
                )
            """)
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

    async def mark_room_announced(self, room_id: str, guild_id: int, user_id: int, lobby_url: str, message_id: int = None, channel_id: int = None):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO announced_rooms (room_id, guild_id, announced_by, lobby_url, message_id, channel_id) VALUES (?, ?, ?, ?, ?, ?)",
                (room_id, guild_id, user_id, lobby_url, message_id, channel_id)
            )
            await db.commit()
            logger.info(f"Room {room_id} marked as announced in guild {guild_id} by user {user_id}")

    async def get_pinned_announcements(self) -> list[tuple[str, int, int, int, str]]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT room_id, guild_id, message_id, channel_id, lobby_url FROM announced_rooms WHERE message_id IS NOT NULL"
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
