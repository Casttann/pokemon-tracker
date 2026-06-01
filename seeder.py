import threading
import time

from scraper import search_cardmarket, MAX_PRICE

_seeding = False


def is_seeding() -> bool:
    return _seeding


def rarity_score(rarity: str) -> int:
    """Rank a card rarity by collecting preference (higher is better).

    Order: Special Illustration Rare > Illustration Rare > Radiant > Holo >
    Triple Rare > Double Rare > any other Rare > everything else.
    """
    r = (rarity or "").lower()
    if "special illustration rare" in r:
        return 7
    if "illustration rare" in r:
        return 6
    if "radiant" in r:
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
MAX_CARDS_PER_POKEMON = 18
# Slots reserved for (cheap) promos so they survive the cap amid fancier cards.
PROMO_RESERVED = 4


def is_desirable(rarity: str) -> bool:
    """True if a rarity is a collectible/special card worth seeding."""
    r = (rarity or "").lower()
    return any(keyword in r for keyword in _DESIRABLE_KEYWORDS)


def is_combo_card(card_name: str) -> bool:
    """True for multi-Pokemon cards (Tag Team etc.), e.g. 'Pikachu & Zekrom-GX'."""
    name = card_name or ""
    return "&" in name or " + " in name


def _is_promo(rarity: str) -> bool:
    return "promo" in (rarity or "").lower()


def select_cards(results: list, max_cards: int = MAX_CARDS_PER_POKEMON,
                 reserved_promos: int = PROMO_RESERVED) -> list:
    """Pick the nice/special cards for one Pokemon (may be several).

    Excludes multi-Pokemon combo cards. Keeps all desirable rarities,
    de-duplicated by (name, set), ranked by rarity then price (fanciest first),
    capped at max_cards but reserving a few slots for cheap promos so they are
    not forgotten. Falls back to one best solo card so every Pokemon gets >=1.
    """
    solo = [r for r in results
            if r.get("cardmarket_url") and not is_combo_card(r.get("card_name"))]
    desirable = [r for r in solo if is_desirable(r.get("rarity"))]

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
        best = pick_best_card(solo)
        return [best] if best else []

    promos = [c for c in unique if _is_promo(c["rarity"])]
    non_promos = [c for c in unique if not _is_promo(c["rarity"])]
    reserved = sorted(promos, key=lambda r: r["price"])[:reserved_promos]

    take_non = max(max_cards - len(reserved), 0)
    chosen = non_promos[:take_non] + reserved
    if len(chosen) < max_cards:
        leftovers = non_promos[take_non:] + [p for p in promos if p not in reserved]
        chosen += leftovers[:max_cards - len(chosen)]
    return chosen[:max_cards]


def _run_seed(app):
    global _seeding
    try:
        with app.app_context():
            from database import get_pokemon_list, get_all_cards, add_card
            # Dedupe against cards already stored (by name + set), so re-running
            # the seed tops up missing special cards instead of skipping the
            # whole Pokemon or creating duplicates.
            owned = {(c["card_name"], c["set_name"]) for c in get_all_cards()}
            for pokemon in get_pokemon_list():
                results = search_cardmarket(pokemon["name"], max_price=MAX_PRICE,
                                            page_size=250)
                for card in select_cards(results):
                    key = (card["card_name"], card["set_name"])
                    if key in owned:
                        continue
                    owned.add(key)
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
