# Gemma Clinical Scribe — MVP Plan

## Product goal

Prove one dependable workflow on the demo Mac:

1. Record or upload a synthetic clinician–patient conversation.
2. Transcribe it with hosted Whisper.
3. Generate a structured SOAP draft with hosted Gemma.
4. Let a clinician review and edit the draft.

The product is a documentation assistant, not a diagnostic system. Generated notes are always visibly marked as drafts.

## Implementation decision

Keep the proven recording and review workflow, with three focused contributions:

- Add MedGemma 4B Q4 as a first-class local GGUF model for the offline upgrade.
- Replace the SOAP prompts with strict transcript-grounding rules.
- Focus the visible demo on recording, transcript review, and an editable draft.

For the first presentation build, use OpenRouter-hosted Gemma and Groq-hosted
Whisper. This removes native desktop packaging and model downloads from the
critical path while preserving the local model integration as a stretch goal.

The original thin FastAPI experiment is preserved under `experiments/thin-api/` only as a fallback.

## Build order

1. Configure OpenRouter Gemma and Groq Whisper through the existing provider APIs.
2. Generate grounded SOAP fields from the prepared transcript.
3. Transcribe the prepared synthetic recording through Groq.
4. Rehearse the focused browser workflow three times.

## MVP boundaries

Not included: diarization, PHI redaction, patient storage, EHR/FHIR integration, billing codes, diagnosis suggestions, fine-tuning, or HIPAA-compliance claims.

Only synthetic or acted conversations are used in development and demonstration.

## Acceptance checks

- The app completes the prepared encounter without local model downloads.
- Medications, symptoms, negatives, and plans in the note are supported by the transcript.
- The note adds no diagnosis, medication, or instruction absent from the conversation.
- Missing API keys produce a clear setup message instead of a broken screen.
- The prepared demo works three consecutive times.
