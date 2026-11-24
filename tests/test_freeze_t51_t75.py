"""Audit M-08/M-09: T51-T75 are frozen like T01-T50 (spec, gold, rows 51-75 of five languages, audits); version 2.0.0."""
import json
import shutil

import pytest
import yaml

from benchmark import validate_tasks as vt
from benchmark.build_gold import GOLD_PATH, SPEC_PATH

GOLD = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
LANGS5 = ["en", "hinglish", "hi", "mr", "gu"]


def freeze_errors(gold=GOLD):
    errors: list[str] = []
    vt.validate_t51_t75_freeze(gold, errors)
    return errors


@pytest.fixture()
def lang_copy(tmp_path, monkeypatch):
    for l in LANGS5:
        shutil.copy(vt.LANG_DIR / f"{l}.jsonl", tmp_path / f"{l}.jsonl")
    monkeypatch.setattr(vt, "LANG_DIR", tmp_path)
    return tmp_path


def edit_row(path, line_no, **changes):
    lines = path.read_text(encoding="utf-8").splitlines()
    row = json.loads(lines[line_no])
    row.update(changes)
    lines[line_no] = json.dumps(row, ensure_ascii=False)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_current_data_matches_the_freeze_and_the_ids_are_t51_to_t75():
    assert freeze_errors() == [] and vt.FROZEN_T51_T75_IDS[0] == "T51" and vt.FROZEN_T51_T75_IDS[-1] == "T75" and len(vt.FROZEN_T51_T75_IDS) == 25


def test_full_validator_still_valid():
    assert vt.validate() == []


@pytest.mark.parametrize("lang", LANGS5)
def test_editing_a_t51_t75_query_in_any_language_is_caught(lang, lang_copy):
    edit_row(lang_copy / f"{lang}.jsonl", 60, query="changed text")  # line 61 = T61
    assert f"{lang}.jsonl rows T51-T75 changed (frozen)" in freeze_errors()


@pytest.mark.parametrize("lang", LANGS5)
def test_editing_the_first_and_last_frozen_rows_is_caught(lang, lang_copy):
    for idx in (50, 74):  # T51 and T75
        shutil.copy(lang_copy / f"{lang}.jsonl", lang_copy / "x.bak")
        edit_row(lang_copy / f"{lang}.jsonl", idx, query="x")
        assert f"{lang}.jsonl rows T51-T75 changed (frozen)" in freeze_errors()
        shutil.copy(lang_copy / "x.bak", lang_copy / f"{lang}.jsonl")


def test_recording_a_human_review_or_editing_t01_t50_does_not_change_the_t51_t75_freeze(lang_copy):
    edit_row(lang_copy / "hi.jsonl", 60, reviewer="Someone", review_status="reviewed")  # review fields are reset before hashing
    edit_row(lang_copy / "hi.jsonl", 10, query="a T11 edit is the business of the T01-T50 freeze, not this one")
    assert freeze_errors() == []


def test_gold_or_spec_change_is_caught(monkeypatch):
    tampered = json.loads(json.dumps(GOLD))
    tampered["T60"]["min_calls"] += 1
    assert "T51-T75 gold changed (frozen)" in freeze_errors(tampered)
    monkeypatch.setattr(vt, "FROZEN_T51_T75_SPEC_SHA256", "0" * 64)
    assert "T51-T75 specs changed (frozen)" in freeze_errors()


def test_audit_files_are_frozen(tmp_path, monkeypatch):
    for name, attr, label in (("batch_T51_T75_language_audit.json", "BATCH4_AUDIT_PATH", "T51-T75 audit file"),
                              ("batch_gu_T51_T75_language_audit.json", "GU2_AUDIT_PATH", "Gujarati T51-T75 audit file")):
        copy = tmp_path / name
        copy.write_bytes((vt.LANG_DIR / name).read_bytes() + b" ")
        monkeypatch.setattr(vt, attr, copy)
        assert f"{label} changed (frozen)" in freeze_errors()
        monkeypatch.undo()


def test_t01_t50_freeze_is_untouched():
    assert vt._sha({t: GOLD[t] for t in vt.FROZEN_T01_T50_IDS}) == vt.FROZEN_T01_T50_GOLD_SHA256


def test_benchmark_version_2_1_0_everywhere():
    cfg = yaml.safe_load((vt.LANG_DIR.parent.parent / "config" / "benchmark.yaml").read_text(encoding="utf-8"))
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    assert cfg["benchmark_version"] == spec["benchmark_version"] == GOLD["_meta"]["benchmark_version"] == "2.1.0"
