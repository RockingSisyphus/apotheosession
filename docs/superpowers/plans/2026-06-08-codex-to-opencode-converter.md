# Codex-to-OpenCode Converter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Python script that recursively scans Codex CLI session `.jsonl` files and converts each to an OpenCode-importable `.json` file.

**Architecture:** Sequential state machine — single-pass event processor. Zero external dependencies (stdlib + pytest for testing). Package `apotheosession` with `conveter.py` as core, `models.py` for type definitions, `main.py` for CLI orchestration.

**Tech Stack:** Python 3.10+, pytest, uv.

**Project Structure:**
```
apotheosession/
  __init__.py
  __main__.py          # python -m apotheosession entry
  main.py              # CLI argument parsing + directory scanner
  converter.py         # State machine converter (core)
  models.py            # Dataclasses for both formats
  opencode_schema.py   # OpenCode JSON builders
  filters.py           # Message/content filters
tests/
  fixtures/            # Sample .jsonl files
  test_models.py
  test_filters.py
  test_converter.py
  test_main.py
```

---

### Task 1: Project scaffolding and pyproject.toml

**Files:**
- Create: `apotheosession/__init__.py`
- Create: `apotheosession/__main__.py`
- Modify: `pyproject.toml`
- Delete: `main.py` (root-level uv-generated file)

- [ ] **Step 1: Write `apotheosession/__init__.py`**

```python
```

- [ ] **Step 2: Write `apotheosession/__main__.py`**

```python
from .main import main

main()
```

- [ ] **Step 3: Delete root `main.py`**

```bash
Remove-Item -LiteralPath "main.py"
```

- [ ] **Step 4: Update `pyproject.toml`**

```toml
[project]
name = "apotheosession"
version = "0.1.0"
description = "Convert Codex CLI session files to OpenCode import format"
readme = "README.md"
requires-python = ">=3.10"
dependencies = []

[dependency-groups]
dev = [
    "pytest>=9.0.3",
    "pytest-cov>=7.1.0",
]

[tool.setuptools.packages.find]
include = ["apotheosession*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 5: Verify package imports**

Run: `uv run python -c "import apotheosession; print('ok')"`
Expected: prints "ok"

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml apotheosession/ tests/
git rm main.py
git commit -m "chore: scaffold apotheosession package with uv"
```

---

### Task 2: Write data models (models.py)

**Files:**
- Create: `apotheosession/models.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: Write models.py with Codex event types and OpenCode target types**

```python
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
```

- [ ] **Step 2: Write tests/test_models.py**

```python
from apotheosession.models import (
    _new_id,
    new_message_id,
    new_part_id,
    OpenCodeInfo,
    OpenCodeMessage,
    OpenCodeSession,
)


def test_new_id_prefix():
    mid = new_message_id()
    assert mid.startswith("msg_")
    assert len(mid) > 4


def test_new_part_id_prefix():
    pid = new_part_id()
    assert pid.startswith("prt_")
    assert len(pid) > 4


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
```

- [ ] **Step 3: Run tests to verify they fail initially (no models module yet)**

Run: `uv run pytest tests/test_models.py -v`
Expected: ImportError (module not found)

- [ ] **Step 4: Create the models file (already done in Step 1)**

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_models.py -v`
Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add apotheosession/models.py tests/test_models.py
git commit -m "feat: add data models for Codex and OpenCode types"
```

---

### Task 3: Filters module

**Files:**
- Create: `apotheosession/filters.py`
- Test: `tests/test_filters.py`

- [ ] **Step 1: Write tests/test_filters.py**

```python
from apotheosession.filters import is_environment_context, is_user_message_text


def test_is_environment_context_detects_xml_block():
    text = "<environment_context>\n  <cwd>/tmp</cwd>\n</environment_context>"
    assert is_environment_context(text)


def test_is_environment_context_false_for_normal_text():
    assert not is_environment_context("hello world")


def test_is_user_message_text_skips_env_context():
    env = "<environment_context><cwd>/tmp</cwd></environment_context>"
    assert not is_user_message_text(env)


def test_is_user_message_text_skips_instructions():
    text = "<InstructionsForCodex>\nDo this\n</InstructionsForCodex>"
    assert not is_user_message_text(text)


