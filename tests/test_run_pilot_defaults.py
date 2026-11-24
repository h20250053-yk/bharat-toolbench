"""Audit C-01: `run_pilot --split full` must default to all five languages (375 items), never silently 300."""
from evaluation import run_pilot
from evaluation.splits import ALL_LANGUAGES, MIDSEM_LANGUAGES, task_ids


def _items_line(capsys, argv):
    # --max-requests 0 stops before the first item: items are loaded and counted, no adapter is built, no model is called
    assert run_pilot.main(argv) == 0
    return next(l for l in capsys.readouterr().out.splitlines() if l.startswith("Model:"))


def test_full_split_defaults_to_375_items(tmp_path, capsys):
    line = _items_line(capsys, ["--model", "local_qwen25_3b", "--split", "full", "--run-file", str(tmp_path / "r.jsonl"), "--max-requests", "0"])
    assert "items: 375" in line and "gu" in line


def test_midsem_four_languages_still_selectable(tmp_path, capsys):
    line = _items_line(capsys, ["--model", "local_qwen25_3b", "--split", "midsem", "--languages", *MIDSEM_LANGUAGES,
                                "--run-file", str(tmp_path / "r.jsonl"), "--max-requests", "0"])
    assert "items: 200" in line


def test_language_constants():
    assert ALL_LANGUAGES == ["en", "hinglish", "hi", "mr", "gu"] and len(task_ids("full")) == 75


def test_model_choices_come_from_models_yaml(tmp_path, capsys):
    """Audit I-01: any key of config/models.yaml is accepted without editing run_pilot.py; unknown keys are rejected."""
    import pytest
    from agents.registry import load_model_config
    keys = load_model_config()
    assert {"local_qwen25_7b", "local_qwen25_14b", "local_llama31_8b"} <= set(keys)
    for k, model in (("local_qwen25_7b", "qwen2.5:7b"), ("local_qwen25_14b", "qwen2.5:14b"), ("local_llama31_8b", "llama3.1:8b")):
        assert keys[k]["model"] == model and keys[k]["provider"] == "ollama"
        assert run_pilot.main(["--model", k, "--split", "pilot", "--run-file", str(tmp_path / f"{k}.jsonl"), "--max-requests", "0"]) == 0
    with pytest.raises(SystemExit):
        run_pilot.main(["--model", "no_such_model", "--split", "pilot"])


def test_existing_run_file_needs_resume(tmp_path):
    """Audit M-07: a fresh run never silently appends to a non-empty run file."""
    import pytest
    f = tmp_path / "old.jsonl"
    old = '{"task_id": "T01_en", "model_key": "local_qwen25_3b", "status": "completed"}\n'
    f.write_text(old, encoding="utf-8")
    with pytest.raises(SystemExit):
        run_pilot.main(["--model", "local_qwen25_3b", "--split", "pilot", "--run-file", str(f), "--max-requests", "0"])
    assert f.read_text(encoding="utf-8") == old
    assert run_pilot.main(["--model", "local_qwen25_3b", "--split", "pilot", "--run-file", str(f), "--resume", "--max-requests", "0"]) == 0
