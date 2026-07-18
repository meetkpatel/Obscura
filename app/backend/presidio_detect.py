"""Presidio — the deterministic PII Scan layer for REDACT.

This is the "Scan (deterministic)" half of Obscura's spine. It replaces the
job that a large hand-rolled regex table + a Gemma NER pass used to do, with
Microsoft Presidio's battle-tested analyzer:

  * dozens of validated recognizers (SSN, credit card w/ Luhn, IBAN, passport,
    driver's license, crypto, medical license, IP, email, phone, ...),
  * spaCy NER for PERSON / LOCATION / ORGANIZATION named entities,
  * context-aware confidence boosting ("SSN:" nearby raises the score).

It returns HIT DICTS in the exact shape phase1's `ground_text_boxes()` already
consumes — `{category, label, text, reason}` — so the OCR word-box grounding,
burn/flatten/scrub, and verify battery downstream are untouched. Presidio finds
the string; Tesseract still fixes the pixels.

Fully on-device: Presidio + the spaCy model are pip/`spacy download` installs
that live on the USB stick next to Ollama. No network path is opened here — the
"Wi-Fi off, egress = 0" guarantee holds.

Optional dependency: if presidio-analyzer / the spaCy model isn't installed,
`available()` returns False and phase1 falls back to its regex + Gemma passes.
"""
from __future__ import annotations

import threading

from contracts import coerce_category

# Presidio's spaCy model. ~590MB, CPU-only, no VRAM contention with Gemma.
SPACY_MODEL = "en_core_web_lg"

# Drop low-confidence detections. Presidio's spaCy PERSON scores ~0.85; regex
# recognizers score 1.0; context boosting adds up to +0.35. 0.40 keeps recall
# high (this is a recall-biased tool) while trimming NER noise.
SCORE_THRESHOLD = 0.40

# Presidio entity_type -> Obscura Category. Anything unlisted is coerced later.
ENTITY_CATEGORY = {
    "PERSON": "person",
    "LOCATION": "address",
    "NRP": "person",                 # nationality / religious / political group
    "ORGANIZATION": "organization",
    "PHONE_NUMBER": "contact",
    "EMAIL_ADDRESS": "contact",
    "URL": "other",
    "CREDIT_CARD": "financial",
    "US_BANK_NUMBER": "financial",
    "IBAN_CODE": "financial",
    "CRYPTO": "financial",
    "US_SSN": "gov_id",
    "US_ITIN": "gov_id",
    "US_DRIVER_LICENSE": "gov_id",
    "US_PASSPORT": "gov_id",
    "MEDICAL_LICENSE": "medical",
    "IP_ADDRESS": "other",
    "DATE_TIME": "date",
}

_LOCK = threading.Lock()
_ANALYZER = None          # lazy singleton (loading spaCy takes ~1-2s)
_INIT_FAILED = False      # remember an import/load failure; don't retry every page


def _build_analyzer():
    """Construct an AnalyzerEngine whose spaCy NER also emits ORGANIZATION
    (records/FOIA docs are full of firm and employer names). Falls back to the
    default engine if this Presidio version doesn't accept the config."""
    from presidio_analyzer import AnalyzerEngine
    from presidio_analyzer.nlp_engine import NlpEngineProvider

    ner_conf = {
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "en", "model_name": SPACY_MODEL}],
        "ner_model_configuration": {
            "model_to_presidio_entity_mapping": {
                "PERSON": "PERSON",
                "GPE": "LOCATION",
                "LOC": "LOCATION",
                "FAC": "LOCATION",
                "ORG": "ORGANIZATION",
                "NORP": "NRP",
                "DATE": "DATE_TIME",
            },
        },
    }
    try:
        nlp_engine = NlpEngineProvider(nlp_configuration=ner_conf).create_engine()
        return AnalyzerEngine(nlp_engine=nlp_engine)
    except Exception:
        # Older/newer Presidio may reject the config shape — default is fine,
        # it just may not surface ORGANIZATION.
        return AnalyzerEngine()


def _analyzer():
    global _ANALYZER, _INIT_FAILED
    if _ANALYZER is not None or _INIT_FAILED:
        return _ANALYZER
    with _LOCK:
        if _ANALYZER is None and not _INIT_FAILED:
            try:
                _ANALYZER = _build_analyzer()
            except Exception:
                _INIT_FAILED = True
    return _ANALYZER


def available() -> bool:
    """True if presidio-analyzer and its spaCy model loaded successfully."""
    return _analyzer() is not None


def presidio_hits(text: str) -> list[dict]:
    """Analyze `text` and return hit dicts for `ground_text_boxes()`.

    Each hit: {category, label, text, reason, confidence}. `text` is the exact
    substring Presidio matched, so OCR grounding can locate it verbatim.
    """
    if not text or not text.strip():
        return []
    analyzer = _analyzer()
    if analyzer is None:
        return []
    try:
        with _LOCK:
            results = analyzer.analyze(
                text=text, language="en", score_threshold=SCORE_THRESHOLD)
    except Exception:
        return []

    hits: list[dict] = []
    for r in results:
        span = text[r.start:r.end].strip()
        if not (2 <= len(span) <= 90):
            continue
        cat = ENTITY_CATEGORY.get(r.entity_type) or coerce_category(r.entity_type)
        hits.append({
            "category": cat,
            "label": r.entity_type,
            "text": span,
            "reason": f"Presidio: {r.entity_type} (score {r.score:.2f}).",
            "confidence": round(float(r.score), 2),
        })
    return hits
