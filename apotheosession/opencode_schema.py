from __future__ import annotations

import time
from datetime import datetime, timezone

from apotheosession.models import (
    OpenCodeInfo,
    OpenCodeMessage,
    new_message_id,
    new_part_id,
    _new_id,
)


def parse_iso_timestamp(iso_str: str) -> int:
    dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    return int(dt.timestamp() * 1000)


def make_text_part(text: str, message_id: str, session_id: str) -> dict:
    return {
        "type": "text",
        "id": new_part_id(),
        "sessionID": session_id,
        "messageID": message_id,
        "text": text,
    }


def make_reasoning_part(message_id: str, session_id: str) -> dict:
    import time as _time
    now = int(_time.time() * 1000)
    return {
        "type": "reasoning",
        "id": new_part_id(),
        "sessionID": session_id,
        "messageID": message_id,
        "text": "[Reasoning encrypted — not available in export]",
        "time": {"start": now, "end": now},
    }


def make_tool_part(
    call_id: str,
    message_id: str,
    session_id: str,
    raw: str | None = None,
    output: str | None = None,
    tool_name: str = "bash",
    error: str | None = None,
) -> dict:
    import time as _time
    part_id = new_part_id()
    now = int(_time.time() * 1000)
    if error:
        state: dict = {"status": "error", "input": {}, "error": error, "time": {"start": now, "end": now}}
    elif raw:
        state = {"status": "pending", "input": {}, "raw": raw}
    elif output is not None:
        state = {
            "status": "completed",
            "input": {},
            "output": output,
            "title": f"Ran {tool_name} command",
            "metadata": {},
            "time": {"start": now, "end": now},
        }
    else:
        state = {
            "status": "completed",
            "input": {},
            "output": "",
            "title": f"Ran {tool_name} command",
            "metadata": {},
            "time": {"start": now, "end": now},
        }
    return {
        "type": "tool",
        "id": part_id,
        "sessionID": session_id,
        "messageID": message_id,
        "callID": call_id,
        "tool": tool_name,
        "state": state,
    }


def make_step_finish_part(
    session_id: str,
    message_id: str,
    input_t: int = 0,
    output_t: int = 0,
    reasoning_t: int = 0,
    cache_read: int = 0,
    cache_write: int = 0,
    total: int = 0,
    reason: str = "stop",
    cost: float = 0,
) -> dict:
    return {
        "type": "step-finish",
        "id": new_part_id(),
        "sessionID": session_id,
        "messageID": message_id,
        "reason": reason,
        "cost": cost,
        "tokens": {
            "input": input_t,
            "output": output_t,
            "reasoning": reasoning_t,
            "cache": {"read": cache_read, "write": cache_write},
            "total": total or (input_t + output_t + reasoning_t),
        },
    }


def make_file_part(filename: str, session_id: str, message_id: str) -> dict:
    file_url = "file:///" + filename.replace("\\", "/").replace(":", "")
    return {
        "type": "file",
        "id": new_part_id(),
        "sessionID": session_id,
        "messageID": message_id,
        "mime": "text/plain",
        "filename": filename,
        "url": file_url,
    }


def make_user_message(
    text: str,
    session_id: str,
    agent: str = "build",
    model_provider: str = "deepseek",
    model_id: str = "deepseek-v4-pro",
) -> OpenCodeMessage:
    msg_id = new_message_id()
    info: dict = {
        "id": msg_id,
        "sessionID": session_id,
        "role": "user",
        "time": {"created": int(time.time() * 1000)},
        "agent": agent,
        "model": {"providerID": model_provider, "modelID": model_id, "variant": "default"},
        "summary": {"diffs": []},
    }
    return OpenCodeMessage(
        info=info,
        parts=[make_text_part(text, msg_id, session_id)],
    )


def make_assistant_message(
    parent_id: str,
    session_id: str,
    agent: str = "build",
    model_id: str = "deepseek-v4-pro",
    provider_id: str = "deepseek",
    cwd: str = "",
    finish: str = "stop",
) -> OpenCodeMessage:
    msg_id = new_message_id()
    return OpenCodeMessage(
        info={
            "id": msg_id,
            "sessionID": session_id,
            "role": "assistant",
            "parentID": parent_id,
            "time": {"created": int(time.time() * 1000)},
            "agent": agent,
            "mode": "build",
            "variant": "default",
            "modelID": model_id,
            "providerID": provider_id,
            "path": {"cwd": cwd or "", "root": cwd or "/"},
            "cost": 0,
            "finish": finish,
            "tokens": {
                "total": 0,
                "input": 0,
                "output": 0,
                "reasoning": 0,
                "cache": {"read": 0, "write": 0},
            },
        },
        parts=[],
    )


def build_info(
    title: str,
    directory: str,
    created_iso: str = "",
    updated_iso: str = "",
    model_provider: str = "deepseek",
    model_id: str = "deepseek-v4-pro",
) -> OpenCodeInfo:
    info = OpenCodeInfo(
        slug=f"codex-{_new_id('ses')[4:12]}",
        directory=directory,
        title=title,
        agent="build",
        model={"providerID": model_provider, "id": model_id, "variant": "default"},
    )
    if created_iso:
        created_ms = parse_iso_timestamp(created_iso)
        info.time = {"created": created_ms}
        if updated_iso:
            info.time["updated"] = parse_iso_timestamp(updated_iso)
    return info
