import os
import asyncio
import logging
from uuid import UUID
from datetime import datetime, timedelta, timezone
import discord
from discord import app_commands
from discord.ext import tasks
from urllib.parse import urlparse

from .database import Database
from .lobby_client import LobbyClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ArchipelagoBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)

        self.tree = app_commands.CommandTree(self)

        db_path = os.getenv("DATABASE_PATH", "botguette.db")
        self.database = Database(db_path)

        api_key = os.environ["LOBBY_API_KEY"]
        allowed_lobbies_str = os.environ["ALLOWED_LOBBIES"]
        self.allowed_lobbies = set(url.strip().rstrip('/') for url in allowed_lobbies_str.split(",") if url.strip())

        allowed_channels_str = os.environ["ALLOWED_CHANNELS"]
        self.allowed_channels = set(int(c.strip()) for c in allowed_channels_str.split(",") if c.strip())

        self.lobby_client = LobbyClient(api_key)
        self.sync_role = os.environ["SYNC_ROLE"]
        self.async_role = os.environ["ASYNC_ROLE"]
        self._register_commands()

    def _register_commands(self):
        @self.tree.command(name="archipelago", description="Announce an Archipelago game")
        @app_commands.describe(
            room_url="The URL of the lobby room",
            game_type="Sync (everyone plays at the same time) or async (play at your own pace)"
        )
        @app_commands.choices(game_type=[
            app_commands.Choice(name="sync", value="sync"),
            app_commands.Choice(name="async", value="async"),
        ])
        async def archipelago(interaction: discord.Interaction, room_url: str, game_type: str):
            await self._handle_archipelago_command(interaction, room_url, game_type)

        @self.tree.command(name="botguette-ban", description="Ban a user from using the bot")
        @app_commands.describe(user="The user to ban", reason="Reason for the ban")
        @app_commands.default_permissions(ban_members=True)
        async def botguette_ban(interaction: discord.Interaction, user: discord.User, reason: str = ""):
            await self._handle_ban_command(interaction, user, reason)

        @self.tree.command(name="botguette-unban", description="Unban a user from using the bot")
        @app_commands.describe(user="The user to unban")
        @app_commands.default_permissions(ban_members=True)
        async def botguette_unban(interaction: discord.Interaction, user: discord.User):
            await self._handle_unban_command(interaction, user)

    async def _handle_archipelago_command(self, interaction: discord.Interaction, room_url: str, game_type: str):
        user_id = interaction.user.id
        is_async = game_type == "async"

        if await self.database.is_user_banned(user_id):
            logger.warning(f"Banned user {user_id} tried /archipelago")
            await interaction.response.send_message("You are not allowed to use this command.", ephemeral=True)
            return

        if isinstance(interaction.channel, discord.Thread):
            await interaction.response.send_message(
                "This command doesn't work in threads. Please use it in a regular channel.",
                ephemeral=True
            )
            return

        if interaction.channel.id not in self.allowed_channels:
            await interaction.response.send_message(
                "This command is not allowed in this channel.",
                ephemeral=True
            )
            return

        try:
            root_url, room_id = parse_room_url(room_url.strip())
        except ValueError as e:
            await interaction.response.send_message(
                f"Invalid room URL: {e}",
                ephemeral=True
            )
            return

        if root_url not in self.allowed_lobbies:
            await interaction.response.send_message(
                f"Lobby `{root_url}` is not allowed. Contact an admin.",
                ephemeral=True
            )
            return

        guild_id = interaction.guild.id
        if await self.database.is_room_announced(room_id, guild_id):
            await interaction.response.send_message("This room was already announced.", ephemeral=True)
            logger.info(f"User {user_id} tried to announce already-announced room {room_id}")
            return

        role_name = self.async_role if is_async else self.sync_role
        role = discord.utils.get(interaction.guild.roles, name=role_name)
        if not role:
            await interaction.response.send_message(
                f"Missing @{role_name} role. Ask an admin to create it.",
                ephemeral=True
            )
            return

        await interaction.response.defer()

        room_info = await self.lobby_client.get_room_info(root_url, room_id)
        if not room_info:
            await interaction.delete_original_response()
            await interaction.followup.send("Couldn't fetch room info from lobby.", ephemeral=True)
            return

        now = datetime.now(timezone.utc)
        min_future_time = now + timedelta(hours=1)
        if room_info.close_date < min_future_time:
            await interaction.delete_original_response()
            await interaction.followup.send(
                f"This room's date is too soon (less than 1 hour from now). Room date: <t:{int(room_info.close_date.timestamp())}:F>",
                ephemeral=True
            )
            return

        safe_room_name = sanitize_room_name(room_info.name)
        timestamp = int(room_info.close_date.timestamp())
        message = (
            f"{role.mention} {interaction.user.mention} is organizing an archipelago "
            f"**{safe_room_name}** at {room_info.url} on <t:{timestamp}:F>"
        )

        await interaction.edit_original_response(content=message)
        original_message = await interaction.original_response()

        if is_async:
            thread = await original_message.create_thread(name=room_info.name[:100])
            thread_msg = await thread.send(f"**{safe_room_name}**\n{room_info.url}")
            await thread_msg.pin()
            await self.database.mark_room_announced(room_id, guild_id, interaction.user.id, root_url)
        else:
            await original_message.pin()
            await self.database.mark_room_announced(room_id, guild_id, interaction.user.id, root_url, original_message.id, interaction.channel.id)

        logger.info(f"Room {room_id} announced by {user_id}")

    async def _handle_ban_command(self, interaction: discord.Interaction, user: discord.User, reason: str):
        await interaction.response.defer(ephemeral=True)

        user_id = user.id
        await self.database.ban_user(user_id, reason)

        await interaction.followup.send(
            f"Banned {user.mention}\nReason: {reason if reason else 'No reason'}",
            ephemeral=True
        )
        logger.info(f"Banned {user_id}: {reason}")

    async def _handle_unban_command(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer(ephemeral=True)

        user_id = user.id
        await self.database.unban_user(user_id)

        await interaction.followup.send(f"Unbanned {user.mention}", ephemeral=True)
        logger.info(f"Unbanned {user_id}")

    async def setup_hook(self):
        await self.database.initialize()

        dev_guild_id = os.getenv("DEV_GUILD_ID")
        if dev_guild_id:
            guild = discord.Object(id=int(dev_guild_id))
            self.tree.copy_global_to(guild=guild)
            logger.info(f"Syncing commands to guild {dev_guild_id}...")
            await self.tree.sync(guild=guild)
            logger.info(f"Commands synced to guild {dev_guild_id}")
        else:
            logger.info("Syncing commands globally...")
            await self.tree.sync()
            logger.info("Commands synced globally")

    async def on_ready(self):
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info("------")
        self.cleanup_expired_pins.start()

    @tasks.loop(hours=1)
    async def cleanup_expired_pins(self):
        logger.info("Checking for expired pins")
        announcements = await self.database.get_pinned_announcements()

        for room_id, guild_id, message_id, channel_id, lobby_url in announcements:
            try:
                channel = self.get_channel(channel_id)
                if not channel:
                    channel = await self.fetch_channel(channel_id)

                message = await channel.fetch_message(message_id)
                room_info = await self.lobby_client.get_room_info(lobby_url, room_id)

                if not room_info or room_info.close_date < datetime.now(timezone.utc):
                    await message.unpin()
                    await self.database.clear_message_id(room_id, guild_id)
                    logger.info(f"Unpinned expired room {room_id}")
                else:
                    timestamp = int(room_info.close_date.timestamp())
                    if f"<t:{timestamp}:F>" not in message.content:
                        role_mention = message.role_mentions[0].mention if message.role_mentions else "<unknown>"
                        user_mention = message.mentions[0].mention if message.mentions else "<unknown>"
                        safe_room_name = sanitize_room_name(room_info.name)
                        new_content = (
                            f"{role_mention} {user_mention} is organizing an archipelago "
                            f"**{safe_room_name}** at {room_info.url} on <t:{timestamp}:F>"
                        )
                        await message.edit(content=new_content)
                        logger.info(f"Updated close date for room {room_id}")
            except discord.NotFound:
                await self.database.clear_message_id(room_id, guild_id)
                logger.info(f"Message deleted for room {room_id}, cleared from DB")
            except Exception as e:
                logger.error(f"Failed to process pin for room {room_id}: {e}")


def parse_room_url(url: str) -> tuple[str, str]:
    parsed = urlparse(url)

    if not parsed.scheme or not parsed.netloc:
        raise ValueError("Invalid URL: missing scheme or domain")

    if parsed.scheme not in ('http', 'https'):
        raise ValueError(f"Invalid URL scheme: {parsed.scheme}")

    path_parts = parsed.path.strip('/').split('/')
    if len(path_parts) != 2 or path_parts[0] != 'room':
        raise ValueError("Invalid URL path: expected /room/{uuid}")

    room_id = path_parts[1]
    try:
        UUID(room_id)
    except ValueError:
        raise ValueError(f"Invalid UUID format: {room_id}")

    root_url = f"{parsed.scheme}://{parsed.netloc}"

    return root_url, room_id.lower()


def sanitize_room_name(name: str) -> str:
    return name.replace('@', '\\@').replace('#', '\\#')


def run_bot():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise ValueError("DISCORD_TOKEN required")

    bot = ArchipelagoBot()
    bot.run(token)


if __name__ == "__main__":
    run_bot()
