"""
Local persistence manager for Promise Tracker.
Ensures that extracted tasks, board modifications, and API keys survive browser refreshes.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv, set_key

PROJECT_DIR = Path(__file__).resolve().parent
STATE_FILE = PROJECT_DIR / "saved_board_state.json"
ENV_FILE = PROJECT_DIR / ".env"

load_dotenv(ENV_FILE)

def get_persisted_api_key() -> str:
    """Retrieves the persisted API key from environment or .env file."""
    load_dotenv(ENV_FILE, override=True)
    return os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", "")

def persist_api_key(api_key: str):
    """Saves the API key into the local .env file so it never disappears on refresh."""
    if not api_key:
        return
    key = api_key.strip()
    if not key:
        return

    # Update or create .env
    if not ENV_FILE.exists():
        with ENV_FILE.open("w", encoding="utf-8") as f:
            f.write(f"GEMINI_API_KEY={key}\n")
    else:
        # Check if GEMINI_API_KEY already exists in .env
        set_key(ENV_FILE, "GEMINI_API_KEY", key)

    os.environ["GEMINI_API_KEY"] = key
    load_dotenv(ENV_FILE, override=True)

def load_saved_board() -> Dict[str, Any]:
    """Loads saved commitments, unresolved items, and transcript from disk."""
    if not STATE_FILE.exists():
        return {
            "commitments": [],
            "unresolved_items": [],
            "raw_transcript": "",
            "extraction_result": None
        }
    with STATE_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)

def save_current_board(
    commitments: List[Any],
    unresolved_items: List[Any],
    raw_transcript: str,
    extraction_result: Optional[Any] = None
):
    """Persists current state of the board to disk."""
    data = {
        "commitments": [c.model_dump(mode="json") if hasattr(c, "model_dump") else c for c in commitments],
        "unresolved_items": [u.model_dump(mode="json") if hasattr(u, "model_dump") else u for u in unresolved_items],
        "raw_transcript": raw_transcript,
        "extraction_result": extraction_result.model_dump(mode="json") if extraction_result and hasattr(extraction_result, "model_dump") else extraction_result
    }
    temporary_file = STATE_FILE.with_suffix(".tmp")
    with temporary_file.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(temporary_file, STATE_FILE)

def clear_persisted_board():
    """Removes the saved state file when user clears the board."""
    if STATE_FILE.exists():
        STATE_FILE.unlink()
