# Pokemon Tracker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local Mac desktop app (Flask + SQLite + vanilla JS) to track a Pokemon card collection with CardMarket price scraping and PokemonTCG API images.

**Architecture:** Flask serves a single-page HTML app that opens automatically in the browser on launch. SQLite stores card data at `~/.pokemon_tracker/tracker.db`. A background APScheduler job scrapes CardMarket prices daily; images come from the PokemonTCG API at card-add time.

**Tech Stack:** Python 3.11+, Flask, SQLAlchemy, APScheduler, BeautifulSoup4, Requests, pytest, HTML/CSS/Vanilla JS

---

## File Map

| File | Responsibility |
|------|---------------|
| `pokemon_data.py` | Static list of 88 Pokemon (name, generation, type) |
| `database.py` | SQLAlchemy models + `init_db()` + all DB helper functions |
| `scraper.py` | CardMarket search + price update |
| `image_lookup.py` | PokemonTCG API image resolver with in-memory cache |
| `scheduler.py` | APScheduler daily job + startup trigger |
| `app.py` | Flask app + all routes |
| `templates/index.html` | Single-page HTML shell |
| `static/style.css` | Dark purple theme |
| `static/app.js` | All frontend logic (fetch, render, modals, filters) |
| `run.sh` | Port finder + Flask launcher + browser opener |
| `tests/conftest.py` | pytest fixtures (test Flask client, temp DB) |
| `tests/test_database.py` | DB model and helper function tests |
| `tests/test_scraper.py` | Scraper unit tests (mocked HTTP) |
| `tests/test_image_lookup.py` | Image lookup tests (mocked HTTP) |
| `tests/test_routes.py` | Flask route integration tests |

---

## Task 1: Project Setup

**Files:**
- Create: `requirements.txt`
- Create: `tests/conftest.py`
- Create: `.gitignore`

- [ ] **Step 1: Create virtual environment and install dependencies**

```bash
cd "/Users/mario-persomal/Desktop/ANTIGRAVITY/Pokemon Tracker"
python3 -m venv venv
source venv/bin/activate
pip install flask sqlalchemy apscheduler beautifulsoup4 requests pytest
pip freeze > requirements.txt
```

- [ ] **Step 2: Create `.gitignore`**

```
venv/
__pycache__/
*.pyc
.superpowers/
~/.pokemon_tracker/
*.db
```

- [ ] **Step 3: Create `tests/conftest.py`**

```python
import os
import tempfile
import pytest
from app import create_app
from database import init_db, db

@pytest.fixture
def app():
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.environ["POKEMON_DB_PATH"] = db_path
    application = create_app(testing=True)
    with application.app_context():
        init_db()
    yield application
    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def client(app):
    return app.test_client()
```

- [ ] **Step 4: Verify pytest runs (no tests yet, just collection)**

```bash
cd "/Users/mario-persomal/Desktop/ANTIGRAVITY/Pokemon Tracker"
source venv/bin/activate
pytest --collect-only
```
Expected: `no tests ran`

- [ ] **Step 5: Commit**

```bash
cd "/Users/mario-persomal/Desktop/ANTIGRAVITY/Pokemon Tracker"
git init
git add requirements.txt .gitignore tests/conftest.py
git commit -m "chore: project setup with dependencies and test config"
```

---

## Task 2: Pokemon Seed Data

**Files:**
- Create: `pokemon_data.py`
- Create: `tests/test_pokemon_data.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_pokemon_data.py`:

```python
from pokemon_data import POKEMON_LIST

def test_total_count():
    assert len(POKEMON_LIST) == 88

def test_required_fields():
    for p in POKEMON_LIST:
        assert "name" in p
        assert "generation" in p
        assert "type_1" in p

def test_special_group_generation():
    specials = [p for p in POKEMON_LIST if p["name"] in ("Pikachu", "Eevee")]
    for p in specials:
        assert p["generation"] == 0

def test_gen1_starters_present():
    names = [p["name"] for p in POKEMON_LIST]
    for name in ["Bulbasaur", "Charmander", "Squirtle", "Charizard"]:
        assert name in names

def test_eevee_evolutions_present():
    names = [p["name"] for p in POKEMON_LIST]
    for name in ["Vaporeon", "Jolteon", "Flareon", "Espeon", "Umbreon",
                 "Leafeon", "Glaceon", "Sylveon"]:
        assert name in names
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_pokemon_data.py -v
```
Expected: `ImportError: No module named 'pokemon_data'`

- [ ] **Step 3: Create `pokemon_data.py`**

