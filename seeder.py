import threading
import time

from scraper import search_cardmarket, MAX_PRICE

_seeding = False


def is_seeding() -> bool:
    return _seeding


def rarity_score(rarity: str) -> int:
    """Rank a card rarity by collecting preference (higher is better).

    Order: Special Illustration Rare > Illustration Rare > Holo >
    Triple Rare > Double Rare > any other Rare > everything else.
    """
    r = (rarity or "").lower()
    if "special illustration rare" in r:
        return 6
    if "illustration rare" in r:
        return 5
    if "holo" in r:
        return 4
    if "triple rare" in r:
        return 3
    if "double rare" in r:
        return 2
    if "rare" in r:
        return 1
    return 0


def pick_best_card(results: list) -> dict | None:
    """Choose the single best card from search results.

    Highest rarity wins; ties go to the cheapest card (keeps it affordable).
    Cards without a CardMarket URL are skipped (can't be stored/refreshed).
    """
    candidates = [r for r in results if r.get("cardmarket_url")]
    if not candidates:
        return None
    return max(candidates, key=lambda r: (rarity_score(r["rarity"]), -r["price"]))


# Rarity keywords considered collectible/"nice" (full arts, alt arts, holos,
# VMAX/VSTAR/ex/Mega, radiant, shiny, rainbow, secret, gold, promos...).
_DESIRABLE_KEYWORDS = (
    "illustration", "holo", "ultra", "rainbow", "hyper", "radiant",
    "vmax", "vstar", "gx", "ex", "mega", "amazing", "shiny", "gold",
    "secret", "promo", "double rare", "full art", "alt",
)

# Per-Pokemon cap so very common Pokemon (Pikachu, Eevee) don't flood the grid.
MAX_CARDS_PER_POKEMON = 15


def is_desirable(rarity: str) -> bool:
    """True if a rarity is a collectible/special card worth seeding."""
    r = (rarity or "").lower()
    return any(keyword in r for keyword in _DESIRABLE_KEYWORDS)


def select_cards(results: list, max_cards: int = MAX_CARDS_PER_POKEMON) -> list:
    """Pick the nice/special cards for one Pokemon (may be several).

    Keeps all desirable rarities, de-duplicated by (name, set), ranked by
    rarity then price (fanciest first), capped at max_cards. Falls back to a
    single best card if nothing qualifies, guaranteeing at least one per Pokemon.
    """
    desirable = [r for r in results
                 if r.get("cardmarket_url") and is_desirable(r.get("rarity"))]
    seen = set()
    unique = []
    for card in sorted(desirable,
                       key=lambda r: (rarity_score(r["rarity"]), r["price"]),
                       reverse=True):
        key = (card["card_name"], card["set_name"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(card)
    if not unique:
        best = pick_best_card(results)
        return [best] if best else []
    return unique[:max_cards]


def _run_seed(app):
    global _seeding
    try:
        with app.app_context():
            from database import get_pokemon_list, get_all_cards, add_card
            existing = {c["pokemon_id"] for c in get_all_cards()}
            for pokemon in get_pokemon_list():
                if pokemon["id"] in existing:
                    continue
                results = search_cardmarket(pokemon["name"], max_price=MAX_PRICE,
                                            page_size=250)
                for card in select_cards(results):
                    add_card(
                        pokemon_id=pokemon["id"],
                        card_name=card["card_name"],
                        set_name=card["set_name"],
                        rarity=card["rarity"],
                        image_url=card.get("image_url"),
                        price=card["price"],
                        cardmarket_url=card["cardmarket_url"],
                    )
                time.sleep(1.0)
    finally:
        _seeding = False


def start_seed(app) -> bool:
    """Populate the wishlist in the background. Returns False if already running."""
    global _seeding
    if _seeding:
        return False
    _seeding = True
    threading.Thread(target=_run_seed, args=[app], daemon=True).start()
    return True
