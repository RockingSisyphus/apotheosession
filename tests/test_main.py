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
