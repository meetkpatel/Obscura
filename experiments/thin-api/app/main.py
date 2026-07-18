import tempfile
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings, get_settings
from app.schemas import HealthResponse, NoteRequest, NoteResponse, ProcessResponse, TranscriptResponse
from app.services.notes import NoteGenerationService, NoteGenerationUnavailableError
from app.services.transcription import TranscriptionService, TranscriptionUnavailableError

ALLOWED_AUDIO_SUFFIXES = {".wav", ".mp3", ".m4a", ".mp4", ".webm", ".ogg", ".flac"}


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield


settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Fully local transcription and MedGemma SOAP drafting",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


def get_transcription_service(
    config: Settings = Depends(get_settings),
) -> TranscriptionService:
    return TranscriptionService(config)


def get_note_service(config: Settings = Depends(get_settings)) -> NoteGenerationService:
    return NoteGenerationService(config)


async def save_upload(file: UploadFile, config: Settings) -> Path:
    suffix = Path(file.filename or "recording.webm").suffix.lower()
    if suffix not in ALLOWED_AUDIO_SUFFIXES:
        supported = ", ".join(sorted(ALLOWED_AUDIO_SUFFIXES))
        raise HTTPException(
            status_code=415,
            detail=f"This audio type is not supported. Use one of: {supported}.",
        )

    max_bytes = config.max_audio_mb * 1024 * 1024
    data = await file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Recording is larger than the {config.max_audio_mb} MB demo limit.",
        )
    if not data:
        raise HTTPException(status_code=400, detail="The recording is empty.")

    temporary = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    temporary.write(data)
    temporary.close()
    return Path(temporary.name)


@app.get("/api/health", response_model=HealthResponse)
async def health(
    transcription: TranscriptionService = Depends(get_transcription_service),
    notes: NoteGenerationService = Depends(get_note_service),
) -> HealthResponse:
    whisper_ready, whisper_detail = transcription.dependency_state()
    medgemma_ready, medgemma_detail = await notes.dependency_state()
    ready = whisper_ready and medgemma_ready
    return HealthResponse(
        status="ready" if ready else "setup_required",
        whisper={"ready": whisper_ready, "detail": whisper_detail},
        medgemma={"ready": medgemma_ready, "detail": medgemma_detail},
    )


@app.post("/api/transcriptions", response_model=TranscriptResponse)
async def create_transcription(
    file: UploadFile = File(...),
    config: Settings = Depends(get_settings),
    service: TranscriptionService = Depends(get_transcription_service),
) -> TranscriptResponse:
    audio_path = await save_upload(file, config)
    try:
        return await service.transcribe(audio_path)
    except TranscriptionUnavailableError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    finally:
        audio_path.unlink(missing_ok=True)


@app.post("/api/notes", response_model=NoteResponse)
async def create_note(
    request: NoteRequest,
    service: NoteGenerationService = Depends(get_note_service),
) -> NoteResponse:
    try:
        return await service.generate(request.transcript)
    except NoteGenerationUnavailableError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@app.post("/api/process", response_model=ProcessResponse)
async def process_encounter(
    file: UploadFile = File(...),
    config: Settings = Depends(get_settings),
    transcription_service: TranscriptionService = Depends(get_transcription_service),
    note_service: NoteGenerationService = Depends(get_note_service),
) -> ProcessResponse:
    audio_path = await save_upload(file, config)
    try:
        transcript = await transcription_service.transcribe(audio_path)
        note = await note_service.generate(transcript.text)
        return ProcessResponse(transcript=transcript, note=note)
    except (TranscriptionUnavailableError, NoteGenerationUnavailableError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    finally:
        audio_path.unlink(missing_ok=True)
