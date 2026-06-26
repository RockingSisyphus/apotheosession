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
    parser.add_argument(
        "--provider",
        default="deepseek",
        help="Provider ID for all messages (default: deepseek). Codex providers (ccswitch, custom) are unavailable in opencode.",
    )
    parser.add_argument(
        "--model",
        default="deepseek-v4-pro",
        help="Model ID for all messages (default: deepseek-v4-pro). Must be available under the configured provider.",
    )
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

        result = convert_file(filepath, provider=args.provider, model_id=args.model)
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