```python
POKEMON_LIST = [
    # Gen 1 — Starters
    {"name": "Bulbasaur",   "generation": 1, "type_1": "Grass",  "type_2": "Poison"},
    {"name": "Ivysaur",     "generation": 1, "type_1": "Grass",  "type_2": "Poison"},
    {"name": "Venusaur",    "generation": 1, "type_1": "Grass",  "type_2": "Poison"},
    {"name": "Charmander",  "generation": 1, "type_1": "Fire",   "type_2": None},
    {"name": "Charmeleon",  "generation": 1, "type_1": "Fire",   "type_2": None},
    {"name": "Charizard",   "generation": 1, "type_1": "Fire",   "type_2": "Flying"},
    {"name": "Squirtle",    "generation": 1, "type_1": "Water",  "type_2": None},
    {"name": "Wartortle",   "generation": 1, "type_1": "Water",  "type_2": None},
    {"name": "Blastoise",   "generation": 1, "type_1": "Water",  "type_2": None},
    # Gen 2
    {"name": "Chikorita",   "generation": 2, "type_1": "Grass",  "type_2": None},
    {"name": "Bayleef",     "generation": 2, "type_1": "Grass",  "type_2": None},
    {"name": "Meganium",    "generation": 2, "type_1": "Grass",  "type_2": None},
    {"name": "Cyndaquil",   "generation": 2, "type_1": "Fire",   "type_2": None},
    {"name": "Quilava",     "generation": 2, "type_1": "Fire",   "type_2": None},
    {"name": "Typhlosion",  "generation": 2, "type_1": "Fire",   "type_2": None},
    {"name": "Totodile",    "generation": 2, "type_1": "Water",  "type_2": None},
    {"name": "Croconaw",    "generation": 2, "type_1": "Water",  "type_2": None},
    {"name": "Feraligatr",  "generation": 2, "type_1": "Water",  "type_2": None},
    # Gen 3
    {"name": "Treecko",     "generation": 3, "type_1": "Grass",  "type_2": None},
    {"name": "Grovyle",     "generation": 3, "type_1": "Grass",  "type_2": None},
    {"name": "Sceptile",    "generation": 3, "type_1": "Grass",  "type_2": None},
    {"name": "Torchic",     "generation": 3, "type_1": "Fire",   "type_2": None},
    {"name": "Combusken",   "generation": 3, "type_1": "Fire",   "type_2": "Fighting"},
    {"name": "Blaziken",    "generation": 3, "type_1": "Fire",   "type_2": "Fighting"},
    {"name": "Mudkip",      "generation": 3, "type_1": "Water",  "type_2": None},
    {"name": "Marshtomp",   "generation": 3, "type_1": "Water",  "type_2": "Ground"},
    {"name": "Swampert",    "generation": 3, "type_1": "Water",  "type_2": "Ground"},
    # Gen 4
    {"name": "Turtwig",     "generation": 4, "type_1": "Grass",  "type_2": None},
    {"name": "Grotle",      "generation": 4, "type_1": "Grass",  "type_2": None},
    {"name": "Torterra",    "generation": 4, "type_1": "Grass",  "type_2": "Ground"},
    {"name": "Chimchar",    "generation": 4, "type_1": "Fire",   "type_2": None},
    {"name": "Monferno",    "generation": 4, "type_1": "Fire",   "type_2": "Fighting"},
    {"name": "Infernape",   "generation": 4, "type_1": "Fire",   "type_2": "Fighting"},
    {"name": "Piplup",      "generation": 4, "type_1": "Water",  "type_2": None},
    {"name": "Prinplup",    "generation": 4, "type_1": "Water",  "type_2": None},
    {"name": "Empoleon",    "generation": 4, "type_1": "Water",  "type_2": "Steel"},
    # Gen 5
    {"name": "Snivy",       "generation": 5, "type_1": "Grass",  "type_2": None},
    {"name": "Servine",     "generation": 5, "type_1": "Grass",  "type_2": None},
    {"name": "Serperior",   "generation": 5, "type_1": "Grass",  "type_2": None},
    {"name": "Tepig",       "generation": 5, "type_1": "Fire",   "type_2": None},
    {"name": "Pignite",     "generation": 5, "type_1": "Fire",   "type_2": "Fighting"},
    {"name": "Emboar",      "generation": 5, "type_1": "Fire",   "type_2": "Fighting"},
    {"name": "Oshawott",    "generation": 5, "type_1": "Water",  "type_2": None},
    {"name": "Dewott",      "generation": 5, "type_1": "Water",  "type_2": None},
    {"name": "Samurott",    "generation": 5, "type_1": "Water",  "type_2": None},
    # Gen 6
    {"name": "Chespin",     "generation": 6, "type_1": "Grass",  "type_2": None},
    {"name": "Quilladin",   "generation": 6, "type_1": "Grass",  "type_2": None},
    {"name": "Chesnaught",  "generation": 6, "type_1": "Grass",  "type_2": "Fighting"},
    {"name": "Fennekin",    "generation": 6, "type_1": "Fire",   "type_2": None},
    {"name": "Braixen",     "generation": 6, "type_1": "Fire",   "type_2": None},
    {"name": "Delphox",     "generation": 6, "type_1": "Fire",   "type_2": "Psychic"},
    {"name": "Froakie",     "generation": 6, "type_1": "Water",  "type_2": None},
    {"name": "Frogadier",   "generation": 6, "type_1": "Water",  "type_2": None},
    {"name": "Greninja",    "generation": 6, "type_1": "Water",  "type_2": "Dark"},
    # Gen 7
    {"name": "Rowlet",      "generation": 7, "type_1": "Grass",  "type_2": "Flying"},
    {"name": "Dartrix",     "generation": 7, "type_1": "Grass",  "type_2": "Flying"},
    {"name": "Decidueye",   "generation": 7, "type_1": "Grass",  "type_2": "Ghost"},
    {"name": "Litten",      "generation": 7, "type_1": "Fire",   "type_2": None},
    {"name": "Torracat",    "generation": 7, "type_1": "Fire",   "type_2": None},
    {"name": "Incineroar",  "generation": 7, "type_1": "Fire",   "type_2": "Dark"},
    {"name": "Popplio",     "generation": 7, "type_1": "Water",  "type_2": None},
    {"name": "Brionne",     "generation": 7, "type_1": "Water",  "type_2": None},
    {"name": "Primarina",   "generation": 7, "type_1": "Water",  "type_2": "Fairy"},
    # Gen 8
    {"name": "Grookey",     "generation": 8, "type_1": "Grass",  "type_2": None},
    {"name": "Thwackey",    "generation": 8, "type_1": "Grass",  "type_2": None},
    {"name": "Rillaboom",   "generation": 8, "type_1": "Grass",  "type_2": None},
    {"name": "Scorbunny",   "generation": 8, "type_1": "Fire",   "type_2": None},
    {"name": "Raboot",      "generation": 8, "type_1": "Fire",   "type_2": None},
    {"name": "Cinderace",   "generation": 8, "type_1": "Fire",   "type_2": None},
    {"name": "Sobble",      "generation": 8, "type_1": "Water",  "type_2": None},
    {"name": "Drizzile",    "generation": 8, "type_1": "Water",  "type_2": None},
    {"name": "Inteleon",    "generation": 8, "type_1": "Water",  "type_2": None},
    # Gen 9
    {"name": "Sprigatito",  "generation": 9, "type_1": "Grass",  "type_2": None},
    {"name": "Floragato",   "generation": 9, "type_1": "Grass",  "type_2": None},
    {"name": "Meowscarada", "generation": 9, "type_1": "Grass",  "type_2": "Dark"},
    {"name": "Fuecoco",     "generation": 9, "type_1": "Fire",   "type_2": None},
    {"name": "Crocalor",    "generation": 9, "type_1": "Fire",   "type_2": None},
    {"name": "Skeledirge",  "generation": 9, "type_1": "Fire",   "type_2": "Ghost"},
    {"name": "Quaxly",      "generation": 9, "type_1": "Water",  "type_2": None},
    {"name": "Quaxwell",    "generation": 9, "type_1": "Water",  "type_2": None},
    {"name": "Quaquaval",   "generation": 9, "type_1": "Water",  "type_2": "Fighting"},
    # Special group (generation = 0)
    {"name": "Pikachu",     "generation": 0, "type_1": "Electric", "type_2": None},
    {"name": "Raichu",      "generation": 0, "type_1": "Electric", "type_2": None},
    {"name": "Eevee",       "generation": 0, "type_1": "Normal",   "type_2": None},
    {"name": "Vaporeon",    "generation": 0, "type_1": "Water",    "type_2": None},
    {"name": "Jolteon",     "generation": 0, "type_1": "Electric", "type_2": None},
    {"name": "Flareon",     "generation": 0, "type_1": "Fire",     "type_2": None},
    {"name": "Espeon",      "generation": 0, "type_1": "Psychic",  "type_2": None},
    {"name": "Umbreon",     "generation": 0, "type_1": "Dark",     "type_2": None},
    {"name": "Leafeon",     "generation": 0, "type_1": "Grass",    "type_2": None},
    {"name": "Glaceon",     "generation": 0, "type_1": "Ice",      "type_2": None},
    {"name": "Sylveon",     "generation": 0, "type_1": "Fairy",    "type_2": None},
]
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_pokemon_data.py -v
```
Expected: 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add pokemon_data.py tests/test_pokemon_data.py
git commit -m "feat: add Pokemon seed data (88 Pokemon)"
```

---

## Task 3: Database Models and Helpers

**Files:**
- Create: `database.py`
- Create: `tests/test_database.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_database.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_database.py -v
```
Expected: `ImportError: No module named 'database'`

- [ ] **Step 3: Create `database.py`**

```python
import os
from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from pokemon_data import POKEMON_LIST

db = SQLAlchemy()


class Pokemon(db.Model):
    __tablename__ = "pokemon"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    generation = db.Column(db.Integer, nullable=False)
    type_1 = db.Column(db.Text, nullable=False)
    type_2 = db.Column(db.Text, nullable=True)
    cards = db.relationship("Card", backref="pokemon", lazy=True)


class Card(db.Model):
    __tablename__ = "cards"
    id = db.Column(db.Integer, primary_key=True)
    pokemon_id = db.Column(db.Integer, db.ForeignKey("pokemon.id"), nullable=False)
    card_name = db.Column(db.Text, nullable=False)
    set_name = db.Column(db.Text, nullable=False)
    rarity = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.Text, nullable=True)
    price_current = db.Column(db.Float, nullable=True)
    price_updated = db.Column(db.Text, nullable=True)
    status = db.Column(db.Text, nullable=False, default="wishlist")
    cardmarket_url = db.Column(db.Text, nullable=False)
    history = db.relationship("PriceHistory", backref="card", lazy=True,
                               cascade="all, delete-orphan")


