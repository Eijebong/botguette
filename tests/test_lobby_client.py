import pytest
from datetime import datetime
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase
from botguette.lobby_client import LobbyClient


class TestLobbyClient(AioHTTPTestCase):
    async def get_application(self):
        app = web.Application()
        app.router.add_get('/api/room/{room_id}', self.handle_room_request)
        return app

    async def handle_room_request(self, request):
        room_id = request.match_info['room_id']

        if request.headers.get('X-Api-Key') != 'test_api_key':
            return web.Response(status=401)

        if room_id == '0755761d-bca9-46c2-8dd6-a6d03200ef66':
            return web.json_response({
                "id": room_id,
                "name": "Test Room",
                "close_date": "2025-09-20T12:00:00",
                "description": "Test description",
                "yamls": []
            })

        return web.Response(status=404)

    async def test_get_room_info_success(self):
        client = LobbyClient("test_api_key")
        url = str(self.server.make_url(''))

        room_info = await client.get_room_info(
            url,
            "0755761d-bca9-46c2-8dd6-a6d03200ef66"
        )

        assert room_info is not None
        assert room_info.id == "0755761d-bca9-46c2-8dd6-a6d03200ef66"
        assert room_info.name == "Test Room"
        assert room_info.description == "Test description"
        assert isinstance(room_info.close_date, datetime)

    async def test_get_room_info_not_found(self):
        client = LobbyClient("test_api_key")
        url = str(self.server.make_url(''))

        room_info = await client.get_room_info(url, "nonexistent-uuid")

        assert room_info is None

    async def test_get_room_info_unauthorized(self):
        client = LobbyClient("wrong_api_key")
        url = str(self.server.make_url(''))

        room_info = await client.get_room_info(
            url,
            "0755761d-bca9-46c2-8dd6-a6d03200ef66"
        )

        assert room_info is None
