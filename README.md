# Botguette

Discord bot used on 360chrism's discord to help with archipelago organization

## Deployment

Required env:

- `DISCORD_TOKEN`
- `LOBBY_API_KEY`
- `ALLOWED_LOBBIES` - Comma-separated
- `ALLOWED_CHANNELS` - Comma-separated channel IDs
- `SYNC_ROLE` - Role name to ping for sync games
- `ASYNC_ROLE` - Role name to ping for async games
- `DEV_GUILD_ID` - (Optional) Set this when developing to sync commands faster (will dupe commands on that server)

## Bot Setup

OAuth2 scopes: `bot`, `applications.commands`

Bot permissions:
- Send Messages
- Create Public Threads
- Send Messages in Threads
- Manage Messages (for pinning)

## Commands

- `/archipelago <room_url> <game_type>` - Announce a game (sync or async)
- `/botguette-ban <user> [reason]` - Ban a user from the bot
- `/botguette-unban <user>` - Unban a user
