"""Verify that cumulative Codex token counts are converted to per-message deltas."""

import json
import time
from pathlib import Path

from apotheosession.converter import Converter, convert_file
from apotheosession.opencode_schema import make_assistant_message


def _mk_token_event(total: int, input_t: int = 0, output_t: int = 0) -> dict:
    return {
        "type": "event_msg",
        "payload": {
            "type": "token_count",
            "info": {
                "total_token_usage": {
                    "total_tokens": total,
                    "input_tokens": input_t,
                    "output_tokens": output_t,
                    "reasoning_output_tokens": 0,
                    "cached_input_tokens": 0,
                }
            },
        },
    }


def _mk_session_meta(cwd: str = "/tmp", model_provider: str = "ccswitch") -> dict:
    return {
        "type": "session_meta",
        "payload": {
            "id": "019ee598-16ea-7ce1-9eaf-522cdfe63705",
            "timestamp": "2026-06-20T23:13:30Z",
            "cwd": cwd,
            "model_provider": model_provider,
            "cli_version": "0.125.0",
        },
    }


def _mk_user_msg(text: str = "hello") -> dict:
    return {
        "type": "response_item",
        "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": text}]},
    }


def _mk_assistant_msg() -> dict:
    return {
        "type": "response_item",
        "payload": {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "ok"}]},
    }


class TestTokenDelta:
    """Unit tests for cumulative-to-per-message token delta computation."""

    def test_single_token_event_is_used_as_delta(self):
        """When there's only one token_count, delta == raw value (no previous to subtract)."""
        events = [
            _mk_session_meta(),
            _mk_user_msg(),
            _mk_assistant_msg(),
            _mk_token_event(total=500, input_t=300, output_t=200),
        ]
        converter = Converter(events)
        session = converter.convert()
        output = session.to_dict()

        # Find the step-finish tokens
        step_parts = [
            p
            for m in output["messages"]
            for p in m["parts"]
            if p.get("type") == "step-finish" and "tokens" in p
        ]
        assert len(step_parts) == 1
        tokens = step_parts[0]["tokens"]
        assert tokens["total"] == 500
        assert tokens["input"] == 300
        assert tokens["output"] == 200

    def test_multiple_token_events_produce_deltas(self):
        """Three cumulative token_count events should produce three per-message deltas."""
        events = [
            _mk_session_meta(),
            _mk_user_msg(text="msg1"),
            _mk_assistant_msg(),
            _mk_token_event(total=100, input_t=60, output_t=40),
            _mk_user_msg(text="msg2"),
            _mk_assistant_msg(),
            _mk_token_event(total=350, input_t=200, output_t=150),
            _mk_user_msg(text="msg3"),
            _mk_assistant_msg(),
            _mk_token_event(total=600, input_t=350, output_t=250),
        ]
        converter = Converter(events)
        session = converter.convert()
        output = session.to_dict()

        step_parts = [
            p
            for m in output["messages"]
            for p in m["parts"]
            if p.get("type") == "step-finish" and "tokens" in p
        ]
        assert len(step_parts) == 3, f"Expected 3 step-finish parts, got {len(step_parts)}"

        totals = [p["tokens"]["total"] for p in step_parts]
        # Cumulative values: 100, 350, 600
        # Expected deltas: 100, 250, 250
        assert totals[0] == 100, f"First delta should be 100, got {totals[0]}"
        assert totals[1] == 250, f"Second delta should be 250 (350-100), got {totals[1]}"
        assert totals[2] == 250, f"Third delta should be 250 (600-350), got {totals[2]}"

    def test_token_info_none_is_skipped(self):
        """token_count events with info=None should be safely skipped."""
        events = [
            _mk_session_meta(),
            _mk_user_msg(),
            _mk_assistant_msg(),
            {
                "type": "event_msg",
                "payload": {"type": "token_count", "info": None},
            },
        ]
        converter = Converter(events)
        session = converter.convert()
        output = session.to_dict()

        step_parts = [
            p
            for m in output["messages"]
            for p in m["parts"]
            if p.get("type") == "step-finish"
        ]
        assert len(step_parts) == 0

    def test_no_token_events_still_produces_output(self):
        """Sessions without any token_count events should convert fine."""
        events = [
            _mk_session_meta(),
            _mk_user_msg(),
            _mk_assistant_msg(),
        ]
        converter = Converter(events)
        session = converter.convert()
        assert session is not None
        output = session.to_dict()
        assert len(output["messages"]) == 2  # user + assistant

    def test_fixture_has_no_cumulative_inflation(self):
        """Fixture: verify token totals are not cumulative (no massive numbers)."""
        fixture = Path(__file__).parent / "fixtures" / "minimal_session.jsonl"
        result = convert_file(str(fixture))
        assert result is not None

        output = result.to_dict()
        step_parts = [
            p
            for m in output["messages"]
            for p in m["parts"]
            if p.get("type") == "step-finish" and "tokens" in p
        ]
        for p in step_parts:
            total = p["tokens"]["total"]
            assert total < 500_000, f"Token total too large (likely cumulative): {total}"
