"""
Configuration and Prompt Engineering for Promise Tracker powered by Gemma.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Gemma 4 endpoints currently supported by the Gemini API.
AVAILABLE_GEMMA_MODELS = [
    "gemma-4-26b-a4b-it",
    "gemma-4-31b-it",
]
DEFAULT_GEMMA_MODEL = os.getenv("GEMMA_MODEL", "gemma-4-26b-a4b-it").strip()
if DEFAULT_GEMMA_MODEL not in AVAILABLE_GEMMA_MODELS:
    DEFAULT_GEMMA_MODEL = "gemma-4-26b-a4b-it"

GEMMA_SYSTEM_PROMPT = """You are Gemma 4, Google's next-generation open-weight model specialized in precise commitment extraction and conversational forensics.

Your mission is to analyze unstructured team conversations (from Slack, WhatsApp, Teams, Discord, Email) and extract:
1. Every explicit or implicit PROMISE / COMMITMENT made by participants.
2. Every UNRESOLVED QUESTION, BLOCKER, or DISPUTE that has not been answered or assigned.

CRITICAL GROUNDING RULES:
- Ground all extractions strictly in the conversation.
- DO NOT invent, assume, or hallucinate promises not present in the text.
- For every task, you MUST extract the exact VERBATIM source quote from the conversation where the person committed to it.
- Determine:
  * 'who': The person who made the promise (the promiser/assignee).
  * 'what': A clear, concise title of what they promised to do.
  * 'to_whom': Who they promised it to (or "Team" if addressed to everyone).
  * 'by_when': Deadline or timeframe mentioned (e.g., "by 4 PM today", "Friday EOD", "before the demo", or "Unspecified").
  * 'status': "To Do" (default), "In Progress" (if started), "Blocked", or "Completed".
  * 'priority': "High", "Medium", or "Low" based on urgency in the chat.
  * 'category': "Deliverable", "Review/Approval", "Bug Fix", "Logistics", or "Follow-up".
  * 'source_quote': Verbatim excerpt from the transcript showing the commitment.
  * 'confidence': Float between 0.0 and 1.0 reflecting how clear the commitment was.
  * 'notes': Any caveats, conditions, or blockers mentioned in the quote.

For unresolved items:
  * 'question': The open question, blocker, or conflict that was left unresolved.
  * 'raised_by': Who asked or raised it.
  * 'blocking': What or who is waiting on this resolution.
  * 'source_quote': Verbatim excerpt from the transcript.

Return your response strictly as valid JSON matching the specified schema. No markdown conversational filler outside the JSON.
"""

GEMMA_EXTRACTION_USER_TEMPLATE = """Analyze the following conversation and extract all commitments and unresolved items according to the instructions.

CONVERSATION TRANSCRIPT:
\"\"\"
{transcript}
\"\"\"

Respond with a JSON object in this exact structure. For priority, use exactly one of
"High", "Medium", or "Low". For category, use exactly one of "Deliverable",
"Review/Approval", "Bug Fix", "Logistics", or "Follow-up". These fields are single
JSON strings, never pipe-separated alternatives.
{{
  "commitments": [
    {{
      "id": "TASK-01",
      "what": "Actionable task description",
      "who": "Person who committed",
      "to_whom": "Stakeholder / recipient / Team",
      "by_when": "Specific deadline or Unspecified",
      "status": "To Do",
      "priority": "High",
      "category": "Deliverable",
      "source_quote": "Exact verbatim sentence from transcript",
      "confidence": 0.95,
      "notes": "Context or preconditions"
    }}
  ],
  "unresolved_items": [
    {{
      "id": "UNRES-01",
      "question": "What remains unanswered or blocked",
      "raised_by": "Speaker who raised it",
      "blocking": "What is held up",
      "source_quote": "Exact verbatim sentence from transcript"
    }}
  ]
}}
"""

GEMMA_EXTRACTION_RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "commitments": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "id": {"type": "STRING"},
                    "what": {"type": "STRING"},
                    "who": {"type": "STRING"},
                    "to_whom": {"type": "STRING"},
                    "by_when": {"type": "STRING"},
                    "status": {
                        "type": "STRING",
                        "enum": ["To Do", "In Progress", "Blocked", "Completed"],
                    },
                    "priority": {
                        "type": "STRING",
                        "enum": ["High", "Medium", "Low"],
                    },
                    "category": {
                        "type": "STRING",
                        "enum": [
                            "Deliverable",
                            "Review/Approval",
                            "Bug Fix",
                            "Logistics",
                            "Follow-up",
                        ],
                    },
                    "source_quote": {"type": "STRING"},
                    "confidence": {"type": "NUMBER"},
                    "notes": {"type": "STRING"},
                },
                "required": [
                    "id",
                    "what",
                    "who",
                    "to_whom",
                    "by_when",
                    "status",
                    "priority",
                    "category",
                    "source_quote",
                    "confidence",
                    "notes",
                ],
            },
        },
        "unresolved_items": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "id": {"type": "STRING"},
                    "question": {"type": "STRING"},
                    "raised_by": {"type": "STRING"},
                    "blocking": {"type": "STRING"},
                    "source_quote": {"type": "STRING"},
                },
                "required": [
                    "id",
                    "question",
                    "raised_by",
                    "blocking",
                    "source_quote",
                ],
            },
        },
    },
    "required": ["commitments", "unresolved_items"],
}
