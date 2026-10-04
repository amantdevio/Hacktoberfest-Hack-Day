import html
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from extractor import (
    CommitmentItem,
    GemmaResponseError,
    parse_gemma_json_response,
    verify_quote_in_text,
)
from gemma_client import GemmaClient
from storage import load_saved_board, save_current_board
from utils import (
    export_commitments_to_csv,
    highlight_transcript_with_quotes,
    next_task_id,
)


class QuoteVerificationTests(unittest.TestCase):
    def test_normalized_quote_returns_original_source_offsets(self):
        transcript = "Maya: I’ll\nsend it tomorrow."

        verified, start, end = verify_quote_in_text("I'll send it", transcript)

        self.assertTrue(verified)
        self.assertEqual(transcript[start:end], "I’ll\nsend it")

    def test_nonverbatim_quote_is_not_verified(self):
        transcript = (
            "Alex will send the comprehensive design document before lunch on Friday."
        )

        verified, start, end = verify_quote_in_text(
            "Alex will send the comprehensive design document before lunch on Monday.",
            transcript,
        )

        self.assertFalse(verified)
        self.assertEqual((start, end), (-1, -1))


class ExtractionParsingTests(unittest.TestCase):
    def test_malformed_json_fails_instead_of_returning_empty_success(self):
        with self.assertRaises(GemmaResponseError):
            parse_gemma_json_response("{not json", "source transcript")

    def test_duplicate_model_ids_are_made_unique(self):
        response = {
            "commitments": [
                {
                    "id": "TASK-01",
                    "what": "Send the report",
                    "who": "Alex",
                    "source_quote": "I will send the report.",
                },
                {
                    "id": "TASK-01",
                    "what": "Review the report",
                    "who": "Maya",
                    "source_quote": "I will review the report.",
                },
            ],
            "unresolved_items": [],
        }

        result = parse_gemma_json_response(
            json.dumps(response),
            "I will send the report. I will review the report.",
        )

        self.assertEqual(
            [item.id for item in result.commitments], ["TASK-01", "TASK-02"]
        )

    def test_invalid_model_json_is_reported_without_fallback_calls(self):
        class ModelStub:
            calls = 0

            def generate_content(self, model, contents, config):
                assert model == "test-model"
                assert contents
                assert "precise commitment extraction" in contents
                assert config.max_output_tokens == 2500
                assert config.response_mime_type == "application/json"
                assert config.response_schema["required"] == [
                    "commitments",
                    "unresolved_items",
                ]
                self.calls += 1
                return SimpleNamespace(text="{not json")

        model_stub = ModelStub()
        client = GemmaClient.__new__(GemmaClient)
        client.api_key = "test-key"
        client.model_name = "test-model"
        client.client = SimpleNamespace(models=model_stub)
        client.fast_client = client.client

        result, error = client.extract_commitments("A test transcript.")

        self.assertEqual(model_stub.calls, 1)
        self.assertEqual(result.commitments, [])
        self.assertEqual(result.grounding_rate, 0.0)
        self.assertIn("invalid extraction response", error)

    def test_extraction_failure_does_not_retry_or_fallback(self):
        requested_models = []

        class ModelStub:
            def generate_content(self, model, contents, config):
                requested_models.append(model)
                assert contents
                assert config.max_output_tokens == 2500
                raise TimeoutError("request timed out")

        client = GemmaClient.__new__(GemmaClient)
        client.api_key = "test-key"
        client.model_name = "test-model"
        client.client = SimpleNamespace(models=ModelStub())
        client.fast_client = client.client

        result, error = client.extract_commitments("A test transcript.")

        self.assertEqual(requested_models, ["test-model"])
        self.assertEqual(result.commitments, [])
        self.assertIn("single request, 45-second timeout", error)

    def test_extraction_schema_requires_expected_fields(self):
        from config import GEMMA_EXTRACTION_RESPONSE_SCHEMA

        commitment_schema = GEMMA_EXTRACTION_RESPONSE_SCHEMA["properties"][
            "commitments"
        ]["items"]
        unresolved_schema = GEMMA_EXTRACTION_RESPONSE_SCHEMA["properties"][
            "unresolved_items"
        ]["items"]
        self.assertEqual(
            commitment_schema["required"],
            list(commitment_schema["properties"]),
        )
        self.assertEqual(
            unresolved_schema["required"],
            list(unresolved_schema["properties"]),
        )

class DisplaySafetyTests(unittest.TestCase):
    def test_highlight_escapes_model_supplied_ids_and_text(self):
        transcript = "I will deliver <the report>."
        item = CommitmentItem(
            id='<img src=x onerror="alert(1)">',
            what="Deliver report",
            who="Alex",
            source_quote="I will deliver <the report>.",
        )

        rendered = highlight_transcript_with_quotes(transcript, [item], [])

        self.assertNotIn("<img", rendered)
        self.assertIn(html.escape(item.id), rendered)
        self.assertIn("&lt;the report&gt;", rendered)

    def test_highlight_uses_normalized_quote_offsets(self):
        transcript = "Maya: I’ll\nsend it tomorrow."
        item = CommitmentItem(
            id="TASK-01",
            what="Send it",
            who="Maya",
            source_quote="I'll send it",
        )

        rendered = highlight_transcript_with_quotes(transcript, [item], [])

        self.assertIn("class='quote-highlight'", rendered)
        self.assertIn("I’ll<br/>send it", rendered)

    def test_csv_export_escapes_formula_cells(self):
        item = CommitmentItem(
            id="TASK-01",
            what="=HYPERLINK(\"https://example.com\")",
            who="Alex",
            source_quote="+cmd|' /C calc'!A0",
        )

        exported = export_commitments_to_csv([item], [])

        self.assertIn("'=HYPERLINK", exported)
        self.assertIn("'+cmd", exported)

    def test_default_gemma_model_is_supported_by_the_api(self):
        from config import AVAILABLE_GEMMA_MODELS, DEFAULT_GEMMA_MODEL

        self.assertIn(DEFAULT_GEMMA_MODEL, AVAILABLE_GEMMA_MODELS)
        self.assertEqual(
            set(AVAILABLE_GEMMA_MODELS),
            {"gemma-4-26b-a4b-it", "gemma-4-31b-it"},
        )

    def test_next_task_id_does_not_collide_after_deletion(self):
        self.assertEqual(next_task_id(["TASK-01", "TASK-03"]), "TASK-02")


class PersistenceTests(unittest.TestCase):
    def test_due_date_is_serialized_and_loaded(self):
        from extractor import CommitmentItem

        with tempfile.TemporaryDirectory() as directory:
            state_file = Path(directory) / "board.json"
            task = CommitmentItem(
                id="TASK-01",
                what="Send report",
                who="Alex",
                source_quote="I will send the report.",
                due_date=date(2026, 10, 5),
            )
            with patch("storage.STATE_FILE", state_file):
                save_current_board([task], [], "I will send the report.")
                state = load_saved_board()

            self.assertEqual(state["commitments"][0]["due_date"], "2026-10-05")

if __name__ == "__main__":
    unittest.main()
