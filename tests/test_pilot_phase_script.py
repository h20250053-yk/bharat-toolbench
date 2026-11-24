"""scripts/pilot_phase.py helpers (the driver itself starts Ollama runs and is exercised in the pilot phase, not here)."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("pilot_phase", Path(__file__).resolve().parent.parent / "scripts" / "pilot_phase.py")
pp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pp)

PS_GPU = "NAME    ID    SIZE    PROCESSOR    CONTEXT    UNTIL\ngemma4:26b    abc    21 GB    100% GPU    16384    9 minutes from now\n"
PS_SPLIT = "NAME    ID    SIZE    PROCESSOR    CONTEXT    UNTIL\ngemma4:26b    abc    27 GB    23%/77% CPU/GPU    16384    9 minutes from now\n"


def test_ps_parser():
    assert pp.ps_is_full_gpu(PS_GPU, "gemma4:26b") is True
    assert pp.ps_is_full_gpu(PS_SPLIT, "gemma4:26b") is False
    assert pp.ps_is_full_gpu(PS_GPU, "gpt-oss:20b") is None and pp.ps_is_full_gpu("", "x") is None


def test_pull_marker_names_are_filesystem_safe():
    assert pp.pull_marker_name("mistral-small3.2:24b") == "mistral-small3.2_24b.done" and pp.pull_marker_name("gpt-oss:20b") == "gpt-oss_20b.done"


def test_languages_and_run_order_constants():
    assert pp.LANGS == ["en", "hinglish", "hi", "mr", "gu"]
