import json
import os
import tempfile
import pytest
from app import create_app
from database import init_db, add_card, update_card_status, save_price_snapshot


@pytest.fixture
def app():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.environ["POKEMON_DB_PATH"] = path
    application = create_app(testing=True)
    with application.app_context():
        init_db()
    yield application
    os.close(fd)
    os.unlink(path)


@pytest.fixture
def client(app):
    return app.test_client()


def _add_owned(app, **kw):
    with app.app_context():
        cid = add_card(
            pokemon_id=kw.get("pokemon_id", 1),
            card_name=kw.get("card_name", "Charizard ex"),
            set_name=kw.get("set_name", "Obsidian Flames"),
            rarity=kw.get("rarity", "SIR"),
            image_url=None,
            price=kw.get("price", 10.0),
            cardmarket_url="https://www.cardmarket.com/test",
        )
        update_card_status(cid, "owned")
    return cid


def test_stats_endpoint_shape(client):
    resp = client.get("/api/stats")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert set(data) == {"totals", "value_over_time", "by_generation",
                         "by_rarity", "top_movers"}
    assert set(data["totals"]) == {"owned_count", "wishlist_count",
                                   "owned_value", "wishlist_value"}


def test_stats_totals(app, client):
    _add_owned(app, price=10.0)
    _add_owned(app, price=5.0)
    with app.app_context():
        add_card(pokemon_id=1, card_name="W", set_name="S", rarity="Rare",
                 image_url=None, price=3.0,
                 cardmarket_url="https://www.cardmarket.com/test")
    data = json.loads(client.get("/api/stats").data)
    assert data["totals"]["owned_count"] == 2
    assert data["totals"]["owned_value"] == 15.0
    assert data["totals"]["wishlist_count"] == 1
    assert data["totals"]["wishlist_value"] == 3.0


def test_stats_top_movers(app, client):
    cid = _add_owned(app, price=10.0)
    with app.app_context():
        save_price_snapshot(cid, 20.0)
    data = json.loads(client.get("/api/stats").data)
    movers = data["top_movers"]
    assert len(movers) == 1
    assert movers[0]["change_pct"] == 100.0


def test_stats_by_generation_and_rarity(app, client):
    _add_owned(app, price=10.0, rarity="SIR")
    data = json.loads(client.get("/api/stats").data)
    assert data["by_generation"][0]["generation"] == 1
    assert data["by_rarity"][0]["rarity"] == "SIR"
    assert data["by_rarity"][0]["count"] == 1


def test_export_xlsx(app, client):
    _add_owned(app, price=10.0)
    resp = client.get("/api/export/xlsx")
    assert resp.status_code == 200
    assert "spreadsheetml" in resp.headers["Content-Type"]
    # XLSX is a zip archive: starts with PK
    assert resp.data[:2] == b"PK"


def test_export_pdf(app, client):
    _add_owned(app, price=10.0)
    resp = client.get("/api/export/pdf")
    assert resp.status_code == 200
    assert resp.headers["Content-Type"] == "application/pdf"
    assert resp.data[:4] == b"%PDF"


def _add(app, **kw):
    with app.app_context():
        return add_card(
            pokemon_id=kw.get("pokemon_id", 1),
            card_name=kw.get("card_name", "Card"),
            set_name="Set", rarity="Rare", image_url=None,
            price=kw.get("price", 5.0),
            cardmarket_url="https://www.cardmarket.com/test",
        )


def test_album_empty_by_default(client):
    resp = client.get("/api/album")
    assert resp.status_code == 200
    assert json.loads(resp.data) == []


def test_album_set_and_get_order(app, client):
    a = _add(app, card_name="A")
    b = _add(app, card_name="B")
    c = _add(app, card_name="C")
    resp = client.put("/api/album", json={"order": [c, a, b]})
    assert resp.status_code == 200
    order = [card["id"] for card in json.loads(resp.data)]
    assert order == [c, a, b]
    # persistido y reflejado en /api/album
    again = [card["id"] for card in json.loads(client.get("/api/album").data)]
    assert again == [c, a, b]


def test_album_reorder_drops_missing(app, client):
    a = _add(app, card_name="A")
    b = _add(app, card_name="B")
    client.put("/api/album", json={"order": [a, b]})
    # Guardar solo b: a sale del álbum
    resp = client.put("/api/album", json={"order": [b]})
    order = [card["id"] for card in json.loads(resp.data)]
    assert order == [b]


def test_album_rejects_bad_payload(client):
    assert client.put("/api/album", json={"order": "nope"}).status_code == 400
    assert client.put("/api/album", json={"order": ["x"]}).status_code == 400
