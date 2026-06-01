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


def _run_seed(app):
    global _seeding
    try:
        with app.app_context():
            from database import get_pokemon_list, get_all_cards, add_card
            existing = {c["pokemon_id"] for c in get_all_cards()}
            for pokemon in get_pokemon_list():
                if pokemon["id"] in existing:
                    continue
                results = search_cardmarket(pokemon["name"], max_price=MAX_PRICE)
                best = pick_best_card(results)
                if best:
                    add_card(
                        pokemon_id=pokemon["id"],
                        card_name=best["card_name"],
                        set_name=best["set_name"],
                        rarity=best["rarity"],
                        image_url=best.get("image_url"),
                        price=best["price"],
                        cardmarket_url=best["cardmarket_url"],
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
