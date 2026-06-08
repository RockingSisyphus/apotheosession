from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from apotheosession.filters import is_user_message_text
from apotheosession.models import (
    OpenCodeInfo,
    OpenCodeMessage,
    OpenCodeSession,
    _new_id,
)
from apotheosession.opencode_schema import (
    build_info,
    make_assistant_message,
    make_file_part,
    make_reasoning_part,
    make_step_finish_part,
    make_text_part,
    make_tool_part,
    make_user_message,
)


def _load_events(filepath: str) -> list[dict]:
    events = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return events


def convert_file(filepath: str) -> OpenCodeSession | None:
    if not os.path.isfile(filepath):
        return None

    events = _load_events(filepath)
    if not events:
        return None

    if events[0].get("type") != "session_meta":
        return None

    return Converter(events).convert()


class Converter:
    """Sequential state machine for Codex -> OpenCode conversion."""

    def __init__(self, events: list[dict]):
        self.events = events
        self.idx = 0
        self.state: str = "IDLE"
        self.session_meta: dict | None = None
        self.turn_contexts: list[dict] = []
        self.session_id = _new_id("ses")  # fallback, overridden by _handle_session_meta

        self.current_user_msg: OpenCodeMessage | None = None
        self.current_assistant_msg: OpenCodeMessage | None = None
        self.pending_tools: dict[str, dict] = {}
        self.messages: list[OpenCodeMessage] = []

        self._has_reasoning: bool = False
        self._title: str = ""
        self._first_user_text: str = ""
        self._last_timestamp: str = ""
        self._model_provider: str = ""
        self._model_id: str = ""

    def convert(self) -> OpenCodeSession:
        while self.idx < len(self.events):
            event = self.events[self.idx]
            self.idx += 1
            self._last_timestamp = event.get("timestamp", "")
            self._dispatch(event)
        self._finalize()
        return self._build_session()

    def _dispatch(self, event: dict) -> None:
        etype = event.get("type", "")
        payload = event.get("payload", {})

        if etype == "session_meta":
            self._handle_session_meta(payload)
        elif etype == "turn_context":
            self.turn_contexts.append(payload)
            if not self._model_id and payload.get("model"):
                self._model_id = payload["model"]
        elif etype == "event_msg":
            self._handle_event_msg(payload)
        elif etype == "response_item":
            self._handle_response_item(payload)

    def _handle_session_meta(self, payload: dict) -> None:
        self.session_meta = payload
        self._model_provider = payload.get("model_provider", "")
        codex_uuid = payload.get("id", "")
        codex_short = codex_uuid.replace("-", "")[:12] if codex_uuid else ""
        if codex_short:
            self.session_id = f"ses_codex_{codex_short}"
        self.state = "IDLE"

    def _handle_event_msg(self, payload: dict) -> None:
        msg_type = payload.get("type", "")

        if msg_type == "task_started":
            self.state = "IN_TURN"

        elif msg_type == "task_complete":
            self._finalize_turn()
            self.state = "IDLE"

        elif msg_type == "turn_aborted":
            if self.current_assistant_msg:
                self.current_assistant_msg.info["finish"] = "error"
            self._finalize_turn()
            self.state = "IDLE"

        elif msg_type == "token_count":
            usage = payload.get("info", {}).get("total_token_usage", {})
            if usage and self.current_assistant_msg:
                part = make_step_finish_part(
                    session_id=self.session_id,
                    message_id=self.current_assistant_msg.info["id"],
                    input_t=usage.get("input_tokens", 0),
                    output_t=usage.get("output_tokens", 0),
                    reasoning_t=usage.get("reasoning_output_tokens", 0),
                    cache_read=usage.get("cached_input_tokens", 0),
                    total=usage.get("total_tokens", 0),
                )
                self.current_assistant_msg.parts.append(part)

        elif msg_type == "exec_command_end":
            call_id = payload.get("call_id", "")
            if call_id in self.pending_tools:
                tool = self.pending_tools[call_id]
                stdout = payload.get("stdout", "")
                stderr = payload.get("stderr", "")
                parts = [s for s in [stdout, stderr] if s]
                merged = "\n".join(parts) if parts else ""
                now = int(time.time() * 1000)
                tool["state"]["status"] = "completed"
                if payload.get("command"):
                    tool["state"]["input"] = {
                        "command": payload["command"],
                        "cwd": payload.get("cwd", ""),
                    }
                if merged:
                    tool["state"]["output"] = merged
                tool["state"]["title"] = f"Ran command (exit {payload.get('exit_code', '?')})"
                tool["state"]["metadata"] = tool["state"].get("metadata", {})
                tool["state"]["time"] = {"start": now, "end": now}
                if payload.get("status") == "completed" and payload.get("exit_code", 0) != 0:
                    tool["state"]["title"] = f"Command failed (exit {payload.get('exit_code')})"

        elif msg_type == "patch_apply_end":
            if self.current_assistant_msg:
                changes = payload.get("changes", {})
                for path in changes:
                    part = make_file_part(
                        filename=path,
                        session_id=self.session_id,
                        message_id=self.current_assistant_msg.info["id"],
                    )
                    self.current_assistant_msg.parts.append(part)

        elif msg_type == "error":
            err_msg = payload.get("message", "Unknown error")
            if self.current_assistant_msg:
                error_part = {
                    "type": "tool",
                    "id": _new_id("prt"),
                    "sessionID": self.session_id,
                    "messageID": self.current_assistant_msg.info["id"],
                    "callID": f"error_{_new_id('call')[5:]}",
                    "tool": "unknown",
                    "state": {"status": "error", "error": err_msg},
                }
                self.current_assistant_msg.parts.append(error_part)

    def _handle_response_item(self, payload: dict) -> None:
        rtype = payload.get("type", "")

        if rtype == "message":
            role = payload.get("role", "")
            content = payload.get("content", [])

            if role == "user":
                text = self._extract_text(content)
                if text and is_user_message_text(text):
                    if not self._first_user_text:
                        self._first_user_text = text[:60]
                    cwd = self.session_meta.get("cwd", "") if self.session_meta else ""
                    self.current_user_msg = make_user_message(
                        text, self.session_id,
                        agent="codex",
                        model_provider=self._model_provider,
                        model_id=self._model_id,
                    )
                    self.messages.append(self.current_user_msg)
                    self.state = "USER_MSG"

            elif role == "assistant":
                parent_id = self.current_user_msg.info["id"] if self.current_user_msg else ""
                cwd = self.session_meta.get("cwd", "") if self.session_meta else ""
                self.current_assistant_msg = make_assistant_message(
                    parent_id, self.session_id,
                    agent="codex",
                    model_id=self._model_id,
                    provider_id=self._model_provider,
                    cwd=cwd,
                )
                if self._has_reasoning:
                    part = make_reasoning_part(
                        self.current_assistant_msg.info["id"], self.session_id
                    )
                    self.current_assistant_msg.parts.append(part)
                    self._has_reasoning = False
                text = self._extract_text(content)
                if text:
                    part = make_text_part(text, self.current_assistant_msg.info["id"], self.session_id)
                    self.current_assistant_msg.parts.append(part)
                self.messages.append(self.current_assistant_msg)
                self.state = "AGENT_MSG"

        elif rtype == "reasoning":
            self._has_reasoning = True

        elif rtype == "function_call":
            name = payload.get("name", "shell_command")
            arguments = payload.get("arguments", "{}")
            call_id = payload.get("call_id", _new_id("call"))

            if self.current_assistant_msg:
                tool = make_tool_part(
                    call_id=call_id,
                    message_id=self.current_assistant_msg.info["id"],
                    session_id=self.session_id,
                    raw=arguments,
                    tool_name=name,
                )
                self.current_assistant_msg.parts.append(tool)
                self.pending_tools[call_id] = tool
                self.state = "TOOL_WAITING"

        elif rtype == "function_call_output":
            call_id = payload.get("call_id", "")
            output = payload.get("output", "")
            if call_id in self.pending_tools:
                now = int(time.time() * 1000)
                tool = self.pending_tools[call_id]
                tool["state"]["status"] = "completed"
                tool["state"]["output"] = output
                tool["state"]["title"] = "Command output received"
                tool["state"]["metadata"] = tool["state"].get("metadata", {})
                tool["state"]["input"] = tool["state"].get("input", {})
                tool["state"]["time"] = {"start": tool["state"].get("time", {}).get("start", now), "end": now}

        elif rtype == "custom_tool_call":
            name = payload.get("name", "apply_patch")
            call_id = payload.get("call_id", _new_id("call"))
            tool_input = payload.get("input", "")

            if self.current_assistant_msg:
                now = int(time.time() * 1000)
                tool = {
                    "type": "tool",
                    "id": _new_id("prt"),
                    "sessionID": self.session_id,
                    "messageID": self.current_assistant_msg.info["id"],
                    "callID": call_id,
                    "tool": name,
                    "state": {
                        "status": payload.get("status", "completed"),
                        "input": {"raw": tool_input},
                        "output": "",
                        "title": f"Ran {name}",
                        "metadata": {},
                        "time": {"start": now, "end": now},
                    },
                }
                self.current_assistant_msg.parts.append(tool)

        elif rtype == "custom_tool_call_output":
            call_id = payload.get("call_id", "")
            output_str = payload.get("output", "{}")
            if self.current_assistant_msg:
                for part in self.current_assistant_msg.parts:
                    if part.get("type") == "tool" and part.get("callID") == call_id:
                        now = int(time.time() * 1000)
                        part["state"]["status"] = "completed"
                        part["state"]["output"] = output_str
                        part["state"]["title"] = "Tool output received"
                        part["state"]["metadata"] = part["state"].get("metadata", {})
                        part["state"]["input"] = part["state"].get("input", {})
                        part["state"]["time"] = {"start": part["state"].get("time", {}).get("start", now), "end": now}

    def _extract_text(self, content: list) -> str:
        texts = []
        for item in content:
            if isinstance(item, dict) and item.get("type", "").endswith("_text"):
                texts.append(item.get("text", ""))
        return "\n".join(texts).strip()

    def _finalize_turn(self) -> None:
        self.current_user_msg = None
        self.current_assistant_msg = None
        self.pending_tools.clear()
        self._has_reasoning = False

    def _finalize(self) -> None:
        if self.current_assistant_msg or self.current_user_msg:
            self._finalize_turn()

    def _build_session(self) -> OpenCodeSession:
        created = ""
        updated = self._last_timestamp
        if self.session_meta:
            created = self.session_meta.get("timestamp", "")

        directory = self.session_meta.get("cwd", "") if self.session_meta else ""

        title = self._first_user_text if self._first_user_text else "Codex Session"
        title = f"{title} | {created[:10]}" if created else title

        info = build_info(
            title=title,
            directory=directory,
            created_iso=created,
            updated_iso=updated,
            model_provider=self._model_provider,
            model_id=self._model_id,
        )
        info.id = self.session_id
        info.slug = f"codex-{self.session_id.replace('ses_codex_', '')}"

        return OpenCodeSession(info=info, messages=self.messages)
