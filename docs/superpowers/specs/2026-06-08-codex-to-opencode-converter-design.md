# Codex-to-OpenCode Session Converter — Design Spec

**Date:** 2026-06-08
**Status:** Approved design

## Problem

Codex CLI stores session history as `.jsonl` (JSON Lines) files under `~/.codex/sessions/YYYY/MM/DD/`. OpenCode uses a different JSON schema for its `export`/`import` commands. No bridge tool exists. Need a Python script that scans Codex session files recursively and converts each into an OpenCode-importable JSON file.

## Approach

**Sequential State Machine** (Approval: Approach 1). Single-pass processing of the event stream with a lightweight state tracker. Zero external dependencies (stdlib only).

## CLI Interface

```
python -m apotheosession [--input DIR] [--output DIR] [--flatten] [--dry-run]

  --input DIR     Source directory (default: ~/.codex/sessions/)
  --output DIR    Output directory (default: ./converted/)
  --flatten       Write all .json files flat instead of mirroring YYYY/MM/DD/
  --dry-run       Show what would be converted without writing
```

Entry point: `main.py` (module `apotheosession`).

## Scanning Logic

1. Walk `--input` recursively, collect all `*.jsonl` files.
2. For each file:
   - Read first line — must parse as `session_meta` event; skip if not.
   - Extract session date from `payload.timestamp` (ISO8601).
   - Run converter → produce OpenCode JSON dict.
   - Write to `--output/<YYYY>/<MM>/<DD>/<slug>.json`.
3. Skipped: empty files, non-JSONL, invalid first line.
4. Slug: `codex-<YYYY-MM-DD>-<first-8-of-session-uuid>`.

## State Machine

### States

```
IDLE → IN_TURN → USER_MSG → AGENT_MSG → TOOL_WAITING → TURN_END → IDLE
```

- **IDLE**: Before first turn or between turns. Reading session_meta.
- **IN_TURN**: `task_started` received, scanning for user/assistant messages.
- **USER_MSG**: Built a user message, awaiting assistant response.
- **AGENT_MSG**: Built assistant message parts (text, reasoning), tracking tool calls.
- **TOOL_WAITING**: Awaiting function_call_output / exec_command_end / patch_apply_end to complete a pending tool.
- **TURN_END**: `task_complete` or `turn_aborted` received. Finalize and close.

### Transitions

| Codex Event | Transition | Action |
|---|---|---|
| `session_meta` | → IDLE | Populate `info.title`, `info.time`, `info.directory`, `info.model` |
| `turn_context` | stay | Store model info, permissions (metadata only) |
| `task_started` | IDLE → IN_TURN | Open a new turn |
| `response_item: message(role=user)` | any → USER_MSG | Create new user `Message`; skip environment-context XML |
| `response_item: message(role=assistant)` | USER_MSG → AGENT_MSG | Create assistant `Message` with `parentID` to previous user msg |
| `response_item: reasoning` | AGENT_MSG | Add `reasoning` part (placeholder text) to current assistant msg |
| `response_item: function_call` | AGENT_MSG → TOOL_WAITING | Add `tool` part (status=pending) |
| `response_item: function_call_output` | TOOL_WAITING | Update matching pending tool with output |
| `event_msg: exec_command_end` | TOOL_WAITING | Update matching tool with stdout/stderr/exit_code, set completed |
| `response_item: custom_tool_call` | AGENT_MSG → TOOL_WAITING | Add `tool` part (status=completed if already finished) |
| `event_msg: patch_apply_end` | TOOL_WAITING | Add `file` or `patch` part with changes/diffs |
| `event_msg: token_count` | AGENT_MSG / TOOL_WAITING | Add `step-finish` part with token/cost info |
| `event_msg: error` | any | Add error metadata to current message or tool |
| `task_complete` / `turn_aborted` | any → TURN_END → IDLE | Finalize assistant msg, pop turn; on abort, add error note |

## Event → OpenCode Mapping

### `info` (session metadata)

| Field | Source |
|---|---|
| `id` | `ses_<random-uuid4>` |
| `slug` | `codex-<first-8-of-uuid>` |
| `projectID` | `"global"` |
| `directory` | `session_meta.payload.cwd` |
| `title` | First user message excerpt (≤60 chars) + date; fallback `"Codex Session <date>"` |
| `version` | `"local"` |
| `time.created` | `session_meta.payload.timestamp` → unix ms |
| `time.updated` | Last event timestamp → unix ms |
| `model.providerID` | `session_meta.payload.model_provider` |
| `model.id` | `turn_context.payload.model` (first occurrence) |
| `agent` | `"codex"` |

### User messages

| Codex Event → | OpenCode |
|---|---|
| `response_item: message(role=user)` with text content (non-environment-context) | `{info: {role:"user", time:{created}}, parts: [{type:"text", text:"..."}]}` |

