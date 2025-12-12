import pytest
from botguette.bot import parse_room_url, sanitize_room_name


def test_parse_room_url_valid():
    url = "https://ap-lobby.bananium.fr/room/0755761d-bca9-46c2-8dd6-a6d03200ef66"
    root_url, room_id = parse_room_url(url)
    assert root_url == "https://ap-lobby.bananium.fr"
    assert room_id == "0755761d-bca9-46c2-8dd6-a6d03200ef66"


def test_parse_room_url_invalid_no_room():
    url = "https://ap-lobby.bananium.fr/0755761d-bca9-46c2-8dd6-a6d03200ef66"
    with pytest.raises(ValueError, match="Invalid URL path"):
        parse_room_url(url)


def test_parse_room_url_invalid_bad_uuid():
    url = "https://ap-lobby.bananium.fr/room/not-a-uuid"
    with pytest.raises(ValueError, match="Invalid UUID format"):
        parse_room_url(url)


def test_parse_room_url_invalid_extra_path():
    url = "https://ap-lobby.bananium.fr/room/0755761d-bca9-46c2-8dd6-a6d03200ef66/extra"
    with pytest.raises(ValueError, match="Invalid URL path"):
        parse_room_url(url)


def test_parse_room_url_invalid_no_protocol():
    url = "ap-lobby.bananium.fr/room/0755761d-bca9-46c2-8dd6-a6d03200ef66"
    with pytest.raises(ValueError, match="Invalid URL"):
        parse_room_url(url)


def test_sanitize_room_name_at_symbol():
    assert sanitize_room_name("Game @everyone") == "Game \\@everyone"


def test_sanitize_room_name_hash_symbol():
    assert sanitize_room_name("Game #general") == "Game \\#general"


def test_sanitize_room_name_both_symbols():
    assert sanitize_room_name("Game @here in #channel") == "Game \\@here in \\#channel"


def test_sanitize_room_name_clean():
    assert sanitize_room_name("Normal Game Name") == "Normal Game Name"


def test_sanitize_room_name_multiple_at():
    assert sanitize_room_name("@user1 and @user2") == "\\@user1 and \\@user2"
