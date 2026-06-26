from __future__ import annotations

import dataclasses
import secrets
import string
import uuid
from typing import Any

_BASE62 = string.digits + string.ascii_uppercase + string.ascii_lowercase

__all__ = [
    "CodexEvent",
    "SessionMeta",
    "TurnContext",
    "OpenCodeInfo",
    "OpenCodeMessage",
    "OpenCodeSession",
    "new_message_id",
    "new_part_id",
]


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
    # camelCase to match OpenCode JSON schema field names
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
    # OpenCode's native format is msg_<12hex><14base62>, e.g. msg_0019f0a0e3c0XyZkLmNoPqRsTu.
    # The 12-hex encodes timestamp*4096+counter; string comparison on the ID is
    # used by MessageV2.latest() to find the latest user/assistant/finished message.
    # Using all-zero hex (timestamp 0) guarantees imported IDs always sort before
    # any OpenCode-generated ID. The 14-base62 suffix provides uniqueness.
    # Format must match exactly: msg_ + 12hex + 14base62, otherwise opencode's
    # timestamp(id) function (BigInt on the hex slice) will throw on non-hex chars
    # like / , -, or extra _.
    suffix = "".join(secrets.choice(_BASE62) for _ in range(14))
    return f"msg_000000000000{suffix}"


def new_part_id() -> str:
    return _new_id("prt")