class PriceHistory(db.Model):
    __tablename__ = "price_history"
    id = db.Column(db.Integer, primary_key=True)
    card_id = db.Column(db.Integer, db.ForeignKey("cards.id"), nullable=False)
    price = db.Column(db.Float, nullable=False)
    recorded = db.Column(db.Text, nullable=False)


def init_db():
    db.create_all()
    if Pokemon.query.count() == 0:
        for p in POKEMON_LIST:
            db.session.add(Pokemon(
                name=p["name"],
                generation=p["generation"],
                type_1=p["type_1"],
                type_2=p.get("type_2"),
            ))
        db.session.commit()


def _card_to_dict(card):
    return {
        "id": card.id,
        "pokemon_id": card.pokemon_id,
        "pokemon_name": card.pokemon.name,
        "pokemon_type_1": card.pokemon.type_1,
        "pokemon_generation": card.pokemon.generation,
        "card_name": card.card_name,
        "set_name": card.set_name,
        "rarity": card.rarity,
        "image_url": card.image_url,
        "price_current": card.price_current,
        "price_updated": card.price_updated,
        "status": card.status,
        "cardmarket_url": card.cardmarket_url,
    }


def get_all_cards(status=None):
    q = Card.query
    if status in ("wishlist", "owned"):
        q = q.filter_by(status=status)
    return [_card_to_dict(c) for c in q.all()]


def get_card_by_id(card_id):
    card = Card.query.get(card_id)
    return _card_to_dict(card) if card else None


def add_card(pokemon_id, card_name, set_name, rarity, image_url,
             price, cardmarket_url):
    now = datetime.now(timezone.utc).isoformat()
    card = Card(
        pokemon_id=pokemon_id,
        card_name=card_name,
        set_name=set_name,
        rarity=rarity,
        image_url=image_url,
        price_current=price,
        price_updated=now,
        status="wishlist",
        cardmarket_url=cardmarket_url,
    )
    db.session.add(card)
    db.session.flush()
    snapshot = PriceHistory(card_id=card.id, price=price, recorded=now)
    db.session.add(snapshot)
    db.session.commit()
    return card.id


def update_card_status(card_id, new_status):
    card = Card.query.get(card_id)
    if card:
        card.status = new_status
        db.session.commit()


def delete_card(card_id):
    card = Card.query.get(card_id)
    if card:
        db.session.delete(card)
        db.session.commit()


def save_price_snapshot(card_id, price):
    now = datetime.now(timezone.utc).isoformat()
    card = Card.query.get(card_id)
    if card:
        card.price_current = price
        card.price_updated = now
        db.session.add(PriceHistory(card_id=card_id, price=price, recorded=now))
        db.session.commit()


def get_price_history(card_id):
    rows = PriceHistory.query.filter_by(card_id=card_id)\
               .order_by(PriceHistory.recorded.asc()).all()
    return [{"price": r.price, "recorded": r.recorded} for r in rows]


def get_pokemon_list():
    pokemon = Pokemon.query.order_by(Pokemon.generation, Pokemon.id).all()
    result = []
    for p in pokemon:
        result.append({
            "id": p.id,
            "name": p.name,
            "generation": p.generation,
            "type_1": p.type_1,
            "type_2": p.type_2,
            "card_count": len(p.cards),
        })
    return result
```

- [ ] **Step 4: Create minimal `app.py` (needed by conftest)**

```python
import os
from flask import Flask
from database import db

def create_app(testing=False):
    app = Flask(__name__)
    db_path = os.environ.get("POKEMON_DB_PATH",
                             os.path.expanduser("~/.pokemon_tracker/tracker.db"))
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["TESTING"] = testing
    db.init_app(app)
    return app
```

- [ ] **Step 5: Install flask-sqlalchemy**

```bash
source venv/bin/activate
pip install flask-sqlalchemy
pip freeze > requirements.txt
```

- [ ] **Step 6: Run tests**

```bash
pytest tests/test_database.py -v
```
Expected: 6 tests PASS

- [ ] **Step 7: Commit**

```bash
git add database.py app.py tests/test_database.py requirements.txt
git commit -m "feat: database models and helper functions"
```

---

## Task 4: CardMarket Scraper

**Files:**
- Create: `scraper.py`
- Create: `tests/test_scraper.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_scraper.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_scraper.py -v
```
Expected: `ImportError: No module named 'scraper'`

- [ ] **Step 3: Create `scraper.py`**

```python
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
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_scraper.py -v
```
Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add scraper.py tests/test_scraper.py
git commit -m "feat: CardMarket scraper (search + price update)"
```

---

## Task 5: PokemonTCG Image Lookup

**Files:**
- Create: `image_lookup.py`
- Create: `tests/test_image_lookup.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_image_lookup.py`:

```python
from unittest.mock import patch
from image_lookup import find_card_image, _cache

MOCK_API_RESPONSE = {
    "data": [
        {
            "id": "sv3-199",
            "name": "Charizard ex",
            "set": {"name": "Obsidian Flames"},
            "images": {
                "large": "https://images.pokemontcg.io/sv3/199_hires.png"
            }
        }
    ]
}

def test_returns_image_url_on_match():
    _cache.clear()
    with patch("image_lookup.requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = MOCK_API_RESPONSE
        url = find_card_image("Charizard ex", "Obsidian Flames")
        assert url == "https://images.pokemontcg.io/sv3/199_hires.png"

def test_returns_none_when_no_match():
    _cache.clear()
    with patch("image_lookup.requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"data": []}
        url = find_card_image("Unknown Card", "Unknown Set")
        assert url is None

def test_uses_cache_on_second_call():
    _cache.clear()
    with patch("image_lookup.requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = MOCK_API_RESPONSE
        find_card_image("Charizard ex", "Obsidian Flames")
        find_card_image("Charizard ex", "Obsidian Flames")
        assert mock_get.call_count == 1

def test_returns_none_on_rate_limit():
    _cache.clear()
    with patch("image_lookup.requests.get") as mock_get:
        mock_get.return_value.status_code = 429
        url = find_card_image("Pikachu", "Some Set")
        assert url is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_image_lookup.py -v
```
Expected: `ImportError: No module named 'image_lookup'`

- [ ] **Step 3: Create `image_lookup.py`**

```python
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
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_image_lookup.py -v
```
Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add image_lookup.py tests/test_image_lookup.py
git commit -m "feat: PokemonTCG API image lookup with in-memory cache"
```

---

## Task 6: Scheduler

**Files:**
- Create: `scheduler.py`

- [ ] **Step 1: Create `scheduler.py`**

(No unit tests — APScheduler is an infrastructure concern. Behavior is verified via integration.)

```python
import os
from datetime import datetime, timezone, timedelta
from apscheduler.schedulers.background import BackgroundScheduler

_scheduler = BackgroundScheduler()
_updating = False


def is_updating() -> bool:
    return _updating


def _run_price_update(app):
    global _updating
    _updating = True
    try:
        with app.app_context():
            from database import get_all_cards, save_price_snapshot
            from scraper import update_price
            cards = get_all_cards()
            for card in cards:
                if not card.get("cardmarket_url"):
                    continue
                price = update_price(card["cardmarket_url"])
                if price is not None:
                    save_price_snapshot(card["id"], price)
            _write_last_update()
    finally:
        _updating = False


