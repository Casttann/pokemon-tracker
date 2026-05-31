from unittest.mock import patch, MagicMock
from scraper import search_cardmarket, update_price

MOCK_SEARCH_HTML = """
<html><body>
<div class="col-selectable">
  <div class="col-auction">
    <a class="product-list--name" href="/en/Pokemon/Products/Singles/Obsidian-Flames/Charizard-ex-199">Charizard ex</a>
  </div>
  <div class="col-sellerProductInfo">
    <span class="col-availability">Special Illustration Rare</span>
    <a class="product-list--expansion">Obsidian Flames</a>
  </div>
  <div class="col-price">
    <span class="fw-bold">45,00 €</span>
  </div>
</div>
</body></html>
"""

def test_search_filters_over_budget():
    with patch("scraper.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = MOCK_SEARCH_HTML
        mock_get.return_value = mock_resp
        results = search_cardmarket("Charizard", max_price=10.0)
        assert results == []

def test_search_returns_results_under_budget():
    with patch("scraper.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = MOCK_SEARCH_HTML
        mock_get.return_value = mock_resp
        results = search_cardmarket("Charizard", max_price=100.0)
        assert len(results) >= 1
        assert results[0]["price"] == 45.0
        assert "cardmarket_url" in results[0]

def test_update_price_returns_none_on_failure():
    with patch("scraper.requests.get") as mock_get:
        mock_get.side_effect = Exception("timeout")
        result = update_price("https://www.cardmarket.com/test")
        assert result is None

def test_search_uses_english_language():
    with patch("scraper.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "<html></html>"
        mock_get.return_value = mock_resp
        search_cardmarket("Pikachu")
        call_url = mock_get.call_args[0][0]
        assert "/en/" in call_url
