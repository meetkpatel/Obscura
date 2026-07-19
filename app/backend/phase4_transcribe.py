"""Phase 4 — TRANSCRIBE (on-device clinical scribe).

Turn a dictation (or an audio note) into a structured clinical note, on-device,
then hand it straight to REDACT. Gemma 4 does the structuring; nothing leaves the
machine — the same guarantee as every other surface.

  dictation text / audio  ->  Gemma structures a SOAP note + pulls entities
                          ->  flags PHI  ->  one click to Redact

Audio: Gemma 4 is natively audio-capable. Ollama's exposure of that varies, so
audio is attempted and falls back to a clear message; the text/dictation path is
always available and is the reliable demo path.
"""
from __future__ import annotations

import base64
import io

import gemma

AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".wma", ".webm"}

SCRIBE_PROMPT = (
    "You are an on-device medical scribe. Turn the clinician's dictation below "
    "into a clean, structured clinical note. Return ONLY JSON:\n"
    '{"patient":"name or empty","date":"YYYY-MM-DD or empty",'
    '"soap":{"subjective":"...","objective":"...","assessment":"...","plan":"..."},'
    '"summary":"one-line summary",'
    '"phi_found":["each patient identifier you see: names, dates, MRNs, phone, '
    'address, etc."]}\n'
    "Keep the clinical content faithful to the dictation — do not invent findings. "
    "If a SOAP section has nothing, use an empty string.\n\nDICTATION:\n"
)


def _structure(text: str, model: str) -> dict:
    try:
        data = gemma.generate_json(SCRIBE_PROMPT + text[:6000], model=model,
                                   num_predict=900, timeout=240)
        if isinstance(data, dict):
            data.setdefault("soap", {})
            data.setdefault("phi_found", [])
            return data
    except gemma.GemmaError as e:
        return {"error": str(e)}
    return {"error": "could not structure the note"}


def transcribe_text(text: str, model: str) -> dict:
    """Structure a typed/pasted dictation into a clinical note. Always available."""
    if not text or not text.strip():
        return {"error": "no dictation text provided"}
    note = _structure(text, model)
    note["transcript"] = text.strip()
    note["source"] = "text"
    return note


def transcribe_audio(audio_bytes: bytes, filename: str, model: str) -> dict:
    """Attempt on-device audio transcription with Gemma 4's native audio, then
    structure it. Falls back to a clear message if the runtime can't take audio."""
    # 1) try to get a transcript from the audio via the model
    transcript = ""
    try:
        b64 = base64.b64encode(audio_bytes).decode()
        # Gemma 4 audio via Ollama: audio is passed like images on some builds.
        raw = gemma.generate(
            "Transcribe this audio recording to plain text verbatim. Output only "
            "the transcript.", model=model, images=[audio_bytes], num_predict=800,
            timeout=240)
        transcript = (raw or "").strip()
    except Exception:
        transcript = ""
    if len(transcript) < 8:
        return {"error": "audio transcription isn't available in this runtime yet. "
                         "Paste the dictation as text — the scribe works the same way.",
                "source": "audio", "transcript": ""}
    note = _structure(transcript, model)
    note["transcript"] = transcript
    note["source"] = "audio"
    return note