def test_is_user_message_text_accepts_normal():
    assert is_user_message_text("What does this function do?")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_filters.py -v`
Expected: 4 failed (ImportError / function not found)

- [ ] **Step 3: Write filters.py**

```python
_ENV_CONTEXT_MARKERS = ["<environment_context>", "<InstructionsForCodex>"]


def is_environment_context(text: str) -> bool:
    return any(marker in text for marker in _ENV_CONTEXT_MARKERS)


def is_user_message_text(text: str) -> bool:
    return not is_environment_context(text)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_filters.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add apotheosession/filters.py tests/test_filters.py
git commit -m "feat: add message filters for Codex internal blocks"
```

---

### Task 4: OpenCode schema builders

**Files:**
- Create: `apotheosession/opencode_schema.py`
- Test: `tests/test_opencode_schema.py`

- [ ] **Step 1: Write tests/test_opencode_schema.py**

```python
import time
from apotheosession.opencode_schema import (
    make_text_part,
    make_reasoning_part,
    make_tool_part,
    make_step_finish_part,
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


def test_make_tool_part_pending():
    part = make_tool_part("call_abc", "msg_1", "ses_1", raw='{"command":"ls"}')
    assert part["type"] == "tool"
    assert part["callID"] == "call_abc"
    assert part["state"]["status"] == "pending"


def test_make_tool_part_completed():
    part = make_tool_part("call_abc", "msg_1", "ses_1", output="file1.txt\n")
    assert part["type"] == "tool"
    assert part["state"]["status"] == "completed"
    assert part["state"]["output"] == "file1.txt\n"


def test_make_step_finish_part():
    part = make_step_finish_part(input_t=100, output_t=50, reason="stop")
    assert part["type"] == "step-finish"
    assert part["tokens"]["input"] == 100
    assert part["tokens"]["output"] == 50


def test_make_user_message():
    msg = make_user_message("hello", "ses_1")
    assert msg.info["role"] == "user"
    assert len(msg.parts) == 1
    assert msg.parts[0]["text"] == "hello"


def test_make_assistant_message():
    msg = make_assistant_message("parent_1", "ses_1")
    assert msg.info["role"] == "assistant"
    assert msg.info["parentID"] == "parent_1"


def test_build_info_minimal():
    info = build_info(title="Test", directory="/tmp")
    assert info.title == "Test"
    assert info.directory == "/tmp"
    assert info.projectID == "global"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_opencode_schema.py -v`
Expected: 9 failed (ImportError)

- [ ] **Step 3: Write opencode_schema.py**

```python
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
    return {
        "type": "reasoning",
        "id": new_part_id(),
        "sessionID": session_id,
        "messageID": message_id,
        "text": "[Reasoning encrypted — not available in export]",
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
    part_id = new_part_id()
    if error:
        state = {"status": "error", "error": error}
    elif raw:
        state = {"status": "pending", "raw": raw}
    elif output is not None:
        state = {"status": "completed", "output": output, "title": f"Ran {tool_name} command"}
    else:
        state = {"status": "completed"}
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
    input_t: int = 0,
    output_t: int = 0,
    reasoning_t: int = 0,
    cache_read: int = 0,
    cache_write: int = 0,
    total: int = 0,
    reason: str = "stop",
) -> dict:
    return {
        "type": "step-finish",
        "id": new_part_id(),
        "reason": reason,
        "tokens": {
            "input": input_t,
            "output": output_t,
            "reasoning": reasoning_t,
            "cache": {"read": cache_read, "write": cache_write},
            "total": total or (input_t + output_t + reasoning_t),
        },
    }


def make_file_part(filename: str, session_id: str, message_id: str) -> dict:
    return {
        "type": "file",
        "id": new_part_id(),
        "sessionID": session_id,
        "messageID": message_id,
        "mime": "text/plain",
        "filename": filename,
    }


def make_user_message(text: str, session_id: str) -> OpenCodeMessage:
    msg_id = new_message_id()
    return OpenCodeMessage(
        info={
            "id": msg_id,
            "sessionID": session_id,
            "role": "user",
            "time": {"created": int(time.time() * 1000)},
        },
        parts=[make_text_part(text, msg_id, session_id)],
    )


def make_assistant_message(parent_id: str, session_id: str) -> OpenCodeMessage:
    msg_id = new_message_id()
    return OpenCodeMessage(
        info={
            "id": msg_id,
            "sessionID": session_id,
            "role": "assistant",
            "parentID": parent_id,
            "time": {"created": int(time.time() * 1000)},
        },
        parts=[],
    )


def build_info(
    title: str,
    directory: str,
    created_iso: str = "",
    updated_iso: str = "",
    model_provider: str = "",
    model_id: str = "",
) -> OpenCodeInfo:
    info = OpenCodeInfo(
        slug=f"codex-{_new_id('ses')[4:12]}",
        directory=directory,
        title=title,
    )
    if created_iso:
        created_ms = parse_iso_timestamp(created_iso)
        info.time = {"created": created_ms}
        if updated_iso:
            info.time["updated"] = parse_iso_timestamp(updated_iso)
    if model_provider or model_id:
        info.model = {}
        if model_provider:
            info.model["providerID"] = model_provider
        if model_id:
            info.model["id"] = model_id
    return info
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_opencode_schema.py -v`
Expected: 10 passed

- [ ] **Step 5: Commit**

```bash
git add apotheosession/opencode_schema.py tests/test_opencode_schema.py
git commit -m "feat: add OpenCode JSON schema builders"
```

---

### Task 5: Core converter — state machine

**Files:**
- Create: `apotheosession/converter.py`
- Test: `tests/test_converter.py`

- [ ] **Step 1: Write tests/test_converter.py with fixture data**

First, create a minimal test fixture `tests/fixtures/minimal_session.jsonl`:

```jsonl
{"timestamp":"2026-05-23T10:32:58.064Z","type":"session_meta","payload":{"id":"019e5464-d3ac-7c92-bc54-52364d981f65","timestamp":"2026-05-23T10:32:34.584Z","cwd":"C:\\Users\\PC\\project","originator":"codex-tui","cli_version":"0.125.0","source":"cli","model_provider":"openai","base_instructions":{"text":"You are Codex..."}}}
{"timestamp":"2026-05-23T10:32:58.074Z","type":"turn_context","payload":{"turn_id":"turn_001","cwd":"C:\\Users\\PC\\project","current_date":"2026-05-23","timezone":"Asia/Taipei","model":"gpt-5.5","approval_policy":"on-request","sandbox_policy":{"type":"workspace-write","writable_roots":[],"network_access":false},"permission_profile":{"type":"managed","file_system":{"type":"restricted","entries":[]},"network":"restricted"},"personality":"pragmatic","collaboration_mode":{"mode":"default","settings":{"model":"gpt-5.5","reasoning_effort":null,"developer_instructions":"# Collaboration Mode: Default\r\n..."}}}}
{"timestamp":"2026-05-23T10:32:58.084Z","type":"event_msg","payload":{"type":"task_started","turn_id":"turn_001","started_at":1779532378,"model_context_window":258400,"collaboration_mode_kind":"default"}}
{"timestamp":"2026-05-23T10:32:58.094Z","type":"response_item","payload":{"type":"message","role":"user","content":[{"type":"input_text","text":"What is the capital of France?"}]}}
{"timestamp":"2026-05-23T10:32:58.104Z","type":"response_item","payload":{"type":"reasoning","summary":[],"content":null,"encrypted_content":"gAAAAABp-FPm5mSp39LWRMOC4Hostg..."}}
{"timestamp":"2026-05-23T10:32:58.114Z","type":"event_msg","payload":{"type":"agent_message","message":"Let me think about this...","phase":"commentary"}}
{"timestamp":"2026-05-23T10:32:58.124Z","type":"response_item","payload":{"type":"message","role":"assistant","content":[{"type":"output_text","text":"The capital of France is Paris."}],"phase":"final_answer"}}
{"timestamp":"2026-05-23T10:32:58.134Z","type":"event_msg","payload":{"type":"token_count","info":{"total_token_usage":{"input_tokens":100,"cached_input_tokens":0,"output_tokens":50,"reasoning_output_tokens":30,"total_tokens":180},"last_token_usage":{"input_tokens":100,"cached_input_tokens":0,"output_tokens":50,"reasoning_output_tokens":30,"total_tokens":180},"model_context_window":258400},"rate_limits":null}}
{"timestamp":"2026-05-23T10:32:58.144Z","type":"event_msg","payload":{"type":"task_complete","turn_id":"turn_001","last_agent_message":"The capital of France is Paris.","completed_at":1779532379,"duration_ms":1500}}
```

Then write the test file:

```python
import json
from pathlib import Path
from apotheosession.converter import convert_file


def test_convert_minimal_session():
    fixture = Path(__file__).parent / "fixtures" / "minimal_session.jsonl"
    result = convert_file(str(fixture))
    assert result is not None
    d = result.to_dict()

    # Check top-level structure
    assert "info" in d
    assert "messages" in d
    assert len(d["messages"]) > 0

    # Check info
    info = d["info"]
    assert info["title"] != ""
    assert info["directory"] == "C:\\Users\\PC\\project"
    assert info["model"]["providerID"] == "openai"
    assert info["model"]["id"] == "gpt-5.5"

    # Check messages
    msgs = d["messages"]
    assert msgs[0]["info"]["role"] == "user"
    assert msgs[0]["parts"][0]["text"] == "What is the capital of France?"

    assert msgs[1]["info"]["role"] == "assistant"
    assert msgs[1]["info"]["parentID"] == msgs[0]["info"]["id"]

    # Check reasoning part exists
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

    # Find tool parts
    tool_parts = [p for m in msgs for p in m["parts"] if p.get("type") == "tool"]
    assert len(tool_parts) >= 1

    # The tool part should have completed status
    if tool_parts:
        assert tool_parts[0]["state"]["status"] in ("completed", "pending")


def test_convert_invalid_file():
    result = convert_file("nonexistent.jsonl")
    assert result is None


def test_convert_empty_file(tmp_path):
    f = tmp_path / "empty.jsonl"
    f.write_text("")
    result = convert_file(str(f))
    assert result is None
```

- [ ] **Step 2: Write tool_call_session.jsonl fixture**

```jsonl
{"timestamp":"2026-05-23T10:35:00.000Z","type":"session_meta","payload":{"id":"abc12345-0000-0000-0000-000000000000","timestamp":"2026-05-23T10:35:00.000Z","cwd":"C:\\Users\\PC\\project","originator":"codex-tui","cli_version":"0.125.0","source":"cli","model_provider":"deepseek","base_instructions":{"text":"You are Codex..."}}}
{"timestamp":"2026-05-23T10:35:00.010Z","type":"event_msg","payload":{"type":"task_started","turn_id":"turn_002","started_at":1779532500,"model_context_window":258400,"collaboration_mode_kind":"default"}}
{"timestamp":"2026-05-23T10:35:00.020Z","type":"response_item","payload":{"type":"message","role":"user","content":[{"type":"input_text","text":"List files in current directory"}]}}
{"timestamp":"2026-05-23T10:35:00.030Z","type":"response_item","payload":{"type":"message","role":"assistant","content":[{"type":"output_text","text":"I'll list the files for you."}],"phase":"commentary"}}
{"timestamp":"2026-05-23T10:35:00.040Z","type":"response_item","payload":{"type":"function_call","name":"shell_command","arguments":"{\"command\":\"Get-ChildItem -Force\",\"workdir\":\"C:\\\\Users\\\\PC\\\\project\",\"timeout_ms\":10000}","call_id":"call_abc123"}}
{"timestamp":"2026-05-23T10:35:01.000Z","type":"event_msg","payload":{"type":"exec_command_end","call_id":"call_abc123","turn_id":"turn_002","command":["pwsh.exe","-Command","Get-ChildItem -Force"],"cwd":"C:\\Users\\PC\\project","source":"agent","stdout":"README.md\n","stderr":"","aggregated_output":"README.md\n","exit_code":0,"duration":{"secs":1,"nanos":0},"status":"completed"}}
{"timestamp":"2026-05-23T10:35:01.010Z","type":"response_item","payload":{"type":"function_call_output","call_id":"call_abc123","output":"Exit code: 0\nWall time: 1 seconds\nOutput:\nREADME.md\n"}}
{"timestamp":"2026-05-23T10:35:01.020Z","type":"response_item","payload":{"type":"message","role":"assistant","content":[{"type":"output_text","text":"Here's what I found: README.md"}],"phase":"final_answer"}}
{"timestamp":"2026-05-23T10:35:01.030Z","type":"event_msg","payload":{"type":"task_complete","turn_id":"turn_002","last_agent_message":"Here's what I found: README.md","completed_at":1779532501,"duration_ms":1030}}
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_converter.py -v`
Expected: 4 failed (ImportError — converter module doesn't exist yet)

- [ ] **Step 4: Write converter.py**

```python
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
    parse_iso_timestamp,
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

    # Validate first event is session_meta
    if events[0].get("type") != "session_meta":
        return None

    return Converter(events).convert()


class Converter:
    """Sequential state machine for Codex → OpenCode conversion."""

    def __init__(self, events: list[dict]):
        self.events = events
        self.idx = 0
        # State
        self.state: str = "IDLE"
        self.session_meta: dict | None = None
        self.turn_contexts: list[dict] = []
        self.session_id = _new_id("ses")

        # Tracked during turns
        self.current_user_msg: OpenCodeMessage | None = None
        self.current_assistant_msg: OpenCodeMessage | None = None
        self.pending_tools: dict[str, dict] = {}  # call_id -> tool part (mutated in-place)
        self.messages: list[OpenCodeMessage] = []

        # Metadata
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
                    input_t=usage.get("input_tokens", 0),
                    output_t=usage.get("output_tokens", 0),
                    reasoning_t=usage.get("reasoning_output_tokens", 0),
                    cache_read=usage.get("cached_input_tokens", 0),
                    total=usage.get("total_tokens", 0),
                )
                part["sessionID"] = self.session_id
                part["messageID"] = self.current_assistant_msg.info["id"]
                self.current_assistant_msg.parts.append(part)

        elif msg_type == "exec_command_end":
            call_id = payload.get("call_id", "")
            if call_id in self.pending_tools:
                tool = self.pending_tools[call_id]
                stdout = payload.get("stdout", "")
                stderr = payload.get("stderr", "")
                merged = stdout + stderr
                tool["state"]["status"] = "completed"
                if payload.get("command"):
                    tool["state"]["input"] = {
                        "command": payload["command"],
                        "cwd": payload.get("cwd", ""),
                    }
                if merged:
                    tool["state"]["output"] = merged
                tool["state"]["title"] = f"Ran command (exit {payload.get('exit_code', '?')})"
                tool["state"]["time"] = {
                    "start": 0,
                    "end": int(time.time() * 1000),
                }
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
                    self.current_user_msg = make_user_message(text, self.session_id)
                    self.messages.append(self.current_user_msg)
                    self.state = "USER_MSG"

            elif role == "assistant":
                parent_id = self.current_user_msg.info["id"] if self.current_user_msg else ""
                self.current_assistant_msg = make_assistant_message(parent_id, self.session_id)
                text = self._extract_text(content)
                if text:
                    part = make_text_part(text, self.current_assistant_msg.info["id"], self.session_id)
                    self.current_assistant_msg.parts.append(part)
                self.messages.append(self.current_assistant_msg)
                self.state = "AGENT_MSG"

        elif rtype == "reasoning":
            if self.current_assistant_msg:
                part = make_reasoning_part(
                    self.current_assistant_msg.info["id"], self.session_id
                )
                self.current_assistant_msg.parts.append(part)

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
                tool = self.pending_tools[call_id]
                tool["state"]["status"] = "completed"
                tool["state"]["output"] = output
                tool["state"]["title"] = "Command output received"

        elif rtype == "custom_tool_call":
            name = payload.get("name", "apply_patch")
            call_id = payload.get("call_id", _new_id("call"))
            tool_input = payload.get("input", "")

            if self.current_assistant_msg:
                tool = {
                    "type": "tool",
                    "id": _new_id("prt"),
                    "sessionID": self.session_id,
                    "messageID": self.current_assistant_msg.info["id"],
                    "callID": call_id,
                    "tool": name,
                    "state": {
                        "status": payload.get("status", "completed"),
                        "input": tool_input,
                    },
                }
                self.current_assistant_msg.parts.append(tool)

        elif rtype == "custom_tool_call_output":
            call_id = payload.get("call_id", "")
            output_str = payload.get("output", "{}")
            # Find matching tool by call_id and update output
            if self.current_assistant_msg:
                for part in self.current_assistant_msg.parts:
                    if part.get("type") == "tool" and part.get("callID") == call_id:
                        part["state"]["output"] = output_str
                        part["state"]["status"] = "completed"
                        part["state"]["title"] = "Tool output received"

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

    def _finalize(self) -> None:
        if self.current_assistant_msg or self.current_user_msg:
            self._finalize_turn()

    def _build_session(self) -> OpenCodeSession:
        created = ""
        updated = self._last_timestamp
        directory = ""
        if self.session_meta:
            created = self.session_meta.get("timestamp", "")

        if self.session_meta and self.session_meta.get("cwd"):
            directory = self.session_meta["cwd"]

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

        return OpenCodeSession(info=info, messages=self.messages)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_converter.py -v`
Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add apotheosession/converter.py tests/test_converter.py tests/fixtures/
git commit -m "feat: add core converter state machine"
```

