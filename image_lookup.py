import requests

POKEMONTCG_API = "https://api.pokemontcg.io/v2/cards"

_cache: dict = {}


def find_card_image(card_name: str, set_name: str) -> str | None:
    """Query PokemonTCG API for card image URL. Caches results in memory."""
    key = (card_name.lower(), set_name.lower())
    if key in _cache:
        return _cache[key]

    try:
        query = f'name:"{card_name}" set.name:"{set_name}"'
        resp = requests.get(
            POKEMONTCG_API,
            params={"q": query, "select": "images,name,set"},
            timeout=10,
        )
        if resp.status_code == 429:
            return None
        if resp.status_code != 200:
            return None

        data = resp.json().get("data", [])
        if not data:
            _cache[key] = None
            return None

        url = data[0].get("images", {}).get("large")
        _cache[key] = url
        return url
    except Exception:
        return None
