import aiohttp
import logging
from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RoomInfo:
    id: str
    name: str
    close_date: datetime
    description: str
    url: str


class LobbyClient:
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def get_room_info(self, root_url: str, room_id: str) -> Optional[RoomInfo]:
        root_url = root_url.rstrip('/')
        api_url = f"{root_url}/api/room/{room_id}"

        headers = {"X-Api-Key": self.api_key}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, headers=headers) as response:
                    if response.status != 200:
                        logger.error(f"Unexpected error fetching room info: {response.status} {await response.text()}")
                        return None

                    data = await response.json()

                    close_date = datetime.fromisoformat(data["close_date"]).replace(tzinfo=timezone.utc)

                    return RoomInfo(
                        id=data["id"],
                        name=data["name"],
                        close_date=close_date,
                        description=data["description"],
                        url=f"{root_url}/room/{room_id}"
                    )
        except Exception as e:
            logger.error(f"Unexpected error fetching room info: {e}")
            return None