def _write_last_update():
    path = os.path.expanduser("~/.pokemon_tracker/last_update.txt")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(datetime.now(timezone.utc).isoformat())


def get_last_update() -> str | None:
    path = os.path.expanduser("~/.pokemon_tracker/last_update.txt")
    try:
        with open(path) as f:
            return f.read().strip()
    except FileNotFoundError:
        return None


def _needs_update() -> bool:
    last = get_last_update()
    if not last:
        return True
    try:
        last_dt = datetime.fromisoformat(last)
        return datetime.now(timezone.utc) - last_dt > timedelta(hours=24)
    except ValueError:
        return True


def start_scheduler(app):
    _scheduler.add_job(
        _run_price_update, "cron", hour=9, minute=0, args=[app]
    )
    _scheduler.start()
    if _needs_update():
        import threading
        t = threading.Thread(target=_run_price_update, args=[app], daemon=True)
        t.start()


def trigger_refresh(app):
    """Manually trigger a price update. Returns False if already running."""
    global _updating
    if _updating:
        return False
    import threading
    t = threading.Thread(target=_run_price_update, args=[app], daemon=True)
    t.start()
    return True
```

- [ ] **Step 2: Commit**

```bash
git add scheduler.py
git commit -m "feat: APScheduler daily price update job"
```

---

## Task 7: Flask Routes

**Files:**
- Modify: `app.py` (add all routes)
- Create: `tests/test_routes.py`

- [ ] **Step 1: Write failing route tests**

Create `tests/test_routes.py`:

```python
import json
import os
import tempfile
import pytest
from app import create_app
from database import init_db, add_card

@pytest.fixture
def client():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.environ["POKEMON_DB_PATH"] = path
    app = create_app(testing=True)
    with app.app_context():
        init_db()
    yield app.test_client()
    os.close(fd)
    os.unlink(path)

def test_get_pokemon_returns_92(client):
    resp = client.get("/api/pokemon")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert len(data) == 92

def test_add_card_success(client):
    resp = client.post("/api/cards", json={
        "pokemon_id": 1,
        "card_name": "Charizard ex",
        "set_name": "Obsidian Flames",
        "rarity": "SIR",
        "price": 45.0,
        "image_url": None,
        "cardmarket_url": "https://www.cardmarket.com/en/Pokemon/test"
    })
    assert resp.status_code == 201
    data = json.loads(resp.data)
    assert "id" in data

def test_add_card_invalid_url(client):
    resp = client.post("/api/cards", json={
        "pokemon_id": 1,
        "card_name": "Test",
        "set_name": "Set",
        "rarity": "Rare",
        "price": 10.0,
        "image_url": None,
        "cardmarket_url": "https://evil.com/bad"
    })
    assert resp.status_code == 400

def test_add_card_price_over_budget(client):
    resp = client.post("/api/cards", json={
        "pokemon_id": 1,
        "card_name": "Test",
        "set_name": "Set",
        "rarity": "Rare",
        "price": 150.0,
        "image_url": None,
        "cardmarket_url": "https://www.cardmarket.com/test"
    })
    assert resp.status_code == 400

def test_patch_card_status(client):
    add_resp = client.post("/api/cards", json={
        "pokemon_id": 1, "card_name": "Test", "set_name": "Set",
        "rarity": "Rare", "price": 10.0, "image_url": None,
        "cardmarket_url": "https://www.cardmarket.com/test"
    })
    card_id = json.loads(add_resp.data)["id"]
    resp = client.patch(f"/api/cards/{card_id}", json={"status": "owned"})
    assert resp.status_code == 200
    assert json.loads(resp.data)["status"] == "owned"

def test_patch_invalid_status(client):
    add_resp = client.post("/api/cards", json={
        "pokemon_id": 1, "card_name": "Test", "set_name": "Set",
        "rarity": "Rare", "price": 10.0, "image_url": None,
        "cardmarket_url": "https://www.cardmarket.com/test"
    })
    card_id = json.loads(add_resp.data)["id"]
    resp = client.patch(f"/api/cards/{card_id}", json={"status": "invalid"})
    assert resp.status_code == 400

def test_delete_card(client):
    add_resp = client.post("/api/cards", json={
        "pokemon_id": 1, "card_name": "Test", "set_name": "Set",
        "rarity": "Rare", "price": 10.0, "image_url": None,
        "cardmarket_url": "https://www.cardmarket.com/test"
    })
    card_id = json.loads(add_resp.data)["id"]
    resp = client.delete(f"/api/cards/{card_id}")
    assert resp.status_code == 204

def test_get_cards_filter_by_status(client):
    client.post("/api/cards", json={
        "pokemon_id": 1, "card_name": "Wishlist Card", "set_name": "Set",
        "rarity": "Rare", "price": 10.0, "image_url": None,
        "cardmarket_url": "https://www.cardmarket.com/w"
    })
    resp = client.get("/api/cards?status=owned")
    assert json.loads(resp.data) == []

def test_get_price_history(client):
    add_resp = client.post("/api/cards", json={
        "pokemon_id": 1, "card_name": "Test", "set_name": "Set",
        "rarity": "Rare", "price": 10.0, "image_url": None,
        "cardmarket_url": "https://www.cardmarket.com/test"
    })
    card_id = json.loads(add_resp.data)["id"]
    resp = client.get(f"/api/cards/{card_id}/history")
    data = json.loads(resp.data)
    assert len(data) == 1
    assert data[0]["price"] == 10.0

def test_status_endpoint(client):
    resp = client.get("/api/status")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert "updating" in data
    assert "last_update" in data
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_routes.py -v
```
Expected: failures (no routes defined yet)

- [ ] **Step 3: Complete `app.py` with all routes**

```python
import os
from flask import Flask, jsonify, request, render_template
from database import db, init_db, get_all_cards, get_card_by_id, add_card, \
    update_card_status, delete_card, get_price_history, get_pokemon_list

MAX_PRICE = 100.0


def create_app(testing=False):
    app = Flask(__name__)
    db_path = os.environ.get("POKEMON_DB_PATH",
                             os.path.expanduser("~/.pokemon_tracker/tracker.db"))
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["TESTING"] = testing
    db.init_app(app)

    with app.app_context():
        init_db()

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/api/pokemon")
    def api_pokemon():
        return jsonify(get_pokemon_list())

    @app.route("/api/cards", methods=["GET"])
    def api_get_cards():
        status = request.args.get("status")
        return jsonify(get_all_cards(status=status))

    @app.route("/api/cards", methods=["POST"])
    def api_add_card():
        data = request.get_json()
        url = data.get("cardmarket_url", "")
        if not url.startswith("https://www.cardmarket.com/"):
            return jsonify({"error": "URL must start with https://www.cardmarket.com/"}), 400
        price = data.get("price")
        if not isinstance(price, (int, float)) or price <= 0 or price > MAX_PRICE:
            return jsonify({"error": f"Price must be a positive number <= {MAX_PRICE}"}), 400
        card_id = add_card(
            pokemon_id=data["pokemon_id"],
            card_name=data["card_name"],
            set_name=data["set_name"],
            rarity=data["rarity"],
            image_url=data.get("image_url"),
            price=float(price),
            cardmarket_url=url,
        )
        return jsonify({"id": card_id}), 201

    @app.route("/api/cards/<int:card_id>", methods=["PATCH"])
    def api_update_card(card_id):
        data = request.get_json()
        new_status = data.get("status")
        if new_status not in ("wishlist", "owned"):
            return jsonify({"error": "status must be 'wishlist' or 'owned'"}), 400
        card = get_card_by_id(card_id)
        if not card:
            return jsonify({"error": "Card not found"}), 404
        update_card_status(card_id, new_status)
        return jsonify(get_card_by_id(card_id))

    @app.route("/api/cards/<int:card_id>", methods=["DELETE"])
    def api_delete_card(card_id):
        delete_card(card_id)
        return "", 204

    @app.route("/api/cards/<int:card_id>/history")
    def api_card_history(card_id):
        return jsonify(get_price_history(card_id))

    @app.route("/api/search", methods=["POST"])
    def api_search():
        from scraper import search_cardmarket
        from image_lookup import find_card_image
        data = request.get_json()
        pokemon_name = data.get("pokemon_name", "")
        results = search_cardmarket(pokemon_name, max_price=MAX_PRICE)
        for r in results:
            r["image_url"] = find_card_image(r["card_name"], r["set_name"])
        return jsonify(results)

    @app.route("/api/refresh", methods=["POST"])
    def api_refresh():
        from scheduler import trigger_refresh, is_updating
        if is_updating():
            return jsonify({"status": "already_running"})
        trigger_refresh(app)
        return jsonify({"status": "started"})

    @app.route("/api/status")
    def api_status():
        from scheduler import get_last_update, is_updating
        return jsonify({
            "last_update": get_last_update(),
            "updating": is_updating(),
        })

    return app


