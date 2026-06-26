"""End-to-end tests using synthetic Codex .jsonl fixtures."""

import json
from pathlib import Path

from apotheosession.converter import convert_file

FIXTURE = Path(__file__).parent / "fixtures" / "minimal_session.jsonl"


def test_e2e_no_codex_provider_in_output():
    """Output must not contain ccswitch or custom provider references anywhere."""
    result = convert_file(str(FIXTURE))
    assert result is not None

    raw = json.dumps(result.to_dict())
    assert "ccswitch" not in raw, "ccswitch provider leaked into output"
    assert "custom" not in raw, '"custom" provider leaked into output'
    assert '"unknown"' not in raw, '"unknown" model leaked into output'


def test_e2e_all_required_fields_present():
    """Every message must include the fields opencode needs to continue the session."""
    result = convert_file(str(FIXTURE))
    assert result is not None

    output = result.to_dict()

    info = output["info"]
    assert info["agent"] == "build"
    assert info["model"]["variant"] == "default"
    assert "providerID" in info["model"]
    assert "id" in info["model"]

    for msg in output["messages"]:
        mi = msg["info"]
        if mi["role"] == "user":
            assert mi["agent"] == "build"
            assert "summary" in mi, "user message missing summary"
            assert mi["summary"] == {"diffs": []}
            assert "model" in mi
            assert "providerID" in mi["model"]
            assert "modelID" in mi["model"]
        elif mi["role"] == "assistant":
            assert mi["agent"] == "build"
            assert mi["mode"] == "build"
            assert "finish" in mi, "assistant message missing finish"
            assert mi["finish"] in ("stop", "tool-calls")
            assert "variant" in mi, "assistant message missing variant"
            assert mi["variant"] == "default"
            assert "path" in mi
            assert "cwd" in mi["path"]
            assert "root" in mi["path"]


def test_e2e_cli_model_override():
    """--provider and --model flags should override all model references."""
    result = convert_file(str(FIXTURE), provider="anthropic", model_id="claude-4")
    assert result is not None

    output = result.to_dict()
    assert output["info"]["model"]["providerID"] == "anthropic"
    assert output["info"]["model"]["id"] == "claude-4"

    for msg in output["messages"]:
        if msg["info"]["role"] == "user":
            assert msg["info"]["model"]["providerID"] == "anthropic"
            assert msg["info"]["model"]["modelID"] == "claude-4"
        elif msg["info"]["role"] == "assistant":
            assert msg["info"]["providerID"] == "anthropic"
            assert msg["info"]["modelID"] == "claude-4"


def test_e2e_message_ids_sort_correctly():
    """Imported message IDs must use msg_000000000000<14base62> format to sort below
    opencode's native msg_<12hex><14base62> IDs and pass opencode's timestamp(id) hex parser."""
    result = convert_file(str(FIXTURE))
    assert result is not None

    output = result.to_dict()
    for msg in output["messages"]:
        mid = msg["info"]["id"]
        assert mid.startswith("msg_000000000000"), f"message ID must start with msg_000000000000, got {mid[:22]}"
        assert len(mid) == 30, f"message ID length must be 30, got {len(mid)}: {mid}"
