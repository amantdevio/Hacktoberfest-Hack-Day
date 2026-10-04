"""
Data models and extraction parsing logic for Promise Tracker.
Checks whether model-provided source quotes occur in the supplied transcript.
"""

import json
import re
from datetime import date
from typing import List, Literal, Optional, Tuple
from pydantic import BaseModel, Field, ValidationError

class CommitmentItem(BaseModel):
    id: str = Field(default_factory=lambda: "TASK-01")
    what: str
    who: str
    to_whom: str = "Team"
    by_when: str = "Unspecified"
    status: str = "To Do"  # "To Do", "In Progress", "Blocked", "Completed"
    priority: str = "Medium"  # "High", "Medium", "Low"
    category: str = "Deliverable"  # "Deliverable", "Review/Approval", "Bug Fix", "Logistics", "Follow-up"
    source_quote: str
    confidence: float = Field(default=0.95, ge=0.0, le=1.0)
    notes: Optional[str] = ""
    verified_in_source: bool = False
    quote_start: Optional[int] = -1
    quote_end: Optional[int] = -1
    due_date: Optional[date] = None
    review_status: Literal[
        "Needs review", "Correct", "Incorrect", "Corrected", "Incomplete"
    ] = "Needs review"
    review_notes: str = ""

class UnresolvedItem(BaseModel):
    id: str = Field(default_factory=lambda: "UNRES-01")
    question: str
    raised_by: str = "Unknown"
    blocking: str = "Unspecified"
    source_quote: str
    verified_in_source: bool = False
    quote_start: Optional[int] = -1
    quote_end: Optional[int] = -1

class ExtractionResult(BaseModel):
    commitments: List[CommitmentItem] = Field(default_factory=list)
    unresolved_items: List[UnresolvedItem] = Field(default_factory=list)
    model_used: str = "gemma-4-26b-a4b-it"
    grounding_rate: float = 1.0
    duration_seconds: float = 0.0
    raw_response: str = ""


class GemmaResponseError(ValueError):
    """Raised when a model response cannot be safely parsed as extraction data."""


def normalize_smart_quotes(s: str) -> str:
    """Normalize unicode curly quotes and apostrophes to standard ASCII."""
    if not s:
        return ""
    return s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')

def clean_quote(quote: str) -> str:
    """Strip bounding quotes and excess whitespace."""
    if not quote:
        return ""
    q = quote.strip()
    if (q.startswith('"') and q.endswith('"')) or (q.startswith("'") and q.endswith("'")):
        q = q[1:-1].strip()
    return q

def verify_quote_in_text(quote: str, text: str) -> Tuple[bool, int, int]:
    """
    Verifies if a quote exists in the source text.
    Returns (is_verified, start_index, end_index).
    Applies exact matching, normalized smart quotes, whitespace-normalized, and fuzzy matching.
    """
    cleaned = clean_quote(quote)
    if not cleaned or not text:
        return False, -1, -1

    # 1. Exact match
    idx = text.find(cleaned)
    if idx != -1:
        return True, idx, idx + len(cleaned)

    # 2. Case-insensitive exact match
    lower_text = text.lower()
    lower_quote = cleaned.lower()
    idx_case = lower_text.find(lower_quote)
    if idx_case != -1:
        return True, idx_case, idx_case + len(cleaned)

    # 3. Normalize punctuation and whitespace while retaining source offsets.
    normalized_chars = []
    source_offsets = []
    in_whitespace = False
    for source_index, char in enumerate(text):
        if char.isspace():
            if not in_whitespace:
                normalized_chars.append(" ")
                source_offsets.append(source_index)
            in_whitespace = True
            continue
        in_whitespace = False
        normalized_chars.append(normalize_smart_quotes(char).lower())
        source_offsets.append(source_index)

    normalized_text = "".join(normalized_chars)
    normalized_quote = re.sub(
        r"\s+", " ", normalize_smart_quotes(cleaned).lower()
    ).strip()
    normalized_index = normalized_text.find(normalized_quote)
    if normalized_index != -1:
        start = source_offsets[normalized_index]
        end = source_offsets[normalized_index + len(normalized_quote) - 1] + 1
        return True, start, end

    return False, -1, -1

