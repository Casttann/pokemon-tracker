from seeder import rarity_score, pick_best_card, is_desirable, select_cards


def _card(name, rarity, price, url="https://prices.pokemontcg.io/cardmarket/" ):
    return {"card_name": name, "set_name": "Set", "rarity": rarity,
            "price": price, "cardmarket_url": url + name, "image_url": None}


def test_rarity_score_order():
    assert rarity_score("Special Illustration Rare") > rarity_score("Illustration Rare")
    assert rarity_score("Illustration Rare") > rarity_score("Radiant Rare")
    assert rarity_score("Radiant Rare") > rarity_score("Rare Holo")
    assert rarity_score("Rare Holo") > rarity_score("Triple Rare")
    assert rarity_score("Triple Rare") > rarity_score("Double Rare")
    assert rarity_score("Double Rare") > rarity_score("Rare")
    assert rarity_score("Common") == 0
    assert rarity_score(None) == 0


def test_pick_best_prefers_higher_rarity():
    results = [
        {"card_name": "A", "rarity": "Rare Holo", "price": 5.0,
         "cardmarket_url": "https://prices.pokemontcg.io/cardmarket/a"},
        {"card_name": "B", "rarity": "Illustration Rare", "price": 40.0,
         "cardmarket_url": "https://prices.pokemontcg.io/cardmarket/b"},
    ]
    assert pick_best_card(results)["card_name"] == "B"


def test_pick_best_ties_break_on_cheapest():
    results = [
        {"card_name": "Expensive", "rarity": "Illustration Rare", "price": 80.0,
         "cardmarket_url": "https://prices.pokemontcg.io/cardmarket/x"},
        {"card_name": "Cheap", "rarity": "Illustration Rare", "price": 30.0,
         "cardmarket_url": "https://prices.pokemontcg.io/cardmarket/y"},
    ]
    assert pick_best_card(results)["card_name"] == "Cheap"


def test_pick_best_skips_cards_without_url():
    results = [
        {"card_name": "NoUrl", "rarity": "Illustration Rare", "price": 30.0,
         "cardmarket_url": ""},
    ]
    assert pick_best_card(results) is None


def test_pick_best_empty():
    assert pick_best_card([]) is None


def test_is_desirable_classification():
    for nice in ["Illustration Rare", "Rare Holo VMAX", "Radiant Rare",
                 "Rare Shiny", "Double Rare", "Rare Rainbow", "Promo",
                 "Rare Holo GX", "Ultra Rare"]:
        assert is_desirable(nice), nice
    for plain in ["Common", "Uncommon", "Rare", None, ""]:
        assert not is_desirable(plain), plain


def test_select_cards_returns_multiple():
    results = [
        _card("VMAX", "Rare Holo VMAX", 30.0),
        _card("Illus", "Illustration Rare", 40.0),
        _card("Radiant", "Radiant Rare", 5.0),
        _card("Plain", "Common", 0.1),
    ]
    selected = select_cards(results)
    names = {c["card_name"] for c in selected}
    assert names == {"VMAX", "Illus", "Radiant"}  # Common excluded


def test_select_cards_dedupes_by_name_and_set():
    results = [_card("Pikachu", "Illustration Rare", 40.0),
               _card("Pikachu", "Illustration Rare", 40.0)]
    assert len(select_cards(results)) == 1


def test_select_cards_respects_cap():
    results = [_card(f"C{i}", "Rare Holo", float(i + 1)) for i in range(30)]
    assert len(select_cards(results, max_cards=15)) == 15


def test_select_cards_fallback_guarantees_one():
    results = [_card("OnlyPlain", "Rare", 3.0)]
    selected = select_cards(results)
    assert len(selected) == 1
    assert selected[0]["card_name"] == "OnlyPlain"


def test_select_excludes_combo_cards():
    results = [
        _card("Pikachu & Zekrom-GX", "Rare Holo GX", 40.0),
        _card("Pikachu", "Illustration Rare", 44.0),
    ]
    names = {c["card_name"] for c in select_cards(results)}
    assert names == {"Pikachu"}


def test_select_fallback_excludes_combos():
    # No desirable solo card; only a combo (excluded) and a plain solo common.
    results = [
        _card("Piplup & Blastoise-GX", "Rare Holo GX", 20.0),
        _card("Piplup", "Common", 0.5),
    ]
    selected = select_cards(results)
    assert len(selected) == 1
    assert selected[0]["card_name"] == "Piplup"


def test_select_keeps_promos_despite_cap():
    fancy = [_card(f"Holo{i}", "Rare Holo", float(i + 1)) for i in range(20)]
    promos = [_card("PromoA", "Promo", 2.0), _card("PromoB", "Promo", 3.0)]
    selected = select_cards(fancy + promos, max_cards=5, reserved_promos=2)
    names = {c["card_name"] for c in selected}
    assert len(selected) == 5
    assert "PromoA" in names and "PromoB" in names