---

### Task 6: CLI entry point and directory scanner (main.py)

**Files:**
- Create: `apotheosession/main.py`
- Test: `tests/test_main.py`

- [ ] **Step 1: Write tests/test_main.py**

```python
import json
from pathlib import Path
from apotheosession.main import parse_args, scan_directory, write_output


def test_parse_args_defaults():
    args = parse_args([])
    assert args.input is not None
    assert args.output is not None
    assert not args.flatten
    assert not args.dry_run


def test_parse_args_custom():
    args = parse_args(["--input", "/custom/in", "--output", "/custom/out", "--flatten", "--dry-run"])
    assert args.input == "/custom/in"
    assert args.output == "/custom/out"
    assert args.flatten
    assert args.dry_run


def test_scan_directory_no_such_path():
    results = scan_directory("/nonexistent/path")
    assert results == []


def test_scan_directory_finds_jsonl(tmp_path):
    sub = tmp_path / "2026" / "05" / "23"
    sub.mkdir(parents=True)
    f = sub / "rollout-2026-05-23T10-00-00-test.jsonl"
    f.write_text('{"timestamp":"2026-05-23T10:00:00Z","type":"session_meta","payload":{"id":"abc","timestamp":"2026-05-23T10:00:00Z","cwd":"/tmp","originator":"codex-tui","cli_version":"0.125.0","source":"cli","model_provider":"openai","base_instructions":{"text":"test"}}}\n')
    results = scan_directory(str(tmp_path))
    assert len(results) == 1
    assert results[0][0].endswith(".jsonl")


def test_scan_directory_skips_non_jsonl(tmp_path):
    (tmp_path / "readme.txt").write_text("hello")
    results = scan_directory(str(tmp_path))
    assert results == []


def test_write_output(tmp_path):
    out_dir = tmp_path / "out"
    data = {"info": {"title": "test"}, "messages": []}
    path = write_output(data, str(out_dir), "2026", "05", "23", "test-slug")
    assert path.exists()
    with open(path) as f:
        assert json.load(f)["info"]["title"] == "test"


def test_write_output_flatten(tmp_path):
    out_dir = tmp_path / "flat"
    data = {"info": {"title": "test"}, "messages": []}
    path = write_output(data, str(out_dir), "2026", "05", "23", "test-slug", flatten=True)
    assert path.exists()
    assert "2026" not in str(path)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_main.py -v`