if __name__ == "__main__":
    port = int(os.environ.get("FLASK_PORT", 5000))
    application = create_app()
    if not application.config.get("TESTING"):
        from scheduler import start_scheduler
        start_scheduler(application)
    application.run(port=port, debug=False)
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_routes.py -v
```
Expected: all tests PASS

- [ ] **Step 5: Run full test suite**

```bash
pytest -v
```
Expected: all tests PASS

- [ ] **Step 6: Commit**

```bash
git add app.py tests/test_routes.py
git commit -m "feat: Flask routes (all API endpoints)"
```

---

## Task 8: Frontend HTML + CSS

**Files:**
- Create: `templates/index.html`
- Create: `static/style.css`

- [ ] **Step 1: Create `templates/index.html`**

```html
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Pokédex Tracker</title>
  <link rel="stylesheet" href="/static/style.css">
</head>
<body>
  <!-- HEADER -->
  <header>
    <div class="header-title">⚡ Pokédex Tracker</div>
    <div class="header-stats">
      <span class="stat"><span class="stat-value" id="stat-total">0</span> cartas</span>
      <span class="stat">Wishlist: <span class="stat-value" id="stat-wishlist">€0</span></span>
      <span class="stat">Colección: <span class="stat-value" id="stat-owned">€0</span></span>
      <span class="stat last-update" id="stat-updated">–</span>
    </div>
    <button class="btn-refresh" id="btn-refresh" onclick="triggerRefresh()">
      <span id="refresh-icon">↻</span> Actualizar precios
    </button>
  </header>

  <!-- FILTERS -->
  <div class="filters">
    <div class="filter-tabs">
      <button class="tab active" onclick="setTab(this, 'all')">Todos</button>
      <button class="tab" onclick="setTab(this, 'wishlist')">Wishlist</button>
      <button class="tab" onclick="setTab(this, 'owned')">Colección</button>
    </div>
    <div class="filter-gens">
      <button class="gen-btn active" onclick="setGen(this, null)">Todas</button>
      <button class="gen-btn" onclick="setGen(this, 1)">Gen 1</button>
      <button class="gen-btn" onclick="setGen(this, 2)">Gen 2</button>
      <button class="gen-btn" onclick="setGen(this, 3)">Gen 3</button>
      <button class="gen-btn" onclick="setGen(this, 4)">Gen 4</button>
      <button class="gen-btn" onclick="setGen(this, 5)">Gen 5</button>
      <button class="gen-btn" onclick="setGen(this, 6)">Gen 6</button>
      <button class="gen-btn" onclick="setGen(this, 7)">Gen 7</button>
      <button class="gen-btn" onclick="setGen(this, 8)">Gen 8</button>
      <button class="gen-btn" onclick="setGen(this, 9)">Gen 9</button>
      <button class="gen-btn" onclick="setGen(this, 0)">Special</button>
    </div>
    <input class="search-input" id="search-input" placeholder="Buscar Pokemon..." oninput="renderGrid()">
  </div>

  <!-- MAIN GRID -->
  <main id="grid"></main>

  <!-- ADD CARD MODAL -->
  <div class="modal-overlay" id="modal-add" style="display:none" onclick="closeAddModal(event)">
    <div class="modal">
      <h2>Añadir carta</h2>
      <div class="modal-search">
        <input class="modal-input" id="add-search-input" placeholder="Nombre del Pokemon...">
        <button class="btn-primary" onclick="searchCards()">Buscar</button>
      </div>
      <div id="search-results"></div>
    </div>
  </div>

  <!-- CARD DETAIL MODAL -->
  <div class="modal-overlay" id="modal-detail" style="display:none" onclick="closeDetailModal(event)">
    <div class="modal modal-detail-inner">
      <div id="detail-content"></div>
    </div>
  </div>

  <script src="/static/app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Create `static/style.css`**

