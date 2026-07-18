"""Shared Pydantic contracts — the frozen interface every phase speaks.

One vocabulary across REDACT / SECURE / ORGANIZE so the frontend renders any
phase's proposals with the same review component.
"""
from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Phase 1 — REDACT
# ---------------------------------------------------------------------------

Category = Literal[
    "person", "organization", "contact", "financial", "medical", "gov_id",
    "signature", "face", "address", "date", "other",
]

# Any model-emitted category outside the set above is coerced to this.
def coerce_category(c: str) -> str:
    valid = {"person", "organization", "contact", "financial", "medical",
             "gov_id", "signature", "face", "address", "date", "other"}
    c = (c or "other").strip().lower()
    # common synonyms the model may produce
    alias = {"org": "organization", "company": "organization",
             "employer": "organization", "name": "person", "phone": "contact",
             "email": "contact", "ssn": "gov_id", "id": "gov_id",
             "dob": "date", "account": "financial", "money": "financial"}
    c = alias.get(c, c)
    return c if c in valid else "other"

# How a box's coordinates were established — drives trust + padding policy.
Source = Literal["regex", "ocr_grounded", "gemma_vision"]


class Box(BaseModel):
    """A pixel-space rectangle proposed for redaction on one page image."""
    x1: int
    y1: int
    x2: int
    y2: int
    category: Category = "other"
    label: str = ""            # e.g. "SSN", "full name"
    text: str = ""             # the matched string, if known (regex/ocr)
    reason: str = ""           # why it's sensitive (Gemma) — for the audit trail
    confidence: float = 0.9
    source: Source = "gemma_vision"
    accepted: bool = True      # recall bias: proposed = accepted by default


class DetectResult(BaseModel):
    page_width: int
    page_height: int
    boxes: list[Box]
    full_text: str = ""        # transcription — feeds the reasoning features
    stats: dict = Field(default_factory=dict)


class ReviewDecision(BaseModel):
    """One reviewer action, journaled for the audit certificate."""
    box_index: int
    action: Literal["accept", "reject", "add", "resize"]
    by: str = "demo-officer"
    ts: str = ""


# ---------------------------------------------------------------------------
# Phase 2 — SECURE
# ---------------------------------------------------------------------------

Severity = Literal["critical", "high", "medium", "low", "info"]
SEVERITY_WEIGHT = {"critical": 40, "high": 20, "medium": 10, "low": 5, "info": 0}


class Finding(BaseModel):
    id: str
    collector: str                       # which scanner produced it
    title: str
    severity: Severity
    detail: str = ""                     # raw, deterministic evidence
    explanation: str = ""                # Gemma plain-English what/why/fix
    remediation: str = ""                # from the FixRegistry, if any
    requires_admin: bool = False
    reversible: bool = False
    path: Optional[str] = None           # for secrets-on-disk -> "send to Redactor"
    can_redact: bool = False


class ScanResult(BaseModel):
    findings: list[Finding]
    safety_score: int
    score_breakdown: dict
    admin: bool
    generated_offline: bool = True


# ---------------------------------------------------------------------------
# Phase 3 — ORGANIZE
# ---------------------------------------------------------------------------

class FileProposal(BaseModel):
    src: str
    dst: str                             # proposed new path (category/newname)
    old_name: str
    new_name: str
    category: str = "other"
    subcategory: str = ""
    doc_type: str = "unknown"
    topic: str = ""
    patient: str = ""                    # healthcare: whose record this is
    reason: str = ""
    confidence: float = 0.5
    quick_hash: str = ""
    is_duplicate: bool = False           # exact copy of another kept file
    excluded: bool = False


class DuplicateGroup(BaseModel):
    sha: str
    size: int
    keep: str                            # the copy to keep
    duplicates: list[str]                # exact copies proposed for removal


class OrganizePlan(BaseModel):
    root: str
    profile: str = "general"             # "healthcare" | "general"
    proposals: list[FileProposal]
    tree_preview: dict = Field(default_factory=dict)
    duplicates: list[DuplicateGroup] = Field(default_factory=list)
    naming_convention: str = ""
    taxonomy_reason: str = ""
    scanned: int = 0
    capped: bool = False                 # hit the per-scan file cap (more remain)
    cap: int = 0


class DirEntry(BaseModel):
    name: str
    path: str
    file_count: int = 0


class DirListing(BaseModel):
    path: str
    parent: Optional[str] = None
    dirs: list[DirEntry] = Field(default_factory=list)
    file_count: int = 0
    drives: list[str] = Field(default_factory=list)
    shortcuts: list[DirEntry] = Field(default_factory=list)


class JournalEntry(BaseModel):
    op: Literal["move", "rename"]
    src: str
    dst: str
    hash: str = ""
    ts: str = ""
    committed: bool = False


# ---------------------------------------------------------------------------
# Shared — egress proof
# ---------------------------------------------------------------------------

class Connection(BaseModel):
    pid: int
    proc: str
    laddr: str
    raddr: str
    is_loopback: bool
    label: str      # "local LLM — allowed" | "EXTERNAL" | "local"


class EgressReport(BaseModel):
    external_count: int
    connections: list[Connection]
    verdict: str
