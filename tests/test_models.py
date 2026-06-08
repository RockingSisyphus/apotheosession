from apotheosession.models import (
    new_message_id,
    new_part_id,
    OpenCodeInfo,
    OpenCodeMessage,
    OpenCodeSession,
)


def test_new_id_prefix():
    mid = new_message_id()
    assert mid.startswith("msg_")
    assert len(mid) == 4 + 32  # "msg_" + uuid hex


def test_new_part_id_prefix():
    pid = new_part_id()
    assert pid.startswith("prt_")
    assert len(pid) == 4 + 32  # "prt_" + uuid hex


def test_opencode_info_to_dict_omits_none():
    info = OpenCodeInfo(title="test", directory="/tmp")
    d = info.to_dict()
    assert d["title"] == "test"
    assert "model" not in d
    assert "time" not in d


def test_opencode_session_to_dict():
    info = OpenCodeInfo(title="Test", directory="/tmp")
    msg = OpenCodeMessage(
        info={"role": "user", "id": "msg_1", "sessionID": "ses_1", "time": {"created": 0}},
        parts=[{"type": "text", "text": "hello", "id": "prt_1", "sessionID": "ses_1", "messageID": "msg_1"}],
    )
    session = OpenCodeSession(info=info, messages=[msg])
    d = session.to_dict()
    assert d["info"]["title"] == "Test"
    assert len(d["messages"]) == 1
    assert d["messages"][0]["parts"][0]["text"] == "hello"
