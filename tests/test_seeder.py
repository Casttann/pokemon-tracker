from seeder import rarity_score, pick_best_card


def test_rarity_score_order():
    assert rarity_score("Special Illustration Rare") > rarity_score("Illustration Rare")
    assert rarity_score("Illustration Rare") > rarity_score("Rare Holo")
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
