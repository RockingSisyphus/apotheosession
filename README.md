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
