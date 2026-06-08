# Apotheosession

Convert Codex CLI session files (`.jsonl`) to OpenCode import format (`.json`).

## Usage

```bash
# Convert all sessions from ~/.codex/sessions/
uv run apotheosession

# Flat output (all files in ./converted/ instead of YYYY/MM/DD/)
uv run apotheosession --flatten

# Custom directories
uv run apotheosession --input ~/.codex/sessions/ --output ./output/

# Preview without writing
uv run apotheosession --dry-run
```

Then import into OpenCode (run from the target project directory):

```bash
cd /path/to/project
opencode import /path/to/converted/codex-2026-05-23-abc12345.json
```

## How it works

Reads Codex `.jsonl` session files, parses the event stream (`session_meta`, `response_item`, `event_msg`), and reconstructs an OpenCode-format JSON with messages, tool calls, file patches, reasoning blocks, and token usage.

Session ID is derived from the Codex UUID (deterministic across runs). The `directory` field preserves Codex's original working directory.

## Known limitations

- Reasoning content from OpenAI is AES-256-GCM encrypted server-side — cannot be decrypted locally; a placeholder is inserted
- `opencode import` always assigns the session to the project where you run the command, regardless of the `directory` field in the JSON
- No native dependency (stdlib only)

## Development

```bash
uv sync
uv run pytest
uv run pytest --cov=apotheosession
```
