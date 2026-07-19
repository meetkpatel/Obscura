import asyncio
from pathlib import Path
from typing import Any

from app.config import Settings
from app.schemas import TranscriptResponse, TranscriptSegment


class TranscriptionUnavailableError(RuntimeError):
    """Raised when the local transcription runtime cannot be used."""


class TranscriptionService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def transcribe(self, audio_path: Path) -> TranscriptResponse:
        return await asyncio.to_thread(self._transcribe_sync, audio_path)

    def _transcribe_sync(self, audio_path: Path) -> TranscriptResponse:
        try:
            import mlx_whisper
        except ImportError as error:
            raise TranscriptionUnavailableError(
                "MLX Whisper is not installed. Run `uv sync --dev` before transcribing."
            ) from error

        try:
            result: dict[str, Any] = mlx_whisper.transcribe(
                str(audio_path),
                path_or_hf_repo=self.settings.whisper_model,
                language="en",
                initial_prompt=(
                    "A clinician and patient are discussing symptoms, medical history, "
                    "medications, dosages, examination findings, and follow-up instructions."
                ),
                word_timestamps=False,
            )
        except Exception as error:
            raise TranscriptionUnavailableError(
                f"Local transcription failed: {error}"
            ) from error

        raw_segments = result.get("segments") or []
        segments = [
            TranscriptSegment(
                id=index,
                start=max(0.0, float(segment.get("start", 0))),
                end=max(0.0, float(segment.get("end", 0))),
                text=str(segment.get("text", "")).strip(),
            )
            for index, segment in enumerate(raw_segments)
            if str(segment.get("text", "")).strip()
        ]

        text = str(result.get("text", "")).strip()
        if not text and segments:
            text = " ".join(segment.text for segment in segments)
        if not text:
            raise TranscriptionUnavailableError(
                "No speech was detected. Try a clearer recording with the microphone closer."
            )

        duration = max((segment.end for segment in segments), default=0.0)
        return TranscriptResponse(
            text=text,
            segments=segments,
            language=str(result.get("language") or "en"),
            duration_seconds=duration,
            model=self.settings.whisper_model,
        )

    @staticmethod
    def dependency_state() -> tuple[bool, str]:
        try:
            import mlx_whisper  # noqa: F401
        except ImportError:
            return False, "MLX Whisper is not installed"
        return True, "MLX Whisper is installed; the model downloads on first use"
