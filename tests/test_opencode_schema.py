import time
from apotheosession.opencode_schema import (
    make_text_part,
    make_reasoning_part,
    make_tool_part,
    make_step_finish_part,
    make_file_part,
    make_user_message,
    make_assistant_message,
    build_info,
    parse_iso_timestamp,
)


def test_parse_iso_timestamp():
    ts = parse_iso_timestamp("2026-05-23T10:32:34.584Z")
    assert isinstance(ts, int)
    assert ts > 1700000000000


def test_make_text_part():
    part = make_text_part("hello", "msg_1", "ses_1")
    assert part["type"] == "text"
    assert part["text"] == "hello"
    assert part["messageID"] == "msg_1"
    assert part["sessionID"] == "ses_1"


def test_make_reasoning_part():
    part = make_reasoning_part("msg_1", "ses_1")
    assert part["type"] == "reasoning"
    assert "encrypted" in part["text"]
    assert "time" in part
    assert "start" in part["time"]
    assert "end" in part["time"]


def test_make_tool_part_pending():
    part = make_tool_part("call_abc", "msg_1", "ses_1", raw='{"command":"ls"}')
    assert part["type"] == "tool"
    assert part["callID"] == "call_abc"
    assert part["state"]["status"] == "pending"
    assert "input" in part["state"]
    assert part["state"]["raw"] == '{"command":"ls"}'


def test_make_tool_part_completed():
    part = make_tool_part("call_abc", "msg_1", "ses_1", output="file1.txt\n")
    assert part["type"] == "tool"
    assert part["state"]["status"] == "completed"
    assert part["state"]["output"] == "file1.txt\n"
    assert "metadata" in part["state"]
    assert "time" in part["state"]
    assert "input" in part["state"]


def test_make_file_part():
    part = make_file_part("C:\\project\\file.ts", "ses_1", "msg_1")
    assert part["type"] == "file"
    assert part["url"].startswith("file:///")
    assert part["sessionID"] == "ses_1"
    assert part["messageID"] == "msg_1"


def test_make_step_finish_part():
    part = make_step_finish_part("ses_1", "msg_1", input_t=100, output_t=50, reason="stop")
    assert part["type"] == "step-finish"
    assert part["sessionID"] == "ses_1"
    assert part["messageID"] == "msg_1"
    assert part["cost"] == 0
    assert part["tokens"]["input"] == 100
    assert part["tokens"]["output"] == 50


def test_make_user_message():
    msg = make_user_message("hello", "ses_1", agent="test", model_provider="dp", model_id="m1")
    assert msg.info["role"] == "user"
    assert msg.info["agent"] == "test"
    assert msg.info["model"]["providerID"] == "dp"
    assert msg.info["model"]["modelID"] == "m1"
    assert msg.info["model"]["variant"] == "default"
    assert msg.info["summary"] == {"diffs": []}
    assert len(msg.parts) == 1
    assert msg.parts[0]["text"] == "hello"


def test_make_user_message_defaults():
    msg = make_user_message("hello", "ses_1")
    assert msg.info["agent"] == "build"
    assert msg.info["model"]["providerID"] == "deepseek"
    assert msg.info["model"]["modelID"] == "deepseek-v4-pro"
    assert msg.info["model"]["variant"] == "default"
    assert msg.info["summary"] == {"diffs": []}


def test_make_assistant_message():
    msg = make_assistant_message("parent_1", "ses_1", agent="test", model_id="m1", provider_id="dp", cwd="/project")
    assert msg.info["role"] == "assistant"
    assert msg.info["parentID"] == "parent_1"
    assert msg.info["agent"] == "test"
    assert msg.info["modelID"] == "m1"
    assert msg.info["providerID"] == "dp"
    assert msg.info["mode"] == "build"
    assert msg.info["variant"] == "default"
    assert msg.info["finish"] == "stop"
    assert msg.info["path"]["cwd"] == "/project"
    assert msg.info["path"]["root"] == "/project"
    assert "cost" in msg.info
    assert "tokens" in msg.info


def test_make_assistant_message_defaults():
    msg = make_assistant_message("p1", "ses_1")
    assert msg.info["agent"] == "build"
    assert msg.info["modelID"] == "deepseek-v4-pro"
    assert msg.info["providerID"] == "deepseek"
    assert msg.info["variant"] == "default"
    assert msg.info["finish"] == "stop"
    assert msg.info["path"]["cwd"] == ""
    assert msg.info["path"]["root"] == "/"


def test_build_info_minimal():
    info = build_info(title="Test", directory="/tmp")
    assert info.title == "Test"
    assert info.directory == "/tmp"
    assert info.projectID == "global"
