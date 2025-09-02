import json
from fastapi.testclient import TestClient
import main

client = TestClient(main.app)

def test_health():
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json().get("ok") is True

def test_chat_missing_key():
    # Should fail cleanly if no API key and default base is OpenAI
    r = client.post("/chat", json={"message":"hello"})
    assert r.status_code in (400, 500)
