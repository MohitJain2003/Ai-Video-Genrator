"""
Unit tests for the list voices API endpoint.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.routes import router
from fastapi import FastAPI


@pytest.fixture(name="client")
def client_fixture():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_list_voices_mock(client: TestClient):
    """Test retrieving voices when ElevenLabs fails or falls back to mock provider."""
    # List voices for elevenlabs provider
    response = client.get("/api/v1/voices?provider=elevenlabs")
    assert response.status_code == 200
    data = response.json()
    assert "voices" in data
    assert len(data["voices"]) > 0
    # The default fallback contains Liam
    first_voice = data["voices"][0]
    assert "id" in first_voice
    assert "name" in first_voice
    assert "gender" in first_voice

    # List voices for cartesia (should return default cartesia voice info)
    response = client.get("/api/v1/voices?provider=cartesia")
    assert response.status_code == 200
    data = response.json()
    assert "voices" in data
    assert len(data["voices"]) > 0

    # List voices for openai (should return alloy, echo, onyx etc)
    response = client.get("/api/v1/voices?provider=openai")
    assert response.status_code == 200
    data = response.json()
    assert "voices" in data
    assert len(data["voices"]) > 0
    voices_list = [v["name"].lower() for v in data["voices"]]
    assert "alloy" in voices_list or "onyx" in voices_list or "mock male" in voices_list
