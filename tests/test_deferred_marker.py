"""Audit M-01: the 47 deferred experimental tests are listed explicitly (so nothing else can be skipped by accident)."""
from conftest import deferred_node_ids


def test_exactly_47_known_experimental_tests_are_deferred():
    ids = deferred_node_ids()
    assert len(ids) == 47
    assert all(i.startswith(("tests/test_eval_nemotron.py::", "tests/test_eval_openrouter.py::")) for i in ids)