```css
:root {
  --bg: #0a0a0f;
  --card-bg: #0f0f1a;
  --border: #312e81;
  --accent: #c084fc;
  --accent-dim: #7c3aed;
  --text: #e2e8f0;
  --text-dim: #64748b;
  --owned: #4ade80;
  --empty: #1a1a2e;
  --radius: 8px;
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  min-height: 100vh;
}

/* HEADER */
header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 24px;
  border-bottom: 1px solid var(--border);
  background: #07070d;
  position: sticky;
  top: 0;
  z-index: 10;
  flex-wrap: wrap;
}

.header-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--accent);
  letter-spacing: 1px;
}

.header-stats {
  display: flex;
  gap: 20px;
  flex: 1;
  flex-wrap: wrap;
}

.stat { font-size: 13px; color: var(--text-dim); }
.stat-value { color: var(--accent); font-weight: 600; }
.last-update { font-size: 11px; }

.btn-refresh {
  background: var(--accent-dim);
  color: white;
  border: none;
  border-radius: var(--radius);
  padding: 8px 16px;
  cursor: pointer;
  font-size: 13px;
  transition: background 0.2s;
}
.btn-refresh:hover { background: var(--accent); }
.btn-refresh.spinning #refresh-icon { display: inline-block; animation: spin 1s linear infinite; }

@keyframes spin { to { transform: rotate(360deg); } }

/* FILTERS */
.filters {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 24px;
  border-bottom: 1px solid var(--border);
  flex-wrap: wrap;
}

.filter-tabs, .filter-gens { display: flex; gap: 4px; }

.tab, .gen-btn {
  background: transparent;
  border: 1px solid var(--border);
  color: var(--text-dim);
  border-radius: 20px;
  padding: 4px 12px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
}
.tab.active, .gen-btn.active {
  background: var(--accent-dim);
  border-color: var(--accent);
  color: white;
}

.search-input {
  background: var(--card-bg);
  border: 1px solid var(--border);
  color: var(--text);
  border-radius: 20px;
  padding: 4px 14px;
  font-size: 13px;
  width: 200px;
  margin-left: auto;
}
.search-input:focus { outline: none; border-color: var(--accent); }

/* GRID */
main {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 16px;
  padding: 24px;
}

/* POKEMON SLOT */
.pokemon-slot { display: flex; flex-direction: column; gap: 8px; }

.slot-label {
  font-size: 11px;
  color: var(--text-dim);
  text-align: center;
  letter-spacing: 0.5px;
}

/* EMPTY SLOT */
.card-empty {
  background: var(--empty);
  border: 1px dashed #2d2d5e;
  border-radius: var(--radius);
  aspect-ratio: 2.5/3.5;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s;
}
.card-empty:hover { border-color: var(--accent); background: #12122a; }
.card-empty .plus { font-size: 28px; color: #2d2d5e; }
.card-empty:hover .plus { color: var(--accent); }

/* CARD TILE */
.card-tile {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
  cursor: pointer;
  transition: border-color 0.2s, transform 0.15s;
  position: relative;
}
.card-tile:hover { border-color: var(--accent); transform: translateY(-2px); }
.card-tile.owned { border-color: #166534; }

.card-img-wrap {
  width: 100%;
  aspect-ratio: 2.5/3.5;
  background: #0a0a18;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}
.card-img-wrap img { width: 100%; height: 100%; object-fit: cover; }

.card-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 40px;
  opacity: 0.4;
}

.card-info {
  padding: 8px;
}
.card-name { font-size: 11px; color: var(--text); font-weight: 600; margin-bottom: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.card-price { font-size: 13px; color: var(--accent); font-weight: 700; }
.card-price.stale { color: #f59e0b; }

.badge {
  position: absolute;
  top: 6px;
  right: 6px;
  border-radius: 10px;
  padding: 2px 7px;
  font-size: 10px;
  font-weight: 600;
}
.badge-wishlist { background: #3b1f7a; color: var(--accent); }
.badge-owned { background: #14532d; color: var(--owned); }
.badge-stale { position: static; background: #78350f; color: #f59e0b; font-size: 9px; }

/* STACK indicator */
.card-stack { position: relative; }
.card-stack::after {
  content: "";
  position: absolute;
  top: 4px;
  left: 4px;
  right: -4px;
  bottom: -4px;
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  z-index: -1;
}

/* MODAL */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.75);
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.modal {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 24px;
  max-width: 480px;
  width: 100%;
  max-height: 80vh;
  overflow-y: auto;
}

.modal h2 { color: var(--accent); margin-bottom: 16px; font-size: 16px; }

.modal-search { display: flex; gap: 8px; margin-bottom: 16px; }
.modal-input {
  flex: 1;
  background: var(--bg);
  border: 1px solid var(--border);
  color: var(--text);
  border-radius: var(--radius);
  padding: 8px 12px;
  font-size: 13px;
}
.modal-input:focus { outline: none; border-color: var(--accent); }

.btn-primary {
  background: var(--accent-dim);
  color: white;
  border: none;
  border-radius: var(--radius);
  padding: 8px 16px;
  cursor: pointer;
  font-size: 13px;
}
.btn-primary:hover { background: var(--accent); }

/* SEARCH RESULTS */
.result-item {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 10px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  margin-bottom: 8px;
  cursor: pointer;
  transition: border-color 0.15s;
}
.result-item:hover { border-color: var(--accent); }
.result-img { width: 40px; height: 56px; object-fit: cover; border-radius: 4px; background: var(--empty); }
.result-info { flex: 1; }
.result-name { font-size: 13px; font-weight: 600; }
.result-set { font-size: 11px; color: var(--text-dim); }
.result-price { font-size: 14px; color: var(--accent); font-weight: 700; }

/* DETAIL MODAL */
.modal-detail-inner { max-width: 600px; }
.detail-layout { display: flex; gap: 20px; }
.detail-img { width: 180px; flex-shrink: 0; border-radius: 8px; }
.detail-meta { flex: 1; }
.detail-pokemon { font-size: 13px; color: var(--accent); margin-bottom: 4px; }
.detail-card-name { font-size: 16px; font-weight: 700; margin-bottom: 4px; }
.detail-set { font-size: 12px; color: var(--text-dim); margin-bottom: 12px; }
.detail-price { font-size: 24px; color: var(--accent); font-weight: 700; margin-bottom: 16px; }
.detail-actions { display: flex; flex-direction: column; gap: 8px; }
.btn-secondary {
  background: transparent;
  border: 1px solid var(--border);
  color: var(--text);
  border-radius: var(--radius);
  padding: 8px 16px;
  cursor: pointer;
  font-size: 13px;
  text-align: left;
}
.btn-secondary:hover { border-color: var(--accent); color: var(--accent); }
.btn-danger { border-color: #7f1d1d; color: #f87171; }
.btn-danger:hover { border-color: #f87171; }

/* SPARKLINE */
.sparkline-wrap { margin: 12px 0; }
.sparkline-label { font-size: 11px; color: var(--text-dim); margin-bottom: 4px; }
svg.sparkline { width: 100%; height: 50px; }

/* EXPANDED CARDS */
.expanded-cards { display: flex; flex-direction: column; gap: 6px; margin-top: 8px; }
.expanded-card {
  display: flex;
  gap: 8px;
  align-items: center;
  background: var(--empty);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 6px;
  cursor: pointer;
}
.expanded-card:hover { border-color: var(--accent); }
.expanded-card img { width: 28px; height: 40px; object-fit: cover; border-radius: 3px; }
.expanded-card-info { flex: 1; font-size: 11px; }
.expanded-card-price { font-size: 12px; color: var(--accent); font-weight: 600; }

/* TYPE COLORS for placeholders */
.type-fire { background: #7f1d1d; }
.type-water { background: #1e3a5f; }
.type-grass { background: #14532d; }
.type-electric { background: #713f12; }
.type-psychic { background: #4a1942; }
.type-normal { background: #292524; }
.type-dark { background: #1c1917; }
.type-fairy { background: #4a1942; }
.type-ice { background: #164e63; }
.type-ghost { background: #2e1065; }
.type-fighting { background: #7c2d12; }
.type-default { background: #1e1e2e; }
```

- [ ] **Step 3: Commit**

```bash
git add templates/index.html static/style.css
git commit -m "feat: HTML template and dark purple CSS theme"
```

---

## Task 9: Frontend JavaScript

**Files:**
- Create: `static/app.js`

- [ ] **Step 1: Create `static/app.js`**

