from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.api.transcribe import router

app = FastAPI()
app.include_router(router, prefix="/api/transcribe")
client = TestClient(app)


def test_audio_configuration_error_is_actionable():
    message = "Groq API key is missing. Open Settings, paste the key, and save."

    with patch(
        "server.api.transcribe.transcribe_audio",
        new=AsyncMock(side_effect=ValueError(message)),
    ):
        response = client.post(
            "/api/transcribe/audio",
            files={"file": ("recording.webm", b"audio", "audio/webm")},
        )

    assert response.status_code == 400
    assert response.json() == {"detail": message}


def test_dictation_configuration_error_is_actionable():
    message = "Groq API key is missing. Open Settings, paste the key, and save."

    with patch(
        "server.api.transcribe.transcribe_audio",
        new=AsyncMock(side_effect=ValueError(message)),
    ):
        response = client.post(
            "/api/transcribe/dictate",
            files={"file": ("recording.webm", b"audio", "audio/webm")},
        )

    assert response.status_code == 400
    assert response.json() == {"detail": message}
