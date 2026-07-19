from pydantic import BaseModel, Field, field_validator


class TranscriptSegment(BaseModel):
    id: int = Field(ge=0)
    start: float = Field(ge=0)
    end: float = Field(ge=0)
    text: str = Field(min_length=1)

    @field_validator("text")
    @classmethod
    def clean_text(cls, value: str) -> str:
        return " ".join(value.split())


class TranscriptResponse(BaseModel):
    text: str = Field(min_length=1)
    segments: list[TranscriptSegment]
    language: str = "en"
    duration_seconds: float = Field(default=0, ge=0)
    model: str


class NoteRequest(BaseModel):
    transcript: str = Field(min_length=20, max_length=100_000)

    @field_validator("transcript")
    @classmethod
    def transcript_is_not_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Transcript cannot be blank")
        return cleaned


class SOAPNote(BaseModel):
    subjective: str = Field(
        description="Patient-reported symptoms, history, and concerns from the transcript"
    )
    objective: str = Field(
        description="Observed or measured findings explicitly stated in the transcript"
    )
    assessment: str = Field(
        description="Clinician assessment explicitly stated in the transcript"
    )
    plan: str = Field(
        description="Tests, medications, instructions, and follow-up explicitly stated in the transcript"
    )
    review_flags: list[str] = Field(
        default_factory=list,
        description="Uncertain or conflicting details that require clinician review",
    )


class NoteResponse(BaseModel):
    note: SOAPNote
    model: str
    status: str = "draft"


class ProcessResponse(BaseModel):
    transcript: TranscriptResponse
    note: NoteResponse


class DependencyState(BaseModel):
    ready: bool
    detail: str


class HealthResponse(BaseModel):
    status: str
    whisper: DependencyState
    medgemma: DependencyState
