from __future__ import annotations

import dataclasses
import uuid
from typing import Any, Literal


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


# ── Codex JSONL event types ──────────────────────────────────


@dataclasses.dataclass
class CodexEvent:
    timestamp: str
    type: str
    payload: dict[str, Any]


@dataclasses.dataclass
class SessionMeta:
    session_id: str
    created_iso: str
    cwd: str
    model_provider: str
    cli_version: str


@dataclasses.dataclass
class TurnContext:
    turn_id: str
    cwd: str
    model: str
    timestamp: str


# ── OpenCode output types ────────────────────────────────────


@dataclasses.dataclass
class OpenCodeInfo:
    id: str = dataclasses.field(default_factory=lambda: _new_id("ses"))
    slug: str = ""
    projectID: str = "global"
    directory: str = ""
    title: str = ""
    version: str = "local"
    agent: str = "codex"
    model: dict | None = None
    time: dict | None = None

    def to_dict(self) -> dict:
        d = dataclasses.asdict(self)
        return {k: v for k, v in d.items() if v is not None}


@dataclasses.dataclass
class OpenCodeMessage:
    info: dict
    parts: list[dict]

    def to_dict(self) -> dict:
        return {"info": self.info, "parts": self.parts}


@dataclasses.dataclass
class OpenCodeSession:
    info: OpenCodeInfo
    messages: list[OpenCodeMessage]

    def to_dict(self) -> dict:
        return {
            "info": self.info.to_dict(),
            "messages": [m.to_dict() for m in self.messages],
        }


def new_message_id() -> str:
    return _new_id("msg")


def new_part_id() -> str:
    return _new_id("prt")
