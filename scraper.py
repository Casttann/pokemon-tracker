import random
import time
import requests
from bs4 import BeautifulSoup

MAX_PRICE = 100.0

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

BASE_URL = "https://www.cardmarket.com/en/Pokemon/Products/Singles"


def _parse_price(text):
    """Parse '45,00 €' or '45.00' into a float."""
    try:
        cleaned = text.replace("€", "").replace(",", ".").strip()
        return float(cleaned)
    except (ValueError, AttributeError):
        return None


def _random_delay():
    time.sleep(random.uniform(1.0, 3.0))


def search_cardmarket(pokemon_name: str, max_price: float = MAX_PRICE) -> list:
    """Search CardMarket for English Pokemon cards by name."""
    url = f"https://www.cardmarket.com/en/Pokemon/Products/Search?searchString={pokemon_name}&language=1"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for row in soup.select(".col-selectable"):
            try:
                name_tag = row.select_one(".product-list--name, a[href*='Singles']")
                price_tag = row.select_one(".fw-bold, .price-container span")
                set_tag = row.select_one(".product-list--expansion, a.expansion")
                rarity_tag = row.select_one(".col-availability span, .rarity")

                if not name_tag or not price_tag:
                    continue

                price = _parse_price(price_tag.get_text())
                if price is None or price > max_price:
                    continue

                href = name_tag.get("href", "")
                card_url = f"https://www.cardmarket.com{href}" if href.startswith("/") else href

                results.append({
                    "card_name": name_tag.get_text(strip=True),
                    "set_name": set_tag.get_text(strip=True) if set_tag else "",
                    "rarity": rarity_tag.get_text(strip=True) if rarity_tag else "",
                    "price": price,
                    "cardmarket_url": card_url,
                })
            except Exception:
                continue
        return results
    except Exception:
        return []


def update_price(cardmarket_url: str) -> float | None:
    """Fetch the current price for a card from its CardMarket URL."""
    try:
        _random_delay()
        resp = requests.get(cardmarket_url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "html.parser")
        price_tag = soup.select_one(".info-list-container .fw-bold, .price-container .fw-bold")
        if not price_tag:
            return None
        return _parse_price(price_tag.get_text())
    except Exception:
        return None
