import json
from pathlib import Path
from apotheosession.converter import convert_file


def test_convert_minimal_session():
    fixture = Path(__file__).parent / "fixtures" / "minimal_session.jsonl"
    result = convert_file(str(fixture))
    assert result is not None
    d = result.to_dict()

    assert "info" in d
    assert "messages" in d
    assert len(d["messages"]) > 0

    info = d["info"]
    assert info["title"] != ""
    assert info["directory"] == "C:\\Users\\PC\\project"
    assert info["projectID"] == "global"
    assert info["id"].startswith("ses_codex_")
    assert info["slug"].startswith("codex-")
    assert info["model"]["providerID"] == "deepseek"
    assert info["model"]["id"] == "deepseek-v4-pro"
    assert info["model"]["variant"] == "default"

    session_id = info["id"]
    msgs = d["messages"]
    assert msgs[0]["info"]["role"] == "user"
    assert msgs[0]["parts"][0]["text"] == "What is the capital of France?"
    assert msgs[0]["info"]["agent"] == "build"
    assert msgs[0]["info"]["sessionID"] == session_id
    assert "model" in msgs[0]["info"]
    assert msgs[0]["info"]["model"]["providerID"] == "deepseek"
    assert msgs[0]["info"]["model"]["modelID"] == "deepseek-v4-pro"
    assert msgs[0]["info"]["summary"] == {"diffs": []}

    assert msgs[1]["info"]["role"] == "assistant"
    assert msgs[1]["info"]["parentID"] == msgs[0]["info"]["id"]
    assert msgs[1]["info"]["sessionID"] == session_id
    assert msgs[1]["info"]["agent"] == "build"
    assert msgs[1]["info"]["mode"] == "build"
    assert msgs[1]["info"]["modelID"] == "deepseek-v4-pro"
    assert msgs[1]["info"]["providerID"] == "deepseek"
    assert msgs[1]["info"]["variant"] == "default"
    assert msgs[1]["info"]["finish"] == "stop"
    assert "path" in msgs[1]["info"]
    assert "tokens" in msgs[1]["info"]
    assert "cost" in msgs[1]["info"]

    parts = msgs[1]["parts"]
    texts = [p["text"] for p in parts if p.get("type") == "text"]
    reasoning = [p for p in parts if p.get("type") == "reasoning"]
    assert any("Paris" in t for t in texts)
    assert len(reasoning) == 1
    assert "encrypted" in reasoning[0]["text"]
    assert "time" in reasoning[0]


def test_convert_file_with_tool_call():
    fixture = Path(__file__).parent / "fixtures" / "tool_call_session.jsonl"
    result = convert_file(str(fixture))
    assert result is not None
    d = result.to_dict()
    session_id = d["info"]["id"]
    msgs = d["messages"]

    for m in msgs:
        assert m["info"]["sessionID"] == session_id, f"message sessionID mismatch: {m['info']['sessionID']} != {session_id}"

    tool_parts = [p for m in msgs for p in m["parts"] if p.get("type") == "tool"]
    assert len(tool_parts) >= 1
    assert tool_parts[0]["state"]["status"] == "completed"
    assert "input" in tool_parts[0]["state"]
    assert "metadata" in tool_parts[0]["state"]
    assert "time" in tool_parts[0]["state"]
    assert "README.md" in tool_parts[0]["state"].get("output", "")


def test_convert_invalid_file():
    result = convert_file("nonexistent.jsonl")
    assert result is None


def test_convert_empty_file():
    import tempfile, os
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        fpath = f.name
    try:
        result = convert_file(fpath)
        assert result is None
    finally:
        os.unlink(fpath)


def test_tool_output_array_is_serialized():
    """function_call_output with array payload.output must be JSON-serialized to string."""
    from apotheosession.converter import Converter

    events = [
        {
            "type": "session_meta",
            "payload": {
                "id": "019ee59a-16ea-7ce1-9eaf-522cdfe63705",
                "timestamp": "2026-06-20T23:13:30Z",
                "cwd": "/tmp",
                "model_provider": "ccswitch",
            },
        },
        {
            "type": "response_item",
            "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "do it"}]},
        },
        {
            "type": "response_item",
            "payload": {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "ok"}]},
        },
        {
            "type": "response_item",
            "payload": {"type": "function_call", "name": "automation_update", "arguments": "{}", "call_id": "call_1"},
        },
        {
            "type": "response_item",
            "payload": {
                "type": "function_call_output",
                "call_id": "call_1",
                "output": [
                    {"type": "input_text", "text": "Done."},
                    {"type": "input_text", "text": '{"id":1}'},
                ],
            },
        },
    ]
    converter = Converter(events)
    session = converter.convert()
    output = session.to_dict()

    tool_parts = [p for m in output["messages"] for p in m["parts"] if p.get("type") == "tool"]
    assert len(tool_parts) == 1
    state_output = tool_parts[0]["state"]["output"]
    assert isinstance(state_output, str), f"expected str, got {type(state_output).__name__}"
    assert "Done." in state_output
    # Inner JSON string will be properly escaped by json.dumps
    import json as _json
    parsed = _json.loads(state_output)
    assert parsed[1]["text"] == '{"id":1}'