Filter out: messages whose text contains `<environment_context>` or `<InstructionsForCodex>` blocks (these are Codex internal/system injections, not user speech).

### Assistant messages

| Codex Event → | OpenCode |
|---|---|
| `response_item: message(role=assistant)` | `{info: {role:"assistant", parentID, time:{created, completed}}, parts: [...]}` |
| `response_item: reasoning` | `{type:"reasoning", text:"[Reasoning encrypted — not available in export]"}` |
| `event_msg: agent_message` | Skipped (redundant with response_item) |

### Tool calls

| Codex Event → | OpenCode Part |
|---|---|
| `function_call(name=shell_command)` | `{type:"tool", callID, tool:"bash", state:{status:"pending", raw:arguments}}` |
| `exec_command_end` | Update tool: `state.status="completed"`, set `input.command`, `output` (stdout+stderr merged), `title`, `time.start`/`end` |
| `function_call_output` | Merge output into matching pending tool |
| `custom_tool_call(name=apply_patch)` | `{type:"tool", callID, tool:"apply_patch", state:{status:"completed", input, output}}` |
| `patch_apply_end` | Add `{type:"file"}` or `{type:"patch"}` part with file changes |
| `error` event_msg | Set `tool.state.status="error"` + error message |

### Lifecycle events

| Codex Event → | OpenCode Part |
|---|---|
| `token_count` | `{type:"step-finish", tokens:{input, output, reasoning, cache, total}}` |
| `task_complete` | Set `time.completed` on last assistant message |
| `turn_aborted` | Finalize with error note, `finish:"error"` on message |

### Filtering rules

Events that are **skipped entirely**:
- `turn_context` (metadata already captured; permissions/sandbox are Codex-internal)
- `event_msg: user_message` (redundant — text already in response_item)
- `event_msg: agent_message` (redundant — text already in response_item)
- `event_msg: task_started` / `task_complete` (used for state transitions, not output)
- Environment-context XML messages (Codex internal)
- `response_item: message(role=developer)` (system prompt injection)

### ID generation

- Session ID: `ses_<uuid4-hex>` (random, fresh)
- Message IDs: `msg_<uuid4-hex>` per message
- Part IDs: `prt_<uuid4-hex>` per part
- Call IDs: reuse the Codex `call_id` as-is (they're already unique strings)
- Original Codex IDs stored in `metadata.codex_id` field on messages/parts

## Output File Organization

```
converted/
  2026/
    05/
      23/
        codex-2026-05-23-019e5464.json
        codex-2026-05-23-019dc997.json
    06/
      08/
        codex-2026-06-08-abc12345.json
```

With `--flatten`:
```
converted/
  codex-2026-05-23-019e5464.json
  codex-2026-05-23-019dc997.json
  codex-2026-06-08-abc12345.json
```

## Edge Case Handling

1. **Aborted turns** (`turn_aborted`): Close the turn, set `finish:"error"` on the last assistant message, include reason.
2. **Multiple tool calls per turn**: `TOOL_WAITING` maintains a `dict[call_id, ToolPart]`. Each output resolves its matching call by `call_id`. Turn advances when all pending tools resolve.
3. **No `task_complete`** (incomplete session at end of file): Finalize whichever state we're in, close any open messages.
4. **Corrupted lines**: Skip individual unparseable lines; emit warning to stderr; continue processing.
5. **Empty session** (only `session_meta`, no turns): Skip file (no messages to convert).
6. **Reasoning-only responses**: Attach reasoning part to a minimal assistant message with placeholder text.
7. **Very long lines** (>100KB): JSONL format handles these natively; Python's `json.loads` handles them fine.
8. **Multiple sessions in one run**: Batch scanning handles them independently.
9. **File already exists in output**: Overwrite by default (idempotent conversion).
10. **Encrypted reasoning**: Placeholder text, not decrypted.

## File Structure

```
apotheosession/
  __init__.py          # empty
  __main__.py          # python -m apotheosession entry
  main.py              # CLI entry, arg parsing, scanner orchestration
  converter.py         # Converter class — state machine + mapping logic
  models.py            # Dataclasses for CodexEvent, SessionMeta, Message, Part, etc.
  opencode_schema.py   # OpenCode JSON builder helpers
  filters.py           # Message filtering (skip env-context, developer msgs, etc.)
```

## Implementation

- **Language**: Python 3.10+ (no dependencies beyond stdlib)
- **Testing**: `pytest`; test with real anonymized .jsonl fixtures (small samples extracted from actual sessions)
- **Idempotent**: Re-running on same input produces identical output

## Future Considerations

- Support for other Codex export formats (if OpenAI adds plaintext reasoning export)
- Incremental conversion (track last-modified timestamps)
- Direct integration with `opencode import` via pipe or subprocess
