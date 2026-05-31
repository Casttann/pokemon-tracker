from unittest.mock import patch
from image_lookup import find_card_image, _cache

MOCK_API_RESPONSE = {
    "data": [
        {
            "id": "sv3-199",
            "name": "Charizard ex",
            "set": {"name": "Obsidian Flames"},
            "images": {
                "large": "https://images.pokemontcg.io/sv3/199_hires.png"
            }
        }
    ]
}

def test_returns_image_url_on_match():
    _cache.clear()
    with patch("image_lookup.requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = MOCK_API_RESPONSE
        url = find_card_image("Charizard ex", "Obsidian Flames")
        assert url == "https://images.pokemontcg.io/sv3/199_hires.png"

def test_returns_none_when_no_match():
    _cache.clear()
    with patch("image_lookup.requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"data": []}
        url = find_card_image("Unknown Card", "Unknown Set")
        assert url is None

def test_uses_cache_on_second_call():
    _cache.clear()
    with patch("image_lookup.requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = MOCK_API_RESPONSE
        find_card_image("Charizard ex", "Obsidian Flames")
        find_card_image("Charizard ex", "Obsidian Flames")
        assert mock_get.call_count == 1

def test_returns_none_on_rate_limit():
    _cache.clear()
    with patch("image_lookup.requests.get") as mock_get:
        mock_get.return_value.status_code = 429
        url = find_card_image("Pikachu", "Some Set")
        assert url is None
