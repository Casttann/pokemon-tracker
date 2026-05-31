import os
import tempfile
import pytest
from database import init_db, add_card, get_all_cards, get_card_by_id, \
    update_card_status, delete_card, save_price_snapshot, get_price_history, db
from app import create_app

@pytest.fixture(autouse=True)
def fresh_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.environ["POKEMON_DB_PATH"] = path
    app = create_app(testing=True)
    with app.app_context():
        init_db()
        yield
    os.close(fd)
    os.unlink(path)

def test_init_db_seeds_pokemon():
    from app import create_app
    app = create_app(testing=True)
    with app.app_context():
        cards = get_all_cards()
        assert isinstance(cards, list)
        from database import Pokemon
        from database import db
        count = db.session.query(Pokemon).count()
        assert count == 92

def test_add_card_returns_id():
    from app import create_app
    app = create_app(testing=True)
    with app.app_context():
        card_id = add_card(
            pokemon_id=1,
            card_name="Charizard ex - 199",
            set_name="Obsidian Flames",
            rarity="Special Illustration Rare",
            image_url="https://example.com/img.jpg",
            price=45.0,
            cardmarket_url="https://www.cardmarket.com/en/Pokemon/Products/Singles/Obsidian-Flames/Charizard-ex-199"
        )
        assert isinstance(card_id, int)

def test_get_all_cards_returns_added_card():
    from app import create_app
    app = create_app(testing=True)
    with app.app_context():
        add_card(pokemon_id=1, card_name="Test Card", set_name="Test Set",
                 rarity="Rare", image_url=None, price=10.0,
                 cardmarket_url="https://www.cardmarket.com/test")
        cards = get_all_cards()
        assert len(cards) == 1
        assert cards[0]["card_name"] == "Test Card"
        assert cards[0]["status"] == "wishlist"

def test_update_card_status():
    from app import create_app
    app = create_app(testing=True)
    with app.app_context():
        card_id = add_card(pokemon_id=1, card_name="Test", set_name="Set",
                           rarity="Rare", image_url=None, price=5.0,
                           cardmarket_url="https://www.cardmarket.com/test")
        update_card_status(card_id, "owned")
        card = get_card_by_id(card_id)
        assert card["status"] == "owned"

def test_delete_card_removes_history():
    from app import create_app
    app = create_app(testing=True)
    with app.app_context():
        card_id = add_card(pokemon_id=1, card_name="Test", set_name="Set",
                           rarity="Rare", image_url=None, price=5.0,
                           cardmarket_url="https://www.cardmarket.com/test")
        save_price_snapshot(card_id, 5.0)
        delete_card(card_id)
        assert get_card_by_id(card_id) is None
        assert get_price_history(card_id) == []

def test_price_snapshot_written_on_add():
    from app import create_app
    app = create_app(testing=True)
    with app.app_context():
        card_id = add_card(pokemon_id=1, card_name="Test", set_name="Set",
                           rarity="Rare", image_url=None, price=25.0,
                           cardmarket_url="https://www.cardmarket.com/test")
        history = get_price_history(card_id)
        assert len(history) == 1
        assert history[0]["price"] == 25.0
