import json
import os
import tempfile
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


def test_scan_directory_finds_jsonl():
    tmp = tempfile.mkdtemp()
    try:
        sub = Path(tmp) / "2026" / "05" / "23"
        sub.mkdir(parents=True)
        f = sub / "rollout-2026-05-23T10-00-00-test.jsonl"
        f.write_text('{"timestamp":"2026-05-23T10:00:00Z","type":"session_meta","payload":{"id":"abc","timestamp":"2026-05-23T10:00:00Z","cwd":"/tmp","originator":"codex-tui","cli_version":"0.125.0","source":"cli","model_provider":"openai","base_instructions":{"text":"test"}}}\n')
        results = scan_directory(tmp)
        assert len(results) == 1
        assert results[0][0].endswith(".jsonl")
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


def test_scan_directory_skips_non_jsonl():
    tmp = tempfile.mkdtemp()
    try:
        (Path(tmp) / "readme.txt").write_text("hello")
        results = scan_directory(tmp)
        assert results == []
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


def test_write_output():
    tmp = tempfile.mkdtemp()
    try:
        data = {"info": {"title": "test"}, "messages": []}
        path = write_output(data, tmp, "2026", "05", "23", "test-slug")
        assert path.exists()
        with open(path) as f:
            assert json.load(f)["info"]["title"] == "test"
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


def test_write_output_flatten():
    tmp = tempfile.mkdtemp()
    try:
        data = {"info": {"title": "test"}, "messages": []}
        path = write_output(data, tmp, "2026", "05", "23", "test-slug", flatten=True)
        assert path.exists()
        assert "2026" not in str(path)
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