```javascript
// State
let allCards = [];
let allPokemon = [];
let activeTab = 'all';
let activeGen = null;
let pollInterval = null;

const TYPE_EMOJI = {
  fire: '🔥', water: '💧', grass: '🌿', electric: '⚡',
  psychic: '🔮', normal: '⬜', dark: '🌑', fairy: '🌸',
  ice: '❄️', ghost: '👻', fighting: '🥊', ground: '🌍',
  flying: '🌬️', steel: '⚙️', poison: '☠️', rock: '🪨',
  dragon: '🐉', bug: '🐛'
};

// ── Init ──────────────────────────────────────────────────────────────────
async function init() {
  await Promise.all([loadPokemon(), loadCards()]);
  loadStatus();
  renderGrid();
}

async function loadPokemon() {
  const resp = await fetch('/api/pokemon');
  allPokemon = await resp.json();
}

async function loadCards() {
  const resp = await fetch('/api/cards');
  allCards = await resp.json();
}

async function loadStatus() {
  const resp = await fetch('/api/status');
  const data = await resp.json();
  const el = document.getElementById('stat-updated');
  el.textContent = data.last_update
    ? 'Actualizado: ' + new Date(data.last_update).toLocaleString('es-ES')
    : 'Nunca actualizado';
  if (data.updating) startPolling();
}

// ── Stats ─────────────────────────────────────────────────────────────────
function updateStats() {
  document.getElementById('stat-total').textContent = allCards.length;
  const sum = (status) => allCards
    .filter(c => c.status === status && c.price_current != null)
    .reduce((acc, c) => acc + c.price_current, 0);
  document.getElementById('stat-wishlist').textContent = '€' + sum('wishlist').toFixed(2);
  document.getElementById('stat-owned').textContent = '€' + sum('owned').toFixed(2);
}

// ── Filters ───────────────────────────────────────────────────────────────
function setTab(btn, tab) {
  document.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  activeTab = tab;
  renderGrid();
}

function setGen(btn, gen) {
  document.querySelectorAll('.gen-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  activeGen = gen;
  renderGrid();
}

// ── Grid ──────────────────────────────────────────────────────────────────
function renderGrid() {
  updateStats();
  const search = document.getElementById('search-input').value.toLowerCase();
  const grid = document.getElementById('grid');
  grid.innerHTML = '';

  const filteredPokemon = allPokemon.filter(p => {
    if (activeGen !== null && p.generation !== activeGen) return false;
    if (search && !p.name.toLowerCase().includes(search)) return false;
    return true;
  });

  for (const pokemon of filteredPokemon) {
    const pokemonCards = allCards.filter(c => c.pokemon_id === pokemon.id);
    const visibleCards = pokemonCards.filter(c => {
      if (activeTab === 'wishlist') return c.status === 'wishlist';
      if (activeTab === 'owned') return c.status === 'owned';
      return true;
    });

    if (activeTab !== 'all' && visibleCards.length === 0) continue;

    const slot = document.createElement('div');
    slot.className = 'pokemon-slot';

    const label = document.createElement('div');
    label.className = 'slot-label';
    label.textContent = pokemon.name;
    slot.appendChild(label);

    if (visibleCards.length === 0) {
      slot.appendChild(buildEmptySlot(pokemon));
    } else if (visibleCards.length === 1) {
      slot.appendChild(buildCardTile(visibleCards[0], pokemon));
    } else {
      slot.appendChild(buildStackedSlot(visibleCards, pokemon));
    }

    grid.appendChild(slot);
  }
}

function buildEmptySlot(pokemon) {
  const el = document.createElement('div');
  el.className = 'card-empty';
  el.innerHTML = '<div class="plus">+</div>';
  el.onclick = () => openAddModal(pokemon.name);
  return el;
}

function buildCardTile(card, pokemon) {
  const el = document.createElement('div');
  el.className = `card-tile ${card.status === 'owned' ? 'owned' : ''}`;
  const stale = card.price_current == null;
  el.innerHTML = `
    <div class="card-img-wrap">
      ${card.image_url
        ? `<img src="${card.image_url}" alt="${card.card_name}" loading="lazy">`
        : `<div class="card-placeholder ${typeClass(pokemon.type_1)}">${typeEmoji(pokemon.type_1)}</div>`}
    </div>
    <div class="badge ${card.status === 'owned' ? 'badge-owned' : 'badge-wishlist'}">
      ${card.status === 'owned' ? '✅' : '💜'}
    </div>
    <div class="card-info">
      <div class="card-name">${card.card_name}</div>
      <div class="card-price ${stale ? 'stale' : ''}">
        ${card.price_current != null ? '€' + card.price_current.toFixed(2) : '–'}
        ${stale ? '<span class="badge badge-stale">⚠</span>' : ''}
      </div>
    </div>`;
  el.onclick = () => openDetailModal(card);
  return el;
}

function buildStackedSlot(cards, pokemon) {
  const wrapper = document.createElement('div');
  wrapper.className = 'card-stack';

  const top = buildCardTile(cards[0], pokemon);
  wrapper.appendChild(top);

  let expanded = false;
  const expandedDiv = document.createElement('div');
  expandedDiv.className = 'expanded-cards';
  expandedDiv.style.display = 'none';
  cards.forEach(card => {
    const item = document.createElement('div');
    item.className = 'expanded-card';
    item.innerHTML = `
      ${card.image_url ? `<img src="${card.image_url}" loading="lazy">` : `<div class="card-placeholder ${typeClass(pokemon.type_1)}" style="width:28px;height:40px;font-size:16px">${typeEmoji(pokemon.type_1)}</div>`}
      <div class="expanded-card-info">
        <div>${card.card_name}</div>
        <div style="color:var(--text-dim);font-size:10px">${card.set_name}</div>
      </div>
      <div class="expanded-card-price">${card.price_current != null ? '€' + card.price_current.toFixed(2) : '–'}</div>`;
    item.onclick = (e) => { e.stopPropagation(); openDetailModal(card); };
    expandedDiv.appendChild(item);
  });
  wrapper.appendChild(expandedDiv);

  top.onclick = (e) => {
    e.stopPropagation();
    expanded = !expanded;
    expandedDiv.style.display = expanded ? 'flex' : 'none';
    expandedDiv.style.flexDirection = 'column';
  };

  return wrapper;
}

function typeClass(type) {
  const t = (type || '').toLowerCase();
  return ['fire','water','grass','electric','psychic','normal','dark',
          'fairy','ice','ghost','fighting'].includes(t) ? `type-${t}` : 'type-default';
}

function typeEmoji(type) {
  return TYPE_EMOJI[(type || '').toLowerCase()] || '❓';
}

// ── Add Card Modal ─────────────────────────────────────────────────────────
function openAddModal(pokemonName = '') {
  document.getElementById('add-search-input').value = pokemonName;
  document.getElementById('search-results').innerHTML = '';
  document.getElementById('modal-add').style.display = 'flex';
}

function closeAddModal(e) {
  if (e.target.id === 'modal-add') document.getElementById('modal-add').style.display = 'none';
}

async function searchCards() {
  const name = document.getElementById('add-search-input').value.trim();
  if (!name) return;
  const resultsEl = document.getElementById('search-results');
  resultsEl.innerHTML = '<div style="color:var(--text-dim);text-align:center;padding:20px">Buscando...</div>';

  const resp = await fetch('/api/search', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({pokemon_name: name})
  });
  const results = await resp.json();
  resultsEl.innerHTML = '';

  if (!results.length) {
    resultsEl.innerHTML = '<div style="color:var(--text-dim);text-align:center;padding:20px">No se encontraron cartas.</div>';
    return;
  }

  const pokemon = allPokemon.find(p => p.name.toLowerCase() === name.toLowerCase());

  for (const r of results) {
    const item = document.createElement('div');
    item.className = 'result-item';
    item.innerHTML = `
      ${r.image_url ? `<img class="result-img" src="${r.image_url}" loading="lazy">` : `<div class="result-img ${typeClass(pokemon?.type_1)}" style="display:flex;align-items:center;justify-content:center;font-size:20px">${typeEmoji(pokemon?.type_1)}</div>`}
      <div class="result-info">
        <div class="result-name">${r.card_name}</div>
        <div class="result-set">${r.set_name} · ${r.rarity}</div>
      </div>
      <div class="result-price">€${r.price.toFixed(2)}</div>`;
    item.onclick = () => addCard(r, pokemon);
    resultsEl.appendChild(item);
  }
}

async function addCard(result, pokemon) {
  if (!pokemon) {
    alert('No se encontró el Pokemon en la lista. Verifica el nombre.');
    return;
  }
  await fetch('/api/cards', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      pokemon_id: pokemon.id,
      card_name: result.card_name,
      set_name: result.set_name,
      rarity: result.rarity,
      price: result.price,
      image_url: result.image_url,
      cardmarket_url: result.cardmarket_url
    })
  });
  document.getElementById('modal-add').style.display = 'none';
  await loadCards();
  renderGrid();
}

// ── Detail Modal ───────────────────────────────────────────────────────────
async function openDetailModal(card) {
  const histResp = await fetch(`/api/cards/${card.id}/history`);
  const history = await histResp.json();
  const pokemon = allPokemon.find(p => p.id === card.pokemon_id);
  const stale = card.price_current == null;

  document.getElementById('detail-content').innerHTML = `
    <div class="detail-layout">
      <div>
        ${card.image_url
          ? `<img class="detail-img" src="${card.image_url}" alt="${card.card_name}">`
          : `<div class="detail-img ${typeClass(pokemon?.type_1)}" style="aspect-ratio:2.5/3.5;display:flex;align-items:center;justify-content:center;font-size:60px;border-radius:8px">${typeEmoji(pokemon?.type_1)}</div>`}
      </div>
      <div class="detail-meta">
        <div class="detail-pokemon">${card.pokemon_name}</div>
        <div class="detail-card-name">${card.card_name}</div>
        <div class="detail-set">${card.set_name} · ${card.rarity}</div>
        <div class="detail-price ${stale ? 'stale' : ''}">
          ${card.price_current != null ? '€' + card.price_current.toFixed(2) : '–'}
          ${stale ? ' <span class="badge badge-stale">⚠ precio no actualizado</span>' : ''}
        </div>
        ${buildSparkline(history)}
        <div class="detail-actions">
          <button class="btn-secondary" onclick="toggleStatus(${card.id}, '${card.status}')">
            ${card.status === 'wishlist' ? '✅ Mover a Colección' : '💜 Mover a Wishlist'}
          </button>
          <a href="${card.cardmarket_url}" target="_blank" style="text-decoration:none">
            <button class="btn-secondary" style="width:100%">🔗 Ver en CardMarket</button>
          </a>
          <button class="btn-secondary btn-danger" onclick="deleteCard(${card.id})">🗑 Eliminar</button>
        </div>
      </div>
    </div>`;
  document.getElementById('modal-detail').style.display = 'flex';
}

function closeDetailModal(e) {
  if (e.target.id === 'modal-detail') document.getElementById('modal-detail').style.display = 'none';
}

function buildSparkline(history) {
  if (!history.length) return '';
  const prices = history.map(h => h.price);
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const range = max - min || 1;
  const w = 200, h = 50, pad = 4;
  const points = prices.map((p, i) => {
    const x = pad + (i / Math.max(prices.length - 1, 1)) * (w - pad * 2);
    const y = h - pad - ((p - min) / range) * (h - pad * 2);
    return `${x},${y}`;
  }).join(' ');
  return `
    <div class="sparkline-wrap">
      <div class="sparkline-label">Historial de precio (${history.length} puntos)</div>
      <svg class="sparkline" viewBox="0 0 ${w} ${h}">
        <polyline points="${points}" fill="none" stroke="#7c3aed" stroke-width="1.5"/>
        <circle cx="${points.split(' ').at(-1).split(',')[0]}" cy="${points.split(' ').at(-1).split(',')[1]}" r="3" fill="#c084fc"/>
      </svg>
    </div>`;
}

async function toggleStatus(cardId, currentStatus) {
  const newStatus = currentStatus === 'wishlist' ? 'owned' : 'wishlist';
  await fetch(`/api/cards/${cardId}`, {
    method: 'PATCH',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({status: newStatus})
  });
  document.getElementById('modal-detail').style.display = 'none';
  await loadCards();
  renderGrid();
}

async function deleteCard(cardId) {
  if (!confirm('¿Eliminar esta carta?')) return;
  await fetch(`/api/cards/${cardId}`, {method: 'DELETE'});
  document.getElementById('modal-detail').style.display = 'none';
  await loadCards();
  renderGrid();
}

// ── Price Refresh ──────────────────────────────────────────────────────────
async function triggerRefresh() {
  const btn = document.getElementById('btn-refresh');
  btn.classList.add('spinning');
  await fetch('/api/refresh', {method: 'POST'});
  startPolling();
}

function startPolling() {
  if (pollInterval) return;
  pollInterval = setInterval(async () => {
    const resp = await fetch('/api/status');
    const data = await resp.json();
    const el = document.getElementById('stat-updated');
    if (!data.updating) {
      clearInterval(pollInterval);
      pollInterval = null;
      document.getElementById('btn-refresh').classList.remove('spinning');
      el.textContent = data.last_update
        ? 'Actualizado: ' + new Date(data.last_update).toLocaleString('es-ES')
        : '–';
      await loadCards();
      renderGrid();
    }
  }, 5000);
}

// ── Boot ──────────────────────────────────────────────────────────────────
init();
```

