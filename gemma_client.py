"""Gemma Client integration using the Google GenAI SDK."""

import time
import os
from typing import Optional, Tuple
from dotenv import load_dotenv
from config import (
    DEFAULT_GEMMA_MODEL,
    GEMMA_EXTRACTION_RESPONSE_SCHEMA,
    GEMMA_SYSTEM_PROMPT,
    GEMMA_EXTRACTION_USER_TEMPLATE,
)
from extractor import (
    GemmaResponseError,
    parse_gemma_json_response,
    ExtractionResult,
)

load_dotenv()

class GemmaClient:
    def __init__(self, api_key: Optional[str] = None, model_name: str = DEFAULT_GEMMA_MODEL):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.model_name = model_name
        self.client = None
        self.fast_client = None
        if self.api_key:
            from google import genai
            from google.genai import types

            http_options = types.HttpOptions(
                timeout=45_000,
                retry_options=types.HttpRetryOptions(attempts=1),
            )
            self.fast_client = genai.Client(
                api_key=self.api_key,
                http_options=http_options,
            )
            self.client = self.fast_client

    def is_configured(self) -> bool:
        return bool(self.api_key and self.fast_client)

    def extract_commitments(
        self,
        transcript: str,
        model_override: Optional[str] = None,
        temperature: float = 0.1
    ) -> Tuple[ExtractionResult, Optional[str]]:
        """
        Runs one bounded extraction request against the selected model.
        """
        if not transcript or not transcript.strip():
            return ExtractionResult(
                commitments=[],
                unresolved_items=[],
                model_used=self.model_name,
                grounding_rate=0.0,
                duration_seconds=0.0,
                raw_response=""
            ), "Please enter or paste a conversation transcript to analyze."

        if not self.is_configured():
            return ExtractionResult(
                commitments=[],
                unresolved_items=[],
                model_used=self.model_name,
                grounding_rate=0.0,
                duration_seconds=0.0,
                raw_response=""
            ), "Gemini API Key is required. Please enter your Google Gemini API Key in the sidebar or set GEMINI_API_KEY in your .env file."

        primary_model = model_override or self.model_name
        user_prompt = GEMMA_EXTRACTION_USER_TEMPLATE.format(transcript=transcript)
        full_prompt = f"{GEMMA_SYSTEM_PROMPT}\n\n{user_prompt}"
        from google.genai import types

        start_time = time.time()
        try:
            response = self.fast_client.models.generate_content(
                model=primary_model,
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=2500,
                    thinking_config=types.ThinkingConfig(thinking_level="minimal"),
                    response_mime_type="application/json",
                    response_schema=GEMMA_EXTRACTION_RESPONSE_SCHEMA,
                ),
            )
            duration = time.time() - start_time
            candidates = getattr(response, "candidates", None) or []
            finish_reason = (
                getattr(candidates[0], "finish_reason", None) if candidates else None
            )
            if finish_reason is not None and str(finish_reason).endswith("MAX_TOKENS"):
                raise GemmaResponseError(
                    "Gemma stopped at its output-token limit, so the JSON response "
                    "is incomplete. Try a shorter transcript."
                )

            result = parse_gemma_json_response(
                raw_text=response.text or "",
                original_transcript=transcript,
                model_name=primary_model,
                duration=duration,
            )
            return result, None
        except GemmaResponseError as exc:
            return ExtractionResult(
                commitments=[],
                unresolved_items=[],
                model_used=primary_model,
                grounding_rate=0.0,
                duration_seconds=time.time() - start_time,
                raw_response=response.text or "",
            ), f"Gemma returned an invalid extraction response: {exc}"
        except Exception as exc:
            duration = time.time() - start_time
            return ExtractionResult(
                commitments=[],
                unresolved_items=[],
                model_used=primary_model,
                grounding_rate=0.0,
                duration_seconds=duration,
                raw_response=f"Error encountered: {exc}",
            ), (
                f"Gemini request to '{primary_model}' failed after "
                f"{duration:.1f}s (single request, 45-second timeout; no model "
                f"fallback): {exc}"
            )
