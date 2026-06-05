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

def test_get_plan_returns_twelve_months(client):
    resp = client.get("/api/plan?year=2026")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert len(data) == 12

def test_post_plan_saves_month(client):
    resp = client.post("/api/plan", json={
        "year": 2026, "month": 6, "budget": 75.0,
        "spent": 28.0, "plan_note": "ETB inglés"})
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data[5]["budget"] == 75.0
    assert data[5]["spent"] == 28.0
    assert data[5]["plan_note"] == "ETB inglés"

def test_post_plan_rejects_bad_month(client):
    resp = client.post("/api/plan", json={"year": 2026, "month": 13})
    assert resp.status_code == 400

def test_post_plan_rejects_negative_budget(client):
    resp = client.post("/api/plan", json={
        "year": 2026, "month": 1, "budget": -5})
    assert resp.status_code == 400
