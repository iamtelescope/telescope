"""Acceptance 4: v1/v2 tile configs produce the same SQL and responses as before chart engine v2."""

import json
from pathlib import Path

import pytest

from tests.fetchers.v1_matrix import cases, run_case

GOLDEN = json.loads((Path(__file__).parent / "v1_chart_golden.json").read_text())


@pytest.mark.parametrize("name,case", list(cases()), ids=[n for n, _ in cases()])
def test_v1_chart_unchanged(name, case):
    assert run_case(case) == GOLDEN[name]
