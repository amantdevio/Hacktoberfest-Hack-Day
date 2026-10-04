"""
Helper utilities for source quote highlighting, data formatting, and multi-format exports.
"""

import io
import csv
import html
from typing import Iterable, List, Dict
from extractor import CommitmentItem, UnresolvedItem, verify_quote_in_text

# Color palette for assignees to visually distinguish commitments in transcript
PERSON_COLORS = [
    "#2563eb",  # Blue
    "#7c3aed",  # Purple
    "#059669",  # Emerald
    "#d97706",  # Amber
    "#dc2626",  # Red
    "#0891b2",  # Cyan
    "#db2777",  # Pink
]

def get_person_color_map(names: List[str]) -> Dict[str, str]:
    color_map = {}
    unique_names = sorted(list(set(names)))
    for idx, name in enumerate(unique_names):
        color_map[name] = PERSON_COLORS[idx % len(PERSON_COLORS)]
    return color_map


def next_task_id(commitment_ids: Iterable[str]) -> str:
    """Return the lowest unused sequential TASK id."""
    existing_ids = set(commitment_ids)
    number = 1
    while f"TASK-{number:02d}" in existing_ids:
        number += 1
    return f"TASK-{number:02d}"


def safe_csv_cell(value: object) -> str:
    """Prevent spreadsheet programs from evaluating exported text as a formula."""
    text = "" if value is None else str(value)
    if text.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + text
    return text

def highlight_transcript_with_quotes(
    transcript: str,
    commitments: List[CommitmentItem],
    unresolved: List[UnresolvedItem]
) -> str:
    """
    Renders the raw transcript into safe HTML with highlighted source quote spans.
    Each highlighted span is colored and shows a tooltip with the task ID and assignee.
    """
    if not transcript:
        return ""

    # Collect unique person names for color coding
    all_names = [c.who for c in commitments if c.who]
    color_map = get_person_color_map(all_names)

    # Collect spans to highlight: (start, end, label, color, type)
    spans = []

    # Map quotes in commitments
    for c in commitments:
        verified, start, end = verify_quote_in_text(c.source_quote, transcript)
        if verified:
            spans.append({
                "start": start,
                "end": end,
                "id": html.escape(c.id),
                "label": f"[{c.id}] Promise by {c.who} ({c.by_when})",
                "color": color_map.get(c.who, "#2563eb"),
                "is_unresolved": False
            })

    # Map quotes in unresolved items
    for u in unresolved:
        verified, start, end = verify_quote_in_text(u.source_quote, transcript)
        if verified:
            spans.append({
                "start": start,
                "end": end,
                "id": html.escape(u.id),
                "label": f"[{u.id}] Unresolved issue raised by {u.raised_by}",
                "color": "#ea580c",  # Warning orange
                "is_unresolved": True
            })

    if not spans:
        # No exact spans found; render escaped text in pre
        escaped_lines = [html.escape(line) for line in transcript.split("\n")]
        return "<div class='transcript-container'>" + "<br/>".join(escaped_lines) + "</div>"

    # Sort spans by start position, resolving overlaps
    spans.sort(key=lambda s: s["start"])
    merged_spans = []
    current_end = -1
    for s in spans:
        if s["start"] >= current_end:
            merged_spans.append(s)
            current_end = s["end"]

    # Build highlighted HTML string
    out = []
    cursor = 0
    for s in merged_spans:
        # Preceding normal text
        if s["start"] > cursor:
            out.append(html.escape(transcript[cursor:s["start"]]))

        # Highlighted text
        highlighted_segment = html.escape(transcript[s["start"]:s["end"]])
        badge_style = f"background-color: {s['color']}22; border-left: 3px solid {s['color']}; padding: 2px 6px; border-radius: 4px; font-weight: 500;"
        tag_html = f"<span class='quote-highlight' style='{badge_style}' title='{html.escape(s['label'])}'>{highlighted_segment}<span style='font-size:0.75rem; vertical-align:super; color:{s['color']}; font-weight:bold; margin-left:3px;'>({s['id']})</span></span>"
        out.append(tag_html)

        cursor = s["end"]

    # Remainder
    if cursor < len(transcript):
        out.append(html.escape(transcript[cursor:]))

    full_html = "".join(out).replace("\n", "<br/>")
    return f"<div class='transcript-container' style='font-family: monospace; line-height: 1.6; padding: 16px; background: rgba(128,128,128,0.06); border-radius: 8px; border: 1px solid rgba(128,128,128,0.2); max-height: 520px; overflow-y: auto;'>{full_html}</div>"

def export_commitments_to_csv(commitments: List[CommitmentItem], unresolved: List[UnresolvedItem]) -> str:
    """Exports tasks and unresolved items to CSV format."""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Headers
    def write_row(values):
        writer.writerow([safe_csv_cell(value) for value in values])

    write_row(["Type", "ID", "Action / Question", "Assignee / Raised By", "Recipient / Target", "Deadline", "Status", "Priority", "Category", "Confidence", "Source Quote", "Notes"])

    for c in commitments:
        write_row([
            "Commitment",
            c.id,
            c.what,
            c.who,
            c.to_whom,
            c.by_when,
            c.status,
            c.priority,
            c.category,
            f"{c.confidence * 100:.0f}%",
            c.source_quote,
            c.notes or ""
        ])

    for u in unresolved:
        write_row([
            "Unresolved Item",
            u.id,
            u.question,
            u.raised_by,
            u.blocking,
            "N/A",
            "Open Question",
            "High",
            "Blocker",
            "N/A",
            u.source_quote,
            f"Blocking: {u.blocking}"
        ])

    return output.getvalue()

def export_commitments_to_markdown(commitments: List[CommitmentItem], unresolved: List[UnresolvedItem], title: str = "Promise Tracker Summary") -> str:
    """Generates a structured, copy-pasteable Markdown report."""
    md = [f"# 📋 {title}\n"]
    md.append(f"*Extracted with Google Gemma via Gemini API*\n")

    md.append("## ✅ Actionable Commitments\n")
    if not commitments:
        md.append("_No commitments extracted._\n")
    else:
        for c in commitments:
            checkbox = "[x]" if c.status == "Completed" else "[ ]"
            md.append(f"- {checkbox} **{c.what}** (`{c.id}`)")
            md.append(f"  - **Assignee:** @{c.who} | **To:** {c.to_whom} | **Deadline:** `{c.by_when}`")
            md.append(f"  - **Status:** `{c.status}` | **Priority:** `{c.priority}` | **Category:** `{c.category}`")
            md.append(f"  - **Source Quote:** _\"{c.source_quote}\"_")
            if c.notes:
                md.append(f"  - **Notes:** {c.notes}")
            md.append("")

    md.append("## ❓ Unresolved Questions & Blockers\n")
    if not unresolved:
        md.append("_No unresolved items._\n")
    else:
        for u in unresolved:
            md.append(f"- **[BLOCKED]** `{u.id}`: {u.question}")
            md.append(f"  - **Raised By:** @{u.raised_by} | **Affecting:** {u.blocking}")
            md.append(f"  - **Quote:** _\"{u.source_quote}\"_")
            md.append("")

    return "\n".join(md)
