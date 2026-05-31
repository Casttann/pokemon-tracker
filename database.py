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
    card = db.session.get(Card, card_id)
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
    card = db.session.get(Card, card_id)
    if card:
        card.status = new_status
        db.session.commit()


def delete_card(card_id):
    card = db.session.get(Card, card_id)
    if card:
        db.session.delete(card)
        db.session.commit()


def save_price_snapshot(card_id, price):
    now = datetime.now(timezone.utc).isoformat()
    card = db.session.get(Card, card_id)
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
