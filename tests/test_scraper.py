from unittest.mock import patch, MagicMock
from scraper import search_cardmarket, update_price

MOCK_SEARCH_JSON = {
    "data": [
        {
            "name": "Charizard ex",
            "set": {"name": "Obsidian Flames"},
            "rarity": "Special Illustration Rare",
            "images": {"small": "https://images.pokemontcg.io/x.png"},
            "cardmarket": {
                "url": "https://prices.pokemontcg.io/cardmarket/obf-223",
                "prices": {"trendPrice": 45.0, "averageSellPrice": 44.0},
            },
        }
    ]
}


def test_search_filters_over_budget():
    with patch("scraper.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = MOCK_SEARCH_JSON
        mock_get.return_value = mock_resp
        results = search_cardmarket("Charizard", max_price=10.0)
        assert results == []


def test_search_returns_results_under_budget():
    with patch("scraper.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = MOCK_SEARCH_JSON
        mock_get.return_value = mock_resp
        results = search_cardmarket("Charizard", max_price=100.0)
        assert len(results) >= 1
        assert results[0]["price"] == 45.0
        assert "cardmarket_url" in results[0]
        assert results[0]["image_url"] == "https://images.pokemontcg.io/x.png"


def test_update_price_returns_none_on_failure():
    with patch("scraper.requests.get") as mock_get:
        mock_get.side_effect = Exception("timeout")
        result = update_price("https://prices.pokemontcg.io/cardmarket/obf-223")
        assert result is None


def test_update_price_returns_current_price():
    with patch("scraper.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": {"cardmarket": {"prices": {"trendPrice": 33.5}}}
        }
        mock_get.return_value = mock_resp
        result = update_price("https://prices.pokemontcg.io/cardmarket/obf-223")
        assert result == 33.5


def test_search_queries_by_name():
    with patch("scraper.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": []}
        mock_get.return_value = mock_resp
        search_cardmarket("Pikachu")
        params = mock_get.call_args.kwargs["params"]
        assert "Pikachu" in params["q"]
