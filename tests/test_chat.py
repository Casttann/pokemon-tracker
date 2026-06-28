import json
from unittest.mock import patch


def test_chat_rejects_missing_history(client):
    resp = client.post("/api/chat", json={})
    assert resp.status_code == 400


def test_chat_rejects_bad_message_shape(client):
    resp = client.post("/api/chat", json={"history": [{"role": "system", "content": "x"}]})
    assert resp.status_code == 400
    resp = client.post("/api/chat", json={"history": [{"role": "user"}]})
    assert resp.status_code == 400


def test_chat_success(client):
    with patch("ai_assistant.chat", return_value=("Hola!", ["add_card"])):
        resp = client.post("/api/chat", json={"history": [{"role": "user", "content": "hola"}]})
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data == {"reply": "Hola!", "mutated": ["add_card"]}


def test_chat_surfaces_assistant_error(client):
    from ai_assistant import AssistantError
    with patch("ai_assistant.chat", side_effect=AssistantError("no api key")):
        resp = client.post("/api/chat", json={"history": [{"role": "user", "content": "hola"}]})
    assert resp.status_code == 500


def test_chat_surfaces_upstream_error(client):
    with patch("ai_assistant.chat", side_effect=RuntimeError("boom")):
        resp = client.post("/api/chat", json={"history": [{"role": "user", "content": "hola"}]})
    assert resp.status_code == 502
