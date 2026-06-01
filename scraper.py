import time

import requests

MAX_PRICE = 100.0

API_BASE = "https://api.pokemontcg.io/v2/cards"
HEADERS = {"Accept": "application/json"}

# The PokemonTCG API rate-limits unauthenticated bursts with HTTP 429.
_MAX_RETRIES = 3
_RETRY_WAIT = 2.0


def _get(url, params=None):
    """GET with simple retry/backoff on rate-limit (429) responses."""
    for attempt in range(_MAX_RETRIES):
        resp = requests.get(url, params=params, headers=HEADERS, timeout=20)
        if resp.status_code == 429 and attempt < _MAX_RETRIES - 1:
            time.sleep(_RETRY_WAIT * (attempt + 1))
            continue
        return resp
    return resp

# Price keys from the PokemonTCG API cardmarket data, in order of preference.
_PRICE_KEYS = ("trendPrice", "averageSellPrice", "avg7", "avg30")


def _extract_price(prices):
    """Pick the best available CardMarket price from a prices dict."""
    if not prices:
        return None
    for key in _PRICE_KEYS:
        value = prices.get(key)
        if isinstance(value, (int, float)) and value > 0:
            return float(value)
    return None


def search_cardmarket(pokemon_name: str, max_price: float = MAX_PRICE,
                      page_size: int = 50) -> list:
    """Search English Pokemon cards by name via the PokemonTCG API.

    CardMarket itself blocks scraping (Cloudflare), so prices and metadata
    are sourced from the free PokemonTCG API, which exposes CardMarket prices.
    A larger page_size (up to 250) covers older promos too, for seeding.
    """
    if not pokemon_name:
        return []
    try:
        resp = _get(API_BASE, params={
            "q": f'name:"{pokemon_name}"',
            "pageSize": page_size,
            "orderBy": "-set.releaseDate",
        })
        if resp.status_code != 200:
            return []
        cards = resp.json().get("data", [])
        results = []
        for card in cards:
            cardmarket = card.get("cardmarket") or {}
            price = _extract_price(cardmarket.get("prices"))
            if price is None or price > max_price:
                continue
            results.append({
                "card_name": card.get("name", ""),
                "set_name": (card.get("set") or {}).get("name", ""),
                "rarity": card.get("rarity") or "",
                "price": price,
                "cardmarket_url": cardmarket.get("url", ""),
                "image_url": (card.get("images") or {}).get("small"),
            })
        results.sort(key=lambda r: r["price"], reverse=True)
        return results
    except Exception:
        return []


def update_price(cardmarket_url: str) -> float | None:
    """Fetch the current CardMarket price for a stored card.

    Stored URLs look like https://prices.pokemontcg.io/cardmarket/<card_id>,
    so the card id is parsed from the URL and re-queried.
    """
    try:
        card_id = cardmarket_url.rstrip("/").split("/")[-1]
        if not card_id:
            return None
        resp = _get(f"{API_BASE}/{card_id}")
        if resp.status_code != 200:
            return None
        data = resp.json().get("data") or {}
        cardmarket = data.get("cardmarket") or {}
        return _extract_price(cardmarket.get("prices"))
    except Exception:
        return None