- [ ] **Step 2: Commit**

```bash
git add static/app.js
git commit -m "feat: frontend JavaScript (grid, modals, filters, price refresh)"
```

---

## Task 10: Launch Script

**Files:**
- Create: `run.sh`

- [ ] **Step 1: Create `run.sh`**

```bash
#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Activate venv
source venv/bin/activate

# Find free port
PORT=5000
for p in $(seq 5000 5010); do
  if ! nc -z localhost $p 2>/dev/null; then
    PORT=$p
    break
  fi
done

if [ $PORT -gt 5010 ]; then
  echo "Error: No free port found (5000-5010)"
  exit 1
fi

echo "Starting Pokédex Tracker on port $PORT..."

# Start Flask
FLASK_PORT=$PORT python app.py &
FLASK_PID=$!

# Wait for Flask to be ready (max 5s)
for i in $(seq 1 10); do
  sleep 0.5
  if nc -z localhost $PORT 2>/dev/null; then
    break
  fi
done

if ! nc -z localhost $PORT 2>/dev/null; then
  echo "Error: Flask failed to start on port $PORT"
  kill $FLASK_PID 2>/dev/null
  exit 1
fi

echo "App running at http://localhost:$PORT"
open "http://localhost:$PORT"

# Keep running
wait $FLASK_PID
```

- [ ] **Step 2: Make executable**

```bash
chmod +x run.sh
```

- [ ] **Step 3: Create `run.command` for double-click launch**

```bash
#!/bin/bash
cd "$(dirname "$0")"
./run.sh
```

```bash
chmod +x run.command
```

- [ ] **Step 4: Commit**

```bash
git add run.sh run.command
git commit -m "feat: launch script with port auto-detection and browser open"
```

---

## Task 11: End-to-End Smoke Test

**Goal:** Verify the full app launches and the UI renders correctly.

- [ ] **Step 1: Run full test suite one final time**

```bash
cd "/Users/mario-persomal/Desktop/ANTIGRAVITY/Pokemon Tracker"
source venv/bin/activate
pytest -v
```
Expected: all tests PASS, no failures.

- [ ] **Step 2: Start the app manually**

```bash
./run.sh
```
Expected: browser opens at `http://localhost:5000`, grid shows 88 Pokemon slots.

- [ ] **Step 3: Test add card flow**

1. Click an empty slot (e.g. Charizard)
2. Click "Buscar" — should call `/api/search` and show results
3. Click a result — card should appear in the grid with image and price
4. Click the card — detail modal should open with sparkline

- [ ] **Step 4: Test status toggle**

1. In detail modal, click "Mover a Colección"
2. Card badge should change from 💜 to ✅
3. Wishlist total in header should decrease, Collection total should increase

- [ ] **Step 5: Final commit**

```bash
git add .
git commit -m "chore: complete Pokemon Tracker implementation"
```