Expected: 6 failed (ImportError — main doesn't have these functions yet)

- [ ] **Step 3: Write main.py**

```python
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert Codex CLI sessions to OpenCode format")
    parser.add_argument(
        "--input",
        default=os.path.expanduser("~/.codex/sessions/"),
        help="Codex sessions directory (default: ~/.codex/sessions/)",
    )
    parser.add_argument(
        "--output",
        default="./converted/",
        help="Output directory (default: ./converted/)",
    )
    parser.add_argument("--flatten", action="store_true", help="Write all .json files flat")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be converted")
    return parser.parse_args(argv)


def scan_directory(input_dir: str) -> list[tuple[str, str, str, str, str]]:
    """Scan input directory for .jsonl files.
    
    Returns list of (filepath, year, month, day, slug) tuples.
    """
    results = []
    root = Path(input_dir)
    if not root.exists():
        return results

    for fpath in root.rglob("*.jsonl"):
        # Read first line to validate and extract date
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                first_line = f.readline().strip()
            if not first_line:
                continue
            import json as _json
            meta = _json.loads(first_line)
            if meta.get("type") != "session_meta":
                continue
            payload = meta.get("payload", {})
            ts = payload.get("timestamp", "")
            session_id = payload.get("id", fpath.stem)
            date_part = ts[:10] if ts else "unknown"
            slug = f"codex-{date_part}-{session_id[:8]}"
            year, month, day = date_part.split("-") if "-" in date_part else ("unknown", "unknown", "unknown")
            results.append((str(fpath), year, month, day, slug))
        except Exception:
            continue

    return results


def write_output(
    data: dict,
    out_dir: str,
    year: str,
    month: str,
    day: str,
    slug: str,
    flatten: bool = False,
) -> Path:
    if flatten:
        out_path = Path(out_dir) / f"{slug}.json"
    else:
        out_path = Path(out_dir) / year / month / day / f"{slug}.json"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return out_path


def main() -> None:
    args = parse_args()

    from apotheosession.converter import convert_file

    files = scan_directory(args.input)
    if not files:
        print(f"No valid Codex session files found in {args.input}", file=sys.stderr)
        sys.exit(1)

    total = len(files)
    converted = 0
    skipped = 0

    for filepath, year, month, day, slug in files:
        if args.dry_run:
            print(f"[DRY RUN] Would convert: {filepath} -> {slug}.json")
            continue

        result = convert_file(filepath)
        if result is None:
            print(f"ERROR: Failed to convert {filepath}", file=sys.stderr)
            skipped += 1
            continue

        data = result.to_dict()
        out_path = write_output(data, args.output, year, month, day, slug, flatten=args.flatten)
        print(f"Converted: {filepath} -> {out_path}")
        converted += 1

    if not args.dry_run:
        print(f"\nDone: {converted} converted, {skipped} skipped, {total} total")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_main.py -v`
Expected: 6 passed

- [ ] **Step 5: Write README.md with usage documentation**

```markdown
# Apotheosession

Convert Codex CLI session files to OpenCode import format.

## Usage

```bash
# Convert all sessions from default Codex directory
uv run python -m apotheosession

# Custom input/output directories
uv run python -m apotheosession --input ~/.codex/sessions/ --output ./converted/

# Flat output (no YYYY/MM/DD hierarchy)
uv run python -m apotheosession --flatten

# Dry run
uv run python -m apotheosession --dry-run
```

Then import into OpenCode:
```bash
opencode import converted/2026/05/23/codex-2026-05-23-abc12345.json
```

## Development

```bash
uv sync
uv run pytest
```
```

- [ ] **Step 6: Commit**

```bash
git add apotheosession/main.py apotheosession/__main__.py tests/test_main.py README.md
git commit -m "feat: add CLI entry point and directory scanner"
```

---

### Task 7: End-to-end integration and final verification

**Files:** None new — run all tests and verify with real data.

- [ ] **Step 1: Run full test suite**

Run: `uv run pytest -v`
Expected: All ~19 tests pass

- [ ] **Step 2: Run coverage**

Run: `uv run pytest --cov=apotheosession`
Expected: >= 85% coverage

- [ ] **Step 3: Run on a real Codex session file**

```bash
# Find a real session file
$real = Get-ChildItem -Path "$env:USERPROFILE\.codex\sessions" -Recurse -Filter "*.jsonl" | Select-Object -First 1
if ($real) {
    uv run python -m apotheosession --input $real.Directory.FullName --output ./converted/
}
```

Expected: Converts at least one real session to ./converted/

- [ ] **Step 4: Create .gitignore**

```bash
@"
__pycache__/
*.pyc
.venv/
converted/
.coverage
"@ | Out-File -FilePath .gitignore -Encoding utf8
```

- [ ] **Step 5: Commit**

```bash
git add .gitignore
git commit -m "chore: add .gitignore, finalize project"
```
