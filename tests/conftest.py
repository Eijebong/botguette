"""Pytest configuration for botguette tests."""
import os
import pytest


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """Set up test environment variables."""
    os.environ.setdefault("LOBBY_API_KEY", "test_api_key")
    os.environ.setdefault("ALLOWED_LOBBIES", "https://ap-lobby.bananium.fr")
    os.environ.setdefault("ALLOWED_CHANNELS", "123456789")
    os.environ.setdefault("DISCORD_TOKEN", "test_token")
    os.environ.setdefault("SYNC_ROLE", "Archipelagoer")
    os.environ.setdefault("ASYNC_ROLE", "Archipelagoer")
