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
    assert info["model"]["providerID"] == "openai"
    assert info["model"]["id"] == "gpt-5.5"

    msgs = d["messages"]
    assert msgs[0]["info"]["role"] == "user"
    assert msgs[0]["parts"][0]["text"] == "What is the capital of France?"

    assert msgs[1]["info"]["role"] == "assistant"
    assert msgs[1]["info"]["parentID"] == msgs[0]["info"]["id"]

    parts = msgs[1]["parts"]
    texts = [p["text"] for p in parts if p.get("type") == "text"]
    reasoning = [p for p in parts if p.get("type") == "reasoning"]
    assert any("Paris" in t for t in texts)
    assert len(reasoning) == 1
    assert "encrypted" in reasoning[0]["text"]


def test_convert_file_with_tool_call():
    fixture = Path(__file__).parent / "fixtures" / "tool_call_session.jsonl"
    result = convert_file(str(fixture))
    assert result is not None
    d = result.to_dict()
    msgs = d["messages"]

    tool_parts = [p for m in msgs for p in m["parts"] if p.get("type") == "tool"]
    assert len(tool_parts) >= 1
    assert tool_parts[0]["state"]["status"] == "completed"
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