def parse_gemma_json_response(raw_text: str, original_transcript: str, model_name: str = "gemma-4-26b-a4b-it", duration: float = 0.0) -> ExtractionResult:
    """
    Robust parser for Gemma output. Extracts JSON blocks even if wrapped in markdown formatting.
    """
    cleaned_json_str = raw_text.strip()
    
    # Strip Gemma 4 thinking tags if present
    if "<thought>" in cleaned_json_str and "</thought>" in cleaned_json_str:
        cleaned_json_str = cleaned_json_str.split("</thought>")[-1].strip()

    # Strip optional Markdown fences, including uppercase ```JSON fences.
    cleaned_json_str = re.sub(
        r"^\s*```(?:json)?\s*", "", cleaned_json_str, count=1, flags=re.IGNORECASE
    )
    cleaned_json_str = re.sub(r"\s*```\s*$", "", cleaned_json_str, count=1)

    # Allow a short preface or trailing note around the JSON object.
    start = cleaned_json_str.find("{")
    end = cleaned_json_str.rfind("}")
    if start != -1 and end >= start:
        cleaned_json_str = cleaned_json_str[start : end + 1]

    try:
        data = json.loads(cleaned_json_str)
    except json.JSONDecodeError as exc:
        raise GemmaResponseError(
            "Gemma returned malformed JSON "
            f"(line {exc.lineno}, column {exc.colno})."
        ) from exc

    if not isinstance(data, dict):
        raise GemmaResponseError("The model response must be a JSON object.")

    commitments_list: List[CommitmentItem] = []
    unresolved_list: List[UnresolvedItem] = []

    raw_commitments = data.get("commitments", [])
    raw_unresolved = data.get("unresolved_items", [])
    if not isinstance(raw_commitments, list) or not isinstance(raw_unresolved, list):
        raise GemmaResponseError(
            "The model response must contain commitment and unresolved-item lists."
        )

    total_quotes = 0
    verified_quotes = 0
    used_commitment_ids = set()
    used_unresolved_ids = set()

    for idx, c in enumerate(raw_commitments):
        if not isinstance(c, dict):
            raise GemmaResponseError(f"Commitment {idx + 1} must be a JSON object.")
        cid = str(c.get("id") or f"TASK-{idx+1:02d}")
        if cid in used_commitment_ids:
            fallback_number = idx + 1
            cid = f"TASK-{fallback_number:02d}"
            while cid in used_commitment_ids:
                fallback_number += 1
                cid = f"TASK-{fallback_number:02d}"
        used_commitment_ids.add(cid)
        quote = c.get("source_quote", "")
        if not isinstance(quote, str):
            quote = ""
        is_verified, start_pos, end_pos = verify_quote_in_text(quote, original_transcript)
        
        total_quotes += 1
        if is_verified:
            verified_quotes += 1

        try:
            confidence = float(c.get("confidence", 0.95))
            if not 0.0 <= confidence <= 1.0:
                raise ValueError("confidence must be between 0 and 1")
            commitments_list.append(
                CommitmentItem(
                    id=cid,
                    what=c.get("what", "Unspecified task"),
                    who=c.get("who", "Unassigned"),
                    to_whom=c.get("to_whom", "Team"),
                    by_when=c.get("by_when", "Unspecified"),
                    status=c.get("status")
                    if c.get("status") in ("To Do", "In Progress", "Blocked", "Completed")
                    else "To Do",
                    priority=c.get("priority")
                    if c.get("priority") in ("High", "Medium", "Low")
                    else "Medium",
                    category=c.get("category")
                    if c.get("category")
                    in ("Deliverable", "Review/Approval", "Bug Fix", "Logistics", "Follow-up")
                    else "Deliverable",
                    source_quote=clean_quote(quote),
                    confidence=confidence,
                    notes=c.get("notes", ""),
                    verified_in_source=is_verified,
                    quote_start=start_pos,
                    quote_end=end_pos,
                )
            )
        except (TypeError, ValueError, ValidationError) as exc:
            raise GemmaResponseError(
                f"Commitment {idx + 1} contains invalid field values."
            ) from exc

    for idx, u in enumerate(raw_unresolved):
        if not isinstance(u, dict):
            raise GemmaResponseError(f"Unresolved item {idx + 1} must be a JSON object.")
        uid = str(u.get("id") or f"UNRES-{idx+1:02d}")
        if uid in used_unresolved_ids:
            fallback_number = idx + 1
            uid = f"UNRES-{fallback_number:02d}"
            while uid in used_unresolved_ids:
                fallback_number += 1
                uid = f"UNRES-{fallback_number:02d}"
        used_unresolved_ids.add(uid)
        quote = u.get("source_quote", "")
        if not isinstance(quote, str):
            quote = ""
        is_verified, start_pos, end_pos = verify_quote_in_text(quote, original_transcript)
        
        total_quotes += 1
        if is_verified:
            verified_quotes += 1

        try:
            unresolved_list.append(
                UnresolvedItem(
                    id=uid,
                    question=u.get("question", "Unspecified question"),
                    raised_by=u.get("raised_by", "Unknown"),
                    blocking=u.get("blocking", "Unspecified"),
                    source_quote=clean_quote(quote),
                    verified_in_source=is_verified,
                    quote_start=start_pos,
                    quote_end=end_pos,
                )
            )
        except (TypeError, ValueError, ValidationError) as exc:
            raise GemmaResponseError(
                f"Unresolved item {idx + 1} contains invalid field values."
            ) from exc

    grounding_rate = (verified_quotes / total_quotes) if total_quotes > 0 else 1.0

    return ExtractionResult(
        commitments=commitments_list,
        unresolved_items=unresolved_list,
        model_used=model_name,
        grounding_rate=round(grounding_rate, 3),
        duration_seconds=round(duration, 2),
        raw_response=raw_text
    )
