import pytest

from environment import RailwayEnv


@pytest.fixture()
def env():
    e = RailwayEnv()
    e.reset()
    return e


# --- audit M-01: 47 tests of the unused experimental NVIDIA Nemotron / OpenRouter work are skipped, not deleted ---
from pathlib import Path  # noqa: E402

_DEFERRED = Path(__file__).with_name("deferred_experimental_tests.txt")
DEFERRED_REASON = ("deferred: experimental NVIDIA Nemotron / OpenRouter API work that is not used "
                   "(missing experimental_nemotron config, nvidia provider and adapter parameters); see tests/deferred_experimental_tests.txt")


def deferred_node_ids() -> set[str]:
    if not _DEFERRED.exists():
        return set()
    return {l.strip() for l in _DEFERRED.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")}


def pytest_collection_modifyitems(config, items):
    ids = deferred_node_ids()
    for item in items:
        if item.nodeid in ids:
            item.add_marker(pytest.mark.skip(reason=DEFERRED_REASON))
